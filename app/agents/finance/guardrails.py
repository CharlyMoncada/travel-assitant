import logging
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

ALLOWED_LANGUAGES = {"en", "es"}

REJECTION_MESSAGE = (
    "Sorry, the finance assistant only supports English and Spanish.\n"
    "Lo siento, el asistente de finanzas solo admite inglés y español."
)


def check_finance_language(text: str) -> tuple[bool, str]:
    """
    Returns (is_allowed, detected_lang).
    Allows English (en) and Spanish (es). Blocks everything else.
    """
    try:
        lang = detect(text)
    except LangDetectException:
        logger.warning("Language detection failed for finance guardrail, defaulting to unknown")
        lang = "unknown"

    logger.info("Finance guardrail: detected language='%s', allowed=%s", lang, lang in ALLOWED_LANGUAGES)
    return lang in ALLOWED_LANGUAGES, lang
