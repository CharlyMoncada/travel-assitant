import os
import json
import asyncio
import httpx
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from ..services.llm import llm_status
from ..services.persistence import get_expense_summary, list_reminders
from ..services.rag import rag_status

router = APIRouter()


class MessagePayload(BaseModel):
    text: str = Field(..., min_length=1, description="Text of the message sent by the user")
    thread_id: str | None = Field(default=None, description="Unique identifier of the thread or session (optional)")
    session_id: str | None = Field(default=None, description="Session alias compatible with the frontend (optional)")


async def fetch_url_status(client: httpx.AsyncClient | None, url: str) -> dict:
    try:
        if client is None:
            # Fallback in case there is no shared client in the app state
            async with httpx.AsyncClient(timeout=1.5) as fallback_client:
                response = await fallback_client.get(url)
        else:
            response = await client.get(url, timeout=1.5)
            
        if response.status_code == 200:
            res = response.json()
            return {
                "online": True,
                "tool_count": res.get("tool_count", 0),
                "tools": res.get("tools", []),
            }
        else:
            return {
                "online": False,
                "error": f"HTTP Error {response.status_code}",
                "tools": []
            }
    except Exception as exc:
        return {
            "online": False,
            "error": str(exc),
            "tools": []
        }


async def get_external_mcp_status(client: httpx.AsyncClient | None) -> dict:
    """
    Queries the status of the two independent MCP servers (ports 8002 and 8003)
    in parallel and non-blocking, and unifies them.
    """
    finance_url = os.getenv("MCP_FINANCE_SERVER_STATUS_URL", "http://localhost:8002/status")
    reminder_url = os.getenv("MCP_REMINDER_SERVER_STATUS_URL", "http://localhost:8003/status")
    
    # Query concurrently in parallel using asyncio.gather
    finance_status, reminder_status = await asyncio.gather(
        fetch_url_status(client, finance_url),
        fetch_url_status(client, reminder_url),
        return_exceptions=True
    )
    
    if isinstance(finance_status, Exception):
        finance_status = {"online": False, "error": str(finance_status), "tools": []}
    if isinstance(reminder_status, Exception):
        reminder_status = {"online": False, "error": str(reminder_status), "tools": []}
        
    global_online = finance_status.get("online", False) and reminder_status.get("online", False)
    unified_tools = finance_status.get("tools", []) + reminder_status.get("tools", [])
    
    return {
        "online": global_online,
        "url": f"{finance_url}, {reminder_url}",
        "tool_count": len(unified_tools),
        "tools": unified_tools,
        "finance_server": finance_status,
        "reminder_server": reminder_status
    }


@router.get("/")
async def root():
    return {"message": "Travel Assistant backend is running"}


@router.get("/app", response_class=HTMLResponse)
async def frontend():
    index_file = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    return FileResponse(index_file)


@router.post("/message")
async def receive_message(request: Request, payload: MessagePayload):
    """
    Handles message submission. Asynchronously invokes the LangChainRouter agent.
    """
    text = payload.text.strip()
    thread_id = payload.thread_id or payload.session_id or "default"
    # We use await because handle_message is now an asynchronous function (MCP Client)
    return await request.app.state.message_orchestrator.handle_message(text, thread_id=thread_id)


@router.get("/expenses")
def expenses():
    """
    Synchronous endpoint. FastAPI runs it automatically in an internal thread pool
    to avoid blocking the main server event loop.
    """
    return get_expense_summary()


@router.get("/reminders")
def reminders():
    """
    Synchronous endpoint. FastAPI runs it automatically in an internal thread pool
    to avoid blocking the main server event loop.
    """
    return {"reminders": list_reminders()}


@router.get("/status")
async def status(request: Request):
    """
    Returns the general status of all subsystems, including the external MCP server.
    """
    db_file = Path("travel_assistant.db").resolve()
    telegram_service = getattr(request.app.state, "telegram_service", None)
    
    client = getattr(request.app.state, "http_client", None)
    mcp_status = await get_external_mcp_status(client)
    
    return {
        "telegram": telegram_service.status() if telegram_service else {
            "enabled": False,
            "running": False,
            "token_set": bool(request.app.state.telegram_token),
        },
        "llm": llm_status(),
        "rag": rag_status(),
        "mcp": mcp_status,
        "database": {
            "path": str(db_file),
            "exists": db_file.exists(),
        },
    }


@router.get("/mcp/tools")
async def mcp_tools(request: Request):
    """
    Maps the tool catalog retrieved from the external MCP server for frontend backwards compatibility.
    """
    client = getattr(request.app.state, "http_client", None)
    mcp_status = await get_external_mcp_status(client)
    
    if mcp_status.get("online"):
        tools_list = []
        for tool in mcp_status.get("tools", []):
            if isinstance(tool, dict):
                # Exposes the rich tool catalog provided by the updated MCP server
                tools_list.append({
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "inputSchema": tool.get("inputSchema"),
                    "examples": []
                })
            else:
                # Fallback mapping for backward compatibility with previous versions
                tools_list.append({
                    "name": tool,
                    "description": f"Business tool '{tool}' provided by the external MCP server.",
                    "examples": []
                })
        return {"tools": tools_list}
        
    return {
        "tools": [],
        "error": f"MCP server offline ({mcp_status.get('url')}). Detail: {mcp_status.get('error') or 'Servers not available'}"
    }
