"""Enemy archetypes — 8 distinct behaviors (BLOQUE 8).

Per GDD §4:
  1. Scout (12x8) — fast, sine wobble, low HP
  2. Cruiser (14x10) — medium tank, twin cannon
  3. Heavy (18x12) — armored, slow, heavy shot
  4. Kamikaze (10x10) — homing, explodes on contact, glow telegraph
  5. Drone (8x8) — spawns 2-3 mini-drones
  6. Sniper (16x8) — static, laser beam with 60f telegraph
  7. Turret (12x12) — anchored, 3-spread rotating
  8. Carrier (20x14) — spawns scouts and drones

Each enemy has HP, speed, sprite size, attack pattern, telegraph, score,
and a `kind` string identifier (used by element-bonus lookup).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W, FIXED_DT
from src.systems.pool import Pool


# Archetype identifiers
class EnemyKind(Enum):
    SCOUT = "scout"
    CRUISER = "cruiser"
    HEAVY = "heavy"
    KAMIKAZE = "kamikaze"
    DRONE = "drone"
    SNIPER = "sniper"
    TURRET = "turret"
    CARRIER = "carrier"


# Enemy state (FSM)
class EnemyState(Enum):
    IDLE = "idle"
    ATTACK = "attack"
    TELEGRAPH = "telegraph"
    DYING = "dying"
    DEAD = "dead"


# Per-archetype config
@dataclass(frozen=True)
class _EnemyConfig:
    hp: int
    speed: float              # px/s
    width: int
    height: int
    score: int
    color: tuple[int, int, int]
    fire_cooldown_s: float    # seconds between shots
    fire_damage: int
    bullet_speed: float
    telegraph_frames: int
    drop_powerup_pct: float
    drop_bomb_pct: float
    drop_1up_pct: float
    # Per-kind behavior flags
    sine_wobble: bool = False
    sine_amplitude: float = 0.0
    sine_freq_hz: float = 0.0
    homing: bool = False
    homing_turn_rate: float = 0.0
    anchored: bool = False
    is_mini: bool = False
    spawns_mini_on_death: bool = False
    spawns_mini_on_timer: bool = False
    mini_spawn_count: int = 0
    spawns_carrier_children: bool = False


ENEMY_CONFIGS: dict[EnemyKind, _EnemyConfig] = {
    EnemyKind.SCOUT: _EnemyConfig(
        hp=1, speed=110.0, width=12, height=8, score=50,
        color=(80, 220, 240),
        fire_cooldown_s=1.5, fire_damage=1, bullet_speed=240.0,
        telegraph_frames=8,
        drop_powerup_pct=0.08, drop_bomb_pct=0.02, drop_1up_pct=0.0,
        sine_wobble=True, sine_amplitude=12.0, sine_freq_hz=1.5,
    ),
    EnemyKind.CRUISER: _EnemyConfig(
        hp=4, speed=60.0, width=14, height=10, score=150,
        color=(180, 180, 220),
        fire_cooldown_s=1.2, fire_damage=1, bullet_speed=220.0,
        telegraph_frames=14,
        drop_powerup_pct=0.12, drop_bomb_pct=0.04, drop_1up_pct=0.0,
    ),
    EnemyKind.HEAVY: _EnemyConfig(
        hp=12, speed=30.0, width=18, height=12, score=400,
        color=(180, 180, 200),
        fire_cooldown_s=2.5, fire_damage=2, bullet_speed=180.0,
        telegraph_frames=24,
        drop_powerup_pct=0.18, drop_bomb_pct=0.06, drop_1up_pct=0.01,
    ),
    EnemyKind.KAMIKAZE: _EnemyConfig(
        hp=1, speed=160.0, width=10, height=10, score=200,
        color=(255, 100, 100),
        fire_cooldown_s=0.0, fire_damage=0, bullet_speed=0.0,
        telegraph_frames=30,
        drop_powerup_pct=0.0, drop_bomb_pct=0.05, drop_1up_pct=0.0,
        homing=True, homing_turn_rate=90.0,
    ),
    EnemyKind.DRONE: _EnemyConfig(
        hp=2, speed=80.0, width=8, height=8, score=80,
        color=(80, 200, 255),
        fire_cooldown_s=0.0, fire_damage=0, bullet_speed=0.0,
        telegraph_frames=0,
        drop_powerup_pct=0.10, drop_bomb_pct=0.0, drop_1up_pct=0.0,
        spawns_mini_on_timer=True, mini_spawn_count=3,
    ),
    EnemyKind.SNIPER: _EnemyConfig(
        hp=2, speed=0.0, width=16, height=8, score=300,
        color=(255, 60, 60),
        fire_cooldown_s=4.0, fire_damage=3, bullet_speed=0.0,  # laser = instant
        telegraph_frames=60,
        drop_powerup_pct=0.15, drop_bomb_pct=0.05, drop_1up_pct=0.0,
        anchored=True,
    ),
    EnemyKind.TURRET: _EnemyConfig(
        hp=6, speed=0.0, width=12, height=12, score=250,
        color=(200, 100, 100),
        fire_cooldown_s=1.0, fire_damage=1, bullet_speed=200.0,
        telegraph_frames=6,
        drop_powerup_pct=0.12, drop_bomb_pct=0.04, drop_1up_pct=0.0,
        anchored=True,
    ),
    EnemyKind.CARRIER: _EnemyConfig(
        hp=20, speed=25.0, width=20, height=14, score=800,
        color=(150, 150, 200),
        fire_cooldown_s=0.0, fire_damage=0, bullet_speed=0.0,
        telegraph_frames=12,
        drop_powerup_pct=0.25, drop_bomb_pct=0.08, drop_1up_pct=0.03,
        spawns_carrier_children=True,
    ),
}


# Mini-drone (spawned by Drone parent)
MINI_DRONE_CONFIG = _EnemyConfig(
    hp=1, speed=100.0, width=6, height=6, score=50,
    color=(120, 200, 255),
    fire_cooldown_s=0.0, fire_damage=0, bullet_speed=0.0,
    telegraph_frames=0,
    drop_powerup_pct=0.0, drop_bomb_pct=0.0, drop_1up_pct=0.0,
    is_mini=True,
)

# String list of archetypes (used for element-bonus lookup)
ENEMY_ARCHETYPES: tuple[str, ...] = tuple(k.value for k in EnemyKind)


@dataclass
class Enemy:
    """Single enemy instance."""
    active: bool = False
    kind: EnemyKind = EnemyKind.SCOUT
    state: EnemyState = EnemyState.IDLE
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    hp: int = 1
    max_hp: int = 1
    fire_cd: float = 0.0
    telegraph_timer: int = 0
    # Sine wobble state
    sine_t: float = 0.0
    sine_origin_x: float = 0.0
    # Homing state
    homing_target: Optional[tuple[float, float]] = None
    # Turret rotation
    cannon_angle: float = 0.0
    # Spawn timer (drone, carrier)
    spawn_timer: float = 0.0
    # Children to spawn (for Drone / Carrier)
    pending_spawn_count: int = 0
    # Cleanup
    is_mini: bool = False
    # Health events
    damage_taken: int = 0
    on_death: bool = False
    on_fire: bool = False
    on_spawn_mini: bool = False

    def on_spawn(self) -> None:
        self.damage_taken = 0
        self.on_death = False
        self.on_fire = False
        self.on_spawn_mini = False
        self.pending_spawn_count = 0
        self.sine_t = 0.0
        self.sine_origin_x = 0.0

    def on_release(self) -> None:
        self.homing_target = None

    def hitbox(self) -> pygame.Rect:
        """70% forgiving hitbox per GDD §5."""
        cfg = ENEMY_CONFIGS[self.kind]
        w = int(cfg.width * 0.7)
        h = int(cfg.height * 0.7)
        return pygame.Rect(int(self.x - w // 2), int(self.y - h // 2), w, h)

    def apply_damage(self, amount: int) -> bool:
        """Returns True if this hit killed the enemy."""
        if not self.active or self.state == EnemyState.DEAD:
            return False
        self.hp -= amount
        self.damage_taken += amount
        if self.hp <= 0:
            self.state = EnemyState.DYING
            self.on_death = True
            return True
        return False

    def update(self, dt: float, player_x: float, player_y: float) -> None:
        """Advance movement, sine wobble, homing, fire cooldown, cull offscreen.

        Fires are reported via self.on_fire=True (caller spawns bullets).
        """
        if not self.active or dt <= 0.0 or self.state == EnemyState.DEAD:
            return
        cfg = ENEMY_CONFIGS[self.kind]
        # Sine wobble (Scout)
        if cfg.sine_wobble:
            self.sine_t += dt
            self.x = self.sine_origin_x + math.sin(self.sine_t * cfg.sine_freq_hz * 2.0 * math.pi) * cfg.sine_amplitude
        # Homing (Kamikaze) — steer toward player
        if cfg.homing and (self.homing_target is None or self.sine_t % 1.0 < dt):
            self.homing_target = (player_x, player_y)
        if cfg.homing and self.homing_target is not None:
            tx, ty = self.homing_target
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 0.01:
                # Current velocity points down (+y). Steer toward target.
                target_angle = math.atan2(dy, dx)
                # Convert current angle to homing
                desired_vx = math.cos(target_angle) * cfg.speed
                desired_vy = math.sin(target_angle) * cfg.speed
                # Turn rate (deg/s -> rad/s)
                turn = math.radians(cfg.homing_turn_rate) * dt
                # Blend current vx/vy toward desired
                self.vx += (desired_vx - self.vx) * min(1.0, turn)
                self.vy += (desired_vy - self.vy) * min(1.0, turn)
            else:
                self.vx = 0.0
                self.vy = cfg.speed
        # Apply velocity
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Spawn timer (Drone / Carrier)
        if cfg.spawns_mini_on_timer or cfg.spawns_carrier_children:
            self.spawn_timer += dt
            if self.spawn_timer >= 3.0:
                self.spawn_timer = 0.0
                if cfg.spawns_carrier_children:
                    self.pending_spawn_count = max(self.pending_spawn_count, 2)
                else:
                    self.pending_spawn_count = max(self.pending_spawn_count, cfg.mini_spawn_count)
        # Fire cooldown (skip if anchored w/ laser telegraph; skip if no fire_cooldown)
        if cfg.fire_cooldown_s > 0.0:
            if self.fire_cd > 0.0:
                self.fire_cd -= dt
            if self.fire_cd <= 0.0:
                self.fire_cd = cfg.fire_cooldown_s
                self.on_fire = True
        # Anchored enemies don't move vertically (already at vy=0)
        # Cull offscreen
        if self.y > INTERNAL_H + 20 or self.x < -20 or self.x > INTERNAL_W + 20:
            self.state = EnemyState.DEAD


def create_enemy(kind: EnemyKind, x: float, y: float) -> Enemy:
    """Factory: returns an inactive Enemy with the kind's config applied.

    The caller is expected to call pool.acquire() (or instantiate directly)
    and then set fields. We provide this for direct construction.
    """
    e = Enemy()
    e.kind = kind
    e.x = x
    e.y = y
    cfg = ENEMY_CONFIGS[kind]
    e.hp = cfg.hp
    e.max_hp = cfg.hp
    e.vy = cfg.speed  # default downward
    e.vx = 0.0
    e.fire_cd = cfg.fire_cooldown_s
    e.sine_origin_x = x
    e.is_mini = cfg.is_mini
    e.active = True
    return e


class EnemyPool:
    """Pool of Enemy instances. Default size 64 per GDD."""

    def __init__(self, capacity: int = 64) -> None:
        self._pool: Pool[Enemy] = Pool(Enemy, capacity)

    @property
    def pool(self) -> Pool[Enemy]:
        return self._pool

    @property
    def active_count(self) -> int:
        return self._pool.active_count

    def spawn(self, kind: EnemyKind, x: float, y: float) -> Enemy | None:
        e = self._pool.acquire()
        if e is None:
            return None
        # Reset
        e.on_spawn()
        e.kind = kind
        e.x = x
        e.y = y
        e.state = EnemyState.IDLE
        cfg = ENEMY_CONFIGS[kind]
        e.hp = cfg.hp
        e.max_hp = cfg.hp
        e.vy = cfg.speed
        e.vx = 0.0
        e.fire_cd = cfg.fire_cooldown_s
        e.sine_origin_x = x
        e.sine_t = 0.0
        e.cannon_angle = 0.0
        e.spawn_timer = 0.0
        e.is_mini = cfg.is_mini
        e.active = True
        return e

    def release(self, e: Enemy) -> None:
        self._pool.release(e)

    def release_all(self) -> None:
        self._pool.release_all()
