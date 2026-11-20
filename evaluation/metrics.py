"""Metrics computed from evaluation/results, never from memory.

Owner: C. Every function takes counts or raw values, so a number in the report
can always be traced back to the rows that produced it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def attack_success_rate(successes: int, trials: int) -> float:
    """ASR = successful attempts / total attempts.

    A zero denominator is an error rather than 0.0, because "no attempt made"
    must never look like "no attack succeeded".
    """
    return _rate(successes, trials, "attack_success_rate")


def block_rate(blocked: int, attempts: int) -> float:
    """Share of attempts a mitigation refused; same denominator rule as ASR."""
    return _rate(blocked, attempts, "block_rate")


def false_positive_rate(blocked: int, normal_attempts: int) -> float:
    """Share of benign questions a mitigation blocked, i.e. its cost to normal use."""
    return _rate(blocked, normal_attempts, "false_positive_rate")


def latency_summary(latencies: Sequence[float]) -> dict[str, float | int]:
    """Count, mean, p50, p95 and max for one condition's latencies."""
    if not latencies:
        raise ValueError("latency_summary: at least one latency is required")
    if any(value < 0 for value in latencies):
        raise ValueError("latency_summary: latencies must be non-negative")

    ordered = sorted(latencies)
    return {
        "count": len(ordered),
        "mean_s": sum(ordered) / len(ordered),
        "p50_s": _percentile(ordered, 0.50),
        "p95_s": _percentile(ordered, 0.95),
        "max_s": ordered[-1],
    }


def _rate(numerator: int, denominator: int, label: str) -> float:
    if denominator <= 0:
        raise ValueError(f"{label}: denominator must be positive, got {denominator}")
    if not 0 <= numerator <= denominator:
        raise ValueError(f"{label}: numerator {numerator} is outside 0..{denominator}")
    return numerator / denominator


def _percentile(ordered: list[float], fraction: float) -> float:
    """Nearest-rank percentile, so small samples stay interpretable."""
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]
