"""
Guardarraíl de salida — enfoque híbrido: prefiltro regex rápido + inspector semántico LLM.

La arquitectura refleja la del guardarraíl de entrada:
  1. Prefiltro regex (< 1 ms, sin coste de API): captura fugas de información
     inequívocas y de alta confianza — trazas de Python, formatos conocidos de claves de API,
     tokens de plantilla, marcadores literales de prompt del sistema, marcado de llamadas a herramientas.
  2. Inspector LLM (gpt-5-nano, una llamada estructurada): detecta fugas sutiles o indirectas
     que el regex no puede expresar — secretos ofuscados o parciales, fragmentos parafraseados
     del prompt del sistema, PII involuntario de otras sesiones, código o
     detalles de implementación incrustados en la respuesta.

Justificación del diseño híbrido:
- Regex puro: excelente para firmas técnicas pero ciego ante fugas semánticas/indirectas
  ("mi clave empieza por sk-...").
- LLM puro: añade ~300 ms de latencia en cada respuesta + coste de API; excesivo para la
  mayoría de respuestas que son trivialmente limpias.
- Híbrido: la ruta determinista rápida elimina la mayoría de casos al instante; el LLM gestiona
  los matizados. Falla de forma abierta (permite el paso) ante errores de API para preservar
  la disponibilidad — la misma política que el guardarraíl de entrada.
"""

from __future__ import annotations

import logging
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.services.llm import get_openai_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mensajes de rechazo públicos
# ---------------------------------------------------------------------------

REJECTION_MESSAGE_OUTPUT_LEAK = (
    "Sorry, I encountered an internal consistency error. Let's try again."
)

REJECTION_MESSAGE_OUTPUT_ERROR = (
    "Sorry, an internal error occurred while generating the response. Please try again."
)

# ---------------------------------------------------------------------------
# Etapa 1 — Prefiltro regex
# Firmas de fuga de salida inequívocas y de alta confianza.
# ---------------------------------------------------------------------------

_OUTPUT_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Tokens de plantilla LLM en la respuesta
    ("template_token_leak",
     re.compile(
         r"(\[INST\]|<<SYS>>|<</SYS>>|<\|system\|>|<\|user\|>|\[SYSTEM\]|###\s*(system|instruction))",
         re.IGNORECASE,
     )),
    # Trazas de Python brutas y tipos de excepción comunes
    ("raw_error_leak",
     re.compile(
         r"(Traceback\s+\(most\s+recent\s+call\s+last\):"
         r"|ZeroDivisionError:|NameError:|TypeError:|AttributeError:"
         r"|ValueError:|KeyError:|ImportError:|RuntimeError:)",
         re.IGNORECASE,
     )),
    # Marcadores literales de prompt del sistema de los agentes
    ("instruction_leak",
     re.compile(
         r"(CRITICAL BEHAVIOR RULES|MANDATORY tool for answering|Strict RAG answer generator"
         r"|get_finance_system_prompt|get_reminder_system_prompt|get_recommender_system_prompt"
         r"|CRITICAL RULE.*NEVER ASK|AVAILABLE SUB-AGENTS|ROUTING RESPONSE FORMAT"
         r"|You are the Intelligent Supervisor)",
         re.IGNORECASE,
     )),
    # Patrones de clave de API / token secreto
    ("secret_leak",
     re.compile(
         r"(sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9\-_\.]{20,}"
         r"|OPENAI_API_KEY\s*=|BRAVE_API_KEY\s*=|TELEGRAM_BOT_TOKEN\s*=)",
         re.IGNORECASE,
     )),
    # Marcado interno de llamadas a herramientas/funciones
    ("tool_call_leak",
     re.compile(
         r"(<tool_call>|<function_call>|<\|tool_call\|>|\{\"tool_name\"\s*:|\"function\"\s*:\s*\"[a-z_]+\")",
         re.IGNORECASE,
     )),
]


def _check_output_patterns(text: str) -> tuple[bool, str | None]:
    """
    Retorna (is_clean, leak_type).
    is_clean=False significa que el prefiltro detectó una fuga.
    """
    for name, pattern in _OUTPUT_PATTERNS:
        if pattern.search(text):
            if name == "secret_leak":
                logger.warning("Output guardrail pre-filter: potential secret token detected")
            else:
                logger.warning("Output guardrail pre-filter: pattern '%s' matched", name)
            return False, name
    return True, None


# ---------------------------------------------------------------------------
# Etapa 2 — Inspector semántico LLM
# ---------------------------------------------------------------------------

