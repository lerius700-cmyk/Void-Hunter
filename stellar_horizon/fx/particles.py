"""Particle FX layer wrapping Void-Hunter's ParticleEngine."""
from __future__ import annotations

import math
import random

import pygame

from src.systems.particle_engine import ParticleEngine
from stellar_horizon.settings import PARTICLE_POOL


class FxLayer:
    def __init__(self, pool_size: int = PARTICLE_POOL) -> None:
        self.engine = ParticleEngine(pool_size=pool_size)

    def emit_sparks(self, x: float, y: float, count: int = 8,
                    color: tuple = (255, 255, 255),
                    speed: float = 140.0) -> None:
        """Burst of N radial sparks at (x, y).

        P_SPARK (kind 0) is a fast, short-lived dot. Each spark is
        tinted by mixing the base color with white so impact flashes
        feel warmer than pure white. Speed gives a wide radial spread.
        """
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            v = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * v
            vy = math.sin(angle) * v
            # Tint: mix between the base color and white.
            t = random.uniform(0.3, 0.9)
            r = int(color[0] * t + 255 * (1 - t))
            g = int(color[1] * t + 255 * (1 - t))
            b = int(color[2] * t + 255 * (1 - t))
            self.engine.emit(0, x, y, vx, vy, color=(r, g, b),
                             life=random.uniform(0.15, 0.30))

    def emit_impact(self, x: float, y: float, count: int = 12,
                    color: tuple = (255, 240, 100)) -> None:
        """Punchy impact: spark burst + shrapnel + flash.

        Used for bullet-vs-ship hits and bomb detonations. Sparks give
        the radial spray, shrapnel adds a few heavier slower pieces
        for a weighty feel, and P_FLASH (kind 11) puts down a single-
        frame white overlay so the hit reads even on a busy frame.
        """
        self.emit_sparks(x, y, count=count, color=color, speed=180.0)
        for _ in range(4):
            angle = random.uniform(0.0, math.tau)
            v = random.uniform(60.0, 120.0)
            self.engine.emit(3, x, y, math.cos(angle) * v,
                             math.sin(angle) * v, color=color, life=0.4)
        self.engine.emit(11, x, y, 0, 0, color=(255, 255, 255), life=0.08)

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
