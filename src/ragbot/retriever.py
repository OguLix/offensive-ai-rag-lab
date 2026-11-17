"""Turns a user question into retrieved chunks.

Owner: B. Phase 0 stub only. Retrieval sanitation lives here so a poisoned or
injected document never reaches the prompt builder unsanitised.
"""

from __future__ import annotations

from ragbot.types import Chunk, MitigationFlags


def retrieve(question: str, collection: str, k: int, flags: MitigationFlags) -> list[Chunk]:
    """Retrieve the top-`k` chunks for `question` from `collection`."""
    raise NotImplementedError("retrieve is implemented by owner B in Phase 1")
