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

    # Per-weapon tuning. `weapon` is an int 0..9 chosen by the
    # gameplay scene via set_weapon(); the same index is used to
    # pick a laser_NN sprite and a cooldown / muzzle velocity.
    WEAPON_COOLDOWN_S = (
        0.10,  # 0 yellow plasma
        0.10,  # 1 red pulse
        0.07,  # 2 blue ion (very fast)
        0.18,  # 3 green acid (slow, heavy)
        0.12,  # 4 purple void
        0.14,  # 5 orange fireball
        0.09,  # 6 white piercing (fast, long range)
        0.11,  # 7 pink heart
        0.13,  # 8 cyan ice
        0.10,  # 9 rainbow streak
    )
    WEAPON_BULLET_SPEED = (
        480.0,
        460.0,
        700.0,
        380.0,
        440.0,
        400.0,
        800.0,
        460.0,
        420.0,
        600.0,
    )

    __slots__ = (
        "x", "y", "vx", "vy", "lives", "shoot_cooldown",
        "invulnerable_frames", "alive", "firing", "thrusting", "bullets",
        "weapon", "_now",
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
        self.weapon: int = 0
        # Scene time, written by update() so _spawn_bullet can stamp
        # the new bullet with `spawn_time` for the VFX to use.
        self._now: float = 0.0

    def set_weapon(self, weapon: int) -> None:
        """Switch to a new weapon (0..9). No-op if already on it."""
        if 0 <= weapon < len(self.WEAPON_COOLDOWN_S) and weapon != self.weapon:
            self.weapon = weapon

    def update(self, dt: float, keys, bullets_pool, now: float = 0.0) -> None:
        if not self.alive:
            return
        # Cache the scene time so _spawn_bullet can stamp the bullet
        # with the same value the VFX will read later.
        self._now = now
        # `keys` is normally a pygame ScancodeWrapper from
        # pygame.key.get_pressed(). Tests sometimes pass a plain dict
        # with only a few entries; use .get() with a False default so
        # missing keys don't raise.
        def _k(k: int) -> bool:
            try:
                return bool(keys[k])
            except (KeyError, IndexError, TypeError):
                return False
        dx = int(_k(pygame.K_d) or _k(pygame.K_RIGHT)) - int(_k(pygame.K_a) or _k(pygame.K_LEFT))
        dy = int(_k(pygame.K_s) or _k(pygame.K_DOWN))  - int(_k(pygame.K_w) or _k(pygame.K_UP))
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
            # Cooldown matches the currently equipped weapon so
            # switching to a faster weapon (e.g. blue ion) immediately
            # changes the cadence.
            self.shoot_cooldown = self.WEAPON_COOLDOWN_S[self.weapon]
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
        # Map weapons to one of 2 SFX so the audio has variety without
        # 10 distinct shoot sounds. Light weapons use "shoot" (short
        # high-freq blip), heavy weapons use "shoot_charged" (longer
        # mid-freq thump).
        sfx_name = "shoot_charged" if self.weapon in (3, 5, 7) else "shoot"
        for b in bullets_pool:
            if not b.alive:
                b.x = self.x + self.BULLET_OFFSET_X
                b.y = self.y
                b.vx = self.WEAPON_BULLET_SPEED[self.weapon]
                b.vy = 0.0
                # Stamp spawn_time + weapon so fx/bullet_vfx.compute()
                # can pick the right animation per bullet.
                b.spawn_time = self._now
                b.weapon = self.weapon
                b.alive = True
                # Fire SFX (best-effort: no-op if audio is down).
                from stellar_horizon.audio import sfx
                sfx.play_event(sfx_name)
                return
