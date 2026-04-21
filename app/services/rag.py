import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import pdfplumber

logger = logging.getLogger(__name__)

PERSIST_DIR = Path(__file__).resolve().parent.parent / "chromadb_store"
COLLECTION_NAME = "travel_rules"
RAG_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "rag_docs"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


_collection = None


def _build_client():
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.Client(
        Settings(
            is_persistent=True,
            persist_directory=str(PERSIST_DIR),
        )
    )


def _build_embedding_function():
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text content from a PDF file."""
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""


def _load_document_files() -> List[Dict[str, str]]:
    documents = []
    if not RAG_DOCS_DIR.exists():
        return documents

    # Process .txt files
    for text_file in sorted(RAG_DOCS_DIR.glob("*.txt")):
        content = text_file.read_text(encoding="utf-8").strip()
        if not content:
            continue
        documents.append(
            {
                "id": f"file_{text_file.stem}",
                "document": content,
                "metadata": {
                    "topic": "normativa",
                    "source": text_file.name,
                    "type": "text",
                },
            }
        )

    # Process .pdf files
    for pdf_file in sorted(RAG_DOCS_DIR.glob("*.pdf")):
        content = _extract_text_from_pdf(pdf_file)
        if not content:
            logger.warning(f"No text extracted from PDF: {pdf_file.name}")
            continue
        documents.append(
            {
                "id": f"file_{pdf_file.stem}",
                "document": content,
                "metadata": {
                    "topic": "normativa",
                    "source": pdf_file.name,
                    "type": "pdf",
                },
            }
        )

    logger.info(f"Loaded {len(documents)} documents from {RAG_DOCS_DIR}")
    return documents


def _get_existing_ids(collection) -> set:
    try:
        response = collection.get(include=["ids"])
        return set(response.get("ids", []))
    except Exception:
        return set()


def init_rag():
    global _collection
    if _collection is not None:
        return _collection

    client = _build_client()
    embedding_function = _build_embedding_function()
    _collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
    )

    documents = _load_document_files()
    existing_ids = _get_existing_ids(_collection)
    new_docs = [doc for doc in documents if doc["id"] not in existing_ids]

    if new_docs:
        _collection.add(
            ids=[doc["id"] for doc in new_docs],
            documents=[doc["document"] for doc in new_docs],
            metadatas=[doc["metadata"] for doc in new_docs],
        )

    return _collection


def query_normative_documents(query: str, n_results: int = 3) -> Tuple[str, List[Dict[str, str]]]:
    from .llm import compose_rag_answer
    
    collection = init_rag()
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    if not documents:
        return (
            "No se encontró documentación específica en este prototipo. "
            "En la siguiente iteración se añadirá más contenido y una lógica de generación completa.",
            [],
        )

    answer = compose_rag_answer(query, documents, metadatas)
    sources = [
        {"document": doc, "metadata": metadata}
        for doc, metadata in zip(documents, metadatas)
    ]
    return answer, sources


def rag_status() -> dict:
    collection = init_rag()
    try:
        count = collection.count()
    except Exception:
        count = None
    return {
        "collection_name": COLLECTION_NAME,
        "document_count": count,
        "persist_directory": str(PERSIST_DIR),
    }
