"""Tests for the evaluation metrics; pure arithmetic, no model or files involved."""

from __future__ import annotations

import pytest

from evaluation import metrics


def test_attack_success_rate() -> None:
    assert metrics.attack_success_rate(3, 10) == pytest.approx(0.3)


def test_attack_success_rate_of_zero_is_zero_not_an_error() -> None:
    assert metrics.attack_success_rate(0, 10) == 0.0


def test_attack_success_rate_rejects_zero_trials() -> None:
    # "no attempt made" must never be reported as "no attack succeeded".
    with pytest.raises(ValueError, match="denominator"):
        metrics.attack_success_rate(0, 0)


def test_attack_success_rate_rejects_more_successes_than_trials() -> None:
    with pytest.raises(ValueError, match="outside"):
        metrics.attack_success_rate(11, 10)


def test_attack_success_rate_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="outside"):
        metrics.attack_success_rate(-1, 10)


def test_block_rate() -> None:
    assert metrics.block_rate(4, 10) == pytest.approx(0.4)


def test_block_rate_rejects_zero_attempts() -> None:
    with pytest.raises(ValueError, match="denominator"):
        metrics.block_rate(0, 0)


def test_false_positive_rate() -> None:
    assert metrics.false_positive_rate(1, 20) == pytest.approx(0.05)


def test_false_positive_rate_rejects_zero_questions() -> None:
    with pytest.raises(ValueError, match="denominator"):
        metrics.false_positive_rate(0, 0)


def test_latency_summary_reports_count_mean_percentiles_and_max() -> None:
    latencies = [float(value) for value in range(1, 11)]

    summary = metrics.latency_summary(latencies)

    assert summary["count"] == 10
    assert summary["mean_s"] == pytest.approx(5.5)
    assert summary["p50_s"] == 5.0
    assert summary["p95_s"] == 10.0
    assert summary["max_s"] == 10.0


def test_latency_summary_handles_a_single_sample() -> None:
    summary = metrics.latency_summary([2.5])

    assert summary["count"] == 1
    assert summary["p50_s"] == 2.5
    assert summary["p95_s"] == 2.5


def test_latency_summary_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one"):
        metrics.latency_summary([])


def test_latency_summary_rejects_negative_latency() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        metrics.latency_summary([0.5, -0.1])
