"""M1: reject injection patterns in the user question before retrieval/LLM. Owner: A."""

from __future__ import annotations

import re

BLOCKED_RESPONSE = (
    "Maaf, permintaan Anda tidak dapat diproses karena terdeteksi sebagai upaya "
    "manipulasi instruksi sistem."
)

# General direct-injection and prompt-extraction patterns (ID and EN).
# Scenario markers (S1-CANARY / S1-OVERRIDE) are intentionally excluded so the
# filter does not overfit to the evaluation judge.
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override_en",
        re.compile(
            r"\b(ignore|disregard|forget)\s+(all\s+|any\s+)?(previous|prior|above)\s+"
            r"(instructions?|rules?|prompts?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "instruction_override_id",
        re.compile(
            r"\b(abaikan|lupakan)\s+(semua\s+|seluruh\s+)?(instruksi|perintah|aturan)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prompt_extraction_term",
        re.compile(
            r"\b(system\s+prompt|prompt\s+sistem|instruksi\s+sistem|"
            r"kode\s+konfigurasi\s+internal|internal\s+configuration\s+code|"
            r"kode\s+rahasia|hidden\s+prompt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prompt_extraction_verb_id",
        re.compile(
            r"\b(cetak|tampilkan|bocorkan|ulang|terjemahkan)\b.{0,40}"
            r"\b(aturan\s+awal|instruksi|prompt)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "prompt_extraction_verb_en",
        re.compile(
            r"\b(reveal|print|show|repeat|translate|dump)\b.{0,40}"
            r"\b(system|initial|hidden)\s+(prompt|instructions?|rules?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "role_switch",
        re.compile(
            r"\b(you\s+are\s+now|mulai\s+sekarang\s+(kamu|anda)\s+adalah|"
            r"mode\s+pengembang|developer\s+mode|echo\s+bot|bot\s+gema)\b",
            re.IGNORECASE,
        ),
    ),
)


def apply(question: str) -> tuple[bool, str]:
    """Return `(blocked, reason)` for a user `question`.

    When `blocked` is True, callers (such as `pipeline.answer`) should short-circuit
    and return `BLOCKED_RESPONSE` with `blocked_by="input_filter"`.
    """
    text = question.strip()
    if not text:
        return False, ""

    for rule_name, pattern in _RULES:
        if pattern.search(text):
            return True, rule_name
    return False, ""
