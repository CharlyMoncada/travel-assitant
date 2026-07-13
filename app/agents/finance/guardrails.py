"""
Guardrails del Agente de Finanzas.

Delega en el módulo común (guardrails_common) y re-exporta los símbolos
que el orquestador necesita, añadiendo mensajes de rechazo específicos
para el dominio de finanzas.
"""

from ..guardrails_common import (
    check_language as _check_language,
    check_prompt_injection,
    REJECTION_MESSAGE_INJECTION,
)

# Mensajes de rechazo específicos del dominio de finanzas
REJECTION_MESSAGE_LANGUAGE = (
    "Sorry, the finance assistant only supports English and Spanish.\n"
    "Lo siento, el asistente de finanzas solo admite inglés y español."
)

# Alias para el orquestador
REJECTION_MESSAGE = REJECTION_MESSAGE_LANGUAGE


def check_finance_language(text: str) -> tuple[bool, str]:
    """
    Comprueba si el texto está en inglés o español.
    Delega en guardrails_common.check_language.

    Returns:
        (is_allowed, detected_lang)
    """
    return _check_language(text)


__all__ = [
    "check_finance_language",
    "check_prompt_injection",
    "REJECTION_MESSAGE",
    "REJECTION_MESSAGE_LANGUAGE",
    "REJECTION_MESSAGE_INJECTION",
]
