"""HTTP routes for the demo UI.

The browser is untrusted: question length, collection name and flag names are
validated here, before anything reaches the pipeline.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request

from ragbot import pipeline
from ragbot.config import Settings
from ragbot.types import MitigationFlags, PipelineResult, mitigation_flag_names

bp = Blueprint("main", __name__)
LOGGER = logging.getLogger(__name__)


@bp.get("/")
def index() -> str:
    """Serve the single chat page."""
    return render_template("index.html")


@bp.get("/api/options")
def options() -> Any:
    """Expose the whitelists and limits the UI may offer."""
    settings: Settings = current_app.config["RAGBOT_SETTINGS"]
    return jsonify(
        {
            "collections": list(settings.allowed_collections),
            "default_collection": settings.default_collection,
            "mitigations": list(mitigation_flag_names()),
            "chat_model": settings.chat_model,
            "max_question_chars": settings.max_question_chars,
        }
    )


@bp.post("/api/chat")
def chat() -> Any:
    """Answer one question; the exchange is stateless so runs stay comparable."""
    settings: Settings = current_app.config["RAGBOT_SETTINGS"]
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _error("Body permintaan harus berupa JSON object.", 400)

    try:
        question = _valid_question(payload.get("question"), settings.max_question_chars)
        collection = _valid_collection(
            payload.get("collection", settings.default_collection), settings
        )
        flags = _valid_flags(payload.get("flags"))
    except ValueError as exc:
        return _error(str(exc), 400)

    try:
        result = pipeline.answer(question, collection, flags)
    except NotImplementedError:
        LOGGER.info("pipeline.answer is still the Phase 0 stub")
        return _error(
            "Pipeline RAG belum diimplementasikan (Fase 1). Ini masih kerangka Fase 0.",
            501,
        )
    except _unreachable_errors() as exc:
        LOGGER.warning("ollama unreachable: %s", exc)
        return _error(
            "Ollama tidak dapat dijangkau di localhost. Jalankan `ollama serve` lalu coba lagi.",
            503,
        )
    except Exception:
        # Detail internal tidak boleh sampai ke klien.
        LOGGER.exception("unhandled error in /api/chat")
        return _error("Terjadi galat internal saat memproses permintaan.", 500)

    return jsonify(_serialize(result))


def _valid_question(raw: Any, limit: int) -> str:
    if not isinstance(raw, str):
        raise ValueError("question wajib berupa string.")
    question = raw.strip()
    if not question:
        raise ValueError("question tidak boleh kosong.")
    if len(question) > limit:
        raise ValueError(f"question maksimal {limit} karakter.")
    return question


def _valid_collection(raw: Any, settings: Settings) -> str:
    if not isinstance(raw, str) or raw not in settings.allowed_collections:
        allowed = ", ".join(settings.allowed_collections)
        raise ValueError(f"collection tidak dikenal. Pilihan yang sah: {allowed}.")
    return raw


def _valid_flags(raw: Any) -> MitigationFlags:
    if raw is None:
        return MitigationFlags()
    if not isinstance(raw, dict):
        raise ValueError("flags wajib berupa object.")

    allowed = mitigation_flag_names()
    unknown = sorted(set(raw) - set(allowed))
    if unknown:
        raise ValueError(f"flag tidak dikenal: {', '.join(unknown)}.")
    for name, value in raw.items():
        if not isinstance(value, bool):
            raise ValueError(f"flag {name} harus boolean.")
    return MitigationFlags(**raw)


def _serialize(result: PipelineResult) -> dict:
    """Send only the fields the inspector panel needs."""
    return {
        "response": result.response,
        "chunks": [
            {
                "doc_id": chunk.doc_id,
                "source": chunk.source,
                "score": chunk.score,
                "text": chunk.text,
            }
            for chunk in result.chunks
        ],
        "messages": result.messages,
        "blocked_by": result.blocked_by,
        "latency_s": result.latency_s,
    }


def _error(message: str, status: int) -> tuple[Any, int]:
    return jsonify({"error": message}), status


def _unreachable_errors() -> tuple[type[BaseException], ...]:
    """Return the exception types that mean "Ollama is not listening".

    The Ollama client speaks over httpx, whose transport errors are not builtins
    ConnectionError, so they are added only when httpx is importable.
    """
    errors: list[type[BaseException]] = [ConnectionError, TimeoutError]
    try:
        httpx = importlib.import_module("httpx")
    except ImportError:
        return tuple(errors)

    for name in ("ConnectError", "ConnectTimeout", "ReadTimeout"):
        candidate = getattr(httpx, name, None)
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            errors.append(candidate)
    return tuple(errors)
