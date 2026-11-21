"""Runs every scenario variant and writes the CSV summary plus JSONL raw logs.

Owner: C. The JSONL trace is written by ``pipeline.answer`` (one line per run);
this module adds the per-run CSV row, the aggregate summary, and the CLI.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import yaml

from attacks import judges
from evaluation import metrics
from ragbot import ingest, pipeline, vectorstore
from ragbot.config import load_settings
from ragbot.mitigations import MitigationFlags

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = PROJECT_ROOT / "attacks" / "scenarios"
NORMAL_QUESTIONS_PATH = PROJECT_ROOT / "evaluation" / "normal_questions.yaml"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

CSV_COLUMNS = [
    "run_id",
    "timestamp",
    "scenario",
    "variant_id",
    "trial",
    "model",
    "temperature",
    "seed",
    "collection",
    "flags",
    "success",
    "judge_rule",
    "blocked_by",
    "latency_s",
    "condition",
    "ingest_flags",
    "kind",
    "question_id",
]

_FLAG_NAMES = (
    "prompt_hardening",
    "input_filter",
    "output_filter",
    "context_isolation",
    "retrieval_sanitizer",
    "ingest_sanitizer",
    "provenance_check",
)


@dataclass(frozen=True)
class Condition:
    """One mitigation condition: collection plus query-time and ingest-time flags."""

    collection: str
    flags: MitigationFlags
    ingest_flags: MitigationFlags


@dataclass(frozen=True)
class RunSpec:
    scenario: str
    variant_id: str
    question: str
    trial: int
    condition: str
    collection: str
    flags: MitigationFlags
    ingest_flags: MitigationFlags
    kind: str  # "attack" or "normal"
    judge_variant: dict[str, Any] | None = field(default=None)


CONDITIONS: dict[str, dict[str, Condition]] = {
    "S1": {
        "baseline": Condition("kb_clean", MitigationFlags(), MitigationFlags()),
        "m1": Condition(
            "kb_clean",
            MitigationFlags(prompt_hardening=True, input_filter=True, output_filter=True),
            MitigationFlags(),
        ),
    },
    "S2": {
        "baseline": Condition("kb_poisoned", MitigationFlags(), MitigationFlags()),
        "m2": Condition(
            "kb_poisoned",
            MitigationFlags(context_isolation=True, retrieval_sanitizer=True),
            MitigationFlags(),
        ),
    },
    "S3": {
        "baseline": Condition("kb_poisoned", MitigationFlags(), MitigationFlags()),
        "m3_provenance": Condition(
            "kb_poisoned_sanitized",
            MitigationFlags(provenance_check=True),
            MitigationFlags(provenance_check=True),
        ),
        "m3_sanitizer": Condition(
            "kb_poisoned_sanitized",
            MitigationFlags(ingest_sanitizer=True),
            MitigationFlags(ingest_sanitizer=True),
        ),
    },
}

DEFAULT_CONDITIONS: dict[str, list[str]] = {
    "S1": ["baseline", "m1"],
    "S2": ["baseline", "m2"],
    "S3": ["baseline", "m3_provenance", "m3_sanitizer"],
}


def load_scenario(scenario_id: str) -> dict[str, Any]:
    matches = sorted(SCENARIOS_DIR.glob(f"{scenario_id.lower()}*.yaml"))
    if not matches:
        raise FileNotFoundError(f"no scenario file found for {scenario_id!r}")
    if len(matches) > 1:
        raise ValueError(f"multiple scenario files for {scenario_id!r}: {matches}")
    with matches[0].open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_normal_questions() -> list[dict[str, Any]]:
    with NORMAL_QUESTIONS_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return list(data["questions"])


def _flags_key(flags: MitigationFlags) -> tuple[bool, ...]:
    return tuple(getattr(flags, name) for name in _FLAG_NAMES)


def _active_flags(flags: MitigationFlags) -> list[str]:
    return [name for name in _FLAG_NAMES if getattr(flags, name)]


def _scenario_path_for_id(scenario_id: str) -> Path:
    matches = sorted(SCENARIOS_DIR.glob(f"{scenario_id.lower()}*.yaml"))
    if not matches:
        raise FileNotFoundError(f"no scenario file found for {scenario_id!r}")
    return matches[0]


def plan_runs(
    scenarios: Sequence[str],
    trials: int,
    *,
    conditions: Sequence[str] | None = None,
    include_normal: bool = True,
    normal_trials: int = 1,
) -> list[RunSpec]:
    """Build the full list of runs without touching the model or the store."""
    if trials < 1:
        raise ValueError("trials must be a positive integer")
    if normal_trials < 1:
        raise ValueError("normal_trials must be a positive integer")

    scenario_ids = [s.upper().strip() for s in scenarios]
    for sid in scenario_ids:
        if sid not in CONDITIONS:
            raise ValueError(f"unknown scenario: {sid!r}")

    specs: list[RunSpec] = []
    requested_by_scenario: dict[str, list[str]] = {}
    for sid in scenario_ids:
        if conditions is not None:
            requested = [c.strip() for c in conditions]
        else:
            requested = list(DEFAULT_CONDITIONS.get(sid, ["baseline"]))
        for name in requested:
            if name not in CONDITIONS[sid]:
                raise ValueError(f"unknown condition {name!r} for {sid}")
        requested_by_scenario[sid] = requested

        scenario_data = load_scenario(sid)
        for variant in scenario_data["variants"]:
            vid = str(variant["id"])
            question = str(variant["question"])
            for cond_name in requested:
                cond = CONDITIONS[sid][cond_name]
                for trial in range(1, trials + 1):
                    specs.append(
                        RunSpec(
                            scenario=sid,
                            variant_id=vid,
                            question=question,
                            trial=trial,
                            condition=cond_name,
                            collection=cond.collection,
                            flags=cond.flags,
                            ingest_flags=cond.ingest_flags,
                            kind="attack",
                            judge_variant=dict(variant),
                        )
                    )

    if include_normal:
        normal_questions = load_normal_questions()
        seen: set[tuple[str, tuple[bool, ...], tuple[bool, ...]]] = set()
        for sid in scenario_ids:
            for cond_name in requested_by_scenario[sid]:
                cond = CONDITIONS[sid][cond_name]
                key = (cond.collection, _flags_key(cond.flags), _flags_key(cond.ingest_flags))
                if key in seen:
                    continue
                seen.add(key)
                for nq in normal_questions:
                    for trial in range(1, normal_trials + 1):
                        specs.append(
                            RunSpec(
                                scenario=sid,
                                variant_id=str(nq["id"]),
                                question=str(nq["question"]),
                                trial=trial,
                                condition=cond_name,
                                collection=cond.collection,
                                flags=cond.flags,
                                ingest_flags=cond.ingest_flags,
                                kind="normal",
                                judge_variant=None,
                            )
                        )

    return specs


def prepare_collection(collection: str, ingest_flags: MitigationFlags) -> int:
    """Build (or verify) one collection. Never touches ``kb_clean``."""
    settings = load_settings()
    if collection not in settings.allowed_collections:
        raise ValueError(f"collection {collection!r} is not allowed")

    if collection == "kb_clean":
        store = vectorstore.get_collection("kb_clean")
        count = store.count()
        if count == 0:
            raise RuntimeError(
                "kb_clean is empty; run: python -m ragbot.ingest "
                "--collection kb_clean --path data/corpus"
            )
        LOGGER.info("kb_clean already has %d chunks; not rebuilding", count)
        return count

    vectorstore.delete_collection(collection)
    total = 0
    total += ingest.ingest_directory(PROJECT_ROOT / "data" / "corpus", collection, ingest_flags)
    total += ingest.ingest_directory(PROJECT_ROOT / "data" / "poisoned", collection, ingest_flags)
    LOGGER.info("prepared %s: %d chunks", collection, total)
    return total


def _unique_collections(specs: Sequence[RunSpec]) -> list[tuple[str, MitigationFlags]]:
    seen: set[tuple[str, tuple[bool, ...]]] = set()
    out: list[tuple[str, MitigationFlags]] = []
    for spec in specs:
        key = (spec.collection, _flags_key(spec.ingest_flags))
        if key in seen:
            continue
        seen.add(key)
        out.append((spec.collection, spec.ingest_flags))
    return out


def _run_id(spec: RunSpec) -> str:
    if spec.kind == "normal":
        return f"N-{spec.variant_id}-{spec.condition}-t{spec.trial:02d}"
    return f"{spec.scenario}-{spec.variant_id}-{spec.condition}-t{spec.trial:02d}"


def _print_plan(specs: Sequence[RunSpec]) -> None:
    LOGGER.info("planned %d runs", len(specs))
    counts: Counter[tuple[str, str]] = Counter()
    for spec in specs:
        label = "NORMAL" if spec.kind == "normal" else spec.scenario
        counts[(label, spec.condition)] += 1
    for (label, condition), count in sorted(counts.items()):
        LOGGER.info("  %-8s / %-16s : %d", label, condition, count)
    LOGGER.info("estimated time at 10s/run: %.1f min", len(specs) * 10 / 60.0)


def run(
    scenarios: Sequence[str],
    trials: int,
    *,
    conditions: Sequence[str] | None = None,
    include_normal: bool = True,
    normal_trials: int = 1,
    prepare: bool = True,
    dry_run: bool = False,
    tag: str | None = None,
    output_dir: Path | None = None,
    output_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Run every planned attempt and return the list of CSV rows."""
    if trials < 1:
        raise ValueError("trials must be a positive integer")

    scenario_ids = [s.upper().strip() for s in scenarios]
    specs = plan_runs(
        scenario_ids,
        trials,
        conditions=conditions,
        include_normal=include_normal,
        normal_trials=normal_trials,
    )

    if dry_run:
        _print_plan(specs)
        return []

    if prepare:
        for collection, ingest_flags in _unique_collections(specs):
            prepare_collection(collection, ingest_flags)

    if output_dir is None:
        output_dir = RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    if tag is None:
        tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if output_path is None:
        output_path = output_dir / f"run-{tag}.csv"

    settings = load_settings()
    rows: list[dict[str, Any]] = []

    total = len(specs)
    for index, spec in enumerate(specs, start=1):
        LOGGER.info("run %d/%d: %s", index, total, _run_id(spec))
        result = pipeline.answer(spec.question, spec.collection, spec.flags)

        if spec.kind == "attack" and spec.judge_variant is not None:
            verdict = judges.judge(spec.scenario, spec.judge_variant, result.response)
            success = bool(verdict["success"])
            judge_rule = str(verdict["rule"])
        else:
            success = False
            judge_rule = "n/a (normal question)"

        row = {
            "run_id": _run_id(spec),
            "timestamp": result.timestamp,
            "scenario": spec.scenario if spec.kind == "attack" else "NORMAL",
            "variant_id": spec.variant_id,
            "trial": spec.trial,
            "model": result.model,
            "temperature": settings.temperature,
            "seed": settings.seed,
            "collection": result.collection,
            "flags": json.dumps(asdict(result.flags), sort_keys=True),
            "success": success,
            "judge_rule": judge_rule,
            "blocked_by": result.blocked_by or "",
            "latency_s": result.latency_s,
            "condition": spec.condition,
            "ingest_flags": json.dumps(asdict(spec.ingest_flags), sort_keys=True),
            "kind": spec.kind,
            "question_id": spec.variant_id,
        }
        rows.append(row)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    LOGGER.info("wrote %d rows to %s", len(rows), output_path)

    summary_path = output_path.with_name(f"summary-{output_path.stem}.csv")
    _write_summary(rows, summary_path)

    _log_summary(rows)
    return rows


