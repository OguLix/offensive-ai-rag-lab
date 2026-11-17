"""Splits corpus files into chunks and loads them into a vector collection.

Owner: A. Phase 0 stub only; implemented together with vectorstore in Phase 1.
"""

from __future__ import annotations

from pathlib import Path

from ragbot.types import MitigationFlags


def ingest_directory(
    path: str | Path,
    collection: str,
    flags: MitigationFlags | None = None,
) -> int:
    """Ingest every supported file under `path` and return the number of chunks stored.

    `flags` matters here because ingest_sanitizer and provenance_check act before
    text ever reaches the vector store.
    """
    raise NotImplementedError("ingest_directory is implemented by owner A in Phase 1")
