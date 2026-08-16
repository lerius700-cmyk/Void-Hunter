"""Bullets: PlayerBullet (moves +X) and EnemyBullet (aims at target)."""
from __future__ import annotations

import math

import pygame


class PlayerBullet:
    SPEED_PX_S = 480.0
    SIZE = (12, 4)
    POOL_SIZE = 32

    __slots__ = ("x", "y", "vx", "vy", "alive")

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.alive = False

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

    __slots__ = ("x", "y", "vx", "vy", "alive", "damage")

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.damage = 1
        self.alive = False

    def spawn(self, x: float, y: float, target_x: float, target_y: float) -> None:
        dx, dy = target_x - x, target_y - y
        d = math.hypot(dx, dy) or 1.0
        self.vx = dx / d * self.SPEED_PX_S
        self.vy = dy / d * self.SPEED_PX_S
        self.x, self.y, self.alive = x, y, True

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if not (-16 <= self.x <= 496 and -16 <= self.y <= 286):
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)
