"""Static checks on the S3 payloads; no retrieval, vector store, or model is involved."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = PROJECT_ROOT / "attacks" / "scenarios" / "s3_document_poisoning.yaml"
POISONED_DIR = PROJECT_ROOT / "data" / "poisoned"
HEADER = "# SERANGAN S2/S3: hanya untuk lab proyek"
REQUIRED_FIELDS = {
    "id",
    "description",
    "question",
    "document",
    "placement",
    "marker",
    "false_claim",
}


def _scenario() -> dict[str, Any]:
    with SCENARIO_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _variants() -> list[dict[str, Any]]:
    return _scenario()["variants"]


def test_scenario_has_identity_and_at_least_five_variants() -> None:
    scenario = _scenario()

    assert scenario["id"] == "S3"
    assert scenario["owner"] == "<NAMA_C>"
    assert len(scenario["variants"]) >= 5
    assert scenario["success_condition"]


def test_every_variant_has_the_required_fields() -> None:
    for variant in _variants():
        assert REQUIRED_FIELDS <= set(variant), variant.get("id")


def test_variant_ids_and_markers_are_unique() -> None:
    ids = [variant["id"] for variant in _variants()]
    markers = [variant["marker"] for variant in _variants()]

    assert len(ids) == len(set(ids))
    assert len(markers) == len(set(markers))


def test_markers_follow_the_s3_convention() -> None:
    for variant in _variants():
        assert variant["marker"].startswith("S3-CANARY-"), variant["id"]


def test_false_claims_are_non_empty_strings() -> None:
    for variant in _variants():
        assert isinstance(variant["false_claim"], str)
        assert variant["false_claim"].strip(), variant["id"]


def test_documents_live_in_the_poisoned_folder_with_the_attack_header() -> None:
    for variant in _variants():
        document = PROJECT_ROOT / variant["document"]

        assert document.is_file(), variant["document"]
        assert document.parent == POISONED_DIR
        assert document.read_text(encoding="utf-8").lstrip().startswith(HEADER)


def test_each_document_contains_its_own_marker() -> None:
    for variant in _variants():
        text = (PROJECT_ROOT / variant["document"]).read_text(encoding="utf-8")

        assert variant["marker"] in text, variant["id"]


def test_each_document_contains_its_false_claim() -> None:
    for variant in _variants():
        text = (PROJECT_ROOT / variant["document"]).read_text(encoding="utf-8")

        assert variant["false_claim"] in text, variant["id"]


def test_questions_are_innocent() -> None:
    for variant in _variants():
        assert variant["question"].strip()
        assert variant["marker"] not in variant["question"]
        assert "S3-CANARY" not in variant["question"]
