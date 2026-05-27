import hashlib
import logging
import re
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional, Tuple

import chromadb
import pdfplumber
from chromadb.config import Settings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = logging.getLogger(__name__)

PERSIST_DIR = Path(__file__).resolve().parent.parent / "chromadb_store"
COLLECTION_NAME = "travel_rules"
RAG_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "rag_docs"

# Valores fijos en código, sin .env
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
UPSERT_BATCH_SIZE = 100
QUERY_CANDIDATES = 15
MAX_DISTANCE = 0.50

PDF_NOISE_PATTERNS = [
    r"\b\d{1,2}/\d{1,2}/\d{2,4},\s+\d{1,2}:\d{2}\s*(?:AM|PM)\b",
    r"\bYour Europe\b",
    r"\bDocumentos de viaje para nacionales de países no pertenecientes a la UE\b",
    r"https?://\S+",
    r"\b\d+/\d+\b",
    r"\bES español\b",
    r"\bBúsqueda\b",
    r"\bMENÚ\b",
    r"\bUcrania\b",
    r"^\s*-\s*ES español\s*",
    r"\bRequisitos de pasaporte, de entrada y de visado\b",
    r"\+\s*tres meses adicionales",
]

_collection = None
_collection_lock = Lock()


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


def _remove_pdf_noise(text: str) -> str:
    cleaned = text
    for pattern in PDF_NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = text.replace("-\n", "")
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _content_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _safe_source_key(source_name: str) -> str:
    return hashlib.sha1(source_name.encode("utf-8")).hexdigest()[:12]


def _last_words(text: str, max_words: int = 30) -> str:
    words = text.split()
    if not words:
        return ""
    return " ".join(words[-max_words:])


