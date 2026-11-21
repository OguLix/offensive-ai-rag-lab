"""M1: block canary or system-prompt leakage in the model answer. Owner: A."""

from __future__ import annotations

import re

BLOCKED_RESPONSE = (
    "Maaf, jawaban diblokir oleh filter keamanan karena terdeteksi memuat "
    "informasi internal sistem."
)

# Matches structured internal/canary tokens embedded in the system prompt
# (e.g. S1-CANARY-RAGREDTEAM-7492) without hard-coding any specific value.
_SECRET_TOKEN_PATTERN = re.compile(r"\b[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9-]{4,}\b")
_WORD_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_NGRAM_SIZE = 7


def apply(response: str, system_prompt: str) -> tuple[str, bool]:
    """Return `(safe_response, blocked)`.

    Detects two leakage modes dynamically against `system_prompt`:
    1. Any structured internal token (such as a planted canary) from `system_prompt`.
    2. A verbatim 7-word sequence copied from `system_prompt`.
    """
    if not response.strip() or not system_prompt.strip():
        return response, False

    if _leaks_secret_token(response, system_prompt) or _leaks_prompt_ngram(response, system_prompt):
        return BLOCKED_RESPONSE, True
    return response, False


def _leaks_secret_token(response: str, system_prompt: str) -> bool:
    lowered_response = response.lower()
    for token in _SECRET_TOKEN_PATTERN.findall(system_prompt):
        if token.lower() in lowered_response:
            return True
    return False


def _leaks_prompt_ngram(response: str, system_prompt: str) -> bool:
    prompt_words = _words(system_prompt)
    response_words = _words(response)
    if len(prompt_words) < _NGRAM_SIZE or len(response_words) < _NGRAM_SIZE:
        return False

    prompt_ngrams = {
        tuple(prompt_words[i : i + _NGRAM_SIZE]) for i in range(len(prompt_words) - _NGRAM_SIZE + 1)
    }
    for i in range(len(response_words) - _NGRAM_SIZE + 1):
        if tuple(response_words[i : i + _NGRAM_SIZE]) in prompt_ngrams:
            return True
    return False


def _words(text: str) -> list[str]:
    return [word.lower() for word in _WORD_PATTERN.findall(text)]
