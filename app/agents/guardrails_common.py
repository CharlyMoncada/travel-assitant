"""
Módulo de guardrails compartido entre los agentes especializados del Travel Assistant.

Proporciona dos capas de seguridad reutilizables:
  1. Guardrail de idioma  — bloquea cualquier texto que no sea inglés (en) o español (es).
  2. Guardrail de prompt injection — detecta patrones de manipulación del agente mediante
     expresiones regulares compiladas sin coste de LLM ni latencia apreciable.

Uso:
    from app.agents.guardrails_common import (
        check_language,
        check_prompt_injection,
        REJECTION_MESSAGE_LANGUAGE,
        REJECTION_MESSAGE_INJECTION,
    )
"""

import re
import logging
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes compartidas
# ---------------------------------------------------------------------------

ALLOWED_LANGUAGES = {"en", "es"}

REJECTION_MESSAGE_LANGUAGE = (
    "Sorry, this assistant only supports English and Spanish.\n"
    "Lo siento, este asistente solo admite inglés y español."
)

REJECTION_MESSAGE_INJECTION = (
    "This request has been blocked for security reasons.\n"
    "Esta solicitud ha sido bloqueada por razones de seguridad."
)

# ---------------------------------------------------------------------------
# Guardrail 1 — Idioma
# ---------------------------------------------------------------------------

def check_language(text: str) -> tuple[bool, str]:
    """
    Comprueba si el texto está en inglés o español.

    Returns:
        (is_allowed, detected_lang)
        is_allowed — True si el idioma está en la lista permitida.
        detected_lang — Código ISO 639-1 detectado (p. ej. 'en', 'es', 'fr').
    """
    try:
        lang = detect(text)
    except LangDetectException:
        logger.warning("Language detection failed, defaulting to 'unknown'")
        lang = "unknown"

    allowed = lang in ALLOWED_LANGUAGES
    logger.info("Language guardrail: detected='%s', allowed=%s", lang, allowed)
    return allowed, lang


# ---------------------------------------------------------------------------
# Guardrail 2 — Prompt injection
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    # --- Anulación de instrucciones ---
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

    # --- Suplantación de rol ---
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

    # --- Extracción del prompt de sistema ---
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

    # --- Tokens de plantilla LLM ---
    ("template_tokens",
     re.compile(
         r"(\[INST\]|<<SYS>>|<</SYS>>|<\|system\|>|<\|user\|>|\[SYSTEM\]|###\s*(system|instruction|prompt))",
         re.IGNORECASE,
     )),

    # --- Escalada de privilegios ---
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

    # --- Exfiltración de datos ---
    ("data_exfiltration",
     re.compile(
         r"\b(leak|exfiltrate|extract|dump|steal)\s+(the\s+)?(data|instructions?|prompt|context|memory|database)\b",
         re.IGNORECASE,
     )),
]


def check_prompt_injection(text: str) -> tuple[bool, str | None]:
    """
    Escanea el texto en busca de patrones de prompt injection conocidos.

    Returns:
        (is_safe, matched_pattern_name)
        is_safe — True si el texto no coincide con ningún patrón de ataque.
        matched_pattern_name — Nombre del patrón detectado, o None si el texto es seguro.
    """
    for pattern_name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(
                "Injection guardrail: pattern '%s' matched in input: '%s'",
                pattern_name,
                text[:120],
            )
            return False, pattern_name
    return True, None