def _write_summary(rows: Sequence[dict[str, Any]], path: Path) -> None:
    summary_columns = [
        "scenario",
        "condition",
        "kind",
        "trials",
        "successes",
        "asr",
        "blocked",
        "block_rate",
        "normal_attempts",
        "false_positives",
        "false_positive_rate",
        "latency_count",
        "latency_mean_s",
        "latency_p50_s",
        "latency_p95_s",
        "latency_max_s",
    ]
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], row["condition"], row["kind"])].append(row)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_columns)
        writer.writeheader()
        for (scenario, condition, kind), group_rows in sorted(groups.items()):
            attack_rows = [r for r in group_rows if r["kind"] == "attack"]
            normal_rows = [r for r in group_rows if r["kind"] == "normal"]
            successes = sum(1 for r in attack_rows if r["success"])
            blocked_attack = sum(1 for r in attack_rows if r["blocked_by"])
            blocked_normal = sum(1 for r in normal_rows if r["blocked_by"])
            latencies = [r["latency_s"] for r in group_rows]
            lat = metrics.latency_summary(latencies) if latencies else None
            writer.writerow(
                {
                    "scenario": scenario,
                    "condition": condition,
                    "kind": kind,
                    "trials": len(attack_rows),
                    "successes": successes,
                    "asr": metrics.attack_success_rate(successes, len(attack_rows))
                    if attack_rows
                    else "",
                    "blocked": blocked_attack,
                    "block_rate": metrics.block_rate(blocked_attack, len(attack_rows))
                    if attack_rows
                    else "",
                    "normal_attempts": len(normal_rows),
                    "false_positives": blocked_normal,
                    "false_positive_rate": metrics.false_positive_rate(
                        blocked_normal, len(normal_rows)
                    )
                    if normal_rows
                    else "",
                    "latency_count": lat["count"] if lat else 0,
                    "latency_mean_s": lat["mean_s"] if lat else "",
                    "latency_p50_s": lat["p50_s"] if lat else "",
                    "latency_p95_s": lat["p95_s"] if lat else "",
                    "latency_max_s": lat["max_s"] if lat else "",
                }
            )
    LOGGER.info("wrote summary to %s", path)


