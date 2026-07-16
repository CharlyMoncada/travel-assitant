import os
import json
import asyncio
import httpx
from fastapi import APIRouter, Request

from ..services.persistence.db import DB_PATH
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
            # Fallback en caso de que no haya cliente compartido en el estado de la app
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
    Consulta el estado de los dos servidores MCP independientes (puertos 8002 y 8003)
    en paralelo y de forma no bloqueante, y los unifica.
    """
    finance_url = os.getenv("MCP_FINANCE_SERVER_STATUS_URL", "http://localhost:8002/status")
    reminder_url = os.getenv("MCP_REMINDER_SERVER_STATUS_URL", "http://localhost:8003/status")
    
    # Consultar de forma concurrente en paralelo usando asyncio.gather
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
    Gestiona el envío de mensajes. Invoca de forma asíncrona al agente LangChainRouter.
    """
    text = payload.text.strip()
    thread_id = payload.thread_id or payload.session_id or "default"
    # Usamos await porque handle_message es ahora una función asíncrona (MCP Client)
    return await request.app.state.message_orchestrator.handle_message(text, thread_id=thread_id)


@router.get("/expenses")
def expenses():
    """
    Endpoint síncrono. FastAPI lo ejecuta automáticamente en un pool de hilos interno
    para evitar bloquear el bucle de eventos principal del servidor.
    """
    return get_expense_summary()


@router.get("/reminders")
def reminders():
    """
    Endpoint síncrono. FastAPI lo ejecuta automáticamente en un pool de hilos interno
    para evitar bloquear el bucle de eventos principal del servidor.
    """
    return {"reminders": list_reminders()}


@router.get("/status")
async def status(request: Request):
    """
    Retorna el estado general de todos los subsistemas, incluido el servidor MCP externo.
    """
    db_file = DB_PATH.resolve()
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
    Mapea el catálogo de herramientas recuperado del servidor MCP externo para compatibilidad con versiones anteriores del frontend.
    """
    client = getattr(request.app.state, "http_client", None)
    mcp_status = await get_external_mcp_status(client)
    
    if mcp_status.get("online"):
        tools_list = []
        for tool in mcp_status.get("tools", []):
            if isinstance(tool, dict):
                # Expone el catálogo de herramientas completo proporcionado por el servidor MCP actualizado
                tools_list.append({
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "inputSchema": tool.get("inputSchema"),
                    "examples": []
                })
            else:
                # Mapeo de fallback para compatibilidad con versiones anteriores
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
