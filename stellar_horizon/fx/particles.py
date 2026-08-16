"""Particle FX layer wrapping Void-Hunter's ParticleEngine."""
from __future__ import annotations

import pygame

from src.systems.particle_engine import ParticleEngine
from stellar_horizon.settings import PARTICLE_POOL


class FxLayer:
    def __init__(self, pool_size: int = PARTICLE_POOL) -> None:
        self.engine = ParticleEngine(pool_size=pool_size)

    def emit_sparks(self, x: float, y: float, count: int = 8) -> None:
        for _ in range(count):
            self.engine.emit(0, x, y, 0, 0)

    def emit_explosion(self, x: float, y: float, scale: float = 1.0) -> None:
        n_sparks = int(16 * scale)
        n_smoke = int(4 * scale)
        for _ in range(n_sparks):
            self.engine.emit(0, x, y, 0, 0)
        for _ in range(n_smoke):
            self.engine.emit(2, x, y, 0, 0)

    def update(self, dt: float) -> None:
        self.engine.update(dt)

    def draw(self, surface) -> None:
        self.engine.draw(surface)
