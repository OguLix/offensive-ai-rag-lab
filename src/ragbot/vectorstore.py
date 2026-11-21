"""ChromaDB access: one persistent client, collections addressed by name.

Owner: A. Embeddings are computed here through the local Ollama embedding model
and passed to ChromaDB explicitly. ChromaDB's built-in embedding function is
never used, because it would silently download a different model from the
internet and make retrieval scores depend on something outside config.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import chromadb
import ollama

from ragbot.config import load_settings
from ragbot.types import Chunk

# Ollama's loopback default; .env.example exposes OLLAMA_HOST for overrides.
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"

# Cosine distance gives a bounded similarity (1 - distance) that is easy to read
# in the UI panel and in the evidence screenshots.
_COLLECTION_METADATA = {"hnsw:space": "cosine"}

# nomic-embed-text is trained with task prefixes; using them noticeably improves
# question-to-passage matching. Other models simply see a short extra prefix.
_TASK_PREFIX = {"document": "search_document: ", "query": "search_query: "}

EmbedKind = Literal["document", "query"]


def get_collection(name: str) -> Any:
    """Return an existing collection or create it; callers never touch the client."""
    settings = load_settings()
    if name not in settings.allowed_collections:
        raise ValueError(f"collection {name!r} is not listed in allowed_collections")
    return _client(settings.chroma_db_path).get_or_create_collection(
        name=name,
        embedding_function=None,
        metadata=_COLLECTION_METADATA,
    )


def delete_collection(name: str) -> None:
    """Drop a collection so it can be rebuilt from scratch; missing ones are ignored."""
    settings = load_settings()
    if name not in settings.allowed_collections:
        raise ValueError(f"collection {name!r} is not listed in allowed_collections")
    client = _client(settings.chroma_db_path)
    if name in {collection.name for collection in client.list_collections()}:
        client.delete_collection(name)


def add_chunks(
    collection: Any,
    ids: Sequence[str],
    texts: Sequence[str],
    metadatas: Sequence[dict[str, Any]],
) -> int:
    """Embed and upsert chunks; upsert keeps re-ingesting the same files idempotent."""
    if not (len(ids) == len(texts) == len(metadatas)):
        raise ValueError("ids, texts and metadatas must have the same length")
    if not ids:
        return 0
    collection.upsert(
        ids=list(ids),
        documents=list(texts),
        metadatas=[dict(meta) for meta in metadatas],
        embeddings=embed(texts, "document"),
    )
    return len(ids)


def query(collection: Any, text: str, k: int) -> list[Chunk]:
    """Return the `k` nearest chunks for `text` with scores and provenance metadata."""
    if k <= 0:
        raise ValueError("k must be a positive integer")
    if collection.count() == 0:
        return []

    raw = collection.query(
        query_embeddings=embed([text], "query"),
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        _to_chunk(chunk_id, document, metadata, distance)
        for chunk_id, document, metadata, distance in zip(
            raw["ids"][0],
            raw["documents"][0],
            raw["metadatas"][0],
            raw["distances"][0],
            strict=True,
        )
    ]


def embed(texts: Sequence[str], kind: EmbedKind) -> list[list[float]]:
    """Embed `texts` with the configured Ollama embedding model."""
    settings = load_settings()
    prefix = _TASK_PREFIX[kind]
    client = ollama.Client(host=os.getenv("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST)
    response = client.embed(
        model=settings.embedding_model,
        input=[f"{prefix}{text}" for text in texts],
    )
    return [list(vector) for vector in response.embeddings]


@lru_cache(maxsize=4)
def _client(path: Path) -> Any:
    # One client per path: ChromaDB warns when several clients open the same
    # persistent directory in one process. Telemetry is off so the lab stays offline.
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(path),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )


def _to_chunk(
    chunk_id: str,
    document: str | None,
    metadata: dict[str, Any] | None,
    distance: float,
) -> Chunk:
    meta = dict(metadata or {})
    doc_id = str(meta.pop("doc_id", chunk_id))
    source = str(meta.pop("source", ""))
    meta["chunk_id"] = chunk_id
    return Chunk(
        doc_id=doc_id,
        text=document or "",
        score=round(1.0 - float(distance), 4),
        source=source,
        meta=meta,
    )
