"""M3: accept only documents that come from the trusted corpus path.

Owner: C. `ingest.ingest_directory` calls this before chunking. The allowlist
is deliberately narrow: adding another trusted root is a security decision,
not a convenience, so it must be reviewed. Documents under `data/poisoned/`
and documents that still contain a lab marker are rejected.
"""

from __future__ import annotations

import re
from pathlib import Path

from ragbot.config import PROJECT_ROOT

TRUSTED_PREFIXES: tuple[str, ...] = ("data/corpus/",)

_LAB_MARKER_PATTERN = re.compile(
    r"\bS[123]-(?:CANARY|OVERRIDE)-[A-Za-z0-9-]+\b",
    re.IGNORECASE,
)
_LAB_HEADER_PATTERN = re.compile(r"^\s*#\s*SERANGAN\s+S2/S3\b", re.IGNORECASE | re.MULTILINE)
_PROJECT_ROOT = PROJECT_ROOT.resolve()


def apply(source: str, text: str) -> bool:
    """Return True only for a trusted source whose text has no lab markers."""
    normalized = _normalize_source(source)
    if not normalized.startswith(TRUSTED_PREFIXES):
        return False
    if _LAB_MARKER_PATTERN.search(text) or _LAB_HEADER_PATTERN.search(text):
        return False
    return True


def _normalize_source(source: str) -> str:
    raw = source.replace("\\", "/").strip()
    if not raw:
        return ""
    path = Path(raw)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    try:
        return path.resolve().relative_to(_PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()
