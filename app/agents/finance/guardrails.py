import re
import logging
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language guardrail
# ---------------------------------------------------------------------------

ALLOWED_LANGUAGES = {"en", "es"}

REJECTION_MESSAGE_LANGUAGE = (
    "Sorry, the finance assistant only supports English and Spanish.\n"
    "Lo siento, el asistente de finanzas solo admite inglés y español."
)

# Keep the original name as an alias so the orchestrator import still works
REJECTION_MESSAGE = REJECTION_MESSAGE_LANGUAGE


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


# ---------------------------------------------------------------------------
# Prompt injection guardrail
# ---------------------------------------------------------------------------

REJECTION_MESSAGE_INJECTION = (
    "This request has been blocked for security reasons.\n"
    "Esta solicitud ha sido bloqueada por razones de seguridad."
)

_INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    # --- Instruction override ---
    ("instruction_override_en",
     re.compile(
         r"ignore\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|rules?|prompts?|guidelines?|constraints?)",
         re.IGNORECASE,
     )),
    ("instruction_override_es",
     re.compile(
         r"ignora\s+(todas?\s+las?\s+)?(instrucciones?|reglas?|normas?|restricciones?|anteriores?)",
         re.IGNORECASE,
     )),
    ("forget_instructions_en",
     re.compile(
         r"forget\s+(your|all|everything|previous|the\s+(above|previous|prior))",
         re.IGNORECASE,
     )),
    ("forget_instructions_es",
     re.compile(
         r"olvida\s+(todo|tus?\s+(instrucciones?|reglas?|restricciones?|rol))",
         re.IGNORECASE,
     )),
    ("new_instructions",
     re.compile(
         r"(new|updated?|actual)\s+instructions?\s*:",
         re.IGNORECASE,
     )),
    ("nuevas_instrucciones",
     re.compile(
         r"nuevas?\s+instrucciones?\s*:",
         re.IGNORECASE,
     )),

    # --- Role hijacking ---
    ("role_hijack_en",
     re.compile(
         r"\b(you\s+are\s+now|act\s+as(\s+a\b)?|pretend\s+(you\s+are|to\s+be)|you\s+will\s+(now\s+)?act\s+as|your\s+new\s+role\s+is)\b",
         re.IGNORECASE,
     )),
    ("role_hijack_es",
     re.compile(
         r"\b(ahora\s+eres|actúa\s+como|finge\s+(ser|que\s+eres)|compórtate\s+como|tu\s+nuevo\s+rol\s+es)\b",
         re.IGNORECASE,
     )),
    ("dan_jailbreak",
     re.compile(
         r"\b(DAN|jailbreak|do\s+anything\s+now|unrestricted\s+mode)\b",
         re.IGNORECASE,
     )),

    # --- System prompt extraction ---
    ("prompt_extraction_en",
     re.compile(
         r"(print|reveal|show|display|output|repeat|disclose)\s+(your\s+)?(system\s+)?(prompt|instructions?|rules?|guidelines?|initial\s+context)",
         re.IGNORECASE,
     )),
    ("prompt_extraction_es",
     re.compile(
         r"(muestra|revela|dime|imprime|repite|divulga)\s+(tu(s)?\s+)?(instrucciones?|prompt|reglas?|contexto\s+inicial)",
         re.IGNORECASE,
     )),
    ("what_are_instructions",
     re.compile(
         r"what\s+are\s+your\s+(instructions?|rules?|prompts?|guidelines?|constraints?)",
         re.IGNORECASE,
     )),
    ("cuales_instrucciones",
     re.compile(
         r"cu[aá]les?\s+son\s+tus\s+(instrucciones?|reglas?|restricciones?)",
         re.IGNORECASE,
     )),

    # --- Special tokens / template injection ---
    ("template_tokens",
     re.compile(
         r"(\[INST\]|<<SYS>>|<</SYS>>|<\|system\|>|<\|user\|>|\[SYSTEM\]|###\s*(system|instruction|prompt))",
         re.IGNORECASE,
     )),

    # --- Privilege escalation ---
    ("privilege_escalation",
     re.compile(
         r"\b(developer\s+mode|god\s+mode|admin\s+mode|sudo\s+|as\s+(a\s+)?(system|admin|root|superuser|developer))\b",
         re.IGNORECASE,
     )),
    ("modo_privilegio",
     re.compile(
         r"\b(modo\s+(dios|administrador|sistema|desarrollador|root)|como\s+(administrador|sistema))\b",
         re.IGNORECASE,
     )),

    # --- Data / memory exfiltration ---
    ("data_exfiltration",
     re.compile(
         r"\b(leak|exfiltrate|extract|dump|steal)\s+(the\s+)?(data|instructions?|prompt|context|memory|database)\b",
         re.IGNORECASE,
     )),
]


def check_prompt_injection(text: str) -> tuple[bool, str | None]:
    """
    Returns (is_safe, matched_pattern_name).
    Scans the input for known prompt injection patterns.
    Returns (True, None) if clean, (False, pattern_name) if a threat is detected.
    """
    for pattern_name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(
                "Finance injection guardrail: pattern '%s' matched in input: '%s'",
                pattern_name,
                text[:120],
            )
            return False, pattern_name
    return True, None
