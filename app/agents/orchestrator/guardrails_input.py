import re
import logging
from langdetect import detect_langs, LangDetectException, DetectorFactory

# Set seed for reproducibility
DetectorFactory.seed = 0

# Warm up detector to load profiles at startup
try:
    detect_langs("warmup")
except Exception:
    pass

logger = logging.getLogger(__name__)

ALLOWED_LANGUAGES = {"en", "es"}

# User-facing bilingual rejection messages
REJECTION_MESSAGE_LANGUAGE = (
    "Sorry, this assistant only supports English and Spanish.\n"
    "Lo siento, este asistente solo admite inglés y español."
)

REJECTION_MESSAGE_INJECTION = (
    "This request has been blocked for security reasons.\n"
    "Esta solicitud ha sido bloqueada por razones de seguridad."
)

# Minimum number of words required to run language detection.
_MIN_WORDS_FOR_LANG_DETECTION = 3

# Minimum confidence required from langdetect before blocking.
_MIN_LANG_CONFIDENCE = 0.85

# A curated set of words/tokens that are strictly Spanish
_SPANISH_INDICATORS = {
    "el", "los", "las", "del", "al", "y", "unos", "unas", "mi", "mis",
    "dónde", "donde", "cómo", "qué", "cuándo", "cuando",
    "quiero", "tengo", "puedes", "dime", "hacer", "hablar", "borrar", "borra", "borres", "borro", "borrado", "encuentra", "pon", "avísame", "notifícame",
    "viaje", "viajes", "vuelo", "vuelos", "avión", "tren", "coche", "habitación", "desayuno", "cerca", "precio", "tarjeta", "estación",
    "mañana", "hoy", "ayer", "año", "años",
    "recordatorio", "recordatorios", "datos", "nuevo", "bueno", "pero", "muy", "gracias", "ayuda", "hijo", "hija", "hijos", "hijas", "hermano", "hermana"
}


def check_language(text: str) -> tuple[bool, str]:
    word_count = len(text.split())
    if word_count < _MIN_WORDS_FOR_LANG_DETECTION:
        logger.info(
            "Language guardrail: input too short (%d word(s)), skipping detection — allowed",
            word_count,
        )
        return True, "unknown"

    try:
        results = detect_langs(text)
        top = results[0]
        lang: str = top.lang
        confidence: float = top.prob
    except LangDetectException:
        logger.warning("Language detection failed, defaulting to allowed")
        return True, "unknown"

    if lang not in ALLOWED_LANGUAGES:
        words = set(re.findall(r'\b\w+\b', text.lower()))
        if not words.isdisjoint(_SPANISH_INDICATORS):
            logger.info(
                "Language guardrail: detected='%s' (conf=%.2f) but contains Spanish indicators. "
                "Overriding to 'es'.",
                lang,
                confidence,
            )
            lang = "es"

    if lang in ALLOWED_LANGUAGES:
        logger.info(
            "Language guardrail: detected='%s' (conf=%.2f), allowed=True",
            lang,
            confidence,
        )
        return True, lang

    if confidence < _MIN_LANG_CONFIDENCE:
        logger.info(
            "Language guardrail: detected='%s' (conf=%.2f < threshold), "
            "confidence too low — allowed",
            lang,
            confidence,
        )
        return True, lang

    logger.info(
        "Language guardrail: detected='%s' (conf=%.2f), allowed=False",
        lang,
        confidence,
    )
    return False, lang


_INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
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
    ("new_instructions_en",
     re.compile(
         r"(new|updated?|actual)\s+instructions?\s*:",
         re.IGNORECASE,
     )),
    ("new_instructions_es",
     re.compile(
         r"nuevas?\s+instrucciones?\s*:",
         re.IGNORECASE,
     )),
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
    ("what_are_instructions_en",
     re.compile(
         r"what\s+are\s+your\s+(instructions?|rules?|prompts?|guidelines?|constraints?)",
         re.IGNORECASE,
     )),
    ("what_are_instructions_es",
     re.compile(
         r"cu[aá]les?\s+son\s+tus\s+(instrucciones?|reglas?|restricciones?)",
         re.IGNORECASE,
     )),
    ("template_tokens",
     re.compile(
         r"(\[INST\]|<<SYS>>|<</SYS>>|<\|system\|>|<\|user\|>|\[SYSTEM\]|###\s*(system|instruction|prompt))",
         re.IGNORECASE,
     )),
    ("privilege_escalation_en",
     re.compile(
         r"\b(developer\s+mode|god\s+mode|admin\s+mode|sudo\s+|as\s+(a\s+)?(system|admin|root|superuser|developer))\b",
         re.IGNORECASE,
     )),
    ("privilege_escalation_es",
     re.compile(
         r"\b(modo\s+(dios|administrador|sistema|desarrollador|root)|como\s+(administrador|sistema))\b",
         re.IGNORECASE,
     )),
    ("data_exfiltration",
     re.compile(
         r"\b(leak|exfiltrate|extract|dump|steal)\s+(the\s+)?(data|instructions?|prompt|context|memory|database)\b",
         re.IGNORECASE,
     )),
]


def check_prompt_injection(text: str) -> tuple[bool, str | None]:
    for pattern_name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(
                "Injection guardrail: pattern '%s' matched in input: '%s'",
                pattern_name,
                text[:120],
            )
            return False, pattern_name
    return True, None
