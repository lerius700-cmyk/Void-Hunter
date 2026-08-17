"""Enemy entity with 6 Phase 1 types: SCOUT, CRUISER, HEAVY, BOMBER, UFO, KAMIKAZE.

Three new types were added in the sprite-expansion pass:
  - BOMBER: slow, drops gravity bombs that fall and explode.
  - UFO: medium speed on a sinuous path, fires aimed shots.
  - KAMIKAZE: very fast, homes toward the player and detonates on contact.

The base shooting behavior (telegraph + cooldown) is shared; each kind
overrides a couple of methods to specialize. Bomber/Kamikaze bullets
are produced by emitting a bullet object the caller can route to a
special pool (gravity bombs) or apply special contact damage.
"""
from __future__ import annotations

import math

import pygame
from src.movement import PathFollower


class EnemyKind:
    SCOUT = "scout"
    CRUISER = "cruiser"
    HEAVY = "heavy"
    BOMBER = "bomber"
    UFO = "ufo"
    KAMIKAZE = "kamikaze"


_TYPE_PARAMS = {
    EnemyKind.SCOUT:     {"hp": 1,  "attack_cd": 1.5, "telegraph": 8,  "score":  50, "speed": 110.0},
    EnemyKind.CRUISER:   {"hp": 4,  "attack_cd": 1.2, "telegraph": 14, "score": 150, "speed":  60.0},
    EnemyKind.HEAVY:     {"hp": 12, "attack_cd": 2.5, "telegraph": 24, "score": 400, "speed":  30.0},
    # New types (Phase 1 expansion).
    EnemyKind.BOMBER:    {"hp": 2,  "attack_cd": 2.4, "telegraph": 12, "score": 200, "speed":  45.0},
    EnemyKind.UFO:       {"hp": 3,  "attack_cd": 1.6, "telegraph": 18, "score": 175, "speed":  70.0},
    EnemyKind.KAMIKAZE:  {"hp": 1,  "attack_cd": 0.0, "telegraph":  0, "score": 100, "speed": 180.0},
}


