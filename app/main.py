import logging
import os
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / ".env", override=True)

# Configurar el logging raíz para mostrar logs INFO en la consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.endpoints import router as api_router
from .agents.orchestrator import TravelAgentOrchestrator
from .services.persistence.db import init_db
from .connectors.telegram_bot import TelegramBotService

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

orchestrator = TravelAgentOrchestrator()
telegram_service = None
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_service
    # Inicio: inicializar BD, RAG y httpx.AsyncClient
    init_db()
    # RAG se inicializa bajo demanda al llamar query_normative_documents()
    
    app.state.http_client = httpx.AsyncClient(timeout=3.0)
    
    # Preconectar los servidores MCP para evitar latencia en el primer mensaje
    try:
        await orchestrator.get_sessions()
    except Exception as exc:
        logger.warning("Could not pre-connect MCP servers during startup: %s", exc)
    
    if TELEGRAM_TOKEN:
        telegram_service = TelegramBotService(orchestrator, token=TELEGRAM_TOKEN)
        try:
            telegram_service.start()
        except Exception as exc:
            logger.error("Could not start Telegram bot", exc_info=exc)
            telegram_service = None
    app.state.telegram_service = telegram_service
    
    yield
    
    # Apagado: detener Telegram y cerrar httpx.AsyncClient
    if telegram_service:
        telegram_service.stop()
    await app.state.http_client.aclose()
    
    # Cerrar limpiamente las conexiones MCP
    try:
        await orchestrator.stop()
    except Exception as exc:
        logger.warning("Error closing persistent MCP connections during shutdown: %s", exc)


app = FastAPI(
    title="Travel Assistant",
    description="Python Travel Assistant for proof-of-concept tests",
    version="0.1.0",
    lifespan=lifespan,
)

frontend_dir = Path(__file__).resolve().parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

app.state.message_orchestrator = orchestrator
app.state.telegram_service = None
app.state.telegram_token = bool(TELEGRAM_TOKEN)

app.include_router(api_router)


def run():
    import uvicorn

    reload = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=reload, reload_dirs=["app"] if reload else None)


if __name__ == "__main__":
    run()
