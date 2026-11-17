"""Metrics computed from evaluation/results, never from memory.

Owner: C. Phase 0 stub only.
"""

from __future__ import annotations


def attack_success_rate(successes: int, trials: int) -> float:
    """ASR = successful attempts / total attempts.

    A zero denominator is an error rather than 0.0, because "no attempt made"
    must never look like "no attack succeeded".
    """
    raise NotImplementedError("metrics.attack_success_rate is implemented by owner C in Phase 3")
