"""Flask route tests; pipeline.answer is mocked so no Ollama call is ever made."""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient

from ragbot import pipeline
from ragbot.types import MitigationFlags, PipelineResult


def test_index_serves_chat_page(client: FlaskClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert b'id="chat-form"' in response.data


def test_options_expose_collections_flags_and_limit(client: FlaskClient) -> None:
    body = client.get("/api/options").get_json()

    assert body["default_collection"] in body["collections"]
    assert "prompt_hardening" in body["mitigations"]
    assert body["max_question_chars"] > 0
    assert body["chat_model"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 5000},
        {"question": "ok", "collection": "kb_tidak_ada"},
        {"question": "ok", "collection": 7},
        {"question": "ok", "flags": {"mitigasi_karangan": True}},
        {"question": "ok", "flags": {"input_filter": "ya"}},
        {"question": "ok", "flags": ["input_filter"]},
    ],
)
def test_chat_rejects_invalid_input(client: FlaskClient, payload: dict) -> None:
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"]


def test_chat_rejects_non_json_body(client: FlaskClient) -> None:
    response = client.post("/api/chat", data="bukan json", content_type="text/plain")

    assert response.status_code == 400


def test_chat_returns_serialised_result_when_pipeline_is_mocked(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch, sample_result: PipelineResult
) -> None:
    captured: dict = {}

    def fake_answer(question: str, collection: str, flags: MitigationFlags) -> PipelineResult:
        captured.update(question=question, collection=collection, flags=flags)
        return sample_result

    monkeypatch.setattr(pipeline, "answer", fake_answer)

    response = client.post(
        "/api/chat",
        json={
            "question": "Jam layanan?",
            "collection": "kb_clean",
            "flags": {"input_filter": True},
        },
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["response"] == sample_result.response
    assert body["blocked_by"] is None
    assert body["chunks"][0] == {
        "doc_id": "doc-contoh",
        "source": "data/corpus/doc-contoh.md",
        "score": 0.91,
        "text": "Jam layanan contoh 08.00-16.00.",
    }
    assert captured["question"] == "Jam layanan?"
    assert captured["collection"] == "kb_clean"
    assert captured["flags"] == MitigationFlags(input_filter=True)


def test_chat_returns_501_while_pipeline_is_still_a_stub(client: FlaskClient) -> None:
    response = client.post("/api/chat", json={"question": "Halo"})

    assert response.status_code == 501
    assert "Fase 0" in response.get_json()["error"]
