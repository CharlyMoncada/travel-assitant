import logging
import os
import time
from contextlib import AsyncExitStack
from typing import Any, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_core.tools import StructuredTool, ToolException
from pydantic import create_model
from .mcp_schema import MCPSchemaTranslator, EmptySchema

logger = logging.getLogger(__name__)

MCP_TOOLS_CACHE_TTL = 300  # Cache TTL in seconds (5 minutes)


class MCPConnectionManager:
    def __init__(self):
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

        logger.info(
            "MCPConnectionManager initialized with MCP servers: %s",
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
            logger.info("Stopping persistent connections for MCPConnectionManager...")

            try:
                await self.stack.aclose()
            except Exception as e:
                logger.warning("Error closing connection stack: %s", e)

            self.stack = None
            self.sessions = []
            self._cached_tools = {}

            logger.info("Persistent connections closed.")

    def _make_mcp_tool_coroutine(self, tool_name: str, server_url: str):
        async def make_tool_call(**kwargs) -> str:
            clean_kwargs = {k: v for k, v in kwargs.items() if v is not None}

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
                raise ToolException(
                    f"Error: The MCP server at {server_url} is currently offline and unavailable."
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

                raise ToolException(
                    f"Error executing tool '{tool_name}' (lost connection with MCP server at {server_url})."
                )

            if getattr(resp, "isError", False) or getattr(resp, "is_error", False):
                error_msg = resp.content[0].text if resp.content else "Unknown error occurred on MCP server."
                raise ToolException(
                    f"Tool execution failed on MCP server: {error_msg}"
                )

            if resp.content and len(resp.content) > 0:
                logger.debug(
                    "Tool '%s' responded with: %s",
                    tool_name,
                    resp.content[0].text,
                )
                return resp.content[0].text

            raise ToolException(
                f"Error: Did not receive response content for '{tool_name}'."
            )

        return make_tool_call

    async def discover_mcp_tools(self) -> dict[str, list[StructuredTool]]:
        sessions = await self.get_sessions()
        langchain_tools_by_server = {}

        for url, session in sessions:
            if url in self._cached_tools:
                cached_entry = self._cached_tools[url]
                if time.time() < cached_entry["expires_at"]:
                    logger.debug("Using cached tools for MCP server %s", url)
                    langchain_tools_by_server[url] = cached_entry["tools"]
                    continue
                else:
                    logger.info("Cache expired for MCP server %s. Refreshing tools...", url)

            try:
                mcp_tools_list = await session.list_tools()
                logger.info(
                    "Discovered catalog from MCP server %s: %s",
                    url,
                    [t.name for t in mcp_tools_list.tools],
                )

                server_tools = []

                for mcp_tool in mcp_tools_list.tools:
                    fields = MCPSchemaTranslator.json_schema_to_pydantic_fields(
                        mcp_tool.inputSchema
                    )
                    model_name = (
                        "".join(c for c in mcp_tool.name if c.isalnum()).capitalize()
                        + "Schema"
                    )

                    if fields:
                        PydanticModelClass = create_model(model_name, **fields)
                    else:
                        PydanticModelClass = EmptySchema

                    server_tools.append(
                        StructuredTool(
                            name=mcp_tool.name,
                            description=mcp_tool.description,
                            coroutine=self._make_mcp_tool_coroutine(mcp_tool.name, url),
                            func=lambda **kwargs: "",
                            args_schema=PydanticModelClass,
                            handle_tool_error=True,
                        )
                    )

                self._cached_tools[url] = {
                    "tools": server_tools,
                    "expires_at": time.time() + MCP_TOOLS_CACHE_TTL,
                }
                langchain_tools_by_server[url] = server_tools

            except Exception as e:
                logger.warning(
                    "Error listing tools for %s: %s. Removing session.",
                    url,
                    e,
                )

                self.sessions = [(u, s) for u, s in self.sessions if u != url]

        return langchain_tools_by_server
