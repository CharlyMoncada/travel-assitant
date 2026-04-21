import json
import logging
import os
import re
from typing import Any, Dict, Optional

from ..orchestrator.mcp_tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

def get_openai_api_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY")


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-nano")


SYSTEM_PROMPT = (
    "Eres un enrutador de herramientas para un asistente de viaje. "
    "Recibe la intención del usuario y responde con un JSON válido que indique la herramienta más adecuada "
    "y el texto que debe usarse como entrada para la herramienta. "
    "Sólo responde con JSON puro."
)

TOOL_PROMPT = (
    "Herramientas disponibles:\n"
    + "\n".join(f"- {name}: {desc}" for name, desc in TOOL_DEFINITIONS.items())
    + "\n"
)

RESPONSE_PROMPT = (
    "Eres un asistente de viaje. Has recibido la salida de una herramienta y debes elaborar una respuesta "
    "natural, clara y útil para el usuario. Responde solo con texto.")

EXTRACTION_PROMPT = (
    "Eres un extractor de intención y parámetros para un asistente de viaje. "
    "Recibe un mensaje del usuario y devuelve un JSON con la intención más probable y los campos relevantes. "
    "Solo responde con JSON válido, sin explicaciones adicionales. "
    "Las intenciones posibles son: expense, reminder, budget, rules, logistics, default. "
    "Para expense extrae amount, currency, category y description si puedes. "
    "Para reminder extrae title, due_time y note. "
    "Un recordatorio puede incluir expresiones como 'check-in', 'check out', 'mañana a las 20hs', 'hoy', 'el 25 de mayo', etc. "
    "Si no estás seguro o el texto no es un gasto ni un recordatorio, usa intent default. "
    "La salida debe ser un único objeto JSON válido."
)

EXTRACTION_RESPONSE_EXAMPLE = (
    "Salida JSON esperada (ejemplo para recordatorio):\n"
    "{\"intent\": \"reminder\", \"title\": \"Check-out\", \"due_time\": \"mañana a las 20:00\", "
    "\"note\": \"recuerdame hacer el check out mañana a las 20hs\"}"
)


def is_available() -> bool:
    return openai is not None and bool(get_openai_api_key())


def llm_status() -> dict:
    return {
        "enabled": bool(get_openai_api_key()),
        "openai_installed": openai is not None,
        "available": is_available(),
        "model": get_openai_model(),
    }


def _get_openai_client():
    if openai is None:
        return None
    api_key = get_openai_api_key()
    if not api_key:
        return None
    return openai.OpenAI(api_key=api_key)


