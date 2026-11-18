"""M2: strip instruction-like text from retrieved chunks before prompting. Owner: B."""

from __future__ import annotations

import re
from dataclasses import replace

from ragbot.types import Chunk

# Only the instruction sentence is dropped; the chunk itself is kept so retrieval
# provenance stays visible in the UI and in the evidence.
_INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore\s+(all\s+|any\s+)?(previous|prior|above)\s+instructions?\b",
        r"\bdisregard\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions?|rules?)\b",
        r"\bforget\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions?|rules?)\b",
        r"\byou\s+are\s+now\b",
        r"\b(reveal|print|show)\s+(the\s+)?(system|hidden)\s+prompt\b",
        r"\bsystem\s+prompt\b",
        r"\babaikan\s+(semua\s+|seluruh\s+)?(instruksi|perintah|aturan)\b",
        r"\blupakan\s+(semua\s+|seluruh\s+)?(instruksi|perintah|aturan)\b",
        r"\bkamu\s+sekarang\s+adalah\b",
        r"\b(cetak|tampilkan|bocorkan)\s+(system\s+prompt|prompt\s+sistem|instruksi\s+sistem)\b",
        r"\bprompt\s+sistem\b",
        r"\bcanary\b",
    )
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def apply(chunks: list[Chunk]) -> list[Chunk]:
    """Return copies of `chunks` with instruction-like sentences removed."""
    return [replace(chunk, text=_sanitise(chunk.text)) for chunk in chunks]


def _sanitise(text: str) -> str:
    kept_lines: list[str] = []
    for line in text.splitlines():
        sentences = [
            sentence for sentence in _SENTENCE_SPLIT.split(line) if not _is_injection(sentence)
        ]
        cleaned = " ".join(sentence for sentence in sentences if sentence.strip())
        if cleaned:
            kept_lines.append(cleaned)
        elif not line.strip():
            kept_lines.append("")
    return "\n".join(kept_lines).strip()


def _is_injection(sentence: str) -> bool:
    return any(pattern.search(sentence) for pattern in _INJECTION_PATTERNS)
