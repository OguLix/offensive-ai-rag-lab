"""Smoke tests for the frozen contract in src/ragbot/types.py."""

from __future__ import annotations

from dataclasses import fields

from ragbot import Chunk, MitigationFlags, PipelineResult
from ragbot.types import mitigation_flag_names

EXPECTED_FLAGS = (
    "prompt_hardening",
    "input_filter",
    "output_filter",
    "context_isolation",
    "retrieval_sanitizer",
    "ingest_sanitizer",
    "provenance_check",
)


def test_mitigation_flags_match_contract_and_default_to_disabled() -> None:
    flags = MitigationFlags()

    assert tuple(field.name for field in fields(MitigationFlags)) == EXPECTED_FLAGS
    assert mitigation_flag_names() == EXPECTED_FLAGS
    assert all(getattr(flags, name) is False for name in EXPECTED_FLAGS)


def test_chunk_meta_is_per_instance_and_blocked_by_defaults_to_none() -> None:
    first = Chunk(doc_id="d1", text="t1", score=0.5, source="s1")
    second = Chunk(doc_id="d2", text="t2", score=0.4, source="s2")

    first.meta["origin"] = "test"

    assert second.meta == {}
    assert Chunk.__dataclass_fields__["meta"].default_factory is dict

    result = PipelineResult(
        question="q",
        chunks=[first],
        messages=[],
        response="r",
        flags=MitigationFlags(),
        model="m",
        collection="kb_clean",
        latency_s=0.1,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert result.blocked_by is None
