"""End-to-end M3 tests through the real ingest pipeline and a fake vector store."""

from __future__ import annotations

import dataclasses
import hashlib
import math
from pathlib import Path

import pytest

from ragbot import ingest, vectorstore
from ragbot.config import PROJECT_ROOT, load_settings
from ragbot.types import MitigationFlags

CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
POISONED_DIR = PROJECT_ROOT / "data" / "poisoned"


def _fake_vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [byte / 255.0 + 0.01 for byte in digest[:8]]
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values]


@pytest.fixture()
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    chroma_dir = tmp_path / "chroma"
    settings = dataclasses.replace(load_settings(), chroma_db_path=chroma_dir)
    monkeypatch.setattr(vectorstore, "load_settings", lambda: settings)
    monkeypatch.setattr(
        vectorstore,
        "embed",
        lambda texts, kind: [_fake_vector(text) for text in texts],
    )
    vectorstore._client.cache_clear()
    yield chroma_dir
    vectorstore._client.cache_clear()


def _documents(collection: str) -> tuple[list[str], list[dict]]:
    rows = vectorstore.get_collection(collection).get(include=["documents", "metadatas"])
    return rows["documents"], rows["metadatas"]


def test_provenance_only_rejects_all_poisoned_documents(isolated_store: Path) -> None:
    flags = MitigationFlags(provenance_check=True)

    stored = ingest.ingest_directory(POISONED_DIR, "kb_poisoned_sanitized", flags)

    assert stored == 0
    assert vectorstore.get_collection("kb_poisoned_sanitized").count() == 0


def test_sanitizer_only_removes_instructions_but_keeps_false_claims(
    isolated_store: Path,
) -> None:
    flags = MitigationFlags(ingest_sanitizer=True)

    stored = ingest.ingest_directory(POISONED_DIR, "kb_poisoned_sanitized", flags)

    assert stored > 0
    documents, metadatas = _documents("kb_poisoned_sanitized")
    joined = "\n".join(documents).lower()
    assert "s2-canary" not in joined
    assert "s3-canary" not in joined
    assert "abaikan aturan" not in joined
    assert "ignore all previous instructions" not in joined
    # S3 false claims are not the sanitizer's target; provenance handles them.
    assert "24 jam" in joined
    assert all(meta["lab_attack_doc"] is True for meta in metadatas)


def test_both_flags_keep_only_clean_corpus(isolated_store: Path) -> None:
    flags = MitigationFlags(provenance_check=True, ingest_sanitizer=True)

    total = ingest.ingest_directory(CORPUS_DIR, "kb_poisoned_sanitized", flags)
    total += ingest.ingest_directory(POISONED_DIR, "kb_poisoned_sanitized", flags)

    assert total > 0
    documents, metadatas = _documents("kb_poisoned_sanitized")
    assert all(meta["lab_attack_doc"] is False for meta in metadatas)
    assert all(meta["source"].startswith("data/corpus/") for meta in metadatas)
    assert all("S2-CANARY" not in doc and "S3-CANARY" not in doc for doc in documents)
