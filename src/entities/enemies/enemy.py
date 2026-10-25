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
import random
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
    SUB_BOSS = "sub_boss"  # BLOQUE 50: mid-waves frenetic mini-boss
    MINE_ASTEROID = "mine_asteroid"  # BLOQUE 63: asteroid camo enemy


# BLOQUE 63 + 65 + 69 + 71: MINE-ASTEROID state machine constants.
# OPENING_Y_THRESHOLD: the y-coordinate (in INTERNAL_W=320 / INTERNAL_H=480
# playfield units) at which a closed MINE-ASTEROID begins to open. Per
# the user's spec, this is the "first quarter" of the 480-tall
# playfield (120/480 = 0.25). The threshold is a NAMED constant (not
# a magic number) so it can be tuned in one place. There is NO visible
# line in the game — the threshold is a behavioral marker, not a
# drawn element. The check uses `>=` (not `>`) so the mine opens AT
# the moment of crossing, not after.
#
# BLOQUE 69: 120 = first quarter (was 200 in BLOQUE 68, which was
# "upper playfield" but lacked a clear visual reference). The user
# said the line in the reference image was a "first quarter"
# indication, so 120/480 = 0.25 = "first quarter" of the map.
OPENING_Y_THRESHOLD: int = 120

# BLOQUE 71: named string constants for the 4 MINE-ASTEROID states
# (the state machine uses string values for readability in
# gameplay_runtime.py logs and render code). closed/open1/open2
# are immune to damage (BLOQUE 71: hits still trigger a white
# flash, but no HP is taken). open3 is the terminal vulnerable
# state (HP=3, 3 hits to destroy). The constants are exported so
# tests can refer to them symbolically instead of using bare
# strings.
MINE_ASTEROID_CLOSED: str = "closed"
MINE_ASTEROID_OPEN1: str = "open1"
MINE_ASTEROID_OPEN2: str = "open2"
MINE_ASTEROID_OPEN3: str = "open3"

# BLOQUE 65: per-state durations in seconds for the 4-state cycle
# (closed -> open1 -> open2 -> open3). The opening sequence plays ONE
# TIME (never returns to closed) — the mine stays in 'open3' and is
# vulnerable until destroyed. The per-state duration is 0.2s, so the
# total opening cycle is 0.6s. Per-state constants are exposed for
# tunability and for tests that need to verify transition timing.
MINE_OPEN1_DURATION_S: float = 0.2   # closed -> open1 transition (0.2s)
MINE_OPEN2_DURATION_S: float = 0.2   # open1 -> open2 transition (0.2s)
MINE_OPEN_DURATION_S: float = 0.6    # BLOQUE 65: total opening cycle (0.6s = 0.2+0.2+indefinite)
                                     # Was 1.0 in BLOQUE 64.5 (was the duration of the legacy 'open' state).
                                     # Kept as a public constant for backward-compat (e.g. test docs that
                                     # still reference it). Equals MINE_OPEN1 + MINE_OPEN2.
MINE_OPEN3_DURATION_S: float = float("inf")  # open3 is the terminal vulnerable state (no transition out)

# BLOQUE 67: fire 1 fan (3 bullets) per second while in open3. The
# mine opens, becomes vulnerable, and CONTINUES firing forward at 1Hz
# until destroyed. The first fan fires on entry to open3; subsequent
# fans fire every MINE_FIRE_INTERVAL_S. Required so the player has a
# continuous threat to dodge while the mine is alive in its open form.
MINE_FIRE_INTERVAL_S: float = 1.0

# Fan pattern for the 3 bullets fired in 'open' state.
MINE_FAN_ANGLE_DEG: float = 15.0       # ±15° from straight down
MINE_FAN_BULLET_SPEED: float = 80.0    # px/s

# 50% powerup drop on destroy.
MINE_POWERUP_DROP_RATE: float = 0.50

# Fraction of obstacle spawns that become MINE-ASTEROID.
# 1/8 = 0.125 per spec.
MINE_SPAWN_FRACTION: float = 1.0 / 4.0  # BLOQUE 64.5: 1/8 → 1/4 (25%, antes 12.5%)


def pick_mine_powerup(rng: random.Random) -> "PowerupKind":
    """BLOQUE 63: pool of powerups MINE-ASTEROID can drop. Excludes
    SCORE (the camo tension is the reward, not the points).

    Equal-weight pick between BOMB / HP / WEAPON.
    """
    from src.entities.asteroid import PowerupKind
    return rng.choice([PowerupKind.BOMB, PowerupKind.HP, PowerupKind.WEAPON])


def should_drop_mine_powerup(rng: random.Random) -> bool:
    """BLOQUE 63: 50% chance MINE-ASTEROID drops a powerup when destroyed."""
    return rng.random() < MINE_POWERUP_DROP_RATE


