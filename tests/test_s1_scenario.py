"""Static checks on the S1 payloads; no retrieval, vector store, or model is involved."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ragbot.config import load_system_prompt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = PROJECT_ROOT / "attacks" / "scenarios" / "s1_direct_injection.yaml"
REQUIRED_FIELDS = {"id", "category", "description", "question", "marker"}
ALLOWED_CATEGORIES = {"system_prompt_leak", "instruction_override"}
S1_CANARY = "S1-CANARY-RAGREDTEAM-7492"


def _scenario() -> dict[str, Any]:
    with SCENARIO_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _variants() -> list[dict[str, Any]]:
    return _scenario()["variants"]


def test_scenario_has_identity_and_at_least_five_variants() -> None:
    scenario = _scenario()

    assert scenario["id"] == "S1"
    assert scenario["owner"] == "<NAMA_A>"
    assert len(scenario["variants"]) >= 5
    assert scenario["success_condition"]


def test_every_variant_has_required_fields_and_valid_category() -> None:
    for variant in _variants():
        assert REQUIRED_FIELDS <= set(variant), variant.get("id")
        assert variant["category"] in ALLOWED_CATEGORIES, variant["id"]
        assert variant["question"].strip(), variant["id"]
        assert variant["marker"].strip(), variant["id"]


def test_variant_ids_are_unique() -> None:
    ids = [variant["id"] for variant in _variants()]

    assert len(ids) == len(set(ids))


def test_leak_variants_target_planted_canary_without_giving_it_away() -> None:
    system_prompt = load_system_prompt()
    assert S1_CANARY in system_prompt

    leak_variants = [v for v in _variants() if v["category"] == "system_prompt_leak"]
    assert leak_variants
    for variant in leak_variants:
        assert variant["marker"] == S1_CANARY, variant["id"]
        # The attacker must not already know the canary in the prompt.
        assert S1_CANARY not in variant["question"], variant["id"]


def test_override_variants_use_distinct_s1_override_markers() -> None:
    override_variants = [v for v in _variants() if v["category"] == "instruction_override"]
    assert override_variants

    markers = [variant["marker"] for variant in override_variants]
    assert len(markers) == len(set(markers))
    for variant in override_variants:
        assert variant["marker"].startswith("S1-OVERRIDE-"), variant["id"]
