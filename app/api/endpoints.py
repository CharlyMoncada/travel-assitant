import os
import json
import asyncio
import time
from pathlib import Path
import httpx
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from ..services.persistence.db import DB_PATH
from ..services.llm import llm_status
from ..services.persistence import get_expense_summary, list_reminders
from ..services.rag import rag_status
from ..agents.orchestrator import format_agent_response

router = APIRouter()


# --- ESQUEMAS PYDANTIC (Type Hints y Documentación OpenAPI) ---

class MessagePayload(BaseModel):
    text: str = Field(..., min_length=1, description="Text of the message sent by the user")
    thread_id: str | None = Field(default=None, description="Unique identifier of the thread or session (optional)")
    session_id: str | None = Field(default=None, description="Session alias compatible with the frontend (optional)")


class ExpenseSummaryResponse(BaseModel):
    total: float = 0.0
    by_category: dict[str, float] = {}
    count: int = 0


class RemindersResponse(BaseModel):
    reminders: list[dict] = []


class MCPToolSchema(BaseModel):
    name: str
    description: str
    inputSchema: dict | None = None
    examples: list[str] = []


class MCPToolsResponse(BaseModel):
    tools: list[MCPToolSchema]


class DatabaseStatus(BaseModel):
    path: str
    exists: bool


class StatusResponse(BaseModel):
    telegram: dict
    llm: dict
    rag: dict
    mcp: dict
    database: DatabaseStatus


# --- INYECCIÓN DE DEPENDENCIAS (Depends) ---

def get_orchestrator(request: Request):
    orchestrator = getattr(request.app.state, "message_orchestrator", None)
    if orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator service is not initialized."
        )
    return orchestrator


def get_http_client(request: Request) -> httpx.AsyncClient | None:
    return getattr(request.app.state, "http_client", None)


# --- CACHÉ EN MEMORIA CON TTL (3s) ---

_mcp_cache = {"timestamp": 0.0, "data": None}


async def fetch_url_status(client: httpx.AsyncClient | None, url: str) -> dict:
    try:
        if client is None:
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


async def get_external_mcp_status(client: httpx.AsyncClient | None, ttl_seconds: float = 3.0) -> dict:
    """
    Consulta el estado de los dos servidores MCP independientes (puertos 8002 y 8003)
    en paralelo con un caché en memoria TTL de 3 segundos para reducir latencias.
    """
    now = time.time()
    if _mcp_cache["data"] is not None and (now - _mcp_cache["timestamp"]) < ttl_seconds:
        return _mcp_cache["data"]

    finance_url = os.getenv("MCP_FINANCE_SERVER_STATUS_URL", "http://localhost:8002/status")
    reminder_url = os.getenv("MCP_REMINDER_SERVER_STATUS_URL", "http://localhost:8003/status")
    
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
    
    result = {
        "online": global_online,
        "url": f"{finance_url}, {reminder_url}",
        "tool_count": len(unified_tools),
        "tools": unified_tools,
        "finance_server": finance_status,
        "reminder_server": reminder_status
    }
    
    _mcp_cache["timestamp"] = now
    _mcp_cache["data"] = result
    return result


# --- ENDPOINTS ---

@router.get("/")
async def root():
    return {"message": "Travel Assistant backend is running"}


@router.get("/app", response_class=HTMLResponse)
async def frontend():
    index_file = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    return FileResponse(index_file)


@router.post("/message")
async def receive_message(
    payload: MessagePayload,
    orchestrator=Depends(get_orchestrator)
):
    """
    Gestiona el envío de mensajes mediante inyección de dependencias (Depends).
    """
    text = payload.text.strip()
    thread_id = payload.thread_id or payload.session_id or "default"
    response = await orchestrator.handle_message(text, thread_id=thread_id)
    return format_agent_response(response)


@router.get("/expenses")
def expenses():
    """
    Endpoint síncrono. FastAPI lo ejecuta en un pool de hilos interno.
    """
    return get_expense_summary()


@router.get("/reminders", response_model=RemindersResponse)
def reminders():
    """
    Endpoint de recordatorios con esquema Pydantic documentado.
    """
    return {"reminders": list_reminders()}


@router.get("/status", response_model=StatusResponse)
async def status(
    request: Request,
    client: httpx.AsyncClient | None = Depends(get_http_client)
):
    """
    Retorna el estado general de todos los subsistemas con caché de 3s para el servidor MCP.
    """
    db_file = DB_PATH.resolve()
    telegram_service = getattr(request.app.state, "telegram_service", None)
    mcp_status = await get_external_mcp_status(client)
    
    return {
        "telegram": telegram_service.status() if telegram_service else {
            "enabled": False,
            "running": False,
            "token_set": bool(getattr(request.app.state, "telegram_token", None)),
        },
        "llm": llm_status(),
        "rag": rag_status(),
        "mcp": mcp_status,
        "database": {
            "path": str(db_file),
            "exists": db_file.exists(),
        },
    }


@router.get("/mcp/tools", response_model=MCPToolsResponse)
async def mcp_tools(client: httpx.AsyncClient | None = Depends(get_http_client)):
    """
    Mapea el catálogo de herramientas con validación Pydantic y error HTTP 503 si el MCP está offline.
    """
    mcp_status = await get_external_mcp_status(client)
    
    if not mcp_status.get("online"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP server offline ({mcp_status.get('url')}). Detail: {mcp_status.get('error') or 'Servers not available'}"
        )

    tools_list = []
    for tool in mcp_status.get("tools", []):
        if isinstance(tool, dict):
            tools_list.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema"),
                "examples": []
            })
        else:
            tools_list.append({
                "name": str(tool),
                "description": f"Business tool '{tool}' provided by the external MCP server.",
                "examples": []
            })
            
    return {"tools": tools_list}
