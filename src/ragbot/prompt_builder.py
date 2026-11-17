"""Builds the message list sent to the LLM.

Owner: B. Phase 0 stub only. This is the seam where document text must be marked
as untrusted data, so an instruction inside a document cannot read as a system rule.
"""

from __future__ import annotations

from ragbot.types import Chunk, MitigationFlags


def build_messages(
    system_prompt: str,
    question: str,
    chunks: list[Chunk],
    flags: MitigationFlags,
) -> list[dict]:
    """Return the final prompt sent to the model, keeping instructions and data apart."""
    raise NotImplementedError("build_messages is implemented by owner B in Phase 1")
