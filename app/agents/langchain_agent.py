import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import BaseModel, Field, create_model

from ..services.llm import get_openai_model
from ..services.persistence.conversation_persistence import (
    get_recent_messages,
    save_message,
)
from ..services.persistence.memory_persistence import (
    format_user_memories,
    save_user_memory,
)
from .finance import create_finance_agent
from .general import create_general_agent
from .prompts import AGENT_SYSTEM_PROMPT
from .reminder import create_reminder_agent
from .supervisor import run_supervisor

logger = logging.getLogger(__name__)


class LangChainAgentRouter:
    """
    Router based on LangChain acting as a multiserver client for the Model Context Protocol (MCP).
    Connects to multiple independent tool servers simultaneously,
    discovers their capabilities dynamically, and exposes the tools to LangChain as StructuredTools.
    """

    def __init__(self):
        self.memory = MemorySaver()

        mcp_servers_env = os.getenv(
            "MCP_SERVERS",
            "http://localhost:8002/sse/,http://localhost:8003/sse/",
        )

        self.mcp_servers = []
        for url in mcp_servers_env.split(","):
            url = url.strip()
            if not url:
                continue
            if url.endswith("/sse"):
                url = url + "/"
            self.mcp_servers.append(url)

        self.mcp_server_url = (
            self.mcp_servers[0]
            if self.mcp_servers
            else "http://localhost:8002/sse/"
        )

        logger.info(
            "LangChainAgentRouter initialized with MCP servers: %s",
            self.mcp_servers,
        )

        self.stack = None
        self.sessions = []
        self._cached_tools = {}

    async def get_sessions(self) -> list[tuple[str, ClientSession]]:
        if not self.stack:
            self.stack = AsyncExitStack()

        active_urls = {url for url, _ in self.sessions}

        for url in self.mcp_servers:
            if url not in active_urls:
                logger.info("Attempting persistent connection to MCP server: %s", url)

                try:
                    read_stream, write_stream = await self.stack.enter_async_context(
                        sse_client(url)
                    )
                    session = await self.stack.enter_async_context(
                        ClientSession(read_stream, write_stream)
                    )
                    await session.initialize()

                    self.sessions.append((url, session))
                    logger.info("Persistent MCP connection established with: %s", url)

                except Exception as e:
                    logger.warning(
                        "Persistent connection failed with MCP server at %s: %s",
                        url,
                        e,
                    )

        return self.sessions

    async def stop(self):
        if self.stack:
            logger.info("Stopping persistent connections for LangChainAgentRouter...")

            try:
                await self.stack.aclose()
            except Exception as e:
                logger.warning("Error closing connection stack: %s", e)

            self.stack = None
            self.sessions = []
            self._cached_tools = {}

            logger.info("Persistent connections for LangChainAgentRouter closed.")

    def _extract_message(self, output: Any) -> str:
        if isinstance(output, str):
            try:
                parsed = json.loads(output)
                return parsed.get("message") or parsed.get("answer") or output
            except json.JSONDecodeError:
                return output

        if isinstance(output, dict):
            return (
                output.get("message")
                or output.get("answer")
                or output.get("query")
                or json.dumps(output, ensure_ascii=False)
            )

        return str(output)

    def _json_schema_to_pydantic_fields(self, schema: dict) -> dict:
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        fields = {}

        for name, prop in properties.items():
            type_str = prop.get("type", "string")
            description = prop.get("description", "")

            if type_str == "string":
                py_type = str
            elif type_str == "number":
                py_type = float
            elif type_str == "integer":
                py_type = int
            elif type_str == "boolean":
                py_type = bool
            elif type_str == "array":
                py_type = list
            elif type_str == "object":
                py_type = dict
            else:
                py_type = Any

            if name in required:
                fields[name] = (py_type, Field(description=description))
            else:
                fields[name] = (
                    Optional[py_type],
                    Field(default=None, description=description),
                )

        return fields

    def _get_local_tools(self) -> list[StructuredTool]:
        try:
            from .tools import get_agent_tools

            local_tools = get_agent_tools()
            logger.info("Adding agent local tools: %s", [t.name for t in local_tools])
            return local_tools

        except Exception as e:
            logger.debug("Failed to load agent local tools: %s", e)
            return []

    async def _discover_mcp_tools(
        self,
        sessions: list[tuple[str, ClientSession]],
    ) -> list[StructuredTool]:
        if not hasattr(self, "_cached_tools"):
            self._cached_tools = {}

        langchain_tools = []

        for url, session in sessions:
            if url in self._cached_tools:
                logger.debug("Using cached tools for MCP server %s", url)
                langchain_tools.extend(self._cached_tools[url])
                continue

            try:
                mcp_tools_list = await session.list_tools()
                logger.info(
                    "Discovered catalog from MCP server %s: %s",
                    url,
                    [t.name for t in mcp_tools_list.tools],
                )

                server_tools = []

                for mcp_tool in mcp_tools_list.tools:
                    fields = self._json_schema_to_pydantic_fields(
                        mcp_tool.inputSchema
                    )
                    model_name = (
                        "".join(c for c in mcp_tool.name if c.isalnum()).capitalize()
                        + "Schema"
                    )

                    if fields:
                        PydanticModelClass = create_model(model_name, **fields)
                    else:

                        class EmptySchema(BaseModel):
                            pass

                        PydanticModelClass = EmptySchema

                    def make_call_closure(tool_name=mcp_tool.name, server_url=url):
                        async def make_tool_call(**kwargs) -> str:
                            clean_kwargs = {
                                k: v for k, v in kwargs.items() if v is not None
                            }

                            logger.info(
                                "Remote invocation of MCP tool '%s' with arguments: %s",
                                tool_name,
                                clean_kwargs,
                            )

                            active_session = None

                            for u, s in self.sessions:
                                if u == server_url:
                                    active_session = s
                                    break

                            if not active_session:
                                logger.info(
                                    "Session for %s not found. Reconnecting...",
                                    server_url,
                                )

                                await self.get_sessions()

                                for u, s in self.sessions:
                                    if u == server_url:
                                        active_session = s
                                        break

                            if not active_session:
                                return (
                                    f"Error: The MCP server at {server_url} "
                                    f"is currently unavailable."
                                )

                            try:
                                resp = await active_session.call_tool(
                                    tool_name,
                                    clean_kwargs,
                                )

                            except Exception as e:
                                logger.error(
                                    "Error invoking remote tool '%s' on %s: %s",
                                    tool_name,
                                    server_url,
                                    e,
                                )

                                self.sessions = [
                                    (u, s)
                                    for u, s in self.sessions
                                    if u != server_url
                                ]

                                if server_url in self._cached_tools:
                                    del self._cached_tools[server_url]

                                return (
                                    f"Error executing tool '{tool_name}' "
                                    f"(lost connection with {server_url})."
                                )

                            if resp.content and len(resp.content) > 0:
                                logger.debug(
                                    "Tool '%s' responded with: %s",
                                    tool_name,
                                    resp.content[0].text,
                                )
                                return resp.content[0].text

                            return (
                                f"Error: Did not receive response content "
                                f"for '{tool_name}'"
                            )

                        return make_tool_call

                    server_tools.append(
                        StructuredTool(
                            name=mcp_tool.name,
                            description=mcp_tool.description,
                            coroutine=make_call_closure(),
                            func=lambda **kwargs: "",
                            args_schema=PydanticModelClass,
                        )
                    )

                self._cached_tools[url] = server_tools
                langchain_tools.extend(server_tools)

            except Exception as e:
                logger.warning(
                    "Error listing tools for %s: %s. Removing session.",
                    url,
                    e,
                )

                self.sessions = [(u, s) for u, s in self.sessions if u != url]

                if url in self._cached_tools:
                    del self._cached_tools[url]

        return langchain_tools

    async def _prune_history_if_needed(
        self,
        temp_agent,
        config: dict,
        thread_id: str,
    ) -> None:
        try:
            state = await temp_agent.aget_state(config)

            if state and "messages" in state.values:
                current_messages = state.values["messages"]

                human_indices = [
                    i
                    for i, msg in enumerate(current_messages)
                    if isinstance(msg, HumanMessage)
                    or getattr(msg, "type", None) == "human"
                ]

                max_turns = 3

                if len(human_indices) > max_turns:
                    keep_from_idx = human_indices[-max_turns]
                    messages_to_remove = current_messages[:keep_from_idx]

                    removals = [
                        RemoveMessage(id=msg.id)
                        for msg in messages_to_remove
                        if getattr(msg, "id", None)
                    ]

                    if removals:
                        logger.info(
                            "Pruning complete turns: removing %d old messages "
                            "in thread '%s'",
                            len(removals),
                            thread_id,
                        )

                        await temp_agent.aupdate_state(
                            config,
                            {"messages": removals},
                            as_node="model",
                        )

        except Exception as e:
            logger.warning(
                "Could not perform turn pruning in thread '%s': %s",
                thread_id,
                e,
                exc_info=True,
            )

    async def _get_clean_history(self, temp_agent, config: dict) -> list:
        history = []

        try:
            state = await temp_agent.aget_state(config)

            if state and "messages" in state.values:
                raw_messages = state.values["messages"]

                logger.info(
                    "Filtering history for Supervisor. Total raw messages: %d",
                    len(raw_messages),
                )

                for msg in raw_messages:
                    msg_type = getattr(msg, "type", None)

                    if msg_type in ["human", "ai"]:
                        has_tool_calls = (
                            (hasattr(msg, "tool_calls") and msg.tool_calls)
                            or (
                                hasattr(msg, "additional_kwargs")
                                and "tool_calls" in msg.additional_kwargs
                            )
                        )

                        if has_tool_calls:
                            continue

                        content_str = str(getattr(msg, "content", ""))

                        if "[ROUTE:" in content_str:
                            continue

                        history.append(msg)

            logger.info(
                "Clean history for Supervisor compiled. Final messages: %d",
                len(history),
            )

        except Exception as e:
            logger.error(
                "Could not read or clean history for Supervisor: %s",
                e,
                exc_info=True,
            )

        return history

    def _get_persistent_history(self, thread_id: str, limit: int = 20) -> list:
        persistent_messages = []

        try:
            rows = get_recent_messages(thread_id, limit=limit)

            for row in rows:
                role = row.get("role")
                content = row.get("content")

                if not content:
                    continue

                if role == "user":
                    persistent_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    persistent_messages.append(AIMessage(content=content))

            logger.info(
                "Loaded %d persistent memory messages for thread '%s'",
                len(persistent_messages),
                thread_id,
            )

        except Exception as e:
            logger.warning(
                "Could not load persistent memory for thread '%s': %s",
                thread_id,
                e,
                exc_info=True,
            )

        return persistent_messages

    def _format_persistent_memory(self, thread_id: str, limit: int = 20) -> str:
        try:
            rows = get_recent_messages(thread_id, limit=limit)

            if not rows:
                return ""

            lines = []

            for row in rows:
                role = row.get("role")
                content = row.get("content")

                if content:
                    lines.append(f"{role}: {content}")

            return "\n".join(lines)

        except Exception as e:
            logger.warning(
                "Could not format persistent memory for thread '%s': %s",
                thread_id,
                e,
                exc_info=True,
            )
            return ""

    def _detect_memory_to_save(self, message: str) -> tuple[str, str, str] | None:
        """
        Detects simple long-term travel preferences from declarative user messages.
        Returns (memory_key, memory_value, category) or None.
        """
        clean_message = message.strip()
        lower_message = clean_message.lower()

        # Do not save questions as memories
        question_markers = ["?", "¿", "cual", "cuál", "que ", "qué ", "como ", "cómo "]
        if any(marker in lower_message for marker in question_markers):
            return None

        if "mi aeropuerto favorito" in lower_message and " es " in lower_message:
            value = clean_message.split(" es ", 1)[1].strip().rstrip(".")
            return ("favorite_airport", value, "travel_preference")

        if "mi presupuesto" in lower_message and " es " in lower_message:
            value = clean_message.split(" es ", 1)[1].strip().rstrip(".")
            return ("budget_preference", value, "travel_preference")

        if "prefiero viajar" in lower_message:
            value = clean_message.split("prefiero viajar", 1)[1].strip().rstrip(".")
            return ("travel_style", value, "travel_preference")

        return None

    def _save_long_term_memory_if_needed(self, thread_id: str, message: str) -> None:
        try:
            detected_memory = self._detect_memory_to_save(message)

            if detected_memory:
                memory_key, memory_value, category = detected_memory
                save_user_memory(thread_id, memory_key, memory_value, category)

                logger.info(
                    "Saved long-term memory for thread '%s': %s=%s",
                    thread_id,
                    memory_key,
                    memory_value,
                )

        except Exception as e:
            logger.warning(
                "Could not persist long-term memory: %s",
                e,
                exc_info=True,
            )

    def _build_memory_context_for_agent(
        self,
        thread_id: str,
        short_term_memory_text: str,
        long_term_memory_text: str,
        message: str,
    ) -> str:
        context_parts = []

        if long_term_memory_text:
            context_parts.append(
                "Long-term user memory:\n"
                f"{long_term_memory_text}"
            )

        if short_term_memory_text:
            context_parts.append(
                "Previous conversation memory for this thread:\n"
                f"{short_term_memory_text}"
            )

        if not context_parts:
            return message

        return (
            "\n\n".join(context_parts)
            + "\n\nCurrent user message:\n"
            + message
        )

    @traceable(name="run_specialized_agent")
    async def _run_specialized_agent(
        self,
        llm: ChatOpenAI,
        route: str,
        message: str,
        config: dict,
        langchain_tools: list,
        local_tools: list,
    ) -> tuple[Any, str]:
        if route == "finance":
            specialized_agent = create_finance_agent(
                llm,
                langchain_tools,
                self.memory,
            )

        elif route == "reminder":
            specialized_agent = create_reminder_agent(
                llm,
                langchain_tools,
                self.memory,
            )

        elif route == "general":
            specialized_agent = create_general_agent(
                llm,
                local_tools,
                self.memory,
            )

        else:
            logger.warning("Unknown route '%s', using fallback agent", route)

            specialized_agent = create_agent(
                llm,
                langchain_tools + local_tools,
                system_prompt=AGENT_SYSTEM_PROMPT,
                checkpointer=self.memory,
                debug=False,
            )

        agent_response = await specialized_agent.ainvoke(
            {"input": message},
            config=config,
        )

        messages = agent_response.get("messages", [])
        output = ""

        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                output = msg.content
                break

        if not output and messages:
            output = (
                messages[-1].content
                if hasattr(messages[-1], "content")
                else str(messages[-1])
            )

        elif not output:
            output = agent_response.get("output", str(agent_response))

        return agent_response, output

    @traceable(name="travel_assistant_handle_message")
    async def handle_message(
        self,
        message: str,
        thread_id: str = "default",
    ) -> dict[str, Any]:
        logger.info(
            "Agent receives message: '%s' (thread: '%s')",
            message,
            thread_id,
        )

        try:
            sessions = await self.get_sessions()

            langchain_tools = await self._discover_mcp_tools(sessions)
            local_tools = self._get_local_tools()

            llm = ChatOpenAI(
                model_name=get_openai_model(),
                temperature=0.0,
            )

            config = {"configurable": {"thread_id": thread_id}}

            temp_agent = create_agent(
                llm,
                [],
                system_prompt="",
                checkpointer=self.memory,
            )

            await self._prune_history_if_needed(temp_agent, config, thread_id)

            history = await self._get_clean_history(temp_agent, config)

            persistent_history = self._get_persistent_history(
                thread_id,
                limit=20,
            )

            if persistent_history:
                history = persistent_history

            long_term_memory_text = format_user_memories(thread_id)

            message_for_supervisor = self._build_memory_context_for_agent(
                thread_id=thread_id,
                short_term_memory_text="",
                long_term_memory_text=long_term_memory_text,
                message=message,
            )

            route, supervisor_text = await run_supervisor(
                llm,
                history,
                message_for_supervisor,
            )

            if not route:
                logger.info("Supervisor assumes direct interaction.")

                final_message = self._extract_message(supervisor_text)

                try:
                    save_message(thread_id, "user", message)
                    save_message(thread_id, "assistant", final_message)
                except Exception as e:
                    logger.warning(
                        "Could not persist supervisor conversation: %s",
                        e,
                        exc_info=True,
                    )

                self._save_long_term_memory_if_needed(thread_id, message)

                return {
                    "llm_used": True,
                    "llm_tool": "supervisor_chat",
                    "agent_used": "supervisor",
                    "tool_response": None,
                    "message": final_message,
                }

            logger.info("Routing request to specialized sub-agent: '%s'", route)

            short_term_memory_text = self._format_persistent_memory(
                thread_id,
                limit=20,
            )

            message_for_agent = self._build_memory_context_for_agent(
                thread_id=thread_id,
                short_term_memory_text=short_term_memory_text,
                long_term_memory_text=long_term_memory_text,
                message=message,
            )

            try:
                save_message(thread_id, "user", message)
            except Exception as e:
                logger.warning(
                    "Could not persist user message: %s",
                    e,
                    exc_info=True,
                )

            self._save_long_term_memory_if_needed(thread_id, message)

            agent_response, output = await self._run_specialized_agent(
                llm,
                route,
                message_for_agent,
                config,
                langchain_tools,
                local_tools,
            )

        except Exception as exc:
            logger.exception(
                "Exception during LangChainAgentRouter execution: %s",
                exc,
            )

            error_message = (
                f"Error connecting to MCP tool servers. "
                f"Please make sure independent servers are started: "
                f"{', '.join(self.mcp_servers)}. "
                f"(Technical detail: {str(exc)})"
            )

            try:
                save_message(thread_id, "assistant", error_message)
            except Exception:
                pass

            return {
                "llm_used": False,
                "llm_tool": None,
                "agent_used": "unknown",
                "tool_response": None,
                "message": error_message,
            }

        final_message = self._extract_message(output)

        try:
            save_message(thread_id, "assistant", final_message)
        except Exception as e:
            logger.warning(
                "Could not persist assistant message: %s",
                e,
                exc_info=True,
            )

        return {
            "llm_used": True,
            "llm_tool": "langchain_agent_via_mcp",
            "agent_used": route,
            "tool_response": agent_response,
            "message": final_message,
        }