class Enemy:
    __slots__ = (
        "x", "y", "vx", "vy", "kind", "hp", "max_hp", "alive",
        "shoot_cooldown", "telegraphing", "telegraph_frames",
        "path_follower", "slot_dx", "slot_dy", "path_done",
        # Type-specific state.
        "bomb_timer",       # BOMBER: seconds until next gravity bomb drop
        "ufo_phase",        # UFO: sinuous oscillation phase
        "ufo_base_y",       # UFO: center y of the sinuous wave
        "kamikaze_charge",  # KAMIKAZE: seconds spent charging (0 = cruising)
        # Visual variant (set by the spawner, used by the draw code).
        "sprite_name",
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
        self.bomb_timer: float = 0.0
        self.ufo_phase: float = 0.0
        self.ufo_base_y: float = 0.0
        self.kamikaze_charge: float = 0.0
        self.sprite_name: str = ""

    def on_spawn(self) -> None:
        params = _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])
        self.hp = self.max_hp = params["hp"]
        self.alive = True
        self.shoot_cooldown = 1.0
        self.telegraphing = False
        self.telegraph_frames = 0
        self.path_done = False
        # Reset per-type state.
        self.bomb_timer = 1.5  # first bomb drops after 1.5s on screen
        self.ufo_phase = 0.0
        self.ufo_base_y = 0.0
        self.kamikaze_charge = 0.0

    def attach_path(self, follower: PathFollower, slot_dx: float, slot_dy: float) -> None:
        self.path_follower = follower
        self.slot_dx, self.slot_dy = slot_dx, slot_dy

    def update(self, dt: float, player) -> list:
        """Returns a list of new bullets to add to the appropriate pool.

        Regular aimed shots are returned as EnemyBullet instances. Bomber
        bombs are returned as EnemyBullet too but flagged via a `_bomb`
        attribute on the bullet (the caller checks for it and routes it
        to a gravity-aware update path).
        """
        from stellar_horizon.entities.bullet import EnemyBullet
        if not self.alive:
            return []
        new_bullets: list = []

        # --- Movement: path follower for all kinds except KAMIKAZE
        # (kamikaze homes in on the player instead of following a path).
        if self.kind == EnemyKind.KAMIKAZE:
            self._update_kamikaze(dt, player)
        else:
            if self.path_follower and not self.path_done:
                pos, vel = self.path_follower.update(dt)
                self.x = pos.x + self.slot_dx
                self.y = pos.y + self.slot_dy
                self.vx, self.vy = vel.x, vel.y
                if self.path_follower.is_complete:
                    self.path_done = True
                    if self.kind == EnemyKind.UFO:
                        # UFO remembers its current Y as the wave centerline.
                        self.ufo_base_y = self.y
            elif self.path_done:
                self.x -= 30.0 * dt
            # UFO: once the entry path is done, oscillate vertically.
            if self.kind == EnemyKind.UFO and self.path_done:
                self.ufo_phase += dt
                self.y = self.ufo_base_y + math.sin(self.ufo_phase * 2.5) * 35.0
                # Keep a small leftward drift even while oscillating.
                self.x -= 18.0 * dt

        # --- Per-type fire behavior ----------------------------------
        if self.kind == EnemyKind.BOMBER:
            self.bomb_timer -= dt
            if self.bomb_timer <= 0.0 and self._can_shoot():
                b = EnemyBullet()
                # Bombs drop straight down with gravity, no aim.
                b.spawn(self.x - 4.0, self.y + 4.0, self.x - 4.0, self.y + 80.0)
                b.speed_mult = 0.55  # slower initial fall
                b._bomb = True
                new_bullets.append(b)
                self.bomb_timer = 2.0
        elif self.kind == EnemyKind.KAMIKAZE:
            # Kamikaze doesn't shoot; it crashes into the player.
            pass
        else:
            # Standard telegraph + cooldown shot.
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

    # ------------------------------------------------------------------
    # Per-kind helpers
    # ------------------------------------------------------------------

    def _update_kamikaze(self, dt: float, player) -> None:
        """Kamikaze: lock onto the player and accelerate toward them."""
        # First 0.4s: cruise in along the entry path (if any).
        if self.path_follower and not self.path_done:
            pos, vel = self.path_follower.update(dt)
            self.x = pos.x + self.slot_dx
            self.y = pos.y + self.slot_dy
            self.vx, self.vy = vel.x, vel.y
            if self.path_follower.is_complete:
                self.path_done = True
            return
        # After entry: home toward player with a strong turn rate.
        self.kamikaze_charge += dt
        dx, dy = player.x - self.x, player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        # Steer velocity toward player. Lerp the heading; max turn rate
        # scales with the kamikaze speed so it always feels committed.
        target_vx = dx / d * 180.0
        target_vy = dy / d * 180.0
        # Quick lerp (0.18 per frame) for a snappy feel.
        self.vx = self.vx + (target_vx - self.vx) * 0.18
        self.vy = self.vy + (target_vy - self.vy) * 0.18
        self.x += self.vx * dt
        self.y += self.vy * dt

    def take_damage(self, amount: int) -> None:
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        if self.kind in (EnemyKind.HEAVY, EnemyKind.BOMBER):
            return pygame.Rect(int(self.x - 9), int(self.y - 6), 18, 12)
        if self.kind == EnemyKind.UFO:
            return pygame.Rect(int(self.x - 7), int(self.y - 5), 14, 10)
        return pygame.Rect(int(self.x - 5), int(self.y - 5), 10, 10)

    def score_value(self) -> int:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["score"]

    def _attack_cooldown(self) -> float:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["attack_cd"]

    def _telegraph_frames(self) -> int:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["telegraph"]

    def _can_shoot(self) -> bool:
        return 0 <= self.x <= 480 and 0 <= self.y <= 270

    # ------------------------------------------------------------------
    # External flags used by the gameplay scene for special effects
    # ------------------------------------------------------------------

    @property
    def contact_damage(self) -> int:
        """Damage dealt on player contact. Kamikaze blows up hard."""
        if self.kind == EnemyKind.KAMIKAZE:
            return 2
        return 1
