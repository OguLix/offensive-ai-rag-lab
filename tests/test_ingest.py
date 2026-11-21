"""Ingest tests using a temporary ChromaDB and deterministic fake embeddings."""

from __future__ import annotations

import dataclasses
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from ragbot import ingest, vectorstore
from ragbot.config import PROJECT_ROOT, load_settings
from ragbot.types import MitigationFlags


def _fake_vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [byte / 255.0 + 0.01 for byte in digest[:8]]
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values]


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


def test_chunk_text_groups_short_paragraphs_and_splits_long_ones() -> None:
    text = "# Judul\n\nParagraf pertama.\n\nParagraf kedua."
    assert ingest.chunk_text(text, max_chars=200) == [text]

    long_text = " ".join(["kata"] * 60)
    chunks = ingest.chunk_text(long_text, max_chars=50)
    assert len(chunks) > 1
    assert all(len(chunk) <= 50 for chunk in chunks)
    assert " ".join(chunks) == long_text


def test_chunk_text_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="positive"):
        ingest.chunk_text("isi", max_chars=0)


def test_ingest_clean_corpus_populates_kb_clean_idempotently(isolated_store: Path) -> None:
    corpus_dir = PROJECT_ROOT / "data" / "corpus"

    first_count = ingest.ingest_directory(corpus_dir, "kb_clean")
    second_count = ingest.ingest_directory(corpus_dir, "kb_clean")

    assert first_count >= 14
    assert second_count == first_count
    collection = vectorstore.get_collection("kb_clean")
    assert collection.count() == first_count

    chunks = vectorstore.query(collection, "Jam layanan?", 2)
    assert len(chunks) == 2
    assert all(chunk.source.startswith("data/corpus/") for chunk in chunks)
    assert all(chunk.meta["lab_attack_doc"] is False for chunk in chunks)


def test_ingest_poisoned_strips_lab_header_skips_readme_and_marks_metadata(
    isolated_store: Path,
) -> None:
    poisoned_dir = PROJECT_ROOT / "data" / "poisoned"

    stored = ingest.ingest_directory(poisoned_dir, "kb_poisoned")

    assert stored == 10  # 5 S2 + 5 S3; data/poisoned/README.md must be skipped
    collection = vectorstore.get_collection("kb_poisoned")
    rows = collection.get(include=["documents", "metadatas"])
    assert all(ingest.LAB_ATTACK_HEADER not in doc for doc in rows["documents"])
    assert all(meta["lab_attack_doc"] is True for meta in rows["metadatas"])
    assert all("readme" not in meta["source"].lower() for meta in rows["metadatas"])


def test_ingest_refuses_poisoned_documents_into_kb_clean(
    isolated_store: Path, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="kb_clean"):
        ingest.ingest_directory(PROJECT_ROOT / "data" / "poisoned", "kb_clean")

    sneaky_dir = tmp_path / "sneaky"
    sneaky_dir.mkdir()
    (sneaky_dir / "attack.md").write_text(
        f"{ingest.LAB_ATTACK_HEADER}\n\n# Palsu\n\nKlaim palsu.",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="kb_clean"):
        ingest.ingest_directory(sneaky_dir, "kb_clean")


def test_ingest_runs_m3_mitigations_only_when_flags_enabled(
    isolated_store: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()
    (doc_dir / "trusted.md").write_text("# Aman\n\nTeks biasa.", encoding="utf-8")
    (doc_dir / "untrusted.md").write_text("# Asing\n\nTeks asing.", encoding="utf-8")

    fake_provenance = SimpleNamespace(apply=lambda source, text: "untrusted" not in source)
    fake_sanitizer = SimpleNamespace(apply=lambda text: text.replace("biasa", "bersih"))

    def fake_get_mitigation(name: str) -> SimpleNamespace:
        return {"provenance_check": fake_provenance, "ingest_sanitizer": fake_sanitizer}[name]

    monkeypatch.setattr(ingest, "get_mitigation", fake_get_mitigation)

    flags = MitigationFlags(provenance_check=True, ingest_sanitizer=True)
    stored = ingest.ingest_directory(doc_dir, "kb_poisoned_sanitized", flags)

    assert stored == 1
    rows = vectorstore.get_collection("kb_poisoned_sanitized").get(include=["documents"])
    assert rows["documents"] == ["# Aman\n\nTeks bersih."]


def test_cli_combines_multiple_paths_and_supports_reset(isolated_store: Path) -> None:
    total = ingest.main(
        [
            "--collection",
            "kb_poisoned",
            "--path",
            str(PROJECT_ROOT / "data" / "corpus"),
            "--path",
            str(PROJECT_ROOT / "data" / "poisoned"),
            "--reset",
        ]
    )

    collection = vectorstore.get_collection("kb_poisoned")
    assert total == collection.count()
    assert total >= 24  # 14 clean + 10 poisoned
