"""Static checks that the chat page keeps the hooks chat.js depends on.

These tests never call Ollama; they only render the template through Flask.
"""

from __future__ import annotations

from flask.testing import FlaskClient

REQUIRED_HOOKS = (
    'id="chat-form"',
    'id="dock-toggle"',
    'id="question"',
    'id="send"',
    'id="history-list"',
    'id="disable-mitigations"',
    'id="reset-chat"',
    'id="attack-menu"',
    'id="attack-panel"',
    'id="mitigation-menu"',
    'id="mitigation-panel"',
    'id="method-menu"',
    'id="collections"',
    'id="answer-panel"',
    'id="answer-meta"',
    'id="answer-title"',
    'id="answer-body"',
    'id="answer-progress"',
    'id="answer-status"',
    'id="answer-action"',
    'id="chunks"',
    'id="messages"',
    'id="chunk-count"',
    'id="model-name"',
)


def test_index_renders_every_hook_chat_js_queries(client: FlaskClient) -> None:
    html = client.get("/").get_data(as_text=True)

    missing = [hook for hook in REQUIRED_HOOKS if hook not in html]
    assert missing == []


def test_answer_panel_starts_in_empty_state(client: FlaskClient) -> None:
    html = client.get("/").get_data(as_text=True)

    assert 'data-state="empty"' in html
    assert 'aria-live="polite"' in html
    assert "Belum ada jawaban" in html


def test_page_has_no_external_asset_references(client: FlaskClient) -> None:
    html = client.get("/").get_data(as_text=True)

    assert "http://" not in html
    assert "https://" not in html
    assert "cdn." not in html


def test_page_has_clean_headings_without_bracket_markers(client: FlaskClient) -> None:
    html = client.get("/").get_data(as_text=True)

    assert '<html lang="id">' in html
    assert html.count("<h1") == 1
    assert "—" not in html
    assert "RAG REDTeam" in html
    assert "ANGGA AI" not in html
    for marker in ("[1]", "[2]", "[3]", "[4]"):
        assert marker not in html
