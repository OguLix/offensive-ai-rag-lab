"""Tests for config loading; they read the real config/settings.yaml, no network."""

from __future__ import annotations

from pathlib import Path

from ragbot.config import load_settings, load_system_prompt


def test_settings_load_with_team_models() -> None:
    settings = load_settings()

    # Nama model disepakati tim di docs/decisions.md; test ini menjaga agar
    # tidak diganti diam-diam.
    assert settings.chat_model == "llama3.2:3b"
    assert settings.embedding_model == "nomic-embed-text"
    assert settings.retrieval_k > 0
    assert isinstance(settings.chroma_db_path, Path)
    assert settings.chroma_db_path.is_absolute()


def test_default_collection_is_whitelisted_and_server_is_loopback() -> None:
    settings = load_settings()

    assert settings.default_collection in settings.allowed_collections
    assert "kb_clean" in settings.allowed_collections
    assert settings.app_host == "127.0.0.1"
    assert settings.max_question_chars > 0


def test_system_prompt_still_has_canary_todo() -> None:
    prompt = load_system_prompt()

    assert prompt.strip()
    assert "TODO(S1" in prompt
