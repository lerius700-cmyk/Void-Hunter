"""Bullets: PlayerBullet (moves +X) and EnemyBullet (aims at target)."""
from __future__ import annotations

import math

import pygame


class PlayerBullet:
    SPEED_PX_S = 480.0
    SIZE = (12, 4)
    POOL_SIZE = 32

    # `spawn_time` is the scene time at which this bullet was fired —
    # the code-driven VFX (fx/bullet_vfx.py) reads it to compute
    # alpha/scale/halo phase. `weapon` is which of the 10 weapons
    # fired this bullet so the VFX knows which animation to apply.
    __slots__ = ("x", "y", "vx", "vy", "alive", "spawn_time", "weapon")

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.alive = False
        self.spawn_time: float = 0.0
        self.weapon: int = 0

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x > 480 + 12 or self.x < -12:
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 6), int(self.y - 2), 12, 4)


class EnemyBullet:
    SPEED_PX_S = 220.0
    SIZE = (8, 8)
    POOL_SIZE = 64

    __slots__ = ("x", "y", "vx", "vy", "alive", "damage",
                 "speed_mult", "_bomb", "_bomb_fuse")

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.damage = 1
        self.alive = False
        self.speed_mult: float = 1.0
        self._bomb: bool = False
        self._bomb_fuse: float = 0.0

    def spawn(self, x: float, y: float, target_x: float, target_y: float) -> None:
        dx, dy = target_x - x, target_y - y
        d = math.hypot(dx, dy) or 1.0
        self.vx = dx / d * self.SPEED_PX_S
        self.vy = dy / d * self.SPEED_PX_S
        self.x, self.y, self.alive = x, y, True
        # Reset per-shot flags.
        self.speed_mult = 1.0
        self._bomb = False
        self._bomb_fuse = 0.0

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        if self._bomb:
            # Gravity bomb: constant horizontal velocity, accelerating
            # downward. Fuse timer kills the bullet if it doesn't hit
            # anything (so they don't accumulate forever).
            self._bomb_fuse += dt
            self.x += self.vx * self.speed_mult * dt
            self.y += self.vy * self.speed_mult * dt
            self.vy += 360.0 * dt  # gravity (px/s^2)
            if self._bomb_fuse > 4.0:
                self.alive = False
        else:
            self.x += self.vx * dt
            self.y += self.vy * dt
        if not (-16 <= self.x <= 496 and -16 <= self.y <= 286):
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        if self._bomb:
            return pygame.Rect(int(self.x - 5), int(self.y - 5), 10, 10)
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)
