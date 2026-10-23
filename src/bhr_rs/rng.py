"""Deterministic random stream, shared across implementations.

Algorithm: xorshift64* with stream derivation, as specified in the internal
fixed-point engine's decision record ADR-001. Sharing it means the logistics
programme, the Rust core and any future implementation consume the same stream
from the same seed, which is what makes a scenario reproducible across
languages.

The shim exposes the subset of the random.Random interface used here, so calling
code does not change shape when the stream implementation changes under it.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, TypeVar

MASK = (1 << 64) - 1
GOLDEN = 0x9E3779B97F4A7C15
MULTIPLIER = 0x2545F4914F6CDD1D

T = TypeVar("T")


class StreamRandom:
    def __init__(self, seed: int) -> None:
        state = seed & MASK
        self._state = state if state else GOLDEN

    @classmethod
    def from_stream(cls, tick: int, system_tag: int) -> "StreamRandom":
        return cls(((tick * GOLDEN) & MASK) ^ (system_tag & MASK))

    def next_u64(self) -> int:
        x = self._state
        x ^= x >> 12
        x ^= (x << 25) & MASK
        x ^= x >> 27
        self._state = x
        return (x * MULTIPLIER) & MASK

    def frac_raw(self) -> int:
        """[0, 65535], the Q16.16 fraction used by the studio engine."""
        return self.next_u64() >> 48

    def random(self) -> float:
        return self.frac_raw() / 65536.0

    def below(self, upper_exclusive: int) -> int:
        if upper_exclusive <= 0:
            raise ValueError("upper_exclusive must be positive")
        return self.next_u64() % upper_exclusive

    def randrange(self, upper_exclusive: int) -> int:
        return self.below(upper_exclusive)

    def randint(self, low: int, high: int) -> int:
        return low + self.below(high - low + 1)

    def uniform(self, low: float, high: float) -> float:
        return low + (high - low) * self.random()

    def choice(self, sequence: Sequence[T]) -> T:
        return sequence[self.below(len(sequence))]

    def choices(self, population: Sequence[T], weights: Iterable[float] = None, k: int = 1) -> List[T]:
        masses = list(weights) if weights is not None else [1.0] * len(population)
        total = float(sum(masses))
        picked: List[T] = []
        for _ in range(k):
            target = self.random() * total
            running = 0.0
            chosen = population[-1]
            for item, mass in zip(population, masses):
                running += mass
                if target <= running:
                    chosen = item
                    break
            picked.append(chosen)
        return picked

    def fork(self, tag: int) -> "StreamRandom":
        return StreamRandom(self.next_u64() ^ tag)
