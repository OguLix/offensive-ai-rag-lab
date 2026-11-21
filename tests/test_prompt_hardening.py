"""Unit tests for M1 prompt hardening."""

from __future__ import annotations

from ragbot import prompt_builder
from ragbot.config import load_system_prompt
from ragbot.mitigations import prompt_hardening
from ragbot.types import Chunk, MitigationFlags


def test_apply_preserves_original_prompt_and_appends_hardening_rules() -> None:
    original = "Anda adalah asisten FAQ."
    hardened = prompt_hardening.apply(original)

    assert hardened.startswith(original)
    assert prompt_hardening.HARDENING_HEADER in hardened
    assert "prioritas mutlak" in hardened.lower()
    assert "menerjemahkan" in hardened.lower()
    assert "roleplay" in hardened.lower()


def test_apply_is_idempotent() -> None:
    once = prompt_hardening.apply("Aturan dasar.")
    twice = prompt_hardening.apply(once)

    assert twice == once


def test_apply_handles_empty_or_whitespace_prompt() -> None:
    hardened = prompt_hardening.apply("   \n  ")

    assert hardened.startswith(prompt_hardening.HARDENING_HEADER)


def test_hardening_does_not_hardcode_s1_canary() -> None:
    hardened = prompt_hardening.apply("Aturan dasar.")

    assert "S1-CANARY" not in hardened
    assert "7492" not in hardened


def test_prompt_builder_uses_real_prompt_hardening_when_flag_enabled() -> None:
    system_prompt = load_system_prompt()
    chunks = [Chunk(doc_id="doc-1", text="Jam layanan 08.00-16.00.", score=0.9, source="clean.md")]

    baseline = prompt_builder.build_messages(
        system_prompt, "Jam layanan?", chunks, MitigationFlags(prompt_hardening=False)
    )
    hardened = prompt_builder.build_messages(
        system_prompt, "Jam layanan?", chunks, MitigationFlags(prompt_hardening=True)
    )

    assert prompt_hardening.HARDENING_HEADER not in baseline[0]["content"]
    assert prompt_hardening.HARDENING_HEADER in hardened[0]["content"]
    assert system_prompt in hardened[0]["content"]
    assert baseline[1] == hardened[1]
