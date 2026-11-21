"""M3: remove instruction-like paragraphs from documents before they are chunked.

Owner: C. A paragraph is dropped when it contains a directive aimed at the
model, a lab canary marker, or a chat-template token. Normal prose is kept;
`tests/test_ingest_sanitizer.py` applies the sanitizer to the whole clean
corpus so a new pattern cannot silently delete legitimate content.
"""

from __future__ import annotations

import re

# Directives that try to change the instruction hierarchy or the output. The
# patterns stay specific to avoid deleting normal FAQ prose.
_DIRECTIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+|your\s+)?"
        r"(previous|prior|above)\s+(instructions?|rules?|prompts?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(abaikan|lupakan)\s+(semua\s+|seluruh\s+)?(instruksi|perintah|aturan)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(note|message|instructions?)\s+to\s+the\s+(assistant|model|ai)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(instruksi|perintah|catatan)\s+(untuk\s+)?(asisten|model|ai)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(instruksi|catatan|pesan)\s+(sistem|redaksi\s+sistem)\b", re.IGNORECASE),
    re.compile(r"\b(system|developer)\s+(instruction|prompt|message)\b", re.IGNORECASE),
    re.compile(
        r"\b(reveal|print|show|repeat|leak)\s+(the\s+|your\s+)?"
        r"(system\s+prompt|hidden\s+prompt|internal\s+instructions?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(pesan|catatan)\s+ini\s+adalah\s+instruksi\b", re.IGNORECASE),
    re.compile(r"\b(kamu|anda)\s+sekarang\s+adalah\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"\b(developer|pengembang|uji)\s+mode\b", re.IGNORECASE),
    re.compile(r"\bmode\s+(uji|pengembang|developer)\b", re.IGNORECASE),
    re.compile(r"\b(reply|respond)\s+with\b", re.IGNORECASE),
    re.compile(r"\b(balas|jawab)\s+(dengan|hanya\s+dengan)\b", re.IGNORECASE),
    re.compile(r"\bcukup\s+jawab\b", re.IGNORECASE),
    re.compile(r"\binstead\s+of\s+answering\b", re.IGNORECASE),
    re.compile(
        r"\b(jangan|tidak\s+perlu)\s+(jelaskan|sebut|sebutkan|ungkapkan)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(do\s+not|don't)\s+(mention|reveal|explain|disclose)\b", re.IGNORECASE),
)

# Lab artefacts and hidden chat-template tokens. A paragraph containing one is
# not trustworthy enough to embed, even if it also contains normal prose.
_LAB_MARKER_PATTERN = re.compile(
    r"\bS[123]-(?:CANARY|OVERRIDE)-[A-Za-z0-9-]+\b",
    re.IGNORECASE,
)
_LAB_HEADER_PATTERN = re.compile(r"^\s*#\s*SERANGAN\s+S2/S3\b", re.IGNORECASE | re.MULTILINE)
_CHAT_TEMPLATE_PATTERN = re.compile(
    r"<\|(?:im_start|im_end|system|user|assistant)\|>|\[/?INST\]|<<\/?SYS>>",
    re.IGNORECASE,
)

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


def apply(text: str) -> str:
    """Return `text` without paragraphs that try to instruct the model."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""

    paragraphs = _PARAGRAPH_SPLIT.split(normalized)
    kept = [paragraph.strip() for paragraph in paragraphs if not _is_directive(paragraph)]
    return "\n\n".join(paragraph for paragraph in kept if paragraph)


def _is_directive(paragraph: str) -> bool:
    if (
        _LAB_MARKER_PATTERN.search(paragraph)
        or _LAB_HEADER_PATTERN.search(paragraph)
        or _CHAT_TEMPLATE_PATTERN.search(paragraph)
    ):
        return True
    return any(pattern.search(paragraph) for pattern in _DIRECTIVE_PATTERNS)
