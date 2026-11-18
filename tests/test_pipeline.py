"""Pipeline tests; every collaborator is faked, so no ChromaDB, Ollama, or log file is touched."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from ragbot import llm_client, logging_utils, pipeline, prompt_builder, retriever
from ragbot.config import Settings
from ragbot.types import Chunk, MitigationFlags, PipelineResult


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        chat_model="model-uji",
        embedding_model="embed-uji",
        temperature=0.0,
        seed=7,
        retrieval_k=3,
        chroma_db_path=tmp_path / "chroma",
        logs_path=tmp_path / "logs",
        default_collection="kb_clean",
        allowed_collections=("kb_clean",),
        app_host="127.0.0.1",
        app_port=5000,
        max_question_chars=2000,
    )


@pytest.fixture()
def calls(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> dict:
    calls: dict = {}

    monkeypatch.setattr(pipeline, "load_settings", lambda: settings)
    monkeypatch.setattr(pipeline, "load_system_prompt", lambda: "PROMPT UJI")

    def fake_retrieve(
        question: str, collection: str, k: int, flags: MitigationFlags
    ) -> list[Chunk]:
        calls.update(question=question, collection=collection, k=k, retrieve_flags=flags)
        return [Chunk(doc_id="doc-1", text="isi dokumen", score=0.9, source="doc-1.md")]

    def fake_build_messages(
        system_prompt: str, question: str, chunks: list[Chunk], flags: MitigationFlags
    ) -> list[dict]:
        calls.update(
            system_prompt=system_prompt,
            build_question=question,
            build_chunks=chunks,
            build_flags=flags,
        )
        return [{"role": "system", "content": system_prompt}]

    def fake_chat(messages: list[dict], model: str, temperature: float, seed: int) -> str:
        calls.update(messages=messages, model=model, temperature=temperature, seed=seed)
        return "jawaban uji"

    def fake_log_result(result: PipelineResult, extra: dict) -> None:
        calls.update(logged=result, extra=extra)

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)
    monkeypatch.setattr(prompt_builder, "build_messages", fake_build_messages)
    monkeypatch.setattr(llm_client, "chat", fake_chat)
    monkeypatch.setattr(logging_utils, "log_result", fake_log_result)
    return calls


def test_returns_complete_result(calls: dict) -> None:
    result = pipeline.answer("Jam layanan?", "kb_clean", MitigationFlags())

    assert result.response == "jawaban uji"
    assert result.question == "Jam layanan?"
    assert result.model == "model-uji"
    assert result.collection == "kb_clean"
    assert result.blocked_by is None


def test_uses_retrieval_k_from_settings(calls: dict) -> None:
    pipeline.answer("Jam layanan?", "kb_clean", MitigationFlags())

    assert calls["k"] == 3


def test_uses_system_prompt_from_config(calls: dict) -> None:
    pipeline.answer("Jam layanan?", "kb_clean", MitigationFlags())

    assert calls["system_prompt"] == "PROMPT UJI"


def test_forwards_generation_settings_to_client(calls: dict) -> None:
    pipeline.answer("Jam layanan?", "kb_clean", MitigationFlags())

    assert calls["messages"] == [{"role": "system", "content": "PROMPT UJI"}]
    assert calls["model"] == "model-uji"
    assert calls["temperature"] == 0.0
    assert calls["seed"] == 7


def test_timestamp_is_iso8601_and_latency_is_measured(calls: dict) -> None:
    result = pipeline.answer("Jam layanan?", "kb_clean", MitigationFlags())

    assert datetime.fromisoformat(result.timestamp).tzinfo is not None
    assert result.latency_s >= 0


def test_logs_result_once(calls: dict) -> None:
    result = pipeline.answer("Jam layanan?", "kb_clean", MitigationFlags())

    assert calls["logged"] is result
    assert calls["extra"] == {}


def test_forwards_flags_to_retriever_and_prompt_builder(calls: dict) -> None:
    flags = MitigationFlags(context_isolation=True, retrieval_sanitizer=True)

    pipeline.answer("Jam layanan?", "kb_clean", flags)

    assert calls["retrieve_flags"] is flags
    assert calls["build_flags"] is flags
