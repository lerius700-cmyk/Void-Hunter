"""Player entity — horizontal fighter controlled by WASD/Arrows + Spacebar."""
from __future__ import annotations

import pygame


class Player:
    SPEED = 165.0
    SHOOT_COOLDOWN_S = 0.10
    BULLET_OFFSET_X = 12
    MAX_LIVES = 3
    IFRAMES_FRAMES = 30
    INVULN_FRAMES_PER_HIT = 30
    BOUND_X_MIN = 8
    BOUND_X_MAX = 472
    BOUND_Y_MIN = 16
    BOUND_Y_MAX = 254
    START_X = 40.0

    __slots__ = (
        "x", "y", "vx", "vy", "lives", "shoot_cooldown",
        "invulnerable_frames", "alive", "firing", "thrusting", "bullets",
    )

    def __init__(self, screen_rect: pygame.Rect) -> None:
        self.x: float = self.START_X
        self.y: float = float(screen_rect.centery)
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.lives: int = self.MAX_LIVES
        self.shoot_cooldown: float = 0.0
        self.invulnerable_frames: int = 0
        self.alive: bool = True
        self.firing: bool = False
        self.thrusting: bool = False
        self.bullets: list = []

    def update(self, dt: float, keys, bullets_pool) -> None:
        if not self.alive:
            return
        dx = int(bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])) - int(bool(keys[pygame.K_a] or keys[pygame.K_LEFT]))
        dy = int(bool(keys[pygame.K_s] or keys[pygame.K_DOWN]))  - int(bool(keys[pygame.K_w] or keys[pygame.K_UP]))
        if dx and dy:
            inv = 0.7071067811865475
            self.vx = dx * self.SPEED * inv
            self.vy = dy * self.SPEED * inv
            self.thrusting = True
        elif dx or dy:
            self.vx = dx * self.SPEED
            self.vy = dy * self.SPEED
            self.thrusting = True
        else:
            self.vx = self.vy = 0.0
            self.thrusting = False
        self.x = max(self.BOUND_X_MIN, min(self.BOUND_X_MAX, self.x + self.vx * dt))
        self.y = max(self.BOUND_Y_MIN, min(self.BOUND_Y_MAX, self.y + self.vy * dt))
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        if self.firing and self.shoot_cooldown <= 0.0 and bullets_pool:
            self._spawn_bullet(bullets_pool)
            self.shoot_cooldown = self.SHOOT_COOLDOWN_S
        if self.invulnerable_frames > 0:
            self.invulnerable_frames -= 1

    def take_hit(self) -> None:
        if not self.alive or self.invulnerable_frames > 0:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.alive = False
        else:
            self.invulnerable_frames = self.INVULN_FRAMES_PER_HIT

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)

    def _spawn_bullet(self, bullets_pool) -> None:
        from stellar_horizon.entities.bullet import PlayerBullet
        for b in bullets_pool:
            if not b.alive:
                b.x = self.x + self.BULLET_OFFSET_X
                b.y = self.y
                b.vx = 480.0
                b.vy = 0.0
                b.alive = True
                return
