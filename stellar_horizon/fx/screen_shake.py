"""Eiserloh trauma² screen shake. Ported from Void-Hunter (no import)."""
from __future__ import annotations

import random


class ScreenShake:
    def __init__(self, max_offset: float = 4.0, decay: float = 6.0) -> None:
        self.trauma: float = 0.0
        self.max_offset: float = max_offset
        self.decay: float = decay
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0

    def add_trauma(self, amount: float) -> None:
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt: float) -> None:
        shake = (self.trauma ** 2) * self.max_offset
        self.offset_x = (random.random() * 2 - 1) * shake
        self.offset_y = (random.random() * 2 - 1) * shake
        self.trauma = max(0.0, self.trauma - self.decay * dt)

    def offset(self) -> tuple[float, float]:
        return self.offset_x, self.offset_y