def _to_json(text: str) -> Optional[Dict[str, Any]]:
    payload = text.strip()
    if payload.startswith("```json"):
        payload = payload.split("```json", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        start = payload.find("{")
        end = payload.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(payload[start:end + 1])
            except json.JSONDecodeError:
                pass
    return None


def _extract_text_from_response(response: Any, context: str = "response") -> str:
    text = getattr(response, "output_text", None)
    logger.debug("LLM %s output_text=%r", context, text)
    if text:
        return text

    collected = []
    for item in getattr(response, "output", []) or []:
        for part in getattr(item, "content", []) or []:
            if hasattr(part, "text") and part.text:
                collected.append(part.text)

    for choice in getattr(response, "choices", []) or []:
        message = getattr(choice, "message", None)
        if message is not None and hasattr(message, "content") and message.content:
            collected.append(message.content)
        elif hasattr(choice, "text") and choice.text:
            collected.append(choice.text)

    text = "".join(collected)
    logger.debug("LLM %s extracted text=%r", context, text)
    return text


def route_tool(user_message: str) -> Optional[Dict[str, str]]:
    if not is_available():
        return None

    prompt = (
        SYSTEM_PROMPT
        + "\n"
        + TOOL_PROMPT
        + "\n"
        + "Si no puedes decidir una herramienta, usa \"default\"."
        + "\n"
        + f"Mensaje del usuario: {user_message}\n"
        + "Salida JSON esperada:\n"
        + '{"tool": "<tool_name>", "input": "<tool_input>"}'
    )

    client = _get_openai_client()
    if client is None:
        return None

    try:
        response = client.responses.create(
            model=get_openai_model(),
            input=prompt,
            max_output_tokens=250,
        )
        text = getattr(response, "output_text", None)
        if not text:
            # fallback to all message contents if output_text is missing
            collected = []
            for item in getattr(response, "output", []) or []:
                for part in getattr(item, "content", []) or []:
                    if hasattr(part, "text") and part.text:
                        collected.append(part.text)
            text = "".join(collected)

        parsed = _to_json(text)
        if parsed and parsed.get("tool") in TOOL_DEFINITIONS:
            return {
                "tool": parsed["tool"],
                "input": parsed.get("input", user_message),
            }
        logger.warning("LLM route_tool no devolvió herramienta válida: %s", text)
    except Exception as exc:
        logger.exception("Error al invocar route_tool en LLM: %s", exc)
    return None


def raw_llm_call(user_message: str, max_output_tokens: int = 250) -> Optional[Dict[str, Any]]:
    if not is_available():
        return None

    client = _get_openai_client()
    if client is None:
        return None

    try:
        logger.debug("LLM raw_llm_call request model=%s user_message=%r", get_openai_model(), user_message)
        response = client.responses.create(
            model=get_openai_model(),
            input=user_message,
            max_output_tokens=max_output_tokens,
            temperature=0.0,
        )
        logger.debug("LLM raw_llm_call responses API response type=%s", type(response).__name__)
        text = _extract_text_from_response(response, "responses")

        if not text and hasattr(client, "chat") and hasattr(client.chat, "completions"):
            logger.debug("LLM raw_llm_call fallback to chat.completions.create")
            chat_response = client.chat.completions.create(
                model=get_openai_model(),
                messages=[{"role": "user", "content": user_message}],
                max_completion_tokens=max_output_tokens,
                temperature=0.0,
            )
            logger.debug("LLM raw_llm_call chat fallback response type=%s", type(chat_response).__name__)
            text = _extract_text_from_response(chat_response, "chat")

        if not text:
            logger.warning("LLM raw_llm_call no text extracted from model response")

        logger.debug("LLM raw_llm_call final output_text=%r", text)
        return {
            "model": get_openai_model(),
            "output_text": text,
        }
    except Exception as exc:
        logger.exception("Error al invocar raw_llm_call en LLM: %s", exc)
        return {"error": str(exc)}


def extract_intent_payload(user_message: str) -> Optional[Dict[str, Any]]:
    if not is_available():
        return None

    prompt = (
        EXTRACTION_PROMPT
        + "\n"
        + TOOL_PROMPT
        + "\n"
        + f"Mensaje del usuario: {user_message}\n"
        + EXTRACTION_RESPONSE_EXAMPLE
    )

    client = _get_openai_client()
    if client is None:
        return None

    try:
        response = client.responses.create(
            model=get_openai_model(),
            input=prompt,
            max_output_tokens=250,
        )
        text = getattr(response, "output_text", None)
        if not text:
            collected = []
            for item in getattr(response, "output", []) or []:
                for part in getattr(item, "content", []) or []:
                    if hasattr(part, "text") and part.text:
                        collected.append(part.text)
            text = "".join(collected)

        parsed = _to_json(text)
        if not parsed or "intent" not in parsed:
            logger.warning("LLM extract_intent_payload no obtuvo intent válido: %s", text)
            return None

        intent = parsed["intent"]
        if intent not in TOOL_DEFINITIONS:
            logger.warning("LLM extract_intent_payload intent desconocido: %s", intent)
            return None

        payload = {"intent": intent, "input": parsed.get("input", user_message)}

        if intent == "expense":
            amount = parsed.get("amount")
            if amount is None:
                logger.warning("LLM extract_intent_payload gasto sin amount: %s", text)
                return None
            payload.update(
                {
                    "amount": float(amount),
                    "currency": parsed.get("currency", "EUR"),
                    "category": parsed.get("category", "otro"),
                    "description": parsed.get("description", user_message),
                }
            )
        elif intent == "reminder":
            due_time = parsed.get("due_time")
            if not due_time:
                logger.warning("LLM extract_intent_payload reminder sin due_time: %s", text)
                return None
            payload.update(
                {
                    "title": parsed.get("title", "Recordatorio de viaje"),
                    "due_time": due_time,
                    "note": parsed.get("note", user_message),
                }
            )

        return payload
    except Exception as exc:
        logger.exception("Error al invocar extract_intent_payload en LLM: %s", exc)
        return None


def render_llm_response(user_message: str, tool_name: str, tool_output: Any) -> Optional[str]:
    if not is_available():
        return None

    client = _get_openai_client()
    if client is None:
        return None

    tool_output_str = json.dumps(tool_output, ensure_ascii=False, indent=2)
    prompt = (
        RESPONSE_PROMPT
        + "\n\nMensaje original: "
        + user_message
        + "\nHerramienta usada: "
        + tool_name
        + "\nSalida de la herramienta:\n"
        + tool_output_str
    )
    try:
        response = client.responses.create(
            model=get_openai_model(),
            input=prompt,
            max_output_tokens=200,
        )
        text = getattr(response, "output_text", None)
        if not text:
            text = "".join(
                part.text
                for item in getattr(response, "output", [])
                if hasattr(item, "content")
                for part in getattr(item, "content", [])
                if hasattr(part, "text")
            )
        return text.strip() if text else None
    except Exception as exc:
        logger.exception("Error al generar render_llm_response: %s", exc)
        return None


def compose_rag_answer(query: str, documents: list, metadatas: list) -> str:
    """Compose answer using LLM based on retrieved RAG documents.
    
    Args:
        query: User question/query
        documents: List of document text from RAG retrieval
        metadatas: List of metadata dicts for each document
        
    Returns:
        Formatted answer with sources, with fallback to simple composition if LLM unavailable.
    """
    if not is_available():
        return _fallback_compose_answer(query, documents, metadatas)

    client = _get_openai_client()
    if client is None:
        return _fallback_compose_answer(query, documents, metadatas)

    documents_text = "\n\n".join(
        f"Documento ({m.get('source', 'unknown')}): {doc}"
        for doc, m in zip(documents, metadatas)
    )

    prompt = (
        f"Basándote en los siguientes documentos relevantes, responde la siguiente pregunta de forma clara y concisa.\n\n"
        f"Pregunta: {query}\n\n"
        f"Documentos:\n{documents_text}\n\n"
        f"Respuesta:"
    )

    try:
        response = client.chat.completions.create(
            model=get_openai_model(),
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=500,
            temperature=0.3,
        )
        answer = response.choices[0].message.content.strip()
        sources = ", ".join(m.get("source", "unknown") for m in metadatas if m)
        logger.debug("RAG LLM composition successful for query: %r", query)
        return f"{answer}\n\n(fuentes: {sources})"
    except Exception as exc:
        logger.exception("Error composing answer with LLM for RAG: %s", exc)
        return _fallback_compose_answer(query, documents, metadatas)


def _fallback_compose_answer(query: str, documents: list, metadatas: list) -> str:
    """Fallback simple composition when LLM is unavailable."""
    summary = " ".join(documents)
    sources = ", ".join(m.get("source", "unknown") for m in metadatas if m)
    return (
        f"Según los documentos más relevantes para '{query}', la información principal es: {summary} "
        f"(fuentes: {sources})."
    )
