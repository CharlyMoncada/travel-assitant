from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

from ..services.llm import llm_status, raw_llm_call
from ..services.persistence import get_expense_summary, list_reminders
from ..services.rag import rag_status

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Travel Assistant backend está en ejecución"}


@router.get("/app", response_class=HTMLResponse)
async def frontend():
    index_file = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    return FileResponse(index_file)


@router.post("/message")
async def receive_message(request: Request, payload: dict):
    text = payload.get("text", "").strip()
    if not text:
        return {"error": "Se requiere un campo text con el mensaje del usuario"}

    return request.app.state.message_router.handle_message(text)


@router.get("/expenses")
async def expenses():
    return get_expense_summary()


@router.get("/reminders")
async def reminders():
    return {"reminders": list_reminders()}


@router.get("/status")
async def status(request: Request):
    db_file = Path("travel_assistant.db").resolve()
    telegram_service = getattr(request.app.state, "telegram_service", None)
    return {
        "telegram": telegram_service.status() if telegram_service else {
            "enabled": False,
            "running": False,
            "token_set": bool(request.app.state.telegram_token),
        },
        "llm": llm_status(),
        "rag": rag_status(),
        "mcp": request.app.state.mcp_service.status(),
        "database": {
            "path": str(db_file),
            "exists": db_file.exists(),
        },
    }


@router.get("/mcp/tools")
async def mcp_tools(request: Request):
    return {"tools": request.app.state.mcp_service.list_tools()}


@router.post("/mcp/execute")
async def mcp_execute(request: Request, payload: dict):
    text = payload.get("text", "").strip()
    if not text:
        return {"error": "Se requiere un campo text con el mensaje del usuario"}

    return request.app.state.mcp_service.execute(text)


@router.post("/llm/test")
async def llm_test(payload: dict):
    text = payload.get("text", "").strip()
    if not text:
        return {"error": "Se requiere un campo text con el mensaje del usuario"}

    return {
        "text": text,
        "llm": llm_status(),
        "raw": raw_llm_call(text),
    }
