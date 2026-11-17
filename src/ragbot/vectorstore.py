"""ChromaDB access: one persistent client, collections addressed by name.

Owner: A. Phase 0 stub only.
"""

from __future__ import annotations

from typing import Any

from ragbot.types import Chunk


def get_collection(name: str) -> Any:
    """Return an existing collection or create it; callers never touch the client."""
    raise NotImplementedError("get_collection is implemented by owner A in Phase 1")


def query(collection: Any, text: str, k: int) -> list[Chunk]:
    """Return the `k` nearest chunks for `text` with scores and provenance metadata."""
    raise NotImplementedError("query is implemented by owner A in Phase 1")
