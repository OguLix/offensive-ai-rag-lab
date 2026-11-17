"""Runs every scenario variant and writes the CSV summary plus JSONL raw logs.

Owner: C. Phase 0 stub only.
"""

from __future__ import annotations

from collections.abc import Sequence


def run(scenarios: Sequence[str], trials: int) -> list[dict]:
    """Run each scenario in each mitigation condition and return the summary rows.

    One row per attempt, with the columns fixed in AGENTS.md Bagian 8.
    """
    raise NotImplementedError("run_experiments.run is implemented by owner C in Phase 3")


def main() -> None:
    """CLI entry point: python -m evaluation.run_experiments --scenario S1 --trials 10."""
    raise NotImplementedError("run_experiments.main is implemented by owner C in Phase 3")
