"""Static checks on the clean corpus; no vector store or model is involved.

The clean corpus is the ground truth that S2/S3 attacks try to override, so it
must cover the attacked topics and must never contain an attack marker or a
planted false claim, otherwise the judges would count a clean answer as a hit.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
SCENARIO_DIR = PROJECT_ROOT / "attacks" / "scenarios"
ATTACK_HEADER = "# SERANGAN"

# Topics attacked by the S2/S3 payloads in data/poisoned/.
REQUIRED_TOPICS = (
    "jam_layanan",
    "biaya_administrasi",
    "prosedur_pengambilan_dokumen",
    "kontak_layanan",
    "pendaftaran",
)


def _corpus_files() -> list[Path]:
    return sorted(p for p in CORPUS_DIR.iterdir() if p.suffix in {".md", ".txt"})


def _attack_strings() -> list[str]:
    strings: list[str] = []
    for scenario_file in sorted(SCENARIO_DIR.glob("*.yaml")):
        with scenario_file.open(encoding="utf-8") as handle:
            scenario = yaml.safe_load(handle) or {}
        for variant in scenario.get("variants") or []:
            for key in ("marker", "false_claim"):
                value = variant.get(key)
                if isinstance(value, str) and value.strip():
                    strings.append(value.strip())
    return strings


def test_corpus_size_matches_agents_md() -> None:
    assert 10 <= len(_corpus_files()) <= 20


@pytest.mark.parametrize("topic", REQUIRED_TOPICS)
def test_attacked_topics_have_a_clean_document(topic: str) -> None:
    assert any(topic in path.stem for path in _corpus_files()), topic


def test_documents_are_non_empty_utf8_with_title() -> None:
    for path in _corpus_files():
        text = path.read_text(encoding="utf-8")
        assert text.startswith("# "), path.name
        assert len(text.split()) >= 30, path.name


def test_corpus_has_no_attack_header_marker_or_false_claim() -> None:
    attack_strings = _attack_strings()
    assert attack_strings, "scenario YAML files should define markers"

    for path in _corpus_files():
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert ATTACK_HEADER not in text, path.name
        assert "canary" not in lowered, path.name
        for needle in attack_strings:
            assert needle.lower() not in lowered, f"{needle!r} found in {path.name}"
