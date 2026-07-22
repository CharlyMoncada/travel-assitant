import asyncio
import logging
import threading

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest
import telegram.error


from app.agents.orchestrator import format_agent_response


logger = logging.getLogger(__name__)


class TelegramBotService:
    def __init__(self, router, token: str):
        self.router = router
        self.token = token
        self.application = None
        self.thread = None

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.message.chat_id)
        logger.info("Telegram bot received /start command from chat: %s", chat_id)
        try:
            await update.message.reply_text(
                "Hello! I am your travel assistant. Send me a text message to start."
            )
        except Exception as e:
            logger.exception("Error responding to /start command in chat %s: %s", chat_id, e)

    async def _reply_with_retry(self, update: Update, chunk: str, max_retries: int = 2):
        for attempt in range(max_retries + 1):
            try:
                await update.message.reply_text(chunk)
                return
            except (telegram.error.TimedOut, telegram.error.NetworkError) as exc:
                if attempt < max_retries:
                    logger.warning(
                        "Telegram reply_text network timeout (attempt %d/%d), retrying in 1s: %s",
                        attempt + 1,
                        max_retries,
                        exc,
                    )
                    await asyncio.sleep(1.0)
                else:
                    logger.error("Failed to send Telegram reply after %d attempts: %s", max_retries + 1, exc)
                    raise

    async def _send_message_in_chunks(self, update: Update, text: str):
        # Telegram tiene un límite de 4096 caracteres. Usamos 4000 para mayor seguridad.
        max_length = 4000
        if len(text) <= max_length:
            await self._reply_with_retry(update, text)
            return

        chunks = []
        while len(text) > max_length:
            split_idx = text.rfind("\n", 0, max_length)
            if split_idx == -1:
                split_idx = text.rfind(" ", 0, max_length)
            if split_idx == -1:
                split_idx = max_length
            
            chunks.append(text[:split_idx].strip())
            text = text[split_idx:].strip()
        
        if text:
            chunks.append(text)

        for chunk in chunks:
            if chunk:
                await self._reply_with_retry(update, chunk)

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.message.chat_id)
        try:
            text = update.message.text or ""
            logger.info("Telegram bot received text message from chat %s: '%s'", chat_id, text)
            
            raw_response = await self.router.handle_message(text, thread_id=chat_id)
            response = format_agent_response(raw_response)
            logger.info("Conversational agent response for chat %s: %s", chat_id, response)
            
            if isinstance(response, dict):
                reply = response.get("message", str(response))
                await self._send_message_in_chunks(update, reply)
            else:
                await self._send_message_in_chunks(update, str(response))
        except Exception as e:
            logger.exception("Error processing Telegram message from chat %s: %s", chat_id, e)

    def start(self):
        request = HTTPXRequest(
            connect_timeout=10.0,
            read_timeout=10.0,
            write_timeout=10.0,
        )
        self.application = (
            ApplicationBuilder()
            .token(self.token)
            .request(request)
            .build()
        )
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        def run_polling():
            logger.info("Telegram bot starting polling (all updates enabled)")
            self.application.run_polling(
                poll_interval=3,
                stop_signals=None,
            )

        self.thread = threading.Thread(target=run_polling, daemon=True)
        self.thread.start()
        logger.info("Telegram bot thread started")

    def stop(self):
        if not self.application:
            return

        try:
            self.application.stop_running()
        except Exception as exc:
            logger.warning("Error stopping Telegram bot: %s", exc)

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                logger.warning("Telegram bot thread did not stop within timeout")

        logger.info("Telegram bot stopped")

    def status(self) -> dict:
        running = bool(self.application and self.thread and self.thread.is_alive())
        return {
            "enabled": True,
            "running": running,
            "token_set": bool(self.token),
        }
