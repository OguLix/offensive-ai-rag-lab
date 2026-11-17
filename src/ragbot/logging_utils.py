"""Writes one JSONL line per run so results can be re-checked without rerunning.

Owner: C. Phase 0 stub only.
"""

from __future__ import annotations

from ragbot.types import PipelineResult


def log_result(result: PipelineResult, extra: dict) -> None:
    """Append `result` plus caller-supplied fields to the JSONL log under logs_path."""
    raise NotImplementedError("log_result is implemented by owner C in Phase 1")
