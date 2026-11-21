"""Offline tests for the experiment runner; no Ollama, ChromaDB, or model involved."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from evaluation import run_experiments
from ragbot import pipeline
from ragbot.config import Settings
from ragbot.types import Chunk, MitigationFlags, PipelineResult


class _FakeStore:
    def count(self) -> int:
        return 5


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        chat_model="model-uji",
        embedding_model="embed-uji",
        temperature=0.0,
        seed=7,
        retrieval_k=3,
        chroma_db_path=tmp_path / "chroma",
        logs_path=tmp_path / "logs",
        default_collection="kb_clean",
        allowed_collections=("kb_clean", "kb_poisoned", "kb_poisoned_sanitized"),
        app_host="127.0.0.1",
        app_port=5000,
        max_question_chars=2000,
    )


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    monkeypatch.setattr(run_experiments, "load_settings", lambda: settings)


def _fake_result(question: str, collection: str, flags: MitigationFlags) -> PipelineResult:
    return PipelineResult(
        question=question,
        chunks=[Chunk(doc_id="d", text="t", score=1.0, source="s")],
        messages=[{"role": "user", "content": question}],
        response="jawaban uji",
        flags=flags,
        model="model-uji",
        collection=collection,
        latency_s=0.12,
        timestamp="2026-01-01T00:00:00+00:00",
        blocked_by=None,
    )


def _patch_store_and_ingest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_experiments.vectorstore, "get_collection", lambda name: _FakeStore())
    monkeypatch.setattr(run_experiments.vectorstore, "delete_collection", lambda name: None)
    monkeypatch.setattr(run_experiments.ingest, "ingest_directory", lambda *a, **k: 3)


def test_plan_counts_for_single_scenario() -> None:
    specs = run_experiments.plan_runs(["S2"], 2, include_normal=False)
    # S2 has 5 variants x 2 conditions x 2 trials = 20
    assert len(specs) == 5 * 2 * 2
    assert all(s.kind == "attack" for s in specs)
    assert all(s.scenario == "S2" for s in specs)


def test_plan_includes_normal_questions_once_per_condition() -> None:
    specs = run_experiments.plan_runs(["S2"], 2, include_normal=True, normal_trials=1)
    attack = [s for s in specs if s.kind == "attack"]
    normal = [s for s in specs if s.kind == "normal"]
    assert len(attack) == 5 * 2 * 2
    # S2 has 2 conditions -> 2 * 10 normal questions
    assert len(normal) == 2 * 10
    assert all(s.trial == 1 for s in normal)


def test_plan_rejects_unknown_scenario() -> None:
    with pytest.raises(ValueError, match="unknown scenario"):
        run_experiments.plan_runs(["S9"], 1)


def test_plan_rejects_unknown_condition() -> None:
    with pytest.raises(ValueError, match="unknown condition"):
        run_experiments.plan_runs(["S2"], 1, conditions=["nope"])


def test_run_writes_required_columns_and_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(pipeline, "answer", _fake_result)
    monkeypatch.setattr(
        run_experiments.judges,
        "judge",
        lambda s, v, r: {"success": False, "rule": "nope"},
    )
    _patch_store_and_ingest(monkeypatch)

    output_path = tmp_path / "out.csv"
    rows = run_experiments.run(
        ["S2"],
        1,
        conditions=["baseline"],
        include_normal=False,
        prepare=True,
        dry_run=False,
        output_path=output_path,
        output_dir=tmp_path,
    )

    assert len(rows) == 5
    assert output_path.exists()
    with output_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == run_experiments.CSV_COLUMNS
        data = list(reader)
    assert len(data) == 5
    assert all(r["scenario"] == "S2" for r in data)
    assert all(r["condition"] == "baseline" for r in data)
    assert all(r["kind"] == "attack" for r in data)
    # run_id unique
    assert len({r["run_id"] for r in data}) == 5


def test_run_marks_normal_questions_without_judging(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(pipeline, "answer", _fake_result)

    called = {"n": 0}

    def fake_judge(s, v, r):
        called["n"] += 1
        return {"success": True, "rule": "marker"}

    monkeypatch.setattr(run_experiments.judges, "judge", fake_judge)
    _patch_store_and_ingest(monkeypatch)

    output_path = tmp_path / "out.csv"
    rows = run_experiments.run(
        ["S2"],
        1,
        conditions=["baseline"],
        include_normal=True,
        normal_trials=1,
        prepare=True,
        output_path=output_path,
        output_dir=tmp_path,
    )

    normal_rows = [r for r in rows if r["kind"] == "normal"]
    assert len(normal_rows) == 10
    assert all(r["judge_rule"] == "n/a (normal question)" for r in normal_rows)
    assert all(r["success"] is False for r in normal_rows)
    # judge only called for attack rows
    attack_count = sum(1 for r in rows if r["kind"] == "attack")
    assert called["n"] == attack_count


def test_run_does_not_touch_kb_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline, "answer", _fake_result)
    monkeypatch.setattr(
        run_experiments.judges,
        "judge",
        lambda s, v, r: {"success": False, "rule": "nope"},
    )

    deleted: list[str] = []

    def fake_delete(name: str) -> None:
        deleted.append(name)

    monkeypatch.setattr(run_experiments.vectorstore, "delete_collection", fake_delete)
    monkeypatch.setattr(run_experiments.vectorstore, "get_collection", lambda name: _FakeStore())
    monkeypatch.setattr(run_experiments.ingest, "ingest_directory", lambda *a, **k: 3)

    run_experiments.run(
        ["S1"],
        1,
        conditions=["baseline", "m1"],
        include_normal=False,
        prepare=True,
        output_path=tmp_path / "out.csv",
        output_dir=tmp_path,
    )

    assert "kb_clean" not in deleted


def test_dry_run_does_not_call_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called = {"n": 0}

    def fake_answer(*a, **k):
        called["n"] += 1
        return _fake_result("q", "kb_clean", MitigationFlags())

    monkeypatch.setattr(pipeline, "answer", fake_answer)

    rows = run_experiments.run(
        ["S1"],
        1,
        conditions=["baseline"],
        include_normal=False,
        prepare=False,
        dry_run=True,
        output_dir=tmp_path,
    )
    assert rows == []
    assert called["n"] == 0


def test_flags_are_serialized_as_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline, "answer", _fake_result)
    monkeypatch.setattr(
        run_experiments.judges,
        "judge",
        lambda s, v, r: {"success": False, "rule": "nope"},
    )
    _patch_store_and_ingest(monkeypatch)

    output_path = tmp_path / "out.csv"
    rows = run_experiments.run(
        ["S1"],
        1,
        conditions=["m1"],
        include_normal=False,
        prepare=True,
        output_path=output_path,
        output_dir=tmp_path,
    )
    assert len(rows) == 6
    flags = json.loads(rows[0]["flags"])
    assert flags["prompt_hardening"] is True
    assert flags["input_filter"] is True
    assert flags["output_filter"] is True
    ingest = json.loads(rows[0]["ingest_flags"])
    assert ingest == {name: False for name in run_experiments._FLAG_NAMES}


def test_summary_file_is_written(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pipeline, "answer", _fake_result)
    monkeypatch.setattr(
        run_experiments.judges,
        "judge",
        lambda s, v, r: {"success": True, "rule": "marker"},
    )
    _patch_store_and_ingest(monkeypatch)

    output_path = tmp_path / "run-x.csv"
    run_experiments.run(
        ["S2"],
        1,
        conditions=["baseline"],
        include_normal=False,
        prepare=True,
        output_path=output_path,
        output_dir=tmp_path,
        tag="x",
    )
    summary_path = tmp_path / "summary-run-x.csv"
    assert summary_path.exists()
