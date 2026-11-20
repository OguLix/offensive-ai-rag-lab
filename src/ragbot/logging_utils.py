"""Writes one JSONL line per run so results can be re-checked without rerunning.

Owner: C.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from ragbot.config import load_settings
from ragbot.types import PipelineResult

_RESULT_FIELDS = frozenset(
    {
        "question",
        "chunks",
        "messages",
        "response",
        "flags",
        "model",
        "collection",
        "latency_s",
        "timestamp",
        "blocked_by",
    }
)


def log_result(result: PipelineResult, extra: dict) -> None:
    """Append `result` plus caller-supplied fields to the JSONL log under logs_path."""
    overlap = _RESULT_FIELDS & extra.keys()
    if overlap:
        # Silently overwriting a trace field would corrupt the evidence file.
        raise ValueError(f"extra must not overwrite result fields: {sorted(overlap)}")

    record = {
        "question": result.question,
        "chunks": [asdict(chunk) for chunk in result.chunks],
        "messages": result.messages,
        "response": result.response,
        "flags": asdict(result.flags),
        "model": result.model,
        "collection": result.collection,
        "latency_s": result.latency_s,
        "timestamp": result.timestamp,
        "blocked_by": result.blocked_by,
        **extra,
    }

    logs_path = load_settings().logs_path
    logs_path.mkdir(parents=True, exist_ok=True)
    path = logs_path / f"runs-{_run_date(result.timestamp)}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _run_date(timestamp: str) -> str:
    """Group lines by run date; a malformed timestamp should fail loudly, not guess."""
    return datetime.fromisoformat(timestamp).date().isoformat()