def _split_large_unit(unit: str, chunk_size: int, overlap: int) -> List[str]:
    if len(unit) <= chunk_size:
        return [unit]

    pieces: List[str] = []
    step = max(1, chunk_size - overlap)
    start = 0

    while start < len(unit):
        end = min(len(unit), start + chunk_size)
        piece = unit[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(unit):
            break
        start += step

    return pieces


def _chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    text = _normalize_text(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: List[str] = []

    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            units.append(paragraph)
            continue

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
        if not sentences:
            units.extend(_split_large_unit(paragraph, chunk_size, overlap))
            continue

        for sentence in sentences:
            if len(sentence) <= chunk_size:
                units.append(sentence)
            else:
                units.extend(_split_large_unit(sentence, chunk_size, overlap))

    chunks: List[str] = []
    current = ""

    for unit in units:
        candidate = f"{current}\n{unit}".strip() if current else unit

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if overlap > 0 and chunks:
            tail = _last_words(chunks[-1], max_words=30)
            current = f"{tail}\n{unit}".strip() if tail else unit

            if len(current) > chunk_size:
                chunks.extend(_split_large_unit(current, chunk_size, overlap))
                current = ""
        else:
            current = unit

    if current:
        chunks.append(current)

    deduped: List[str] = []
    seen = set()

    for chunk in chunks:
        normalized = chunk.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)

    return deduped


def _extract_pdf_pages(pdf_path: Path) -> List[Tuple[int, str]]:
    pages: List[Tuple[int, str]] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                page_text = _remove_pdf_noise(page_text)
                page_text = _normalize_text(page_text)

                if page_text:
                    pages.append((page_number, page_text))

    except Exception as exc:
        logger.exception("Error extracting PDF %s: %s", pdf_path, exc)

    return pages


def _build_chunks_from_text_file(text_file: Path) -> List[Dict[str, object]]:
    content = _normalize_text(text_file.read_text(encoding="utf-8"))

    if not content:
        return []

    source = text_file.name
    source_hash = _content_hash(content)
    source_key = _safe_source_key(source)

    chunks = _chunk_text(content)
    documents: List[Dict[str, object]] = []

    for chunk_index, chunk in enumerate(chunks):
        documents.append(
            {
                "id": f"{source_key}:{source_hash}:{chunk_index:05d}",
                "document": chunk,
                "metadata": {
                    "topic": "normativa",
                    "source": source,
                    "type": "text",
                    "page": 0,
                    "chunk_index": chunk_index,
                    "content_hash": source_hash,
                },
            }
        )

    return documents


def _build_chunks_from_pdf_file(pdf_file: Path) -> List[Dict[str, object]]:
    pages = _extract_pdf_pages(pdf_file)

    if not pages:
        logger.warning("No text extracted from PDF: %s", pdf_file.name)
        return []

    source = pdf_file.name
    full_text = "\n".join(text for _, text in pages)
    source_hash = _content_hash(full_text)
    source_key = _safe_source_key(source)

    documents: List[Dict[str, object]] = []
    global_chunk_index = 0

    for page_number, page_text in pages:
        page_chunks = _chunk_text(page_text)

        for page_chunk_index, chunk in enumerate(page_chunks):
            documents.append(
                {
                    "id": f"{source_key}:{source_hash}:{page_number:04d}:{page_chunk_index:04d}",
                    "document": chunk,
                    "metadata": {
                        "topic": "normativa",
                        "source": source,
                        "type": "pdf",
                        "page": page_number,
                        "chunk_index": global_chunk_index,
                        "content_hash": source_hash,
                    },
                }
            )
            global_chunk_index += 1

    return documents


def _load_document_chunks() -> List[Dict[str, object]]:
    documents: List[Dict[str, object]] = []

    if not RAG_DOCS_DIR.exists():
        logger.warning("RAG docs dir does not exist: %s", RAG_DOCS_DIR)
        return documents

    for text_file in sorted(RAG_DOCS_DIR.glob("*.txt")):
        documents.extend(_build_chunks_from_text_file(text_file))

    for pdf_file in sorted(RAG_DOCS_DIR.glob("*.pdf")):
        documents.extend(_build_chunks_from_pdf_file(pdf_file))

    logger.info("Loaded %s chunks from %s", len(documents), RAG_DOCS_DIR)
    return documents


def _iter_batches(
    items: List[Dict[str, object]],
    batch_size: int,
) -> Iterable[List[Dict[str, object]]]:
    for index in range(0, len(items), batch_size):
        yield items[index:index + batch_size]


def _get_indexed_sources(collection) -> Dict[str, str]:
    try:
        response = collection.get(include=["metadatas"])
    except Exception as exc:
        logger.warning("Could not inspect existing collection state: %s", exc)
        return {}

    source_to_hash: Dict[str, str] = {}

    for metadata in response.get("metadatas", []) or []:
        source = metadata.get("source")
        content_hash = metadata.get("content_hash")

        if source and content_hash and source not in source_to_hash:
            source_to_hash[source] = content_hash

    return source_to_hash


def _sync_collection(collection, chunks: List[Dict[str, object]]) -> None:
    current_sources: Dict[str, str] = {}

    for item in chunks:
        metadata = item["metadata"]
        current_sources[metadata["source"]] = metadata["content_hash"]

    indexed_sources = _get_indexed_sources(collection)

    removed_sources = set(indexed_sources) - set(current_sources)

    changed_or_new_sources = [
        source
        for source, content_hash in current_sources.items()
        if indexed_sources.get(source) != content_hash
    ]

    for source in removed_sources:
        logger.info("Deleting removed source from index: %s", source)
        collection.delete(where={"source": source})

    if not changed_or_new_sources:
        return

    for source in changed_or_new_sources:
        logger.info("Refreshing source in index: %s", source)
        collection.delete(where={"source": source})

    chunks_to_index = [
        item
        for item in chunks
        if item["metadata"]["source"] in changed_or_new_sources
    ]

    for batch in _iter_batches(chunks_to_index, UPSERT_BATCH_SIZE):
        collection.add(
            ids=[item["id"] for item in batch],
            documents=[item["document"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
        )

    logger.info("Indexed %s chunks", len(chunks_to_index))


def init_rag():
    global _collection

    if _collection is not None:
        return _collection

    with _collection_lock:
        if _collection is not None:
            return _collection

        client = _build_client()
        embedding_function = _build_embedding_function()

        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

        chunks = _load_document_chunks()
        _sync_collection(_collection, chunks)

    return _collection


def _prepare_ranked_sources(
    results: Dict[str, List[List[object]]],
    n_results: int,
    max_distance: Optional[float],
) -> List[Dict[str, object]]:
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    ranked: List[Dict[str, object]] = []
    seen = set()

    for document, metadata, distance in zip(documents, metadatas, distances):
        if max_distance is not None and distance is not None and float(distance) > max_distance:
            continue

        key = (
            metadata.get("source"),
            metadata.get("page"),
            metadata.get("chunk_index"),
        )

        if key in seen:
            continue

        seen.add(key)

        ranked.append(
            {
                "document": document,
                "metadata": metadata,
                "distance": float(distance) if distance is not None else None,
                "score": round(1 - float(distance), 4) if distance is not None else None,
            }
        )

        if len(ranked) >= n_results:
            break

    return ranked


def query_normative_documents(
    query: str,
    n_results: int = 3,
) -> Tuple[str, List[Dict[str, object]]]:
    from .llm import compose_rag_answer

    normalized_query = _normalize_text(query)

    if not normalized_query:
        return "La consulta está vacía.", []

    collection = init_rag()
    candidate_count = max(n_results * 3, QUERY_CANDIDATES)

    results = collection.query(
        query_texts=[normalized_query],
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    sources = _prepare_ranked_sources(
        results=results,
        n_results=n_results,
        max_distance=MAX_DISTANCE,
    )

    if sources and sources[0].get("distance") is not None and sources[0]["distance"] > 0.45:
        return (
            "No encontré documentación suficientemente específica para responder con seguridad.",
            sources,
        )

    answer = compose_rag_answer(
        normalized_query,
        [item["document"] for item in sources],
        [item["metadata"] for item in sources],
    )

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
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "query_candidates": QUERY_CANDIDATES,
        "max_distance": MAX_DISTANCE,
    }