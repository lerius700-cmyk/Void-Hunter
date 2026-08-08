"""Screen shake — Eiserloh trauma² model, max 8px.

DO NOT touch the formula. Per GDD §10:
    offset_x = max_px * trauma² * noise(seed, t)
    offset_y = max_px * trauma² * noise(seed + 1, t)
    trauma -= decay * dt
    trauma = clamp(0, 1)

The max_px scales from 4 (seed) to 8 (production).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from src.core.settings import SHAKE_MAX_PX, TRAUMA_DECAY


@dataclass
class ScreenShake:
    """Eiserloh trauma² camera shake. State-only; consumer queries offset."""
    trauma: float = 0.0
    decay: float = TRAUMA_DECAY
    max_px: float = SHAKE_MAX_PX
    seed: int = 0
    _time: float = 0.0
    _noise_x: float = 0.0
    _noise_y: float = 0.0

    def add_trauma(self, amount: float) -> None:
        """Add trauma, clamped to [0, 1]."""
        self.trauma = max(0.0, min(1.0, self.trauma + amount))

    def update(self, dt: float) -> None:
        """Advance decay + refresh noise values."""
        if dt <= 0.0:
            return
        # Trauma decays with time
        self.trauma = max(0.0, self.trauma - self.decay * dt)
        # Refresh pseudo-noise based on time
        self._time += dt
        rng = random.Random(int(self._time * 60) ^ self.seed)
        self._noise_x = rng.uniform(-1.0, 1.0)
        self._noise_y = rng.uniform(-1.0, 1.0)

    def get_offset(self) -> tuple[float, float]:
        """Return (offset_x, offset_y) per the formula.

        With trauma=0 → (0, 0). With trauma=1 → ±max_px.
        """
        if self.trauma <= 0.0:
            return (0.0, 0.0)
        sq = self.trauma * self.trauma
        return (self.max_px * sq * self._noise_x, self.max_px * sq * self._noise_y)

    def reset(self) -> None:
        self.trauma = 0.0
        self._time = 0.0
        self._noise_x = 0.0
        self._noise_y = 0.0
