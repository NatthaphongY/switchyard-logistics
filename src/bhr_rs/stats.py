"""Statistical machinery for the B4 claim (BHR-RS-08).

Every test here is implemented directly on the standard library so that an
external reader can re-derive the numbers without installing anything, and so
that no result depends on a library version.

Tests, and what each one protects against:

  * percentile bootstrap of the paired mean difference: the headline interval;
  * permutation test with a sign-flip null: does the difference survive an
    exchangeability null that assumes no effect at all;
  * exact sign test (binomial): how many scenarios improved, ignoring magnitude;
  * Cliff's delta: an effect size that does not assume a distribution;
  * holdout split: tune on one half, report on the other, so the reported effect
    was not selected after the fact.
"""

from __future__ import annotations

import math
import statistics
from typing import Dict, List, Sequence, Tuple

from .rng import StreamRandom


def bootstrap_ci(
    values: Sequence[float], resamples: int = 20000, seed: int = 7, alpha: float = 0.05
) -> Tuple[float, float, float]:
    """Percentile bootstrap of the mean. Returns (mean, low, high)."""
    if not values:
        return 0.0, 0.0, 0.0
    rng = StreamRandom(seed)
    count = len(values)
    means = []
    for _ in range(resamples):
        total = 0
        for _ in range(count):
            total += values[rng.randrange(count)]
        means.append(total / count)
    means.sort()
    low = means[int((alpha / 2.0) * resamples)]
    high = means[int((1.0 - alpha / 2.0) * resamples) - 1]
    return statistics.fmean(values), low, high


def sign_flip_permutation(
    differences: Sequence[float], resamples: int = 20000, seed: int = 11
) -> float:
    """Two-sided p-value under the sign-flip null.

    The null says each pair's sign is a coin flip. This is the correct null for a
    paired design and does not assume normality.
    """
    if not differences:
        return 1.0
    rng = StreamRandom(seed)
    observed = abs(statistics.fmean(differences))
    count = len(differences)
    hits = 0
    for _ in range(resamples):
        total = 0.0
        for value in differences:
            total += value if rng.randrange(2) else -value
        if abs(total / count) >= observed:
            hits += 1
    return (hits + 1.0) / (resamples + 1.0)


def sign_test_p(wins: int, losses: int) -> float:
    """Exact two-sided binomial test on wins versus losses (ties excluded)."""
    trials = wins + losses
    if trials == 0:
        return 1.0
    tail = sum(math.comb(trials, k) for k in range(0, min(wins, losses) + 1))
    return min(1.0, 2.0 * tail / (2 ** trials))


def cliffs_delta(sample_a: Sequence[float], sample_b: Sequence[float]) -> float:
    """Probability that a draw from A exceeds a draw from B, minus the reverse."""
    if not sample_a or not sample_b:
        return 0.0
    wins = 0
    losses = 0
    for left in sample_a:
        for right in sample_b:
            wins += left > right
            losses += left < right
    return (wins - losses) / (len(sample_a) * len(sample_b))


def holdout_split(count: int, train_fraction: float = 0.5) -> Tuple[List[int], List[int]]:
    """Deterministic interleaved split.

    Interleaving (rather than a contiguous cut) keeps both halves exposed to every
    block of seeds, so a slow drift in the generator cannot masquerade as a
    train/test difference.
    """
    cut = int(round(count * train_fraction))
    train = [index for index in range(count) if index % 2 == 0][:cut]
    test = [index for index in range(count) if index % 2 == 1]
    return train, test


def summarise_differences(
    differences: Sequence[float], resamples: int = 10000
) -> Dict[str, float]:
    mean, low, high = bootstrap_ci(differences, resamples=resamples)
    wins = sum(1 for value in differences if value > 0)
    losses = sum(1 for value in differences if value < 0)
    return {
        "mean": round(mean, 6),
        "ci_low": round(low, 6),
        "ci_high": round(high, 6),
        "wins": wins,
        "losses": losses,
        "ties": len(differences) - wins - losses,
        "p_permutation": round(sign_flip_permutation(differences, resamples=resamples), 6),
        "p_sign": round(sign_test_p(wins, losses), 6),
    }
