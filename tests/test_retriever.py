"""Retriever tests; the vector store and sanitizer are faked, so no ChromaDB or Ollama needed."""

from __future__ import annotations

import pytest

from ragbot import retriever, vectorstore
from ragbot.mitigations import retrieval_sanitizer
from ragbot.types import Chunk, MitigationFlags


def _chunk(doc_id: str) -> Chunk:
    return Chunk(
        doc_id=doc_id,
        text=f"isi {doc_id}",
        score=0.5,
        source=f"data/corpus/{doc_id}.md",
    )


@pytest.fixture()
def faked_store(monkeypatch: pytest.MonkeyPatch) -> dict:
    calls: dict = {}

    def fake_get_collection(name: str) -> str:
        calls["collection"] = name
        return f"store:{name}"

    def fake_query(store: str, text: str, k: int) -> list[Chunk]:
        calls["store"] = store
        calls["text"] = text
        calls["k"] = k
        return [_chunk("doc-1"), _chunk("doc-2")]

    monkeypatch.setattr(vectorstore, "get_collection", fake_get_collection)
    monkeypatch.setattr(vectorstore, "query", fake_query)
    return calls


def test_retrieve_forwards_question_collection_and_k(faked_store: dict) -> None:
    retriever.retrieve("Jam layanan?", "kb_clean", 3, MitigationFlags())

    assert faked_store == {
        "collection": "kb_clean",
        "store": "store:kb_clean",
        "text": "Jam layanan?",
        "k": 3,
    }


def test_retrieve_returns_chunks_in_retrieval_order(faked_store: dict) -> None:
    chunks = retriever.retrieve("Jam layanan?", "kb_clean", 2, MitigationFlags())

    assert [chunk.doc_id for chunk in chunks] == ["doc-1", "doc-2"]


def test_retrieve_skips_sanitizer_when_flag_is_disabled(
    faked_store: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_called(chunks: list[Chunk]) -> list[Chunk]:
        raise AssertionError("sanitizer must not run while the flag is off")

    monkeypatch.setattr(retrieval_sanitizer, "apply", fail_if_called)

    retriever.retrieve("Jam layanan?", "kb_clean", 2, MitigationFlags())


def test_retrieve_sanitizes_chunks_when_flag_is_enabled(
    faked_store: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[list[Chunk]] = []
    cleaned = [_chunk("doc-1")]

    def fake_apply(chunks: list[Chunk]) -> list[Chunk]:
        received.append(chunks)
        return cleaned

    monkeypatch.setattr(retrieval_sanitizer, "apply", fake_apply)

    chunks = retriever.retrieve(
        "Jam layanan?", "kb_clean", 2, MitigationFlags(retrieval_sanitizer=True)
    )

    assert chunks == cleaned
    assert [chunk.doc_id for chunk in received[0]] == ["doc-1", "doc-2"]


def test_retrieve_rejects_non_positive_k(faked_store: dict) -> None:
    with pytest.raises(ValueError):
        retriever.retrieve("Jam layanan?", "kb_clean", 0, MitigationFlags())
