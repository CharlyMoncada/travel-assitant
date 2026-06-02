import json
import logging
import os
from typing import Any, Optional
from contextlib import AsyncExitStack

from ..services.llm import get_openai_model
from langchain.agents import create_agent
from .prompts import AGENT_SYSTEM_PROMPT
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage
from pydantic import BaseModel, Field, create_model
from langsmith import traceable
from langchain.agents import create_agent

from mcp import ClientSession
from mcp.client.sse import sse_client

# Import specialized agents and supervisor from their dedicated packages
from .supervisor import run_supervisor
from .finance import create_finance_agent
from .reminder import create_reminder_agent
from .general import create_general_agent

logger = logging.getLogger(__name__)


class LangChainAgentRouter:
    """
    Router based on LangChain acting as a multiserver client for the Model Context Protocol (MCP).
    Connects to multiple independent tool servers simultaneously,
    discovers their capabilities dynamically, and exposes the tools to LangChain as StructuredTools.
    """
    def __init__(self):
        self.memory = MemorySaver()
        # Parse server URLs from environment variable or use ports 8002 and 8003 as defaults
        mcp_servers_env = os.getenv(
            "MCP_SERVERS", 
            "http://localhost:8002/sse/,http://localhost:8003/sse/"
        )
        
        # Normalize URLs to ensure they end with a trailing slash if ending with '/sse'
        # This prevents Starlette 307 redirects that block/hang the client
        self.mcp_servers = []
        for url in mcp_servers_env.split(","):
            url = url.strip()
            if not url:
                continue
            if url.endswith("/sse"):
                url = url + "/"
            self.mcp_servers.append(url)
            
        # Maintain backwards compatibility with references to mcp_server_url
        self.mcp_server_url = self.mcp_servers[0] if self.mcp_servers else "http://localhost:8002/sse/"
        logger.info("LangChainAgentRouter initialized with MCP servers: %s", self.mcp_servers)
        
        # Persistent resources initialization
        self.stack = None
        self.sessions = []
        self._cached_tools = {}

    async def get_sessions(self) -> list[tuple[str, ClientSession]]:
        """
        Returns active persistent sessions. If the stack is not initialized
        or there are disconnected servers, it attempts to (re)connect transparently.
        """
        if not self.stack:
            self.stack = AsyncExitStack()
            
        active_urls = {url for url, _ in self.sessions}
        for url in self.mcp_servers:
            if url not in active_urls:
                logger.info("Attempting persistent connection to MCP server: %s", url)
                try:
                    read_stream, write_stream = await self.stack.enter_async_context(sse_client(url))
                    session = await self.stack.enter_async_context(ClientSession(read_stream, write_stream))
                    await session.initialize()
                    self.sessions.append((url, session))
                    logger.info("Persistent MCP connection established with: %s", url)
                except Exception as e:
                    logger.warning("Persistent connection failed with MCP server at %s: %s", url, e)
        return self.sessions

    async def stop(self):
        """
        Gracefully closes all persistent connections with the MCP servers.
        """
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
                fields[name] = (Optional[py_type], Field(default=None, description=description))
                
        return fields

    def _get_local_tools(self) -> list[StructuredTool]:
        """
        Safely loads agent local tools.
        """
        try:
            from .tools import get_agent_tools
            local_tools = get_agent_tools()
            logger.info("Adding agent local tools: %s", [t.name for t in local_tools])
            return local_tools
        except Exception as e:
            logger.debug("Failed to load agent local tools: %s", e)
            return []

    async def _discover_mcp_tools(self, sessions: list[tuple[str, ClientSession]]) -> list[StructuredTool]:
        """
        Discovers the tool catalog of all active MCP sessions
        and converts them into LangChain StructuredTools. Uses a local cache
        to prevent discovery latency on each message.
        """
        if not hasattr(self, "_cached_tools"):
            self._cached_tools = {}
            
        langchain_tools = []
        for url, session in sessions:
            # If we already have cached tools for this URL, use them
            if url in self._cached_tools:
                logger.debug("Using cached tools for MCP server %s", url)
                langchain_tools.extend(self._cached_tools[url])
                continue
                
            try:
                mcp_tools_list = await session.list_tools()
                logger.info("Discovered catalog from MCP server %s: %s", url, [t.name for t in mcp_tools_list.tools])
                
                server_tools = []
                for mcp_tool in mcp_tools_list.tools:
                    # Convert JSON schema to Pydantic fields
                    fields = self._json_schema_to_pydantic_fields(mcp_tool.inputSchema)
                    model_name = "".join(c for c in mcp_tool.name if c.isalnum()).capitalize() + "Schema"
                    
                    if fields:
                        PydanticModelClass = create_model(model_name, **fields)
                    else:
                        class EmptySchema(BaseModel):
                            pass
                        PydanticModelClass = EmptySchema
                    
                    # Closure generator for tool call
                    def make_call_closure(tool_name=mcp_tool.name, server_url=url):
                        async def make_tool_call(**kwargs) -> str:
                            clean_kwargs = {k: v for k, v in kwargs.items() if v is not None}
                            logger.info("Remote invocation of MCP tool '%s' with filtered arguments: %s", tool_name, clean_kwargs)
                            
                            # Find the current active session for this URL
                            active_session = None
                            for u, s in self.sessions:
                                if u == server_url:
                                    active_session = s
                                    break
                                    
                            if not active_session:
                                # Attempt immediate reconnection
                                logger.info("Session for %s not found or inactive. Reconnecting...", server_url)
                                await self.get_sessions()
                                for u, s in self.sessions:
                                    if u == server_url:
                                        active_session = s
                                        break
                                        
                            if not active_session:
                                return f"Error: The MCP server at {server_url} is currently unavailable."
                                
                            try:
                                resp = await active_session.call_tool(tool_name, clean_kwargs)
                            except Exception as e:
                                logger.error("Error invoking remote tool '%s' on %s: %s. Removing session.", tool_name, server_url, e)
                                # Remove from active sessions list to force reconnection later
                                self.sessions = [(u, s) for u, s in self.sessions if u != server_url]
                                # Clear tool cache associated with this server
                                if server_url in self._cached_tools:
                                    del self._cached_tools[server_url]
                                return f"Error executing tool '{tool_name}' (lost connection with {server_url})."
                                
                            if resp.content and len(resp.content) > 0:
                                logger.debug("Tool '%s' responded with: %s", tool_name, resp.content[0].text)
                                return resp.content[0].text
                            return f"Error: Did not receive response content for '{tool_name}'"
                        return make_tool_call
                    
                    server_tools.append(
                        StructuredTool(
                            name=mcp_tool.name,
                            description=mcp_tool.description,
                            coroutine=make_call_closure(),
                            func=lambda **kwargs: "",  # synchronous fallback
                            args_schema=PydanticModelClass
                        )
                    )
                
                # Cache tools for this server
                self._cached_tools[url] = server_tools
                langchain_tools.extend(server_tools)
                
            except Exception as e:
                logger.warning("Error listing tools for %s: %s. Removing session.", url, e)
                # Remove from active sessions list
                self.sessions = [(u, s) for u, s in self.sessions if u != url]
                if url in self._cached_tools:
                    del self._cached_tools[url]
                
        return langchain_tools

    async def _prune_history_if_needed(self, temp_agent, config: dict, thread_id: str) -> None:
        """
        Prunes thread history keeping only complete user conversational turns
        to prevent orphaned ToolMessages.
        """
        try:
            state = await temp_agent.aget_state(config)
            if state and "messages" in state.values:
                current_messages = state.values["messages"]
                
                # Identify messages of type HumanMessage
                from langchain_core.messages import HumanMessage
                human_indices = [
                    i for i, msg in enumerate(current_messages) 
                    if isinstance(msg, HumanMessage) or getattr(msg, "type", None) == "human"
                ]
                
                max_turns = 3  # Keep the last 3 complete user conversational turns
                if len(human_indices) > max_turns:
                    # The index of the HumanMessage that starts the first turn we want to KEEP
                    keep_from_idx = human_indices[-max_turns]
                    messages_to_remove = current_messages[:keep_from_idx]
                    
                    removals = [
                        RemoveMessage(id=msg.id) 
                        for msg in messages_to_remove 
                        if getattr(msg, "id", None)
                    ]
                    
                    if removals:
                        logger.info(
                            "Pruning complete turns: Removing %d old messages in thread '%s' "
                            "(keeping the last %d complete user turns)", 
                            len(removals), 
                            thread_id,
                            max_turns
                        )
                        await temp_agent.aupdate_state(config, {"messages": removals}, as_node="model")
        except Exception as e:
            logger.warning("Could not perform turn pruning in thread '%s': %s", thread_id, e, exc_info=True)

    async def _get_clean_history(self, temp_agent, config: dict) -> list:
        """
        Gets clean conversational history (omitting internal routing messages
        and low-level tool executions) to feed the Supervisor.
        """
        history = []
        try:
            state = await temp_agent.aget_state(config)
            if state and "messages" in state.values:
                raw_messages = state.values["messages"]
                logger.info("Filtering history for the Supervisor. Total raw messages in checkpointer: %d", len(raw_messages))
                
                for idx, msg in enumerate(raw_messages):
                    msg_type = getattr(msg, "type", None)
                    msg_class = msg.__class__.__name__
                    
                    # Descriptive debug log for each message in the checkpointer
                    logger.debug("Message in checkpointer [%d]: class=%s, type=%s, id=%s", idx, msg_class, msg_type, getattr(msg, "id", None))
                    
                    # Only include explicit conversational messages (HumanMessage or AIMessage)
                    if msg_type in ["human", "ai"]:
                        # Strictly omit AIMessages with tool calls (function calling)
                        has_tool_calls = (
                            (hasattr(msg, "tool_calls") and msg.tool_calls) or 
                            (hasattr(msg, "additional_kwargs") and "tool_calls" in msg.additional_kwargs)
                        )
                        if has_tool_calls:
                            logger.debug("Omit AIMessage with tool_calls (function calling): id=%s", getattr(msg, "id", None))
                            continue
                            
                        # Omit supervisor routing tags
                        content_str = str(getattr(msg, "content", ""))
                        if "[ROUTE:" in content_str:
                            logger.debug("Omit message with routing tag: %s", content_str[:40])
                            continue
                            
                        history.append(msg)
                        logger.info("-> Added to Supervisor history: type=%s, content='%s...'", msg_type, content_str[:40].replace('\n', ' '))
                    else:
                        logger.debug("Omit non-conversational message: type=%s, class=%s", msg_type, msg_class)
                        
            logger.info("Clean history for the Supervisor compiled successfully. Final messages: %d", len(history))
        except Exception as e:
            logger.error("Could not read or clean history for the Supervisor: %s", e, exc_info=True)
        return history
    
    @traceable(name="run_specialized_agent")
    async def _run_specialized_agent(
        self, 
        llm: ChatOpenAI, 
        route: str, 
        message: str, 
        config: dict, 
        langchain_tools: list, 
        local_tools: list
    ) -> tuple[Any, str]:
        """
        Builds, configures, and invokes the corresponding specialized sub-agent by delegating to its module.
        Returns a tuple (agent_response, output_text).
        """
        if route == "finance":
            specialized_agent = create_finance_agent(llm, langchain_tools, self.memory)
        elif route == "reminder":
            specialized_agent = create_reminder_agent(llm, langchain_tools, self.memory)
        elif route == "general":
            specialized_agent = create_general_agent(llm, local_tools, self.memory)
        else:
            logger.warning("Unknown route '%s', using all available tools as fallback", route)
            from langchain.agents import create_agent
            from .prompts import AGENT_SYSTEM_PROMPT
            specialized_agent = create_agent(
                llm,
                langchain_tools + local_tools,
                system_prompt=AGENT_SYSTEM_PROMPT,
                checkpointer=self.memory,
                debug=False,
            )

        # Invoke the sub-agent. This will automatically add the HumanMessage and corresponding
        # tool/assistant responses to the checkpointer.
        agent_response = await specialized_agent.ainvoke({"input": message}, config=config)

        messages = agent_response.get("messages", [])
        output = ""
        # Search in reverse order for the last AIMessage containing text assistant response
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                output = msg.content
                break
        
        if not output and messages:
            output = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        elif not output:
            output = agent_response.get("output", str(agent_response))

        return agent_response, output

    @traceable(name="travel_assistant_handle_message")
    async def handle_message(self, message: str, thread_id: str = "default") -> dict[str, Any]:
        """
        Asynchronously processes a user message. Connects to multiple remote MCP servers,
        discovers available tools on all of them, evaluates intent with a Supervisor LLM,
        and dynamically runs the corresponding sub-agent or handles chit-chat directly.
        """
        logger.info("Agent receives message: '%s' (thread: '%s')", message, thread_id)
        try:
            # Obtain persistent sessions (and auto-heal/connect if necessary)
            sessions = await self.get_sessions()
            
            # 1. Discover combined tool catalog from all MCP servers
            langchain_tools = await self._discover_mcp_tools(sessions)

            # 2. Add agent local tools (e.g. 'rules')
            local_tools = self._get_local_tools()

            llm = ChatOpenAI(model_name=get_openai_model(), temperature=0.0)
            config = {"configurable": {"thread_id": thread_id}}

            # 3. Create a temporary empty agent to access the conversational checkpointer
            temp_agent = create_agent(llm, [], system_prompt="", checkpointer=self.memory)

            # 3.5. Limit and prune thread history if it exceeds the maximum
            await self._prune_history_if_needed(temp_agent, config, thread_id)

            # 4. Get clean conversational history
            history = await self._get_clean_history(temp_agent, config)

            # 5. Invoke the Supervisor LLM to determine routing or engage in direct conversation (routing skill)
            route, supervisor_text = await run_supervisor(llm, history, message)

            # 6. Flow A: The Supervisor decides to chat directly or ask for clarifications
            if not route:
                logger.info("The Supervisor assumes direct interaction (chit-chat or clarification). Saving to history.")
    
                return {
                    "llm_used": True,
                    "llm_tool": "supervisor_chat",
                    "agent_used": "supervisor",
                    "tool_response": None,
                    "message": self._extract_message(supervisor_text),
                }

            # 7. Flow B: Routing to specialized sub-agent
            logger.info("Routing request to specialized sub-agent: '%s'", route)
            # Explicitly persist the user message in the checkpointer
            # so it figures in the history inspected by the Supervisor.
            agent_response, output = await self._run_specialized_agent(
                llm, route, message, config, langchain_tools, local_tools
            )

        except Exception as exc:
            logger.exception("Exception during LangChainAgentRouter execution: %s", exc)
            return {
                "llm_used": False,
                "llm_tool": None,
                "agent_used": "unknown",
                "tool_response": None,
                "message": (
                    f"Error connecting to MCP tool servers. "
                    f"Please make sure independent servers are started: {', '.join(self.mcp_servers)}. "
                    f"(Technical detail: {str(exc)})"
                ),
            }

        return {
            "llm_used": True,
            "llm_tool": "langchain_agent_via_mcp",
            "agent_used": route,
            "tool_response": agent_response,
            "message": self._extract_message(output),
        }
