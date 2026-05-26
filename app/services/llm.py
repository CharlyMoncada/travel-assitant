import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

def get_openai_api_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY")


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-nano")


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
        f"Document ({m.get('source', 'unknown')}): {doc}"
        for doc, m in zip(documents, metadatas)
    )

    prompt = (
        f"Based on the following relevant documents, answer the following question clearly and concisely.\n\n"
        f"Question: {query}\n\n"
        f"Documents:\n{documents_text}\n\n"
        f"Answer:"
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
        return f"{answer}\n\n(sources: {sources})"
    except Exception as exc:
        logger.exception("Error composing answer with LLM for RAG: %s", exc)
        return _fallback_compose_answer(query, documents, metadatas)


def _fallback_compose_answer(query: str, documents: list, metadatas: list) -> str:
    """Fallback simple composition when LLM is unavailable."""
    summary = " ".join(documents)
    sources = ", ".join(m.get("source", "unknown") for m in metadatas if m)
    return (
        f"According to the most relevant documents for '{query}', the main information is: {summary} "
        f"(sources: {sources})."
    )
