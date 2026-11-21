"""Vector store tests.

Unit tests use a real ChromaDB in a temp folder but a fake embedding, so they
need neither Ollama nor network. The integration test talks to local Ollama.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
from pathlib import Path

import pytest

from ragbot import vectorstore
from ragbot.config import load_settings
from ragbot.types import Chunk

# A tiny vocabulary-based embedding: texts sharing words get close vectors,
# which is enough to check ranking and score direction deterministically.
_VOCAB = ("jam", "layanan", "biaya", "administrasi", "kontak", "pendaftaran")


def _fake_vector(text: str) -> list[float]:
    words = text.lower().replace("?", " ").split()
    vector = [float(sum(word.startswith(term) for word in words)) for term in _VOCAB]
    # A small hash-based component keeps unrelated texts from becoming zero vectors.
    vector.append(int(hashlib.md5(text.encode()).hexdigest()[:4], 16) / 65535 * 0.01 + 0.01)
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector]


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    settings = dataclasses.replace(load_settings(), chroma_db_path=tmp_path / "chroma")
    calls: dict = {"embed": []}

    def fake_embed(texts: list[str], kind: str) -> list[list[float]]:
        calls["embed"].append((kind, list(texts)))
        return [_fake_vector(text) for text in texts]

    monkeypatch.setattr(vectorstore, "load_settings", lambda: settings)
    monkeypatch.setattr(vectorstore, "embed", fake_embed)
    vectorstore._client.cache_clear()
    yield calls
    vectorstore._client.cache_clear()


def _seed(collection: object) -> None:
    vectorstore.add_chunks(
        collection,
        ids=["jam::0", "biaya::0", "kontak::0"],
        texts=[
            "Jam layanan Senin sampai Jumat 08.00-16.00.",
            "Biaya administrasi Rp25.000 per permohonan.",
            "Kontak layanan lewat email.",
        ],
        metadatas=[
            {"doc_id": "jam", "source": "data/corpus/02_jam_layanan.md", "chunk_index": 0},
            {"doc_id": "biaya", "source": "data/corpus/03_biaya.md", "chunk_index": 0},
            {"doc_id": "kontak", "source": "data/corpus/05_kontak.md", "chunk_index": 0},
        ],
    )


def test_get_collection_rejects_names_outside_whitelist(store: dict) -> None:
    with pytest.raises(ValueError, match="allowed_collections"):
        vectorstore.get_collection("kb_lain")


def test_query_on_empty_collection_returns_nothing_without_embedding(store: dict) -> None:
    collection = vectorstore.get_collection("kb_clean")

    assert vectorstore.query(collection, "Jam layanan?", 3) == []
    assert store["embed"] == []


def test_query_returns_ranked_chunks_with_provenance(store: dict) -> None:
    collection = vectorstore.get_collection("kb_clean")
    _seed(collection)

    chunks = vectorstore.query(collection, "Jam layanan?", 2)

    assert len(chunks) == 2
    assert all(isinstance(chunk, Chunk) for chunk in chunks)
    top = chunks[0]
    assert top.doc_id == "jam"
    assert top.source == "data/corpus/02_jam_layanan.md"
    assert top.text.startswith("Jam layanan")
    assert top.meta == {"chunk_index": 0, "chunk_id": "jam::0"}
    assert chunks[0].score >= chunks[1].score
    assert -1.0 <= top.score <= 1.0
    assert store["embed"][-1] == ("query", ["Jam layanan?"])


def test_add_chunks_is_idempotent_and_embeds_as_documents(store: dict) -> None:
    collection = vectorstore.get_collection("kb_clean")
    _seed(collection)
    _seed(collection)

    assert collection.count() == 3
    assert {kind for kind, _ in store["embed"]} == {"document"}


def test_add_chunks_validates_lengths(store: dict) -> None:
    collection = vectorstore.get_collection("kb_clean")

    with pytest.raises(ValueError, match="same length"):
        vectorstore.add_chunks(collection, ["a"], ["x", "y"], [{}])
    assert vectorstore.add_chunks(collection, [], [], []) == 0


def test_query_rejects_non_positive_k(store: dict) -> None:
    collection = vectorstore.get_collection("kb_clean")

    with pytest.raises(ValueError, match="positive"):
        vectorstore.query(collection, "Jam layanan?", 0)


def test_collections_are_isolated_and_deletable(store: dict) -> None:
    clean = vectorstore.get_collection("kb_clean")
    _seed(clean)
    poisoned = vectorstore.get_collection("kb_poisoned")

    assert poisoned.count() == 0
    vectorstore.delete_collection("kb_poisoned")
    vectorstore.delete_collection("kb_poisoned")  # missing collection is not an error
    assert vectorstore.get_collection("kb_clean").count() == 3


def test_embed_uses_configured_model_and_task_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class FakeClient:
        def __init__(self, host: str) -> None:
            captured["host"] = host

        def embed(self, model: str, input: list[str]) -> object:
            captured["model"] = model
            captured["input"] = input
            return type("Resp", (), {"embeddings": [[0.1, 0.2]] * len(input)})()

    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.setattr(vectorstore.ollama, "Client", FakeClient)

    vectors = vectorstore.embed(["Jam layanan?"], "query")

    assert vectors == [[0.1, 0.2]]
    assert captured["host"] == vectorstore.DEFAULT_OLLAMA_HOST
    assert captured["model"] == load_settings().embedding_model
    assert captured["input"] == ["search_query: Jam layanan?"]


@pytest.mark.integration
def test_real_embedding_ranks_matching_passage_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = dataclasses.replace(load_settings(), chroma_db_path=tmp_path / "chroma")
    monkeypatch.setattr(vectorstore, "load_settings", lambda: settings)
    vectorstore._client.cache_clear()
    try:
        collection = vectorstore.get_collection("kb_clean")
        try:
            _seed(collection)
        except ConnectionError:
            pytest.skip("Ollama is not running on localhost")
        chunks = vectorstore.query(collection, "Berapa biaya administrasinya?", 1)
        assert chunks[0].doc_id == "biaya"
    finally:
        vectorstore._client.cache_clear()
