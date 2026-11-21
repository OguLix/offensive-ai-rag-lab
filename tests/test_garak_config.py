"""Static checks on garak local-scan configs; no garak venv or server required."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import pytest

from ragbot.config import PROJECT_ROOT, load_settings
from ragbot.types import mitigation_flag_names

GARAK_DIR = PROJECT_ROOT / "garak"
CONFIG_FILES = (
    ("rest_baseline.json", set()),
    ("rest_m1.json", {"prompt_hardening", "input_filter", "output_filter"}),
)


def _load_rest_config(filename: str) -> dict:
    path = GARAK_DIR / filename
    assert path.is_file(), filename
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw["rest"]["RestGenerator"]


@pytest.mark.parametrize(("filename", "expected_enabled"), CONFIG_FILES)
def test_rest_config_targets_loopback_chat_endpoint_only(
    filename: str, expected_enabled: set[str]
) -> None:
    cfg = _load_rest_config(filename)
    parsed = urlparse(cfg["uri"])

    # AGENTS.md Bagian 2: garak may only target the local chatbot on 127.0.0.1.
    assert parsed.scheme == "http"
    assert parsed.hostname == "127.0.0.1"
    assert parsed.path == "/api/chat"
    assert cfg["method"].lower() == "post"
    assert cfg["response_json"] is True
    assert cfg["response_json_field"] == "response"


@pytest.mark.parametrize(("filename", "expected_enabled"), CONFIG_FILES)
def test_rest_config_payload_matches_routes_contract(
    filename: str, expected_enabled: set[str]
) -> None:
    cfg = _load_rest_config(filename)
    settings = load_settings()
    template = cfg["req_template_json_object"]

    assert template["question"] == "$INPUT"
    assert template["collection"] in settings.allowed_collections
    assert set(template["flags"]) == set(mitigation_flag_names())

    enabled = {name for name, value in template["flags"].items() if value is True}
    assert enabled == expected_enabled


def test_run_script_enforces_loopback_guard_and_has_no_external_urls() -> None:
    script = (GARAK_DIR / "run_scan.ps1").read_text(encoding="utf-8")

    assert "127\\.0\\.0\\.1" in script
    urls = re.findall(r"https?://[^\s'\"`)]+", script)
    assert all(url.startswith(("http://127.0.0.1", "http://127\\.0\\.0\\.1")) for url in urls), urls
