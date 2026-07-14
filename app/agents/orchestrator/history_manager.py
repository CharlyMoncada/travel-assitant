import logging
from langchain_core.messages import AIMessage, HumanMessage
from app.services.persistence.conversation_persistence import get_recent_messages
from app.services.persistence.memory_persistence import save_user_memory

logger = logging.getLogger(__name__)


class ChatMemoryService:
    @staticmethod
    def get_persistent_history(thread_id: str, limit: int = 20) -> list:
        persistent_messages = []

        try:
            rows = get_recent_messages(thread_id, limit=limit)

            for row in rows:
                role = row.get("role")
                content = row.get("content")

                if not content:
                    continue

                if role == "user":
                    persistent_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    persistent_messages.append(AIMessage(content=content))

            logger.info(
                "Loaded %d persistent memory messages for thread '%s'",
                len(persistent_messages),
                thread_id,
            )

        except Exception as e:
            logger.warning(
                "Could not load persistent memory for thread '%s': %s",
                thread_id,
                e,
                exc_info=True,
            )

        return persistent_messages

    @staticmethod
    def format_persistent_memory(thread_id: str, limit: int = 20) -> str:
        try:
            rows = get_recent_messages(thread_id, limit=limit)
            return "\n".join(
                f"{row['role']}: {row['content']}"
                for row in rows
                if row.get("content")
            )

        except Exception as e:
            logger.warning(
                "Could not format persistent memory for thread '%s': %s",
                thread_id,
                e,
                exc_info=True,
            )
            return ""

    @staticmethod
    def detect_memory_to_save(message: str) -> tuple[str, str, str] | None:
        """
        Detects simple long-term travel preferences from declarative user messages.
        Returns (memory_key, memory_value, category) or None.
        """
        clean_message = message.strip()
        lower_message = clean_message.lower()

        # Do not save questions as memories
        question_markers = ["?", "¿", "cual", "cuál", "que ", "qué ", "como ", "cómo ", "what ", "how ", "where ", "which ", "who "]
        if any(marker in lower_message for marker in question_markers):
            return None

        # Spanish heuristics
        if "mi aeropuerto favorito" in lower_message and " es " in lower_message:
            value = clean_message.split(" es ", 1)[1].strip().rstrip(".")
            return ("favorite_airport", value, "travel_preference")
        # English heuristics
        if "my favorite airport" in lower_message and " is " in lower_message:
            value = clean_message.split(" is ", 1)[1].strip().rstrip(".")
            return ("favorite_airport", value, "travel_preference")

        if "mi presupuesto" in lower_message and " es " in lower_message:
            value = clean_message.split(" es ", 1)[1].strip().rstrip(".")
            return ("budget_preference", value, "travel_preference")
        if "my budget" in lower_message and " is " in lower_message:
            value = clean_message.split(" is ", 1)[1].strip().rstrip(".")
            return ("budget_preference", value, "travel_preference")

        if "prefiero viajar" in lower_message:
            value = lower_message.split("prefiero viajar", 1)[1].strip().rstrip(".")
            return ("travel_style", value, "travel_preference")
        if "i prefer to travel" in lower_message:
            value = lower_message.split("i prefer to travel", 1)[1].strip().rstrip(".")
            return ("travel_style", value, "travel_preference")
        if "i prefer traveling" in lower_message:
            value = lower_message.split("i prefer traveling", 1)[1].strip().rstrip(".")
            return ("travel_style", value, "travel_preference")

        return None

    @classmethod
    def save_long_term_memory_if_needed(cls, thread_id: str, message: str) -> None:
        try:
            detected_memory = cls.detect_memory_to_save(message)

            if detected_memory:
                memory_key, memory_value, category = detected_memory
                save_user_memory(thread_id, memory_key, memory_value, category)

                logger.info(
                    "Saved long-term memory for thread '%s': %s=%s",
                    thread_id,
                    memory_key,
                    memory_value,
                )

        except Exception as e:
            logger.warning(
                "Could not persist long-term memory: %s",
                e,
                exc_info=True,
            )

    @staticmethod
    def build_memory_context_for_agent(
        thread_id: str,
        short_term_memory_text: str,
        long_term_memory_text: str,
        message: str,
    ) -> str:
        context_parts = []

        if long_term_memory_text:
            context_parts.append(
                "Long-term user memory:\n"
                f"{long_term_memory_text}"
            )

        if short_term_memory_text:
            context_parts.append(
                "Previous conversation memory for this thread:\n"
                f"{short_term_memory_text}"
            )

        if not context_parts:
            return message

        return (
            "\n\n".join(context_parts)
            + "\n\nCurrent user message:\n"
            + message
        )