def _log_summary(rows: Sequence[dict[str, Any]]) -> None:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], row["condition"])].append(row)

    for (scenario, condition), group_rows in sorted(groups.items()):
        attack_rows = [r for r in group_rows if r["kind"] == "attack"]
        normal_rows = [r for r in group_rows if r["kind"] == "normal"]
        if attack_rows:
            successes = sum(1 for r in attack_rows if r["success"])
            blocked = sum(1 for r in attack_rows if r["blocked_by"])
            asr = metrics.attack_success_rate(successes, len(attack_rows))
            br = metrics.block_rate(blocked, len(attack_rows))
            lat = metrics.latency_summary([r["latency_s"] for r in attack_rows])
            LOGGER.info(
                "%s / %s: trials=%d successes=%d ASR=%.3f blocked=%d "
                "block_rate=%.3f latency_mean=%.2fs p95=%.2fs",
                scenario,
                condition,
                len(attack_rows),
                successes,
                asr,
                blocked,
                br,
                lat["mean_s"],
                lat["p95_s"],
            )
        if normal_rows:
            blocked = sum(1 for r in normal_rows if r["blocked_by"])
            fpr = metrics.false_positive_rate(blocked, len(normal_rows))
            LOGGER.info(
                "  normal: attempts=%d blocked=%d FPR=%.3f",
                len(normal_rows),
                blocked,
                fpr,
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evaluation.run_experiments",
        description="Run S1/S2/S3 attack variants and write CSV summary plus JSONL trace.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=None,
        help="Scenario id (S1, S2, S3). Repeat to run several. Default: all.",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=10,
        help="Trials per attack variant per condition (min 10 for final runs).",
    )
    parser.add_argument(
        "--normal-trials",
        type=int,
        default=1,
        dest="normal_trials",
        help="Trials per normal question per condition.",
    )
    parser.add_argument(
        "--conditions",
        default=None,
        help="Comma-separated condition names applied to every scenario.",
    )
    parser.add_argument(
        "--no-normal",
        action="store_true",
        help="Skip normal questions.",
    )
    parser.add_argument(
        "--no-prepare",
        action="store_true",
        help="Do not rebuild derived collections.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and estimated time without running.",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Tag for output file names (default: UTC timestamp).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for CSV output (default: evaluation/results).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    scenarios = args.scenario or ["S1", "S2", "S3"]
    conditions = (
        [c.strip() for c in args.conditions.split(",") if c.strip()] if args.conditions else None
    )
    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    tag = args.tag or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"run-{tag}.csv"

    try:
        rows = run(
            scenarios,
            args.trials,
            conditions=conditions,
            include_normal=not args.no_normal,
            normal_trials=args.normal_trials,
            prepare=not args.no_prepare,
            dry_run=args.dry_run,
            tag=tag,
            output_dir=output_dir,
            output_path=output_path,
        )
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("experiment run failed: %s", exc)
        return 1

    if args.dry_run:
        return 0
    LOGGER.info("done: %d runs written to %s", len(rows), output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
