"""Offline tests for the JSONL run log; nothing is written outside tmp_path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ragbot import logging_utils
from ragbot.config import Settings
from ragbot.types import Chunk, MitigationFlags, PipelineResult


@pytest.fixture()
def logs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    settings = Settings(
        chat_model="model-uji",
        embedding_model="embed-uji",
        temperature=0.0,
        seed=0,
        retrieval_k=4,
        chroma_db_path=tmp_path / "chroma",
        logs_path=tmp_path / "logs",
        default_collection="kb_clean",
        allowed_collections=("kb_clean",),
        app_host="127.0.0.1",
        app_port=5000,
        max_question_chars=2000,
    )
    monkeypatch.setattr(logging_utils, "load_settings", lambda: settings)
    return settings.logs_path


@pytest.fixture()
def result() -> PipelineResult:
    return PipelineResult(
        question="Jam layanan?",
        chunks=[
            Chunk(
                doc_id="doc-1",
                text="Layanan buka 08.00-16.00.",
                score=0.91,
                source="data/corpus/doc-1.md",
                meta={"section": "jam"},
            )
        ],
        messages=[
            {"role": "system", "content": "PROMPT UJI"},
            {"role": "user", "content": "Jam layanan?"},
        ],
        response="Layanan buka 08.00-16.00.",
        flags=MitigationFlags(input_filter=True),
        model="model-uji",
        collection="kb_clean",
        latency_s=0.42,
        timestamp="2026-11-20T10:00:00+00:00",
    )


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_writes_one_line_per_call(logs_dir: Path, result: PipelineResult) -> None:
    assert not logs_dir.exists()

    logging_utils.log_result(result, {})

    path = logs_dir / "runs-2026-11-20.jsonl"
    assert path.exists()
    assert len(_lines(path)) == 1


def test_line_contains_the_full_trace(logs_dir: Path, result: PipelineResult) -> None:
    logging_utils.log_result(result, {})

    record = json.loads(_lines(logs_dir / "runs-2026-11-20.jsonl")[0])
    assert record["question"] == "Jam layanan?"
    assert record["response"] == "Layanan buka 08.00-16.00."
    assert record["chunks"] == [
        {
            "doc_id": "doc-1",
            "text": "Layanan buka 08.00-16.00.",
            "score": 0.91,
            "source": "data/corpus/doc-1.md",
            "meta": {"section": "jam"},
        }
    ]
    assert record["messages"][0] == {"role": "system", "content": "PROMPT UJI"}
    assert record["flags"]["input_filter"] is True
    assert record["model"] == "model-uji"
    assert record["collection"] == "kb_clean"
    assert record["latency_s"] == 0.42
    assert record["timestamp"] == "2026-11-20T10:00:00+00:00"
    assert record["blocked_by"] is None


def test_appends_instead_of_overwriting(logs_dir: Path, result: PipelineResult) -> None:
    logging_utils.log_result(result, {"trial": 1})
    logging_utils.log_result(result, {"trial": 2})

    lines = _lines(logs_dir / "runs-2026-11-20.jsonl")
    assert len(lines) == 2
    assert [json.loads(line)["trial"] for line in lines] == [1, 2]


def test_merges_extra_fields(logs_dir: Path, result: PipelineResult) -> None:
    logging_utils.log_result(result, {"scenario": "S1", "variant_id": "v03", "success": True})

    record = json.loads(_lines(logs_dir / "runs-2026-11-20.jsonl")[0])
    assert record["scenario"] == "S1"
    assert record["variant_id"] == "v03"
    assert record["success"] is True


def test_rejects_extra_that_overwrites_trace_fields(logs_dir: Path, result: PipelineResult) -> None:
    with pytest.raises(ValueError, match="response"):
        logging_utils.log_result(result, {"response": "dipalsukan"})

    assert not logs_dir.exists()


def test_keeps_non_ascii_text_readable(logs_dir: Path, result: PipelineResult) -> None:
    result.question = "Apa jam layanan – akhir pekan?"
    result.response = "Tidak ada layanan — tutup."

    logging_utils.log_result(result, {})

    path = logs_dir / "runs-2026-11-20.jsonl"
    raw = path.read_text(encoding="utf-8")
    assert "–" in raw and "—" in raw
    assert json.loads(raw)["question"] == "Apa jam layanan – akhir pekan?"