def spawn_obstacle(rng: random.Random) -> tuple[str, dict]:
    """BLOQUE 63: spawn one obstacle. ~1/8 of obstacles are MINE_ASTEROID,
    the rest are regular asteroids (caller picks variant/scale).

    Returns:
        ("asteroid", payload) where payload is a dict with x/y/variant/scale
            keys suitable for constructing an Asteroid.
        ("mine_asteroid", payload) where payload is a dict with x/y keys
            suitable for constructing an Enemy(MINE_ASTEROID).
    """
    from src.core.settings import INTERNAL_H, INTERNAL_W
    if rng.random() < MINE_SPAWN_FRACTION:
        # MINE_ASTEROID — pick a starting x, y, and DRIFT VELOCITY near
        # the spawn line. Without drift, the mine would be stuck at the
        # spawn y forever (vx=vy=0 by default on the Enemy dataclass)
        # and would never reach OPENING_Y_THRESHOLD to trigger the open
        # cycle. This was the bug that made MINE-ASTEROIDs "static" in
        # gameplay: they were being spawned at y=-80..0 with no velocity
        # and never appeared on screen.
        x = rng.uniform(24, INTERNAL_W - 24)
        y = rng.uniform(-80, 0)
        drift_vx = rng.uniform(-15, 15)  # same range as regular asteroids
        drift_vy = rng.uniform(20, 50)   # downward drift, same as asteroids
        return ("mine_asteroid", {
            "x": x, "y": y,
            "drift_vx": drift_vx, "drift_vy": drift_vy,
        })
    # Regular asteroid
    from src.entities.asteroid import spawn_asteroid
    ast = spawn_asteroid(rng)
    # BLOQUE 64.A: ``hp`` was removed from the Asteroid dataclass.
    # The obstacle payload still includes a placeholder (0) for the
    # legacy ``asteroid`` consumer code, which now ignores the field.
    return ("asteroid", {
        "x": ast.x, "y": ast.y,
        "variant": ast.variant, "scale": ast.scale,
        "drift_vx": ast.drift_vx, "drift_vy": ast.drift_vy,
        "hidden_powerup": ast.hidden_powerup,
    })


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
    # BLOQUE 58.6.2: wrap_around — when the enemy exits the bottom of the
    # screen, wrap it back to the top instead of marking it DEAD. Used by
    # SUB_BOSS for the "entra y sale del mapa repetidas veces" pattern.
    wrap_around: bool = False
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
        sine_wobble=False, sine_amplitude=0.0, sine_freq_hz=0.0,
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
    # BLOQUE 50: SUB_BOSS — mid-wave mini-boss. Fast (90 px/s, 1.5x cruiser),
    # HP 20 (more than cruiser, less than full boss), high fire rate (every
    # 0.4s = 2.5 shots/s), and a frenetic sine wobble (3 Hz, 22px amplitude)
    # so it's hard to track. Aim-shot at the player, so the player has to
    # dodge constantly. Visually a yellow/orange dart.
    # BLOQUE 58.6.2: HP x20 (20 -> 400) per user request, sine wobble OFF
    # (moves in straight line instead). wrap_around=True so the sub-boss
    # re-enters from the top after exiting the bottom (continuous entry/exit
    # pattern, no sine wobble, just a clean vertical line).
    # BLOQUE 58.6.3: hitbox 50% bigger (16x10 -> 24x14) so it's easier
    # to shoot, AND random entry point (re-enters at a random x within
    # the playfield instead of always center-vertical). Propulsion
    # animation is rendered separately in the gameplay_runtime draw.
    # BLOQUE 58.6.4: 4-entry movement cycle. Each entry the sub-boss
    # exits through a different wall and re-enters through it. Every
    # 2 entries the cycle does an "L pattern" (vertical then horizontal
    # to exit through a side wall) instead of a straight line:
    #   0: top -> down -> bottom
    #   1: top -> down -> L-right -> right (L pattern)
    #   2: bottom -> up -> top
    #   3: bottom -> up -> L-left -> left (L pattern)
    # Re-entry happens through the wall it just exited.
    EnemyKind.SUB_BOSS: _EnemyConfig(
        hp=400, speed=90.0, width=24, height=14, score=600,
        color=(255, 200, 80),
        fire_cooldown_s=0.4, fire_damage=1, bullet_speed=280.0,
        telegraph_frames=6,
        drop_powerup_pct=0.30, drop_bomb_pct=0.15, drop_1up_pct=0.05,
        sine_wobble=False, sine_amplitude=0.0, sine_freq_hz=0.0,
        wrap_around=True,
    ),
    # BLOQUE 63 + 64.A + 65: MINE_ASTEROID. Camouflage enemy that uses the
    # asteroid aesthetic when closed (visually identical to a regular
    # asteroid). BLOQUE 64.A: HP=3 (was 2) so it takes 3 hits to
    # destroy. The closed-state bullet immunity (BLOQUE 63) is
    # preserved; hits land only when mine_state is open1/open2/open3
    # (BLOQUE 65 4-state cycle).
    # fire_cooldown_s is unused (the mine fires via its own state
    # machine, not the legacy fire_cd/telegraph path).
    EnemyKind.MINE_ASTEROID: _EnemyConfig(
        hp=3, speed=30.0, width=16, height=16, score=0,
        color=(140, 100, 60),  # brown rocky palette (matches asteroid)
        fire_cooldown_s=0.0, fire_damage=0, bullet_speed=0.0,
        telegraph_frames=0,
        drop_powerup_pct=0.0, drop_bomb_pct=0.0, drop_1up_pct=0.0,  # handled by pick_mine_powerup
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
    # BLOQUE 47: SQUADRON (Star Fox 64 style) — leader/follower path tracking.
    # If squadron_id >= 0, the enemy's position is computed from a shared
    # sine-wave path each frame, replayed with a time_offset. This makes
    # followers trail the leader exactly.
    squadron_id: int = -1
    squadron_origin_x: float = 0.0
    squadron_time_offset: float = 0.0  # seconds behind the leader (0 for leader)
    squadron_age: float = 0.0         # seconds since this enemy "entered" the path
                                       # starts at -time_offset_s so followers appear
                                       # at the leader's past position
    # BLOQUE 58.next: leader flag, mirrored from SpawnedShip.is_leader at
    # spawn time by runtime.spawn_pattern_wave. Default False for all
    # non-leader enemies (followers keep the default SCOUT HP from the
    # pool, no scaling). Exposed as a public attribute so downstream
    # consumers (HUD, score, AI) can read it directly.
    is_leader: bool = False
    # BLOQUE 58.6.4: SUB_BOSS movement pattern state. Tracks which
    # entry cycle we're on and whether the current path includes
    # an "L pattern" (vertical-then-horizontal exit). Used by the
    # wrap-around in update() and the L turn check.
    sb_entry_count: int = 0        # how many times the sub-boss has entered
    sb_current_wall: str = "top"  # which wall the current entry is from
    sb_is_l: bool = False         # current path is an L pattern
    sb_turn_done: bool = False    # L turn already executed
    sb_turn_at_x: float = 0.0    # for vertical L: x to start the sideways leg
    sb_turn_at_y: float = 0.0    # for vertical L: y to start the sideways leg
    sb_post_turn_vx: float = 0.0 # velocity after the L turn (horizontal)
    sb_post_turn_vy: float = 0.0 # velocity after the L turn (vertical=0)
    # BLOQUE 58.6x: optional PathFollower (Bezier + Waypoint). If set,
    # update() uses it to drive position + velocity (and the vx/vy straight-
    # line code below is bypassed). If None, the enemy falls through to the
    # original straight-line + L-turn motion. Forward-declared; the actual
    # type lives in src.movement.follower to keep the dependency one-way.
    path_follower: object | None = None  # PathFollower | None (forward-ref)
    path_slot_dx: float = 0.0           # formation slot offset (added to path pos)
    path_slot_dy: float = 0.0
    # BLOQUE 59: animation state for per-frame sprite lookup. The new
    # sprite system (Assets/sprites/enemies/<kind>/<animation>/frame_NN.png)
    # has 4 animations x 10 frames per ship. animation_state is one of
    # "idle", "thrust", "damage", "death". animation_frame is 0..9 and
    # advances by 1 every ANIMATION_FRAME_DURATION seconds.
    animation_state: str = "idle"
    animation_frame: int = 0
    animation_timer: float = 0.0
    ANIMATION_FRAME_DURATION: float = 0.08  # 10 frames at 12.5 FPS, ~80ms per frame
    # BLOQUE 65: MINE_ASTEROID state machine. mine_state is one of
    # "closed" | "open1" | "open2" | "open3". The 4-state cycle is
    # closed -> open1 -> open2 -> open3 (each transition 0.2s; total
    # opening 0.6s), then open3 is the TERMINAL vulnerable state
    # (no transition out — the mine never closes after opening). Only
    # used when kind == EnemyKind.MINE_ASTEROID. For other enemy kinds,
    # these fields stay at their default values.
    mine_state: str = "closed"  # MINE_ASTEROID only
    state_timer: float = 0.0
    has_opened: bool = False
    mine_variant: int = 0  # 0-4, mirrors Asteroid.variant for closed sprite
    # BLOQUE 64.A: per-instance red-flash timer for the MINE-ASTEROID.
    # When apply_damage lands a hit (mine_state != "closed"), this is
    # set to 0.2s and the draw code applies a red-tint overlay. The
    # update() method ticks it down by dt each frame. Default 0.0
    # (no flash). Other enemy kinds ignore this field.
    # BLOQUE 71: superseded by ``hit_timer`` (white flash). Kept for
    # back-compat with the existing BLOQUE 64.A tests
    # (test_bloque_64_asteroid_polish.py). New code should set
    # ``hit_timer`` instead.
    mine_hit_flash_timer: float = 0.0
    # BLOQUE 71: per-instance white-flash timer. Set by ``hit()`` to
    # HIT_FLASH_DURATION_S so the render code can apply a white
    # palette-swap overlay. Decremented by dt in update(). Default 0.0
    # (no flash). Used by all enemy kinds (for consistency with
    # regular Asteroid.hit() and Player hit feedback) but currently
    # only the MINE-ASTEROID has a render branch that reads it (the
    # other enemies still use the legacy red flash via
    # ``mine_hit_flash_timer`` — see gameplay_runtime.py).
    hit_timer: float = 0.0
    # BLOQUE 67: cooldown until the next fan fires in open3. Set to 0
    # on spawn (so the first fire happens immediately on entry to
    # open3) and reset to MINE_FIRE_INTERVAL_S after each fire. Other
    # states (closed/open1/open2) ignore this field. Other enemy kinds
    # ignore this field.
    mine_fire_cooldown: float = 0.0

    @property
    def animation_path(self) -> str:
        """BLOQUE 59: relative path under Assets/sprites/ for the current
        animation frame. Empty string if kind is not a redesigned enemy.

        BLOQUE 65: MINE_ASTEROID uses a 4-state cycle
        (closed/open1/open2/open3). Each non-closed state is a single
        static frame (no per-frame counter), so the frame index is
        always 0 for those. The terminal state is open3 (the user's
        new ship reference) which the mine stays in until destroyed.
        """
        kind_value = self.kind.value if hasattr(self.kind, "value") else str(self.kind)
        if kind_value == "sub_boss":
            return ""  # sub-boss keeps its own 4-direction sprites
        if kind_value == "mine_asteroid":
            # BLOQUE 65: 4-state cycle closed/open1/open2/open3.
            # Each state is a single static frame; the per-state sprite
            # is loaded from the corresponding directory. The terminal
            # state open3 reuses the legacy `open/` directory (now
            # containing the user's new ship reference).
            state = self.mine_state
            if state not in ("closed", "open1", "open2", "open3"):
                idx = 0
                return f"enemies/mine_asteroid/closed/frame_{idx:02d}.png"
            if state == "open3":
                # Terminal state: render the user's new ship reference
                # (loaded from the legacy `open/` directory after the
                # BLOQUE 65 swap).
                return "enemies/mine_asteroid/open/frame_00.png"
            if state == "closed":
                # BLOQUE 66: variant-aware closed state. mine_variant is
                # set at spawn time (gameplay_runtime.py) to mirror the
                # 5 asteroid variants (round/elongated/spiked/hollowed/
                # cracked). The closed sprite is a byte-level copy of
                # the matching asteroid variant, so the camouflage is
                # real — a player cannot distinguish a MINE_ASTEROID
                # from a regular asteroid by variant. Out-of-range
                # variants clamp to 4 (cracked) for safety.
                v = max(0, min(4, int(self.mine_variant)))
                return f"enemies/mine_asteroid/closed/frame_{v:02d}.png"
            return f"enemies/mine_asteroid/{state}/frame_00.png"
        return f"enemies/{kind_value}/{self.animation_state}/frame_{self.animation_frame:02d}.png"

    def on_spawn(self) -> None:
        self.damage_taken = 0
        self.on_death = False
        self.on_fire = False
        self.on_spawn_mini = False
        self.pending_spawn_count = 0
        self.sine_t = 0.0
        self.sine_origin_x = 0.0
        # BLOQUE 47: reset squadron state
        self.squadron_id = -1
        self.squadron_origin_x = 0.0
        self.squadron_time_offset = 0.0
        self.squadron_age = 0.0
        # BLOQUE 58.6x: reset path follower
        self.path_follower = None
        self.path_slot_dx = 0.0
        self.path_slot_dy = 0.0
        # BLOQUE 58.next: reset leader flag (default False, runtime sets
        # True on the leader during spawn_pattern_wave)
        self.is_leader = False
        # BLOQUE 59: reset animation state on respawn
        self.animation_state = "idle"
        self.animation_frame = 0
        self.animation_timer = 0.0
        # BLOQUE 63: reset MINE_ASTEROID state machine
        self.mine_state = "closed"
        self.state_timer = 0.0
        self.has_opened = False
        self.mine_variant = 0
        # BLOQUE 67: reset fire cooldown (first fire happens on entry to open3)
        self.mine_fire_cooldown = 0.0
        # BLOQUE 58.6.4: sub-boss movement state is NOT reset here
        # because it persists across wrap-arounds (entry_count,
        # current_wall, etc. are needed for the next entry).

    def on_release(self) -> None:
        self.homing_target = None

    def _step_path_follower(self, dt: float) -> None:
        """BLOQUE 58.6x: advance the attached PathFollower and copy the
        resulting position + velocity onto this enemy. The follower's
        internal t is updated; if the path completes, vx/vy is set to 0
        and the enemy stays at the end position (caller can decide to
        cull or recycle).
        """
        # Local import to avoid a circular dep at module load time.
        from src.movement.follower import PathFollower

        follower: PathFollower = self.path_follower  # type: ignore[assignment]
        pos, vel = follower.update(dt)
        self.x = pos.x + self.path_slot_dx
        self.y = pos.y + self.path_slot_dy
        self.vx = vel.x
        self.vy = vel.y

    def attach_path(
        self,
        follower: "PathFollower",
        slot_dx: float = 0.0,
        slot_dy: float = 0.0,
    ) -> None:
        """Attach a PathFollower + formation slot offset. From this point
        on, update() drives position from the follower instead of vx/vy.
        """
        self.path_follower = follower
        self.path_slot_dx = slot_dx
        self.path_slot_dy = slot_dy

    def hitbox(self) -> pygame.Rect:
        """70% forgiving hitbox per GDD §5. SUB_BOSS gets a tighter 55%
        hitbox (BLOQUE 50) to make it harder to track + hit, matching
        its frenetic movement and high fire rate.
        """
        cfg = ENEMY_CONFIGS[self.kind]
        # BLOQUE 50: SUB_BOSS is harder to hit (50% — boss-like evasion)
        if self.kind == EnemyKind.SUB_BOSS:
            scale = 0.5
        else:
            scale = 0.7
        w = int(cfg.width * scale)
        h = int(cfg.height * scale)
        return pygame.Rect(int(self.x - w // 2), int(self.y - h // 2), w, h)

    def hit(self, damage: int = 1) -> bool:
        """BLOQUE 71: new public API for "this enemy was hit by a bullet".
        Returns True if this hit killed the enemy.

        Sets ``self.hit_timer = HIT_FLASH_DURATION_S`` for visual flash
        feedback in ALL cases. MINE-ASTEROID behavior:
          - closed/open1/open2: immune. hit_timer is set but no damage
            is taken. Returns False.
          - open3: vulnerable. hit_timer is set AND ``hp`` is decremented
            by ``damage``. Returns True if HP reached 0 (killed),
            False otherwise.

        Other enemy kinds: hit_timer is set for consistency, then
        ``apply_damage(damage)`` is called (which decrements HP and
        may kill the enemy). This ensures every hit in the game
        produces a visible flash, regardless of the enemy kind.

        Design note: ``hit()`` is a thin wrapper over ``apply_damage``
        for non-MINE kinds. The split is intentional — BLOQUE 71
        standardizes the hit-API surface (every entity has a
        ``hit(damage)`` method that returns a bool), while
        ``apply_damage`` remains the internal damage pipeline.
        """
        from src.core.settings import HIT_FLASH_DURATION_S
        self.hit_timer = HIT_FLASH_DURATION_S
        if self.kind == EnemyKind.MINE_ASTEROID:
            # MINE-ASTEROID: closed/open1/open2 are immune; only open3
            # takes damage. The hit_timer is already set above so the
            # player gets visual feedback even on immune hits.
            if self.mine_state != MINE_ASTEROID_OPEN3:
                return False
            # BLOQUE 71 fix round 1: delegate the MINE open3 kill to
            # apply_damage() so the canonical death pipeline runs
            # (state=DYING, animation_state="death", on_death=True).
            # The previous direct `self.alive = False` shortcut skipped
            # the death animation, leaving the MINE disappearing without
            # an explosion. We also set alive=False to keep the
            # ``test_mine_open3_destroyed_at_zero_hp`` test assertion
            # (``e.alive is False``) and to preserve the historical
            # contract that a killed enemy has ``alive == False``.
            destroyed = self.apply_damage(damage)
            if destroyed:
                self.alive = False
            return destroyed
        # Other enemy kinds: defer to the existing apply_damage path
        destroyed = self.apply_damage(damage)
        if destroyed:
            self.alive = False
        return destroyed

    def apply_damage(self, amount: int) -> bool:
        """Returns True if this hit killed the enemy.

        BLOQUE 63: MINE_ASTEROID is immune to player bullets when its
        state == "closed" (camouflage — looks like a regular asteroid).
        All other states (opening/open/closing) are vulnerable. Use
        ``EnemyState`` for the legacy FSM states (DEAD/DYING/etc) and
        ``self.state`` (a string) for the MINE_ASTEROID FSM (closed,
        opening, open, closing). They share the ``state`` attribute name
        so a check for ``state == "closed"`` doubles as both a MINE-state
        and a "not yet transitioning" sentinel.

        BLOQUE 64.A: MINE_ASTEROID HP=3. When a hit lands, the
        ``mine_hit_flash_timer`` is set to 0.2s so the draw code can
        apply a red-tint overlay and the player sees the damage
        progression.
        """
        if not self.active or self.state == EnemyState.DEAD:
            return False
        # BLOQUE 63: MINE_ASTEROID closed-state bullet immunity
        if self.kind == EnemyKind.MINE_ASTEROID and self.mine_state == "closed":
            return False
        self.hp -= amount
        self.damage_taken += amount
        # BLOQUE 64.A: MINE_ASTEROID red flash on a successful hit. The
        # flash is set BEFORE the death check so a killing hit also
        # flashes the sprite for 0.2s before the death animation kicks
        # in. (The draw code skips the red overlay when
        # animation_state == "death" so the flash is short-lived.)
        if self.kind == EnemyKind.MINE_ASTEROID:
            self.mine_hit_flash_timer = 0.2
        if self.hp <= 0:
            self.state = EnemyState.DYING
            # BLOQUE 59: trigger the death animation
            self.animation_state = "death"
            self.animation_frame = 0
            self.animation_timer = 0.0
            self.on_death = True
            return True
        # BLOQUE 59: hit that doesn't kill transitions to damage animation
        self.animation_state = "damage"
        self.animation_frame = 0
        self.animation_timer = 0.0
        return False

    def update(self, dt: float, player_x: float, player_y: float) -> None:
        """Advance movement, optional sine wobble, homing, fire cooldown, cull offscreen.

        Fires are reported via self.on_fire=True (caller spawns bullets).
        BLOQUE 58.59: Scout ships no longer sine-wobble (all ships move in
        a straight line by default). Curved motion is now handled by the
        BezierPath / FlightFormation system, not by per-enemy oscillation.
        BLOQUE 59: also advances the per-frame animation state. Frame rate
        is ANIMATION_FRAME_DURATION per frame (12.5 FPS). idle and thrust
        loop (frame 0..9 cyclically); damage and death are one-shots that
        transition back to idle when the animation completes.
        """
        if not self.active or dt <= 0.0 or self.state == EnemyState.DEAD:
            return
        # BLOQUE 71.2: tick down the white-flash timer for ALL enemy kinds
        # (MINE + SCOUT + CRUISER + HEAVY). Previously this decrement was
        # only inside the MINE_ASTEROID branch below, which caused
        # non-MINE enemies to stay "blancuscas" (white overlay 70%) for
        # the rest of the run because their hit_timer never decremented.
        if self.hit_timer > 0.0:
            self.hit_timer = max(0.0, self.hit_timer - dt)
        # BLOQUE 63: MINE_ASTEROID state machine. Lives BEFORE the rest
        # of update() so the MINE-ASTEROID never falls through to the
        # straight-line drift / sine-wobble / homing code below (which
        # would re-position it like a normal enemy). The MINE-ASTEROID
        # uses the same vx/vy as an asteroid (drift down + lateral
        # jitter), so we DO apply vx/vy here, but everything else
        # (sine wobble, homing, fire cooldown) is skipped.
        if self.kind == EnemyKind.MINE_ASTEROID:
            # BLOQUE 64.A: tick down the red-flash timer (legacy MINE
            # red flash, kept for back-compat with BLOQUE 64.A tests).
            # The white hit_timer decrement has been moved to the top
            # of update() so it applies to all enemy kinds.
            if self.mine_hit_flash_timer > 0.0:
                self.mine_hit_flash_timer = max(0.0, self.mine_hit_flash_timer - dt)
            self._update_mine_asteroid(dt)
            return
        # BLOQUE 59: advance animation frame. Use integer division to
        # avoid floating point drift (subtracting FRAME_DURATION in a
        # while loop accumulates 1e-15 errors per iter; int division
        # computes the exact frame count).
        self.animation_timer += dt
        frames_to_advance = int(self.animation_timer / self.ANIMATION_FRAME_DURATION)
        if frames_to_advance > 0:
            self.animation_timer -= frames_to_advance * self.ANIMATION_FRAME_DURATION
            self.animation_frame += frames_to_advance
            if self.animation_state in ("idle", "thrust"):
                self.animation_frame %= 10
            elif self.animation_frame >= 10:
                # damage and death are one-shots; return to idle
                self.animation_frame = 0
                self.animation_state = "idle"
        cfg = ENEMY_CONFIGS[self.kind]
        # BLOQUE 58.6x: if a PathFollower is attached, drive position +
        # velocity from it. The straight-line / L-turn code below is
        # bypassed for this enemy. The follower is responsible for the
        # path's end-of-life (it sets is_complete when t >= 1.0; we let
        # the wave manager decide whether to cull the enemy).
        if self.path_follower is not None:
            self._step_path_follower(dt)
            # Spawn timer / fire cooldown still tick even with a path
            if cfg.spawns_mini_on_timer or cfg.spawns_carrier_children:
                self.spawn_timer += dt
                if self.spawn_timer >= 3.0:
                    self.spawn_timer = 0.0
                    if cfg.spawns_carrier_children:
                        self.pending_spawn_count = max(self.pending_spawn_count, 2)
                    else:
                        self.pending_spawn_count = max(
                            self.pending_spawn_count, cfg.mini_spawn_count
                        )
            if cfg.fire_cooldown_s > 0.0:
                if self.fire_cd > 0.0:
                    self.fire_cd -= dt
                if self.fire_cd <= 0.0:
                    self.fire_cd = cfg.fire_cooldown_s
                    self.on_fire = True
            return
        # Sine wobble (legacy — disabled by BLOQUE 58.59; kept for compat
        # but no enemy config sets it to True anymore).
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
        # BLOQUE 58.6.4: sub-boss L turn check BEFORE applying velocity.
        # This way the turn point is checked in the same frame the
        # sub-boss reaches it, so the L pattern is smooth.
        if cfg.wrap_around and self.kind == EnemyKind.SUB_BOSS:
            if self.sb_is_l and not self.sb_turn_done:
                self._sub_boss_check_l_turn(cfg)
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
        # BLOQUE 58.6.2: wrap_around for SUB_BOSS — when it exits the
        # bottom, wrap it back to the top of the screen so the player
        # gets a continuous "entra y sale del mapa" pattern.
        # BLOQUE 58.6.3: random x on re-entry so the sub-boss doesn't
        # always come down the same vertical line.
        # BLOQUE 58.6.4: 4-entry movement cycle. Each entry, the sub-boss
        # exits through a wall and re-enters through that SAME wall
        # (going the opposite direction). Every 2 entries (cycles 1 and 3)
        # the path is an "L" — enter from a vertical wall, move vertically
        # partway, then turn 90° and exit through a side wall. This makes
        # the sub-boss more dynamic and less predictable than a straight
        # vertical line.
        if cfg.wrap_around and self.kind == EnemyKind.SUB_BOSS:
            # BLOQUE 58.6.4: also check the L-pattern turn BEFORE the
            # wrap-around check, so the turn happens before the sub-boss
            # actually exits the screen.
            if self.sb_is_l and not self.sb_turn_done:
                self._sub_boss_check_l_turn(cfg)
            # Now check if the sub-boss has exited any wall
            self._sub_boss_handle_warp(cfg)
        # Cull offscreen (other enemies, or sub-boss that can't wrap)
        elif self.y > INTERNAL_H + 20 or self.x < -20 or self.x > INTERNAL_W + 20:
            self.state = EnemyState.DEAD

    def _sub_boss_check_l_turn(self, cfg: "_EnemyConfig") -> None:
        """BLOQUE 58.6.4: when the sub-boss reaches its L turn point,
        change velocity from vertical to horizontal (or vice versa).
        After the turn, the sub-boss moves sideways until it exits
        through a side wall, then re-enters from that wall.
        """
        # Vertical L (entered from top, going down): turn at sb_turn_at_y
        if self.sb_current_wall == "top" and not self.sb_turn_done:
            if self.y >= self.sb_turn_at_y:
                self.vx = self.sb_post_turn_vx
                self.vy = self.sb_post_turn_vy
                self.sb_turn_done = True
        # Vertical L (entered from bottom, going up): turn at sb_turn_at_y
        elif self.sb_current_wall == "bottom" and not self.sb_turn_done:
            if self.y <= self.sb_turn_at_y:
                self.vx = self.sb_post_turn_vx
                self.vy = self.sb_post_turn_vy
                self.sb_turn_done = True

    def _sub_boss_handle_warp(self, cfg: "_EnemyConfig") -> None:
        """BLOQUE 58.6.4: detect which wall the sub-boss exited and
        re-enter through that SAME wall (going the opposite direction).
        Every 2 entries, the re-entry uses an "L" pattern (vertical
        then horizontal exit, or horizontal then vertical exit). The
        L direction alternates so the sub-boss doesn't always L to
        the same side.

        After the L pattern exits through a side wall, the "same wall
        re-entry" rule applies again — the sub-boss comes back from
        that side wall, going the opposite direction. So the wall
        sequence over time is: top → bottom → right → left → top → ...
        """
        # Figure out which wall the sub-boss just exited through
        exit_wall: str | None = None
        if self.y > INTERNAL_H + 20:
            exit_wall = "bottom"
        elif self.y < -20:
            exit_wall = "top"
        elif self.x > INTERNAL_W + 20:
            exit_wall = "right"
        elif self.x < -20:
            exit_wall = "left"
        if exit_wall is None:
            return
        # Increment entry count for the next entry
        self.sb_entry_count += 1
        # Re-enter through the SAME wall (per user requirement)
        # i.e. if it just exited through the bottom, next entry is also
        # from the bottom (but now moving UP, since it just came from above)
        margin = max(cfg.width // 2 + 4, 16)
        speed = cfg.speed
        # Determine if this entry should be an L pattern (every 2 entries)
        is_l_entry = (self.sb_entry_count % 2) == 1
        # The L turn direction alternates so the sub-boss doesn't
        # always L to the same side. The L direction depends on the
        # current wall + entry count parity.
        #   - Vertical wall (top/bottom) → L to LEFT or RIGHT
        #   - Horizontal wall (left/right) → L to UP or DOWN
        l_dir = (self.sb_entry_count // 2) % 2  # 0 or 1
        if exit_wall == "bottom":
            # Was moving down, exited bottom. Next entry from bottom (up).
            self.sb_current_wall = "bottom"
            self.x = float(random.randint(margin, INTERNAL_W - margin))
            self.y = INTERNAL_H + 20.0
            self.vx = 0.0
            self.vy = -speed
            if is_l_entry:
                # L pattern: enter from bottom, up, then turn (L or R)
                # Enter from the half OPPOSITE the L turn direction so
                # the L actually has room to work
                if l_dir == 0:
                    # L to the right
                    self.x = float(random.randint(margin, INTERNAL_W // 2))
                    self.sb_is_l = True
                    self.sb_turn_at_y = INTERNAL_H * 0.6
                    self.sb_post_turn_vx = speed
                    self.sb_post_turn_vy = 0.0
                else:
                    # L to the left
                    self.x = float(random.randint(INTERNAL_W // 2, INTERNAL_W - margin))
                    self.sb_is_l = True
                    self.sb_turn_at_y = INTERNAL_H * 0.6
                    self.sb_post_turn_vx = -speed
                    self.sb_post_turn_vy = 0.0
            else:
                self.sb_is_l = False
            self.sb_turn_done = False
        elif exit_wall == "top":
            # Was moving up, exited top. Next entry from top (down).
            self.sb_current_wall = "top"
            self.x = float(random.randint(margin, INTERNAL_W - margin))
            self.y = -20.0
            self.vx = 0.0
            self.vy = speed
            if is_l_entry:
                # L pattern: enter from top, down, then turn (L or R)
                if l_dir == 0:
                    # L to the right
                    self.x = float(random.randint(margin, INTERNAL_W // 2))
                    self.sb_is_l = True
                    self.sb_turn_at_y = INTERNAL_H * 0.4
                    self.sb_post_turn_vx = speed
                    self.sb_post_turn_vy = 0.0
                else:
                    # L to the left
                    self.x = float(random.randint(INTERNAL_W // 2, INTERNAL_W - margin))
                    self.sb_is_l = True
                    self.sb_turn_at_y = INTERNAL_H * 0.4
                    self.sb_post_turn_vx = -speed
                    self.sb_post_turn_vy = 0.0
            else:
                self.sb_is_l = False
            self.sb_turn_done = False
        elif exit_wall == "right":
            # Was moving right, exited right. Next entry from right (left).
            self.sb_current_wall = "right"
            self.y = float(random.randint(margin, INTERNAL_H - margin))
            self.x = INTERNAL_W + 20.0
            self.vx = -speed
            self.vy = 0.0
            if is_l_entry:
                # L pattern: enter from right, left, then turn (U or D)
                if l_dir == 0:
                    # L upward
                    self.y = float(random.randint(margin, INTERNAL_H // 2))
                    self.sb_is_l = True
                    self.sb_turn_at_x = INTERNAL_W * 0.6
                    self.sb_post_turn_vx = 0.0
                    self.sb_post_turn_vy = -speed
                else:
                    # L downward
                    self.y = float(random.randint(INTERNAL_H // 2, INTERNAL_H - margin))
                    self.sb_is_l = True
                    self.sb_turn_at_x = INTERNAL_W * 0.6
                    self.sb_post_turn_vx = 0.0
                    self.sb_post_turn_vy = speed
            else:
                self.sb_is_l = False
            self.sb_turn_done = False
        elif exit_wall == "left":
            # Was moving left, exited left. Next entry from left (right).
            self.sb_current_wall = "left"
            self.y = float(random.randint(margin, INTERNAL_H - margin))
            self.x = -20.0
            self.vx = speed
            self.vy = 0.0
            if is_l_entry:
                # L pattern: enter from left, right, then turn (U or D)
                if l_dir == 0:
                    # L upward
                    self.y = float(random.randint(margin, INTERNAL_H // 2))
                    self.sb_is_l = True
                    self.sb_turn_at_x = INTERNAL_W * 0.4
                    self.sb_post_turn_vx = 0.0
                    self.sb_post_turn_vy = -speed
                else:
                    # L downward
                    self.y = float(random.randint(INTERNAL_H // 2, INTERNAL_H - margin))
                    self.sb_is_l = True
                    self.sb_turn_at_x = INTERNAL_W * 0.4
                    self.sb_post_turn_vx = 0.0
                    self.sb_post_turn_vy = speed
            else:
                self.sb_is_l = False
            self.sb_turn_done = False
        # Reset fire cooldown so the re-entry feels threatening
        self.fire_cd = 0.5

    # -----------------------------------------------------------------------
    # BLOQUE 63 + 65: MINE_ASTEROID state machine + firing
    # -----------------------------------------------------------------------
    def _update_mine_asteroid(self, dt: float) -> None:
        """Advance the MINE_ASTEROID state machine: drift down like an
        asteroid, transition through open1 -> open2 -> open3 based on
        the timer. When transitioning to 'open3', fires 3 bullets in a
        fan via _fire_mine_bullets (caller is responsible for spawning
        the actual ProjectilePool entries; this method only flips state).

        BLOQUE 65: 4-state cycle (closed/open1/open2/open3) — the cycle
        is ONE-WAY. Once the mine reaches 'open3', it stays there until
        destroyed. Per-state durations: open1=0.2s, open2=0.2s, open3
        is terminal. The opening sequence takes 0.6s total.

        BLOQUE 67: while in open3, the mine fires 1 fan (3 bullets)
        forward per second at MINE_FIRE_INTERVAL_S. The first fan fires
        on entry to open3; subsequent fans fire every interval. This
        makes the open form an active threat that the player must
        engage with, not a passive target. The mine continues to fire
        at 1Hz until its HP drops to 0 (i.e. it's destroyed).

        Implementation note: the timer advances BEFORE the transition
        check, and a single large tick can chain through multiple
        states by using the remaining time after each transition. This
        is essential for the state machine to behave correctly under
        variable timestep updates.
        """
        # Drift down (mimic asteroid motion)
        self.x += self.vx * dt
        self.y += self.vy * dt
        # BLOQUE 68: cull off-screen BEFORE the state branches. The
        # previous cull at the bottom of this function was dead code
        # (every branch returned before reaching it). Mines that drift
        # past the bottom of the playfield must be marked DEAD so the
        # enemy pool removes them.
        if self.y > INTERNAL_H + 32:
            self.state = EnemyState.DEAD
            return
        if self.mine_state == "closed":
            if not self.has_opened and self.y > 0.0 and self.y >= OPENING_Y_THRESHOLD:
                # BLOQUE 69: the check is now `y >= OPENING_Y_THRESHOLD`
                # (>=, not >). The threshold (120) is the "first
                # quarter" of the 480-tall playfield. The check uses
                # >= so the mine opens AT the moment of crossing, not
                # after. There is NO visible line in the game — the
                # threshold is a behavioral marker.
                #
                # BLOQUE 68 history:
                # - The original check was `y < 200`. The mine spawns
                #   at y=-80..0 (off-screen above), so the check was
                #   TRUE from the spawn position and the mine opened
                #   immediately on the first tick — but it was off-screen
                #   so the player never saw it open.
                # - The corrected check (`y > 0 AND y < 200`) required
                #   the mine to enter the visible playfield before
                #   opening. This worked but the threshold (200) was
                #   high (~42% down the map).
                # - BLOQUE 69 lowers the threshold to 120 (1/4 of the
                #   map, "first quarter") per the user's spec.
                self.mine_state = "open1"
                self.state_timer = 0.0
            return
        # For non-closed states: advance timer, then check transition.
        # The loop caps at 4 iterations so a huge dt cannot spin the
        # state machine forever; the cap matches the maximum possible
        # transitions (closed -> open1 -> open2 -> open3). After each
        # transition, we subtract the consumed time from the remaining
        # time so a single large tick can chain through multiple states
        # without over-accelerating.
        remaining = dt
        for _ in range(4):
            if self.mine_state == "open1":
                self.state_timer += remaining
                if self.state_timer < MINE_OPEN1_DURATION_S:
                    return
                # Transition to 'open2', consume the time it took
                remaining = max(0.0, self.state_timer - MINE_OPEN1_DURATION_S)
                self.state_timer = 0.0
                self.mine_state = "open2"
                if remaining <= 0.0:
                    return
            elif self.mine_state == "open2":
                self.state_timer += remaining
                if self.state_timer < MINE_OPEN2_DURATION_S:
                    return
                # Transition to 'open3' (terminal). Fires 3 bullets in
                # a fan via the integration site. The first fan fires
                # on entry; subsequent fans fire every MINE_FIRE_INTERVAL_S
                # (BLOQUE 67) — the mine continues to threaten the
                # player at 1Hz until destroyed.
                remaining = max(0.0, self.state_timer - MINE_OPEN2_DURATION_S)
                self.state_timer = 0.0
                self.mine_state = "open3"
                self.has_opened = True  # mark cycle complete (BLOQUE 63 invariant)
                self.on_fire = True
                # First fire is on entry. Set cooldown to the interval
                # so the next fire happens MINE_FIRE_INTERVAL_S later.
                self.mine_fire_cooldown = MINE_FIRE_INTERVAL_S
                if remaining <= 0.0:
                    return
            elif self.mine_state == "open3":
                # BLOQUE 67: terminal state. The mine stays in open3
                # until destroyed (HP=0). Continuously fires 1 fan
                # forward per second while alive. Tick the cooldown
                # down by dt; when it reaches 0, set on_fire=True
                # (the integration site at gameplay_runtime.py:1941
                # reads on_fire, fires the fan, and sets it back to
                # False) and reset the cooldown.
                self.mine_fire_cooldown -= dt
                if self.mine_fire_cooldown <= 0.0:
                    self.on_fire = True
                    self.mine_fire_cooldown = MINE_FIRE_INTERVAL_S
                return
            else:
                # Unknown state — bail out
                return

    def _fire_mine_bullets(self, pool: "ProjectilePool") -> None:
        """BLOQUE 63 + 65: spawn 3 BULLET_ENEMY_MINE bullets in a fan
        pattern (±15° from straight down, 80 px/s). Called by the
        integration site when the MINE_ASTEROID transitions to 'open3'
        (was 'open' in BLOQUE 63).

        Imports are local to keep the module import graph clean.
        """
        from src.systems.projectile import (
            BULLET_ENEMY_MINE, OWNER_ENEMY, ProjectilePool,
        )
        import math
        # Spawn 3 bullets at -15°, 0°, +15° from straight down
        speed = MINE_FAN_BULLET_SPEED
        for angle_deg in (-MINE_FAN_ANGLE_DEG, 0.0, MINE_FAN_ANGLE_DEG):
            # 0° = straight down = positive y axis. pygame y is down.
            # angle measured from straight down, +clockwise (right) = +x
            rad = math.radians(angle_deg)
            vx = speed * math.sin(rad)
            vy = speed * math.cos(rad)
            pool.spawn(
                kind=BULLET_ENEMY_MINE,
                x=self.x,
                y=self.y,
                vx=vx,
                vy=vy,
                damage=1,
                owner=OWNER_ENEMY,
            )


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


def sub_boss_facing_angle(vx: float, vy: float) -> int:
    """BLOQUE 58.6.5: compute the rotation angle (in degrees) for the
    SUB_BOSS sprite to face its velocity direction.

    The sprite is drawn with the V apex at the BOTTOM (nose-DOWN by
    design), and pygame.transform.rotate(surf, deg) rotates CCW in
    math (which is CW on screen because pygame y-axis points down).
    So:
        vy > 0  (going DOWN)  -> 0   (no rotation, nose already down)
        vy < 0  (going UP)    -> 180 (nose flips up)
        vx > 0  (going RIGHT) -> 90  (nose goes right)
        vx < 0  (going LEFT)  -> 270 (nose goes left)

    When both axes are non-zero, the dominant axis wins (the ship
    moves mostly in 4 cardinal directions, so this is robust).
    """
    if abs(vy) >= abs(vx):
        return 0 if vy >= 0 else 180
    return 90 if vx > 0 else 270


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
