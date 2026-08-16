"""Enemy entity with 3 Phase 1 types: SCOUT, CRUISER, HEAVY."""
from __future__ import annotations

import pygame
from src.movement import PathFollower


class EnemyKind:
    SCOUT = "scout"
    CRUISER = "cruiser"
    HEAVY = "heavy"


_TYPE_PARAMS = {
    EnemyKind.SCOUT:   {"hp": 1,  "attack_cd": 1.5, "telegraph": 8,  "score": 50,  "speed": 110.0},
    EnemyKind.CRUISER: {"hp": 4,  "attack_cd": 1.2, "telegraph": 14, "score": 150, "speed": 60.0},
    EnemyKind.HEAVY:   {"hp": 12, "attack_cd": 2.5, "telegraph": 24, "score": 400, "speed": 30.0},
}


class Enemy:
    __slots__ = (
        "x", "y", "vx", "vy", "kind", "hp", "max_hp", "alive",
        "shoot_cooldown", "telegraphing", "telegraph_frames",
        "path_follower", "slot_dx", "slot_dy", "path_done",
    )

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.kind: str = EnemyKind.SCOUT
        self.hp: int = 1
        self.max_hp: int = 1
        self.alive: bool = False
        self.shoot_cooldown: float = 0.0
        self.telegraphing: bool = False
        self.telegraph_frames: int = 0
        self.path_follower: PathFollower | None = None
        self.slot_dx: float = 0.0
        self.slot_dy: float = 0.0
        self.path_done: bool = False

    def on_spawn(self) -> None:
        params = _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])
        self.hp = self.max_hp = params["hp"]
        self.alive = True
        self.shoot_cooldown = 1.0
        self.telegraphing = False
        self.telegraph_frames = 0
        self.path_done = False

    def attach_path(self, follower: PathFollower, slot_dx: float, slot_dy: float) -> None:
        self.path_follower = follower
        self.slot_dx, self.slot_dy = slot_dx, slot_dy

    def update(self, dt: float, player) -> list:
        from stellar_horizon.entities.bullet import EnemyBullet
        if not self.alive:
            return []
        new_bullets: list = []
        if self.path_follower and not self.path_done:
            pos, vel = self.path_follower.update(dt)
            self.x = pos.x + self.slot_dx
            self.y = pos.y + self.slot_dy
            self.vx, self.vy = vel.x, vel.y
            if self.path_follower.is_complete:
                self.path_done = True
        elif self.path_done:
            self.x -= 30.0 * dt
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        if self.telegraphing:
            self.telegraph_frames -= 1
            if self.telegraph_frames <= 0 and self._can_shoot():
                b = EnemyBullet()
                b.spawn(self.x, self.y, player.x, player.y)
                new_bullets.append(b)
                self.telegraphing = False
        elif self.shoot_cooldown <= 0.0 and self._can_shoot():
            self.telegraphing = True
            self.telegraph_frames = self._telegraph_frames()
            self.shoot_cooldown = self._attack_cooldown()
        if self.x < -32 or self.y < -32 or self.y > 302:
            self.alive = False
        return new_bullets

    def take_damage(self, amount: int) -> None:
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        if self.kind == EnemyKind.HEAVY:
            return pygame.Rect(int(self.x - 10), int(self.y - 6), 20, 12)
        return pygame.Rect(int(self.x - 6), int(self.y - 6), 12, 12)

    def score_value(self) -> int:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["score"]

    def _attack_cooldown(self) -> float:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["attack_cd"]

    def _telegraph_frames(self) -> int:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["telegraph"]

    def _can_shoot(self) -> bool:
        return 0 <= self.x <= 480 and 0 <= self.y <= 270
