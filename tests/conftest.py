"""Shared fixtures. Nothing here contacts Ollama, so tests run on any machine."""

from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from ragbot.types import Chunk, MitigationFlags, PipelineResult


@pytest.fixture()
def app() -> Flask:
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture()
def sample_result() -> PipelineResult:
    """A made-up trace; it proves serialisation, not that retrieval works."""
    return PipelineResult(
        question="Jam layanan?",
        chunks=[
            Chunk(
                doc_id="doc-contoh",
                text="Jam layanan contoh 08.00-16.00.",
                score=0.91,
                source="data/corpus/doc-contoh.md",
            )
        ],
        messages=[
            {"role": "system", "content": "TODO"},
            {"role": "user", "content": "Jam layanan?"},
        ],
        response="Jam layanan contoh 08.00-16.00.",
        flags=MitigationFlags(),
        model="TODO_ISI_DI_FASE_0",
        collection="kb_clean",
        latency_s=0.42,
        timestamp="2026-01-01T00:00:00+00:00",
    )
