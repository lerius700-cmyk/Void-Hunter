"""SeededRNG — splitmix64 wrapper for the roguelike system (BLOQUE 57).

Wraps splitmix64 with a Pythonic API: random(), randint(), choice(),
choices(), shuffle(), gauss(). State is fully owned by the instance;
no global `random` is touched. State can be saved/restored for
replay divergence detection.

NO `import random` — every method derives from internal state.
"""
from __future__ import annotations

import math
from typing import Any, Sequence, TypeVar

from src.roguelike.seed import _MASK_64, splitmix64

T = TypeVar("T")


class SeededRNG:
    """Deterministic RNG based on splitmix64. Replaces `random` for
    roguelike code paths.

    Usage:
        rng = SeededRNG(seed=42)
        rng.random()              # float in [0, 1)
        rng.randint(1, 6)         # int in [1, 6]
        rng.choice(['a', 'b'])    # 'a' or 'b'
        rng.choices(pool, [0.7, 0.3])  # weighted choice
        rng.shuffle([1, 2, 3])    # in-place shuffle
        rng.gauss(0, 1)           # normal distribution

        # Save/restore for replay
        state = rng.state_dict()
        rng2 = SeededRNG(seed=0)
        rng2.load_state_dict(state)
        assert rng.random() == rng2.random()  # identical outputs
    """

    def __init__(self, seed: int) -> None:
        # Normalize seed to 64-bit unsigned. splitmix64 state is the
        # CURRENT state, output is one step ahead.
        self._state: int = int(seed) & _MASK_64
        self._gauss_cached: float | None = None

    def _next(self) -> int:
        """Advance state and return next 64-bit output."""
        self._state, out = splitmix64(self._state)
        return out

    def _next_float(self) -> float:
        """Float in [0.0, 1.0) from upper 53 bits (IEEE 754 precision)."""
        out = self._next()
        # Top 53 bits / 2^53. This is what CPython's `random.random` does.
        return (out >> 11) / (1 << 53)

    def random(self) -> float:
        """Uniform float in [0.0, 1.0)."""
        return self._next_float()

    def randint(self, a: int, b: int) -> int:
        """Random integer in [a, b], inclusive on both ends."""
        if a > b:
            raise ValueError(f"randint: a ({a}) must be <= b ({b})")
        n = b - a + 1
        # Reject sampling for unbiased uniform over [0, n).
        # For typical n < 2^32 this loop runs ~1 time on average.
        threshold = (-n) % n  # largest multiple of n that fits in 64 bits
        while True:
            out = self._next()
            if out >= threshold:
                return a + (out % n)

    def choice(self, seq: Sequence[T]) -> T:
        """Pick one element uniformly."""
        if not seq:
            raise ValueError("choice: empty sequence")
        idx = self.randint(0, len(seq) - 1)
        return seq[idx]

    def choices(
        self,
        seq: Sequence[T],
        weights: Sequence[float] | None = None,
    ) -> T:
        """Pick one element with optional weights. `weights` need not sum to 1.

        If weights is None, behaves like choice(). Negative weights raise
        ValueError. Zero-weight elements are never chosen.
        """
        if not seq:
            raise ValueError("choices: empty sequence")
        if weights is None:
            return self.choice(seq)
        if len(weights) != len(seq):
            raise ValueError(
                f"choices: weights length ({len(weights)}) != seq length ({len(seq)})"
            )
        if any(w < 0 for w in weights):
            raise ValueError("choices: negative weight not allowed")
        total = float(sum(weights))
        if total <= 0.0:
            raise ValueError("choices: weights sum to zero or less")
        # Walk the cumulative distribution.
        r = self._next_float() * total
        acc = 0.0
        for item, w in zip(seq, weights):
            acc += w
            if r < acc:
                return item
        # Floating point edge: r == total. Return last item.
        return seq[-1]

    def shuffle(self, seq: list[Any]) -> None:
        """In-place Fisher-Yates shuffle. O(n) using this RNG."""
        n = len(seq)
        for i in range(n - 1, 0, -1):
            j = self.randint(0, i)
            seq[i], seq[j] = seq[j], seq[i]

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Normal distribution via Box-Muller. Returns one sample.

        Caches the second sample (polar method variant) so two calls
        give independent normals without re-computing.
        """
        cached = self._gauss_cached
        if cached is not None:
            self._gauss_cached = None
            return float(mu + sigma * cached)
        # Polar Box-Muller (avoids trig calls, slight bias is acceptable)
        while True:
            u1 = self._next_float() * 2.0 - 1.0
            u2 = self._next_float() * 2.0 - 1.0
            s = u1 * u1 + u2 * u2
            if 0.0 < s < 1.0:
                break
        factor = math.sqrt(-2.0 * math.log(s) / s)
        z1 = u1 * factor
        z2 = u2 * factor
        self._gauss_cached = z2
        return float(mu + sigma * z1)

    # ------------------------------------------------------------------
    # State save / restore (for replay)
    # ------------------------------------------------------------------
    def state_dict(self) -> dict[str, Any]:
        """Snapshot the RNG state. Pass to load_state_dict() to restore."""
        d: dict[str, Any] = {"state": self._state}
        if self._gauss_cached is not None:
            d["gauss_cached"] = self._gauss_cached
        return d

    def load_state_dict(self, d: dict[str, Any]) -> None:
        """Restore RNG state from a state_dict()."""
        if "state" not in d:
            raise ValueError("state_dict missing 'state' key")
        self._state = int(d["state"]) & _MASK_64
        if "gauss_cached" in d and d["gauss_cached"] is not None:
            self._gauss_cached = float(d["gauss_cached"])
        else:
            self._gauss_cached = None
