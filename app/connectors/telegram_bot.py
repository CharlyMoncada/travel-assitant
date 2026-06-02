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
        chat_id = str(update.message.chat_id)
        logger.info("Telegram bot received /start command from chat: %s", chat_id)
        try:
            await update.message.reply_text(
                "Hello! I am your travel assistant. Send me a text message to start."
            )
        except Exception as e:
            logger.exception("Error responding to /start command in chat %s: %s", chat_id, e)

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.message.chat_id)
        try:
            text = update.message.text or ""
            logger.info("Telegram bot received text message from chat %s: '%s'", chat_id, text)
            
            response = await self.router.handle_message(text, thread_id=chat_id)
            logger.info("Conversational agent response for chat %s: %s", chat_id, response)
            
            if isinstance(response, dict):
                reply = response.get("message", str(response))
                if response.get("llm_used"):
                    agent_used = response.get("agent_used", "unknown")
                    tool_name = response.get("llm_tool", "unknown")
                    
                    # Human-readable names of the specialized agents
                    agent_names = {
                        "supervisor": "Supervisor (Router)",
                        "finance": "Finance Specialist",
                        "reminder": "Reminder Specialist",
                        "general": "General Specialist / RAG"
                    }
                    agent_display = agent_names.get(agent_used, str(agent_used).capitalize())
                    
                    # Extract the tools actually executed (from MCP or local)
                    tools_executed = []
                    tool_resp = response.get("tool_response")
                    
                    if isinstance(tool_resp, dict) and "messages" in tool_resp:
                        for msg in tool_resp["messages"]:
                            # Support for StructuredTool call objects in LangGraph
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    tools_executed.append(tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", str(tc)))
                    
                    # Build detailed metadata signature
                    signature = f"🤖 Agent: {agent_display}"
                    if tools_executed:
                        signature += f"\n🛠️ MCP/Local Tools: {', '.join(tools_executed)}"
                    else:
                        signature += f"\n🛠️ Flow: {tool_name}"
                        
                    reply = f"{reply}\n\n({signature})"
                await update.message.reply_text(reply)
            else:
                await update.message.reply_text(str(response))
        except Exception as e:
            logger.exception("Error processing Telegram message from chat %s: %s", chat_id, e)

    def start(self):
        self.application = ApplicationBuilder().token(self.token).build()
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
            self.application.stop()
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
