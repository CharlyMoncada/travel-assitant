"""
Guardrails del Agente de Recordatorios.

Delega en el módulo común (guardrails_common) y re-exporta los símbolos
que el orquestador necesita, añadiendo mensajes de rechazo específicos
para el dominio de recordatorios.
"""

from ..guardrails_common import (
    check_language as _check_language,
    check_prompt_injection,
    REJECTION_MESSAGE_INJECTION,
)

# Mensajes de rechazo específicos del dominio de recordatorios
REJECTION_MESSAGE_LANGUAGE = (
    "Sorry, the reminder assistant only supports English and Spanish.\n"
    "Lo siento, el asistente de recordatorios solo admite inglés y español."
)

# Alias para el orquestador
REJECTION_MESSAGE = REJECTION_MESSAGE_LANGUAGE


def check_reminder_language(text: str) -> tuple[bool, str]:
    """
    Comprueba si el texto está en inglés o español.
    Delega en guardrails_common.check_language.

    Returns:
        (is_allowed, detected_lang)
    """
    return _check_language(text)


__all__ = [
    "check_reminder_language",
    "check_prompt_injection",
    "REJECTION_MESSAGE",
    "REJECTION_MESSAGE_LANGUAGE",
    "REJECTION_MESSAGE_INJECTION",
]
