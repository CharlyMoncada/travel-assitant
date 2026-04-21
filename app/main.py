import logging
import os
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / ".env", override=True)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .agents import TravelAssistant
from .api.endpoints import router as api_router
from .orchestrator.router import MessageRouter
from .orchestrator.mcp import MCPServer
from .services.persistence import init_db
from .services.rag import init_rag
from .connectors.telegram_bot import TelegramBotService

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

app = FastAPI(
    title="Travel Assistant",
    description="Asistente de viaje Python para pruebas de concepto",
    version="0.1.0",
)

frontend_dir = Path(__file__).resolve().parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

assistant = TravelAssistant()
mcp_service = MCPServer(assistant)
router = MessageRouter(assistant, mcp_service=mcp_service)
telegram_service = None
logger = logging.getLogger(__name__)

app.state.message_router = router
app.state.mcp_service = mcp_service
app.state.telegram_service = None
app.state.telegram_token = bool(TELEGRAM_TOKEN)

@app.on_event("startup")
async def startup_event():
    global telegram_service
    init_db()
    init_rag()
    if TELEGRAM_TOKEN:
        telegram_service = TelegramBotService(router, token=TELEGRAM_TOKEN)
        try:
            telegram_service.start()
        except Exception as exc:
            logger.error("No se pudo iniciar el bot de Telegram", exc_info=exc)
            telegram_service = None
    app.state.telegram_service = telegram_service

app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_event():
    if telegram_service:
        telegram_service.stop()


def run():
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
