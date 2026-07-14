import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

def get_openai_api_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY")


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5-nano")


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
        "You are a strict RAG answer generator for travel regulations.\n"
        "Answer ONLY using the provided documents.\n"
        "Do NOT use external knowledge.\n"
        "Do NOT infer country-specific requirements unless the documents explicitly mention them.\n"
        "If the documents do not contain enough specific information, say exactly that.\n"
        "Reply in the same language as the question.\n\n"
        f"Question: {query}\n\n"
        f"Documents:\n{documents_text}\n\n"
        "Answer:"
    )

    try:
        response = client.chat.completions.create(
            model=get_openai_model(),
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=500,
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
