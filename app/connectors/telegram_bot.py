import logging
import threading

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters


logger = logging.getLogger(__name__)


class TelegramBotService:
    def __init__(self, router, token: str):
        self.router = router
        self.token = token
        self.application = None
        self.thread = None

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Hola! Soy tu asistente de viaje. Envíame un mensaje de texto para empezar."
        )

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text or ""
        response = self.router.handle_message(text)
        if isinstance(response, dict):
            reply = response.get("message", str(response))
            if response.get("llm_used"):
                tool_name = response.get("llm_tool", "desconocida")
                reply = f"{reply}\n\n(LLM usado, herramienta: {tool_name})"
            await update.message.reply_text(reply)
        else:
            await update.message.reply_text(str(response))

    def start(self):
        self.application = ApplicationBuilder().token(self.token).build()
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        def run_polling():
            logger.info("Telegram bot starting polling")
            self.application.run_polling(
                poll_interval=3,
                allowed_updates=["message"],
                stop_signals=None,
            )

        self.thread = threading.Thread(target=run_polling, daemon=True)
        self.thread.start()
        logger.info("Telegram bot thread started")

    def stop(self):
        if not self.application:
            return

        try:
            self.application.stop()
        except Exception as exc:
            logger.warning("Error al detener el bot de Telegram: %s", exc)

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                logger.warning("El hilo del bot de Telegram no se detuvo dentro del tiempo de espera")

        logger.info("Telegram bot stopped")

    def status(self) -> dict:
        running = bool(self.application and self.thread and self.thread.is_alive())
        return {
            "enabled": True,
            "running": running,
            "token_set": bool(self.token),
        }
