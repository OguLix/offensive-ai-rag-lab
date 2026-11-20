"""Offline tests for the Ollama wrapper; nothing here contacts a server."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from ragbot import llm_client


class _FakeMessage:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeResponse:
    def __init__(self, content: str | None) -> None:
        self.message = _FakeMessage(content)


class _FakeClient:
    """Stands in for ollama.Client and records what chat() asked for."""

    def __init__(self) -> None:
        self.host: str | None = None
        self.calls: list[dict[str, Any]] = []
        self.content: str | None = "jawaban uji"
        self.error: BaseException | None = None

    def chat(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return _FakeResponse(self.content)


@pytest.fixture()
def fake(monkeypatch: pytest.MonkeyPatch) -> _FakeClient:
    client = _FakeClient()

    def factory(host: str | None = None) -> _FakeClient:
        client.host = host
        return client

    monkeypatch.setattr(llm_client.ollama, "Client", factory)
    return client


def test_returns_assistant_text(fake: _FakeClient) -> None:
    assert llm_client.chat([{"role": "user", "content": "Halo"}], "model-uji", 0.0, 0) == (
        "jawaban uji"
    )


def test_forwards_request_unchanged(fake: _FakeClient) -> None:
    messages = [{"role": "user", "content": "Halo"}]

    llm_client.chat(messages, "model-uji", 0.2, 7)

    call = fake.calls[0]
    assert call["model"] == "model-uji"
    assert call["messages"] is messages
    assert call["options"] == {"temperature": 0.2, "seed": 7}


def test_uses_ollama_host_from_env(fake: _FakeClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9999")

    llm_client.chat([{"role": "user", "content": "Halo"}], "model-uji", 0.0, 0)

    assert fake.host == "http://127.0.0.1:9999"


def test_falls_back_to_loopback(fake: _FakeClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    llm_client.chat([{"role": "user", "content": "Halo"}], "model-uji", 0.0, 0)

    assert fake.host == llm_client.DEFAULT_HOST


def test_connection_error_is_not_swallowed(fake: _FakeClient) -> None:
    # routes.py turns httpx transport errors into 503, so they must escape here.
    fake.error = httpx.ConnectError("ollama down")

    with pytest.raises(httpx.ConnectError):
        llm_client.chat([{"role": "user", "content": "Halo"}], "model-uji", 0.0, 0)


def test_missing_content_becomes_empty_string(fake: _FakeClient) -> None:
    fake.content = None

    assert llm_client.chat([{"role": "user", "content": "Halo"}], "model-uji", 0.0, 0) == ""
