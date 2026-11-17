"""Objective success checks, driven by canaries and planted false claims.

Phase 0 stub. Owner is not fixed in AGENTS.md Bagian 3 yet; the decision is
recorded in docs/decisions.md before Phase 3 work starts.
"""

from __future__ import annotations

from typing import Any


def judge(scenario: str, variant: dict, response: str) -> dict[str, Any]:
    """Return {"success": bool, "rule": str} for one attempt.

    Deterministic rules are required: a human reading the evidence folder must be
    able to reproduce the verdict without rerunning the model.
    """
    raise NotImplementedError("judges.judge is implemented together with the Phase 3 harness")
