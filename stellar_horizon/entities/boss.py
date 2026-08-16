"""Boss: ASTEROID_GUARDIAN, 2 phases + entry + dying."""
from __future__ import annotations

import math

import pygame
from src.movement import HybridPath, PathFollower

from stellar_horizon.waves.bezier_horizontal import path_boss_entry


class BossPhase:
    ENTERING = "entering"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    DYING = "dying"
    DEAD = "dead"


class Boss:
    MAX_HP = 60
    PHASE_2_HP_THRESHOLD = 30
    DYING_DURATION_S = 1.5
    PHASE_1_ATTACK_CD = 1.2
    PHASE_2_ATTACK_CD = 0.9
    ARENA_X = 350.0
    ARENA_Y = 135.0
    HITBOX_W = 48
    HITBOX_H = 48

    __slots__ = (
        "x", "y", "hp", "max_hp", "phase", "entry_follower",
        "alive", "attack_cd", "dying_timer",
        "beam_telegraph", "beam_telegraph_frames", "beam_active", "beam_active_frames",
        "beam_timer",
    )

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.hp: int = self.MAX_HP
        self.max_hp: int = self.MAX_HP
        self.phase: str = BossPhase.ENTERING
        self.entry_follower: PathFollower = PathFollower(HybridPath.from_segments([path_boss_entry()]))
        self.alive: bool = True
        self.attack_cd: float = 0.5
        self.dying_timer: float = 0.0
        self.beam_telegraph: bool = False
        self.beam_telegraph_frames: int = 0
        self.beam_active: bool = False
        self.beam_active_frames: int = 0
        self.beam_timer: float = 0.0

    def update(self, dt: float, player) -> list:
        from stellar_horizon.entities.bullet import EnemyBullet
        new_bullets: list = []
        if self.phase == BossPhase.DEAD:
            return new_bullets
        if self.phase == BossPhase.ENTERING:
            pos, _ = self.entry_follower.update(dt)
            self.x, self.y = pos.x, pos.y
            if self.entry_follower.is_complete:
                self.phase = BossPhase.PHASE_1
            return new_bullets
        if self.phase == BossPhase.DYING:
            self.dying_timer += dt
            if self.dying_timer >= self.DYING_DURATION_S:
                self.phase = BossPhase.DEAD
                self.alive = False
            return new_bullets
        self.attack_cd = max(0.0, self.attack_cd - dt)
        if self.attack_cd <= 0.0:
            if self.phase == BossPhase.PHASE_1:
                b = EnemyBullet()
                b.spawn(self.x, self.y, player.x, player.y)
                new_bullets.append(b)
                self.attack_cd = self.PHASE_1_ATTACK_CD
            else:
                dx, dy = player.x - self.x, player.y - self.y
                base_angle = math.atan2(dy, dx)
                for offset in (-0.20, 0.0, +0.20):
                    b = EnemyBullet()
                    a = base_angle + offset
                    b.x, b.y = self.x, self.y
                    b.vx = math.cos(a) * EnemyBullet.SPEED_PX_S
                    b.vy = math.sin(a) * EnemyBullet.SPEED_PX_S
                    b.alive = True
                    new_bullets.append(b)
                self.attack_cd = self.PHASE_2_ATTACK_CD
        if self.phase == BossPhase.PHASE_2:
            self.beam_timer += dt
            if not self.beam_telegraph and not self.beam_active and self.beam_timer >= 3.5:
                self.beam_telegraph = True
                self.beam_telegraph_frames = 60
                self.beam_timer = 0.0
            if self.beam_telegraph:
                self.beam_telegraph_frames -= 1
                if self.beam_telegraph_frames <= 0:
                    self.beam_telegraph = False
                    self.beam_active = True
                    self.beam_active_frames = 20
            if self.beam_active:
                self.beam_active_frames -= 1
                if self.beam_active_frames <= 0:
                    self.beam_active = False
        return new_bullets

    def take_damage(self, amount: int) -> None:
        if self.phase in (BossPhase.ENTERING, BossPhase.DYING, BossPhase.DEAD):
            return
        self.hp = max(0, self.hp - amount)
        if self.hp == 0:
            self.phase = BossPhase.DYING
            self.dying_timer = 0.0
        elif self.hp <= self.PHASE_2_HP_THRESHOLD and self.phase == BossPhase.PHASE_1:
            self.phase = BossPhase.PHASE_2

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.HITBOX_W // 2), int(self.y - self.HITBOX_H // 2),
                           self.HITBOX_W, self.HITBOX_H)

    def score_value(self) -> int:
        return 5000
