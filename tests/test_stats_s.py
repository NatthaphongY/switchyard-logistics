"""Statistical machinery: properties that make the B4 claim checkable."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from switchyard.stats import (  # noqa: E402
    bootstrap_ci,
    cliffs_delta,
    holdout_split,
    sign_flip_permutation,
    sign_test_p,
    summarise_differences,
)


def test_bootstrap_interval_brackets_the_mean_and_is_ordered():
    mean, low, high = bootstrap_ci([1.0, 2.0, 3.0, 4.0, 5.0], resamples=2000)
    assert low <= mean <= high
    assert high - low < 5.0


def test_bootstrap_is_deterministic_for_a_fixed_seed():
    first = bootstrap_ci([0.5, 1.5, 2.5], resamples=500, seed=3)
    second = bootstrap_ci([0.5, 1.5, 2.5], resamples=500, seed=3)
    assert first == second


def test_permutation_test_rejects_a_consistent_effect():
    differences = [2.0] * 30
    assert sign_flip_permutation(differences, resamples=2000) < 0.01


def test_permutation_test_does_not_reject_noise():
    differences = [1.0, -1.0] * 15
    assert sign_flip_permutation(differences, resamples=2000) > 0.2


def test_sign_test_punishes_a_lopsided_split():
    assert sign_test_p(10, 0) <= 0.01
    assert sign_test_p(5, 5) == 1.0
    assert sign_test_p(0, 0) == 1.0


def test_cliffs_delta_is_extreme_for_complete_separation():
    assert cliffs_delta([3.0, 4.0, 5.0], [1.0, 2.0, 0.0]) == 1.0
    assert cliffs_delta([1.0, 2.0], [3.0, 4.0]) == -1.0


def test_holdout_split_is_disjoint_and_deterministic():
    train, test = holdout_split(20)
    assert not set(train) & set(test)
    assert train == holdout_split(20)[0]
    assert len(train) + len(test) == 20


def test_summary_reports_wins_losses_and_ties():
    summary = summarise_differences([1.0, 1.0, 0.0, -1.0], resamples=500)
    assert summary["wins"] == 2
    assert summary["losses"] == 1
    assert summary["ties"] == 1
    assert summary["ci_low"] <= summary["mean"] <= summary["ci_high"]
