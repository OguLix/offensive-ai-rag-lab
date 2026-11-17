"""Reads config/settings.yaml and the optional .env file in one place.

Nothing else in the project reads YAML or environment variables directly,
so a wrong model name or path is fixed in a single spot.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"
DEFAULT_SYSTEM_PROMPT_PATH = PROJECT_ROOT / "config" / "prompts" / "system_prompt.txt"


@dataclass(frozen=True)
class Settings:
    """Resolved project settings; paths are absolute so the app can start anywhere."""

    chat_model: str
    embedding_model: str
    temperature: float
    seed: int
    retrieval_k: int
    chroma_db_path: Path
    logs_path: Path
    default_collection: str
    allowed_collections: tuple[str, ...]
    app_host: str
    app_port: int
    max_question_chars: int


def load_settings(path: str | Path | None = None) -> Settings:
    """Load settings from YAML, honouring RAGBOT_SETTINGS_PATH as an override."""
    # load_dotenv dipanggil di sini, bukan saat import, supaya test tidak
    # terpengaruh .env milik mesin pengembang.
    load_dotenv(PROJECT_ROOT / ".env")

    resolved = Path(path or os.getenv("RAGBOT_SETTINGS_PATH") or DEFAULT_SETTINGS_PATH)
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved

    with resolved.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    raw_allowed = _require(raw, "allowed_collections")
    # String tunggal akan terpecah jadi per karakter kalau tidak dicek di sini.
    if not isinstance(raw_allowed, list | tuple):
        raise ValueError("allowed_collections must be a YAML list of collection names")
    allowed = tuple(str(name) for name in raw_allowed)
    default_collection = str(_require(raw, "default_collection"))
    if default_collection not in allowed:
        raise ValueError(
            f"default_collection {default_collection!r} is not listed in allowed_collections"
        )

    return Settings(
        chat_model=str(_require(raw, "chat_model")),
        embedding_model=str(_require(raw, "embedding_model")),
        temperature=float(_require(raw, "temperature")),
        seed=int(_require(raw, "seed")),
        retrieval_k=int(_require(raw, "retrieval_k")),
        chroma_db_path=_resolve_path(raw, "chroma_db_path"),
        logs_path=_resolve_path(raw, "logs_path"),
        default_collection=default_collection,
        allowed_collections=allowed,
        app_host=str(_require(raw, "app_host")),
        app_port=int(_require(raw, "app_port")),
        max_question_chars=int(_require(raw, "max_question_chars")),
    )


def load_system_prompt(path: str | Path | None = None) -> str:
    """Return the system prompt text; the pipeline must not hard-code it."""
    resolved = Path(path or DEFAULT_SYSTEM_PROMPT_PATH)
    return resolved.read_text(encoding="utf-8").strip()


def _require(raw: dict[str, Any], key: str) -> Any:
    if key not in raw:
        raise ValueError(f"settings.yaml is missing required key: {key}")
    return raw[key]


def _resolve_path(raw: dict[str, Any], key: str) -> Path:
    value = Path(str(_require(raw, key)))
    return value if value.is_absolute() else PROJECT_ROOT / value