_OUTPUT_INSPECTOR_SYSTEM_PROMPT = """\
You are a strict output safety inspector for a Travel Assistant chatbot.
Your ONLY job is to analyze the assistant's response and determine if it accidentally
leaks internal information that should never reach the end user.
You must NEVER modify or summarize the response — only classify it.

CLASSIFY AS NOT CLEAN (is_clean=false) if the response contains:

1. PARTIAL or OBFUSCATED SECRETS: hints at API keys, tokens, or passwords even without
   the full value (e.g. "my key starts with sk-", "the token ends in XYZ").

2. INDIRECT SYSTEM PROMPT LEAKAGE: the response reveals that the assistant has specific
   internal instructions, rules, or configuration beyond what a normal assistant would say.
   Examples of leaks:
     - "I am configured to route finance queries to a separate finance module."
     - "My internal rules say I cannot discuss non-European destinations."
     - "I have a prompt that tells me to always use the get_weather tool first."
   Note: saying "I can help you with travel expenses" is NOT a leak — it is a normal
   description of capability.

3. INTERNAL CODE or IMPLEMENTATION DETAILS: Python function names, class names, variable
   names, SQL queries, or internal architecture details that are not relevant to the user's
   question.

4. PII FROM OTHER SESSIONS: user data (names, expenses, reminders, preferences) that
   clearly belongs to a different conversation session or a different user account.

CLASSIFY AS CLEAN (is_clean=true) if the response is:
- A normal answer about travel, hotels, flights, weather, packing, expenses, or reminders.
- A greeting, clarification, or apology that doesn't reveal internal information.
- An explanation of the assistant's general capabilities (NOT implementation specifics).
- A list of expenses or reminders for multiple destinations (Rome, Berlin, NYC, etc.) —
  a single user can have many trips planned simultaneously; this is NOT cross-session PII.

IMPORTANT — cross_session_pii means data from a DIFFERENT USER, not data about multiple
trips or destinations from the SAME user. Only flag it when the response contains
information that clearly identifies someone other than the person being served
(e.g. a different name, a different account ID, or data that is completely
unrelated to the current user's own travel activity).

When in doubt, classify as clean to avoid blocking legitimate responses.
"""


class OutputIntegrityDecision(BaseModel):
    is_clean: bool = Field(
        description="True if the response is safe to return to the user. False if it contains an indirect information leak."
    )
    leak_type: str | None = Field(
        default=None,
        description="One of: 'partial_secret_leak', 'indirect_prompt_leak', 'code_leak', 'cross_session_pii'. Null if is_clean=True.",
    )


# ---------------------------------------------------------------------------
# Singleton del cliente LLM para el guardarraíl de salida.
# Se inicializa una sola vez al cargar el módulo, evitando el overhead
# de crear una nueva instancia de ChatOpenAI en cada respuesta.
# ---------------------------------------------------------------------------

def _build_output_guardrail_llm():
    """Construye el inspector LLM estructurado de salida. Llamado una sola vez."""
    timeout_val = float(os.getenv("GUARDRAIL_TIMEOUT", "5.0"))
    llm = ChatOpenAI(
        model=get_openai_model(),
        temperature=0.0,
        request_timeout=timeout_val,
        max_retries=0,
    )
    return llm.with_structured_output(OutputIntegrityDecision)


_OUTPUT_GUARDRAIL_STRUCTURED_LLM = _build_output_guardrail_llm()


# Whitelist determinista de respuestas triviales y confirmaciones benignas conocidas.
_TRIVIAL_BENIGN_OUTPUTS: set[str] = {
    "de nada", "un placer", "de nada, ¡un placer!", "¡de nada!",
    "you're welcome", "my pleasure", "happy to help!", "¡hasta luego!",
    "gasto registrado", "recordatorio creado", "gasto eliminado", "recordatorio eliminado",
    "gasto modificado", "recordatorio modificado"
}


async def check_output_integrity(text: str) -> tuple[bool, str | None]:
    """
    Verificación completa de integridad de salida híbrida.

    Retorna:
        (is_clean, leak_type)

    Flujo:
        1. Verificación determinista en Lista Blanca para respuestas breves benignas.
        2. Prefiltro regex (instantáneo, sin llamada a la API).
        3. Inspector semántico LLM (asíncrono, salida estructurada).
        4. En caso de error de API del LLM: registrar advertencia y permitir la respuesta (fail-open).
    """
    # Etapa 0 — Lista blanca determinista para frases benignas conocidas (0 ms, 100% seguro)
    normalized_output = text.strip().lower().strip(".!?,:;")
    if normalized_output in _TRIVIAL_BENIGN_OUTPUTS:
        return True, None

    # Etapa 1 — prefiltro regex
    is_clean_regex, regex_leak_type = _check_output_patterns(text)
    if not is_clean_regex:
        return False, regex_leak_type

    # Etapa 2 — inspección semántica LLM (usa el singleton del módulo)
    try:
        decision: OutputIntegrityDecision = await _OUTPUT_GUARDRAIL_STRUCTURED_LLM.ainvoke([
            SystemMessage(content=_OUTPUT_INSPECTOR_SYSTEM_PROMPT),
            HumanMessage(content=text),
        ])

        logger.info(
            "LLM output guardrail decision: is_clean=%s, leak_type=%s",
            decision.is_clean,
            decision.leak_type,
        )

        if not decision.is_clean:
            return False, decision.leak_type or "semantic_leak"

        return True, None

    except Exception as exc:
        logger.warning(
            "LLM output guardrail API error — failing open (response allowed): %s", exc
        )
        return True, None


