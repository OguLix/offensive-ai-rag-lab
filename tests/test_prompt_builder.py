"""Prompt builder tests; both mitigation modules are faked, so no Ollama call is made."""

from __future__ import annotations

import pytest

from ragbot import prompt_builder
from ragbot.mitigations import context_isolation, prompt_hardening
from ragbot.types import Chunk, MitigationFlags


def _chunk(doc_id: str, text: str) -> Chunk:
    return Chunk(doc_id=doc_id, text=text, score=0.5, source=f"data/corpus/{doc_id}.md")


@pytest.fixture()
def chunks() -> list[Chunk]:
    return [
        _chunk("doc-1", "Jam layanan 08.00-16.00."),
        _chunk("doc-2", "Tutup pada hari Minggu."),
    ]


def _must_not_be_called(*args: object) -> str:
    raise AssertionError("mitigation must not run while its flag is off")


def test_returns_system_then_user_messages(chunks: list[Chunk]) -> None:
    messages = prompt_builder.build_messages("SISTEM", "Jam layanan?", chunks, MitigationFlags())

    assert [message["role"] for message in messages] == ["system", "user"]


def test_baseline_keeps_system_prompt_and_skips_mitigations(
    chunks: list[Chunk], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prompt_hardening, "apply", _must_not_be_called)
    monkeypatch.setattr(context_isolation, "apply", _must_not_be_called)

    messages = prompt_builder.build_messages("SISTEM", "Jam layanan?", chunks, MitigationFlags())

    assert messages[0]["content"] == "SISTEM"


def test_baseline_orders_chunks_then_question(chunks: list[Chunk]) -> None:
    messages = prompt_builder.build_messages("SISTEM", "Jam layanan?", chunks, MitigationFlags())

    assert messages[1]["content"] == (
        "Jam layanan 08.00-16.00.\n\nTutup pada hari Minggu.\n\nJam layanan?"
    )


def test_system_message_has_no_document_text(chunks: list[Chunk]) -> None:
    messages = prompt_builder.build_messages("SISTEM", "Jam layanan?", chunks, MitigationFlags())

    assert "08.00" not in messages[0]["content"]


def test_context_isolation_receives_chunks_and_wraps_context(
    chunks: list[Chunk], monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[list[Chunk]] = []

    def fake_apply(retrieved: list[Chunk]) -> str:
        received.append(retrieved)
        return "KONTEKS TERISOLASI"

    monkeypatch.setattr(context_isolation, "apply", fake_apply)

    messages = prompt_builder.build_messages(
        "SISTEM", "Jam layanan?", chunks, MitigationFlags(context_isolation=True)
    )

    assert received == [chunks]
    assert messages[1]["content"] == "KONTEKS TERISOLASI\n\nPERTANYAAN PENGGUNA:\nJam layanan?"


def test_prompt_hardening_rewrites_system_prompt(
    chunks: list[Chunk], monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[str] = []

    def fake_apply(system_prompt: str) -> str:
        received.append(system_prompt)
        return "SISTEM DIPERKUAT"

    monkeypatch.setattr(prompt_hardening, "apply", fake_apply)

    messages = prompt_builder.build_messages(
        "SISTEM", "Jam layanan?", chunks, MitigationFlags(prompt_hardening=True)
    )

    assert received == ["SISTEM"]
    assert messages[0]["content"] == "SISTEM DIPERKUAT"


def test_empty_chunks_still_send_the_question() -> None:
    messages = prompt_builder.build_messages("SISTEM", "Jam layanan?", [], MitigationFlags())

    assert messages[1]["content"] == "Jam layanan?"


def test_chunks_are_not_mutated(chunks: list[Chunk]) -> None:
    snapshot = [(chunk.doc_id, chunk.text) for chunk in chunks]

    prompt_builder.build_messages("SISTEM", "Jam layanan?", chunks, MitigationFlags())

    assert [(chunk.doc_id, chunk.text) for chunk in chunks] == snapshot
