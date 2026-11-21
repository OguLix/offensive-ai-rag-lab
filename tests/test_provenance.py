"""M3 provenance tests: only the clean corpus is trusted."""

from __future__ import annotations

from pathlib import Path

from ragbot.config import PROJECT_ROOT
from ragbot.mitigations import provenance

CLEAN_SOURCE = "data/corpus/02_jam_layanan.md"
POISONED_SOURCE = "data/poisoned/s3_v01_jam_layanan.md"
CLEAN_TEXT = "# Jam layanan\n\nLayanan buka 08.00 sampai 16.00."


def test_accepts_clean_corpus_source() -> None:
    assert provenance.apply(CLEAN_SOURCE, CLEAN_TEXT) is True


def test_accepts_windows_separator() -> None:
    assert provenance.apply(r"data\corpus\02_jam_layanan.md", CLEAN_TEXT) is True


def test_accepts_absolute_path_under_corpus() -> None:
    source = (PROJECT_ROOT / CLEAN_SOURCE).as_posix()

    assert provenance.apply(source, CLEAN_TEXT) is True


def test_rejects_poisoned_path() -> None:
    assert provenance.apply(POISONED_SOURCE, "Klaim palsu.") is False


def test_rejects_unknown_source() -> None:
    assert provenance.apply("tmp/notes.md", CLEAN_TEXT) is False


def test_rejects_path_traversal_out_of_corpus() -> None:
    source = "data/corpus/../poisoned/s3_v01_jam_layanan.md"

    assert provenance.apply(source, "Klaim palsu.") is False


def test_rejects_marker_inside_trusted_source() -> None:
    assert provenance.apply(CLEAN_SOURCE, "Kode: S3-CANARY-v01") is False


def test_rejects_lab_header_inside_trusted_source() -> None:
    text = "# SERANGAN S2/S3: hanya untuk lab proyek\n\nKlaim palsu."

    assert provenance.apply(CLEAN_SOURCE, text) is False


def test_rejects_absolute_path_outside_project(tmp_path: Path) -> None:
    source = (tmp_path / "notes.md").as_posix()

    assert provenance.apply(source, CLEAN_TEXT) is False


def test_rejects_empty_source() -> None:
    assert provenance.apply("", CLEAN_TEXT) is False
