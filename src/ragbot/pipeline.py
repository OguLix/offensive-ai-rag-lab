"""Single entry point used by the Flask app and by the experiment runner.

Owner: B (shared contract). Phase 0 stub only. Everything RAG-related stays behind
this function so the UI and the runner always measure the same path.
"""

from __future__ import annotations

from ragbot.types import MitigationFlags, PipelineResult


def answer(question: str, collection: str, flags: MitigationFlags) -> PipelineResult:
    """Answer `question` from `collection` and return the full trace of the run."""
    raise NotImplementedError("pipeline.answer is implemented by owner B in Phase 1")
