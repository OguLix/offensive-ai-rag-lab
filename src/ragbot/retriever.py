"""Turns a user question into retrieved chunks.

Owner: B. Retrieval sanitation lives here so a poisoned or injected document
never reaches the prompt builder unsanitised.
"""

from __future__ import annotations

from ragbot import vectorstore
from ragbot.mitigations import get_mitigation
from ragbot.types import Chunk, MitigationFlags


def retrieve(question: str, collection: str, k: int, flags: MitigationFlags) -> list[Chunk]:
    """Retrieve the top-`k` chunks for `question` from `collection`."""
    if k <= 0:
        raise ValueError("k must be a positive integer")

    store = vectorstore.get_collection(collection)
    chunks = vectorstore.query(store, question, k)

    if flags.retrieval_sanitizer:
        # Registry lookup keeps a disabled mitigation out of the call path.
        sanitizer = get_mitigation("retrieval_sanitizer")
        chunks = sanitizer.apply(chunks)

    return chunks
