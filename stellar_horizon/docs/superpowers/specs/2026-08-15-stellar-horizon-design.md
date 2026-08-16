# STELLAR HORIZON — Design Spec

> **Version:** 1.0
> **Date:** 2026-08-15
> **Status:** DESIGN — awaiting user approval
> **Author:** Mavis (brainstorming session with Lerius)
> **Project path:** `void-hunter/stellar_horizon/`
> **Target Phase 1:** Vertical slice playable (1 act, 3-4 waves, 1 boss)

---

## §0 · Executive Summary

**STELLAR HORIZON** is a horizontal space shooter built on the same engine and
core systems as Void-Hunter, but redesigned for left→right combat in 480×270
(16:9) with 16-bit pixel art aesthetics and MIDI music.

It reuses Void-Hunter's movement, formation, particle, and audio-synth packages
as a library (Approach A: Library-Import), then layers a new player, enemy,
boss, HUD, scene, and wave system designed specifically for horizontal play
where the player is on the left, bullets fire right, and enemies enter from
the right, top, and bottom following bezier flight paths.

Phase 1 ships a **vertical slice**: one act, three or four waves, one boss,
all core systems functional end-to-end. Phases 2+ scale to a full game
(three acts, eighteen-plus waves, three bosses, multi-ambiente parallax).

---

## §1 · Goals & Non-Goals

### Goals (in scope)
- Reuse Void-Hunter's `src/movement/`, `src/audio/synth`, `src/systems/particle_engine`, and `src/utils/` as a library (zero re-implementation of bezier math, formations, audio synth, particles).
- Build a fully playable horizontal shmup: 480×270 internal, fullscreen 1920×1080 window with 4× nearest-neighbor scale.
- Make **bezier flight paths** the defining feature — every enemy wave is one or more `BezierPath` / `WaypointPath` / `HybridPath` from Void-Hunter's library, re-expressed for horizontal entry vectors.
- Ship Phase 1 as a complete vertical slice (1 act, 3-4 waves, 1 boss, asteroid-belt background) that can be played start-to-finish.

### Non-Goals (out of scope for Phase 1)
- Procedural roguelike mode (Phase 5).
- Multiple acts and multiple bosses (Phases 3+).
- Leaderboards, achievements, Steam release.
- Dash, bomb/missile secondary attack, HP bar (these are Phase 2).
- Re-deriving bezier math (we import from `src/movement`).

---

## §2 · High Concept

A 16-bit pixel-art horizontal shmup where the player pilots a small fighter
on the left edge of a 480×270 starfield, dispatching waves of alien craft
that enter from the right, top, and bottom following graceful bezier curves.
The first act takes place in an asteroid belt, with rock formations drifting
in parallax and a guardian boss made of living asteroid rock defending the
sector.

The core fantasy: **bezier motion is the visual signature.** Every enemy
sweep, every dive, every boss entrance is a hand-tuned curve. The game is
read at a glance: you see the curve, you know where the enemy is going.

---

## §3 · Architecture

### 3.1 Library-Import (Approach A — approved)

```
void-hunter/
├── src/                                  # VOID HUNTER — untouched
│   ├── movement/                         # ← STELLAR HORIZON imports from here
│   │   ├── bezier.py                     #     BezierPath, Point
│   │   ├── waypoint.py                   #     WaypointPath
│   │   ├── hybrid.py                     #     HybridPath
│   │   ├── follower.py                   #     PathFollower
│   │   ├── formation.py                  #     FlightFormation, FormationKind
│   │   └── spec.py                       #     FormationPathSpec
│   ├── audio/
│   │   └── synth.py                      # ← play_sfx, register_sfx
│   ├── systems/
│   │   └── particle_engine.py            # ← ParticleEngine
│   └── utils/
│       ├── easing.py                     # ← ease_out_cubic, etc.
│       └── palette.py                    # ← neon colors
└── stellar_horizon/                      # ← THIS PROJECT lives here
    ├── main.py
    ├── settings.py
    ├── README.md
    ├── stellar_horizon/                  # game package
    │   ├── core/
    │   ├── entities/
    │   ├── waves/
    │   ├── scenes/
    │   ├── ui/
    │   ├── audio/
    │   └── fx/
    ├── assets/
    │   ├── sprites/                      # 16-bit custom (user-drawn)
    │   ├── backgrounds/
    │   └── midi/
    └── tests/
```

**The 4 imports that 90% of the game depends on:**

```python
# Movement + formations (re-used from VH, no modification)
from src.movement import (
    BezierPath, WaypointPath, HybridPath, PathFollower,
    FlightFormation, FormationPathSpec, FormationKind, Point,
)

# SFX (re-used; 24 synthesized SFX from VH)
from src.audio.synth import play_sfx, register_sfx

# Particles (re-used; 18 kinds from VH)
from src.systems.particle_engine import ParticleEngine

# Utilities
from src.utils.easing import ease_out_cubic
from src.utils.palette import neon_cyan, neon_red, neon_white
```

If at any point during Phase 2+ a file in `src/` needs to be modified for
horizontal-specific behavior, we **copy that file into
`stellar_horizon/movement/` (or appropriate location) and modify the copy**.
We never edit `src/` directly.

---

## §4 · File Tree (Phase 1 target)

```
void-hunter/stellar_horizon/
├── main.py                                # CLI: --easy, --act 1, --boss, --check
├── settings.py                            # INTERNAL_W=480, INTERNAL_H=270, FPS=120
├── README.md
│
├── stellar_horizon/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── game.py                        # Game class, fixed-timestep loop
│   │   ├── scene_manager.py               # 5 states: TITLE, GAMEPLAY, BOSS_FIGHT, ACT_CLEARED, GAME_OVER
│   │   └── clock.py                       # pygame.time.Clock + accumulator wrapper
│   │
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── player.py                      # Player: WASD/Arrows + Space, 3 lives
│   │   ├── bullet.py                      # PlayerBullet (+x), EnemyBullet (aimed)
│   │   ├── enemy.py                       # Enemy base + 3 Phase 1 types: SCOUT, CRUISER, HEAVY
│   │   └── boss.py                        # ASTEROID_GUARDIAN, 2 phases
│   │
│   ├── waves/
│   │   ├── __init__.py
│   │   ├── bezier_horizontal.py           # 3 preset paths + helpers
│   │   ├── formations_h.py                # rotated V, horizontal line, diamond pointing -X
│   │   ├── wave_specs.py                  # dataclass for JSON deserialization
│   │   ├── wave_manager.py                # scheduler (uses src PathFollower + FormationPathSpec)
│   │   └── waves_act1.json                # 3-4 waves for Phase 1
│   │
│   ├── scenes/
│   │   ├── __init__.py
│   │   ├── title.py                       # main menu with MIDI loop
│   │   ├── gameplay.py                    # main game loop, render, update
│   │   ├── boss_intro.py                  # 2-second warning + boss enters via bezier
│   │   └── game_over.py                   # retry / quit
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── hud.py                         # HP, score, lives, wave#, boss HP
│   │   └── backgrounds.py                 # asteroid_belt + 2 placeholder for acts 2/3
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── midi_player.py                 # pygame.mixer.music wrapper
│   │   └── sfx.py                         # maps game events to VH synth SFX
│   │
│   └── fx/
│       ├── __init__.py
│       ├── particles.py                   # wrapper around src.systems.particle_engine
│       └── screen_shake.py                # Eiserloh trauma² (ported from VH, no import)
│
├── assets/
│   ├── sprites/
│   │   ├── player/                        # 16x16 idle + thrust (2 frames)
│   │   ├── enemies/                       # 16x16 SCOUT/CRUISER, 24x16 HEAVY
│   │   ├── bullets/                       # 12x4 player, 8x8 enemy
│   │   ├── boss/                          # 64x64 ASTEROID_GUARDIAN
│   │   └── particles/                     # spark, smoke, explosion
│   ├── backgrounds/
│   │   ├── act1_asteroid_belt.png         # 480x270 (or tiling strip for parallax)
│   │   ├── act2_nebula.png                # placeholder for Phase 3
│   │   └── act3_sun_close.png             # placeholder for Phase 4
│   └── midi/
│       ├── title.mid
│       ├── act1.mid
│       ├── boss.mid
│       └── game_over.mid
│
└── tests/
    ├── test_player.py                     # movement, bounds, shoot
    ├── test_enemy.py                      # 3 types, attack patterns, hp
    ├── test_boss.py                       # FSM phases, attack patterns
    ├── test_bullet.py                     # player + enemy bullets
    ├── test_horizontal_bezier.py          # 3 preset paths validate
    ├── test_formations_h.py               # rotations correct
    ├── test_wave_manager.py               # JSON load + scheduling
    ├── test_scenes.py                     # scene transitions
    ├── test_hud.py                        # layout, score, lives
    └── test_midi_player.py                # load + play
```

**Phase 1 estimate:** ~2,850 LOC of Python + ~65 tests (per §18.2 breakdown).

---

## §5 · Player

### 5.1 Movement

| Attribute | Value | Source / rationale |
|---|---|---|
| Position (start) | (40, 135) | 40 px from left edge, vertical center of 270 |
| Sprite | 16×16 (idle) + 16×16 (thrust) | 2-frame animation |
| Hitbox | 8×8 (centered) | smaller than sprite for fairness |
| Bounds X | 8 to 472 | keeps sprite fully on-screen |
| Bounds Y | 16 to 254 | top/bottom margins for HUD |
| Speed (WASD/Arrows) | 165 px/s | matches Void-Hunter default |
| Speed (8-dir) | 165 px/s both axes simultaneously | diagonal normalized via `max(\|dx\|,\|dy\|)` |
| **Lives** | **3** | arcade, decided 2026-08-15 |
| Shoot key | Spacebar (auto-fire 0.10s cooldown, 12 shots/s) | |
| Bullet spawn | (player.x + 12, player.y) | emerges from ship's right wing |
| I-frames after hit | 30 frames (0.25 s @ 120 FPS) | |

**Out of Phase 1 (deferred to Phase 2):**
- Dash (Shift key, 0.18 s burst at 480 px/s, i-frames)
- Bomb / missile (Q key, screen-clear)
- HP bar (30 HP segmented)

### 5.2 Player class skeleton

```python
# stellar_horizon/entities/player.py
import pygame
from src.audio.synth import play_sfx


class Player:
    SPEED = 165.0
    SHOOT_COOLDOWN_S = 0.10
    BULLET_OFFSET_X = 12
    MAX_LIVES = 3
    IFRAMES_FRAMES = 30

    def __init__(self, screen_rect: pygame.Rect) -> None:
        self.x, self.y = 40.0, screen_rect.centery
        self.vx, self.vy = 0.0, 0.0
        self.lives = self.MAX_LIVES
        self.shoot_cooldown = 0.0
        self.invulnerable_frames = 0
        self.alive = True
        self.firing = False
        self.thrusting = False
        self.bullets: list["PlayerBullet"] = []

    def update(self, dt: float, keys, bullets_pool) -> None:
        # Input → velocity (8-dir, normalized)
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN])  - (keys[pygame.K_w] or keys[pygame.K_UP])
        if dx and dy:
            inv = 1.0 / (2 ** 0.5)
            self.vx = dx * self.SPEED * inv
            self.vy = dy * self.SPEED * inv
        else:
            self.vx = dx * self.SPEED
            self.vy = dy * self.SPEED
        # Position update
        self.x = max(8, min(472, self.x + self.vx * dt))
        self.y = max(16, min(254, self.y + self.vy * dt))
        # Shoot
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        if self.firing and self.shoot_cooldown <= 0.0:
            self._spawn_bullet(bullets_pool)
            self.shoot_cooldown = self.SHOOT_COOLDOWN_S
        # Iframes
        if self.invulnerable_frames > 0:
            self.invulnerable_frames -= 1

    def take_hit(self) -> None:
        if self.invulnerable_frames > 0 or not self.alive:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.alive = False
        else:
            self.invulnerable_frames = self.IFRAMES_FRAMES
        play_sfx("player_hit")

    def _spawn_bullet(self, pool) -> None:
        b = pool.acquire()
        b.x = self.x + self.BULLET_OFFSET_X
        b.y = self.y
        b.vx = PlayerBullet.SPEED_PX_S
        b.vy = 0.0
        b.alive = True
        play_sfx("player_shoot")

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)
```

---

## §6 · Bullets

### 6.1 PlayerBullet

| Attribute | Value |
|---|---|
| Speed | 480 px/s in +X direction (no Y component) |
| Sprite | 12×4 cyan/yellow beam |
| Hitbox | 12×4 (matches sprite) |
| Damage | 1 (Phase 1) |
| Lifetime | despawn when x > 480 (off-screen right) |
| Max on-screen | 32 (pool size) |

### 6.2 EnemyBullet

| Attribute | Value |
|---|---|
| Speed | 220 px/s, aimed at player position at spawn time |
| Sprite | 8×8 red/magenta orb |
| Hitbox | 6×6 |
| Damage | 1 (Phase 1) |
| Lifetime | despawn when off-screen (any edge) |
| Max on-screen | 64 (pool size) |

```python
# stellar_horizon/entities/bullet.py
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
        if self.x > 480 + 12:
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
```

---

## §7 · Enemies (Phase 1: 3 types)

### 7.1 Type table

| Type | HP | Speed | Attack | Telegraph | Sprite | Score |
|---|---|---|---|---|---|---|
| **SCOUT** | 1 | 110 px/s along path | aimed bullet, 1.5 s cooldown | 8 f yellow blink | 16×16 red | 50 |
| **CRUISER** | 4 | 60 px/s along path | twin cannon, 1.2 s | 14 f red glow | 16×16 orange | 150 |
| **HEAVY** | 12 | 30 px/s along path | heavy shot, 2.5 s, damage 2 | 24 f red glow | 24×16 gray-silver | 400 |

(Phase 2 adds KAMIKAZE and SNIPER; not in Phase 1.)

### 7.2 Enemy base

```python
# stellar_horizon/entities/enemy.py
import math
import pygame
from src.movement import PathFollower, Point
from src.audio.synth import play_sfx


class EnemyKind:
    SCOUT = "scout"
    CRUISER = "cruiser"
    HEAVY = "heavy"


class Enemy:
    """An enemy that follows a PathFollower and shoots at the player."""

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.kind: str = EnemyKind.SCOUT
        self.hp: int = 1
        self.max_hp: int = 1
        self.alive: bool = True
        self.shoot_cooldown: float = 0.0
        self.telegraph_frames: int = 0
        self.telegraphing: bool = False
        self.path_follower: PathFollower | None = None
        self.slot_dx: float = 0.0
        self.slot_dy: float = 0.0
        self.path_done: bool = False

    def attach_path(self, follower: PathFollower, slot_dx: float, slot_dy: float) -> None:
        self.path_follower = follower
        self.slot_dx, self.slot_dy = slot_dx, slot_dy

    def update(self, dt: float, player) -> list["EnemyBullet"]:
        """Update position via path follower; return list of new bullets to spawn."""
        new_bullets: list[EnemyBullet] = []
        if not self.alive:
            return new_bullets

        # Path-driven motion
        if self.path_follower and not self.path_done:
            pos, vel = self.path_follower.update(dt)
            self.x = pos.x + self.slot_dx
            self.y = pos.y + self.slot_dy
            self.vx, self.vy = vel.x, vel.y
            if self.path_follower.is_complete:
                self.path_done = True
        elif self.path_done and self.alive:
            # Drift gently off-screen left after path completes
            self.x -= 30.0 * dt

        # Shoot at player
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        if self.telegraphing:
            self.telegraph_frames -= 1
            if self.telegraph_frames <= 0 and self._can_shoot():
                b = EnemyBullet()
                b.spawn(self.x, self.y, player.x, player.y)
                new_bullets.append(b)
                self.telegraphing = False
                play_sfx("enemy_shoot")
        elif self.shoot_cooldown <= 0.0 and self._can_shoot():
            self.telegraphing = True
            self.telegraph_frames = self._telegraph_frames()
            self.shoot_cooldown = self._attack_cooldown()

        # Off-screen culling (left or top/bottom)
        if self.x < -32 or self.y < -32 or self.y > 302:
            self.alive = False

        return new_bullets

    # Per-type parameters (overridden by subclasses if needed)
    def _attack_cooldown(self) -> float:
        return {"scout": 1.5, "cruiser": 1.2, "heavy": 2.5}.get(self.kind, 1.5)

    def _telegraph_frames(self) -> int:
        return {"scout": 8, "cruiser": 14, "heavy": 24}.get(self.kind, 8)

    def _can_shoot(self) -> bool:
        # Only shoot if in play area
        return 0 <= self.x <= 480 and 0 <= self.y <= 270

    def take_damage(self, amount: int) -> None:
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False
            play_sfx("enemy_explode")

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 6), int(self.y - 6), 12, 12)
```

---

## §8 · Bezier Flight Paths (horizontal)

This is the **signature feature** of the game. The three preset paths
below cover 80% of Phase 1's wave variety; more are added as needed.

### 8.1 Three preset paths

```python
# stellar_horizon/waves/bezier_horizontal.py
from src.movement import BezierPath, WaypointPath, HybridPath, Point


def path_s_right_to_left(y_offset: float = 0.0) -> BezierPath:
    """Enter from off-screen right, sweep in an S, exit off-screen left.

    Used by: SCOUT formations crossing the screen.
    """
    return BezierPath(
        p0=Point(490, 60 + y_offset),    # off-screen right
        p1=Point(380, 60 + y_offset),    # pull left
        p2=Point(100, 200 - y_offset),   # pull down-left (S-curve)
        p3=Point(-20, 200 - y_offset),   # off-screen left
    )


def path_top_dive(side: str = "right") -> BezierPath:
    """Enter from top, arc down to the right (or left).

    Used by: SCOUT diving at the player.
    """
    end_x = 470 if side == "right" else 10
    return BezierPath(
        p0=Point(200, -20),              # off-screen top
        p1=Point(200, 50),               # pull down
        p2=Point(380 if side == "right" else 100, 150),
        p3=Point(end_x, 240),            # off-screen bottom
    )


def path_zigzag_exit_top() -> HybridPath:
    """Enter from right, zigzag, exit off-screen top.

    Used by: SCOUT/CRUISER squadrons that need varied motion.
    """
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 100),
            p1=Point(300, 100),
            p2=Point(200, 180),
            p3=Point(300, 220),
        ),
        WaypointPath(
            [Point(300, 220), Point(380, 150), Point(250, 80), Point(200, -20)],
            speed_px_s=140.0,
        ),
    ])
```

### 8.2 Why these paths work

- **`path_s_right_to_left`**: classic "sweep across" — the enemy traverses the screen visibly, giving the player a clear target. The S-curve makes it feel organic, not robotic.
- **`path_top_dive`**: vertical threat — comes from above, gives the player a moment to react after it appears at the top edge.
- **`path_zigzag_exit_top`**: combo path — starts as a bezier, transitions to waypoints for the sharp zigzag, exits the top. Shows off the HybridPath capability.

### 8.3 Path validation (in tests)

Each preset path's `position_at(0)` must be off-screen on at least one axis,
and `position_at(1)` must be off-screen on at least one axis. This ensures
enemies "enter from off-screen" and "leave the screen", not appear mid-screen.

---

## §9 · Formations (horizontal)

```python
# stellar_horizon/waves/formations_h.py
from src.movement import FlightFormation


def v_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]:
    """V formation with apex pointing -X (enemies advancing toward the left)."""
    base = FlightFormation.v(count, spacing)  # VH's V points -Y
    # Rotate 90° CW so wings end up at +X (behind the leader):
    # (x, y) -> (y, -x)
    return [(y, -x) for (x, y) in base.offsets]


def line_horizontal(count: int = 5, spacing: float = 22.0) -> list[tuple[float, float]]:
    """Horizontal line of N slots, perpendicular to the direction of motion."""
    half = (count - 1) * spacing / 2.0
    return [(-half + i * spacing, 0.0) for i in range(count)]


def diamond_pointing_left(count: int = 5, spacing: float = 20.0) -> list[tuple[float, float]]:
    """Diamond formation with vertex pointing -X."""
    if count == 1:
        return [(0.0, 0.0)]
    offsets = [(0.0, 0.0)]
    layer = 1
    while len(offsets) < count:
        # Order: top-front, front, bottom-front, back, etc.
        offsets.append((-spacing * layer, 0.0))            # front
        if len(offsets) >= count: break
        offsets.append((-spacing * 0.5, -spacing * layer))  # top-front
        if len(offsets) >= count: break
        offsets.append((-spacing * 0.5, +spacing * layer))  # bottom-front
        if len(offsets) >= count: break
        offsets.append((+spacing * layer, 0.0))             # back
        layer += 1
    return offsets[:count]


def wedge_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]:
    """Wedge (> shape) with tip pointing -X."""
    if count == 1:
        return [(0.0, 0.0)]
    offsets = [(0.0, 0.0)]
    for i in range(1, (count + 1) // 2 + 1):
        offsets.append((spacing * i, -spacing * i))
        offsets.append((spacing * i, +spacing * i))
    offsets.sort(key=lambda p: (p[0], p[1]))
    return offsets[:count]
```

**Note:** `v_pointing_left` and `wedge_pointing_left` rotate the V's offsets
from Void-Hunter by 90° clockwise — a clean algebraic transformation that
preserves the underlying formation math while orienting it for horizontal
play. We don't modify `src/movement/formation.py`; we wrap it.

---

## §10 · Waves (JSON + scheduler)

### 10.1 JSON schema (Phase 1)

```json
// stellar_horizon/waves/waves_act1.json
{
  "act": 1,
  "act_name": "Asteroid Belt",
  "background": "act1_asteroid_belt",
  "midi_track": "act1.mid",
  "boss": {
    "kind": "ASTEROID_GUARDIAN",
    "phases": 2,
    "hp": 60,
    "entry_path": "boss_entry"
  },
  "waves": [
    {
      "id": "w1_intro",
      "duration_s": 12.0,
      "spawns": [
        {
          "delay_s": 0.5,
          "formation": "v_pointing_left",
          "formation_count": 5,
          "enemy_kind": "SCOUT",
          "path": "s_right_to_left",
          "path_y_offset": 0
        }
      ]
    },
    {
      "id": "w2_layered",
      "duration_s": 18.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "line_horizontal",
          "formation_count": 6,
          "enemy_kind": "CRUISER",
          "path": "s_right_to_left",
          "path_y_offset": 60
        },
        {
          "delay_s": 6.0,
          "formation": "v_pointing_left",
          "formation_count": 3,
          "enemy_kind": "SCOUT",
          "path": "top_dive",
          "path_side": "right"
        }
      ]
    },
    {
      "id": "w3_mixed",
      "duration_s": 22.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "diamond_pointing_left",
          "formation_count": 5,
          "enemy_kind": "HEAVY",
          "path": "s_right_to_left",
          "path_y_offset": 100
        },
        {
          "delay_s": 8.0,
          "formation": "v_pointing_left",
          "formation_count": 4,
          "enemy_kind": "SCOUT",
          "path": "zigzag_exit_top"
        }
      ]
    },
    {
      "id": "w4_boss_rush",
      "duration_s": 14.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "line_horizontal",
          "formation_count": 8,
          "enemy_kind": "SCOUT",
          "path": "s_right_to_left",
          "path_y_offset": 0
        },
        {
          "delay_s": 2.0,
          "formation": "line_horizontal",
          "formation_count": 6,
          "enemy_kind": "CRUISER",
          "path": "s_right_to_left",
          "path_y_offset": 60
        }
      ]
    }
  ]
}
```

### 10.2 Wave manager (uses `src.movement`)

```python
# stellar_horizon/waves/wave_manager.py
import json
from pathlib import Path
from src.movement import PathFollower, FormationPathSpec

from stellar_horizon.waves.bezier_horizontal import (
    path_s_right_to_left, path_top_dive, path_zigzag_exit_top,
)
from stellar_horizon.waves.formations_h import (
    v_pointing_left, line_horizontal, diamond_pointing_left, wedge_pointing_left,
)
from stellar_horizon.entities.enemy import Enemy, EnemyKind

PATH_BUILDERS = {
    "s_right_to_left": lambda **kw: path_s_right_to_left(y_offset=kw.get("y_offset", 0)),
    "top_dive":         lambda **kw: path_top_dive(side=kw.get("side", "right")),
    "zigzag_exit_top":  lambda **kw: path_zigzag_exit_top(),
    "boss_entry":       lambda **kw: __import__("stellar_horizon.waves.bezier_horizontal",
                                                fromlist=["path_boss_entry"]).path_boss_entry(),
}

FORMATION_BUILDERS = {
    "v_pointing_left":       lambda count, spacing: v_pointing_left(count, spacing),
    "line_horizontal":       lambda count, spacing: line_horizontal(count, spacing),
    "diamond_pointing_left": lambda count, spacing: diamond_pointing_left(count, spacing),
    "wedge_pointing_left":   lambda count, spacing: wedge_pointing_left(count, spacing),
}

KIND_MAP = {
    "scout":   EnemyKind.SCOUT,
    "cruiser": EnemyKind.CRUISER,
    "heavy":   EnemyKind.HEAVY,
}


class WaveManager:
    """Reads waves JSON, schedules spawns over time, hands enemies to gameplay."""

    def __init__(self, json_path: Path) -> None:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.act = data["act"]
        self.background = data["background"]
        self.midi_track = data["midi_track"]
        self.boss_spec = data.get("boss")
        self.waves = data["waves"]
        self.current_wave_index = 0
        self.elapsed_s = 0.0
        self.spawn_queue: list[tuple[float, list[Enemy]]] = []  # (t, [enemies])
        self.spawned_enemies: list[Enemy] = []
        self.wave_complete = False

    def begin(self) -> None:
        """Build the spawn queue for the current wave."""
        self.spawned_enemies.clear()
        self.spawn_queue.clear()
        wave = self.waves[self.current_wave_index]
        for spawn in wave["spawns"]:
            t = spawn["delay_s"]
            enemies = self._build_formation(spawn)
            self.spawn_queue.append((t, enemies))
        self.spawn_queue.sort(key=lambda x: x[0])
        self.elapsed_s = 0.0
        self.wave_complete = False

    def update(self, dt: float) -> list[Enemy]:
        """Spawn enemies whose delay has elapsed. Returns newly-spawned enemies."""
        new_spawns: list[Enemy] = []
        while self.spawn_queue and self.elapsed_s >= self.spawn_queue[0][0]:
            _, enemies = self.spawn_queue.pop(0)
            for e in enemies:
                e.on_spawn()
                self.spawned_enemies.append(e)
            new_spawns.extend(enemies)
        self.elapsed_s += dt
        if not self.spawn_queue and not self.spawned_enemies:
            self.wave_complete = True
        return new_spawns

    def next_wave(self) -> bool:
        """Advance to the next wave. Returns False if no more waves."""
        self.current_wave_index += 1
        if self.current_wave_index >= len(self.waves):
            return False
        self.begin()
        return True

    def _build_formation(self, spawn: dict) -> list[Enemy]:
        offsets = FORMATION_BUILDERS[spawn["formation"]](spawn["formation_count"], 18.0)
        path = PATH_BUILDERS[spawn["path"]](
            y_offset=spawn.get("path_y_offset", 0),
            side=spawn.get("path_side", "right"),
        )
        # Wrap in a single-segment HybridPath with explicit duration so we can
        # set spawn_interval via FormationPathSpec.
        from src.movement import HybridPath, WaypointPath
        # BezierPath intrinsic duration is 1s per 80px; we override here:
        from src.movement.bezier import BezierPath
        seg_dur = max(0.5, path.length_estimate / 80.0) if isinstance(path, BezierPath) else 4.0
        if isinstance(path, BezierPath):
            hybrid = HybridPath([path], [seg_dur])
        elif isinstance(path, HybridPath):
            hybrid = path
        else:
            hybrid = HybridPath([path], [4.0])
        kind = KIND_MAP[spawn["enemy_kind"]]
        spec = FormationPathSpec(
            formation=__import__("src.movement.formation", fromlist=["FlightFormation"]).FlightFormation.__class__,
            path=hybrid,
            enemy_kind=kind,
            spawn_interval_s=0.12,
        )
        # Manual build so we can apply our custom offsets:
        enemies: list[Enemy] = []
        for i, (dx, dy) in enumerate(offsets):
            e = Enemy()
            e.on_spawn()
            e.kind = kind
            follower = PathFollower(hybrid)
            e.attach_path(follower, slot_dx=dx, slot_dy=dy)
            enemies.append(e)
        return enemies
```

(Implementation note: the formation offsets are computed by our `formations_h.py` helpers and applied per-slot when building the `Enemy` instances. The `FlightFormation` object inside `FormationPathSpec` is only used as a metadata container; the actual `slot_dx/dy` values come from our rotated offsets.)

---

## §11 · Boss (ASTEROID_GUARDIAN)

### 11.1 Stats

| Attribute | Value |
|---|---|
| HP | 60 (Phase 1) |
| Sprite | 64×64 (rock-like, glowing core) |
| Hitbox | 48×48 (centered) |
| Entry path | bezier S-curve from off-screen right, ending at (350, 135) |
| Final position | (350, 135) — left-center, fights from there |
| Phases | 2 (split at HP 30) |
| Score on kill | 5000 |
| Damage on contact | 1 + screen shake |

### 11.2 FSM

```
SPAWN
  │  (after BOSS_INTRO 2s)
  ▼
PHASE_1 (HP 60→30)              PHASE_2 (HP 30→0)
  - aim-and-shoot, 1.2s cd        - 3-spread every 0.9s
  - spread 3 every 2.0s           - laser beam telegraph 60f + 20f active (every 3.5s)
  - small drift horizontal        - small drift + slow vertical bob
       │                                │
       └──── HP <= 30 ──────────────►   │
                                        │
                              (HP <= 0) ▼
                                   DYING (1.5s)
                                        │
                                        ▼
                                    DEAD
```

### 11.3 Entry path

```python
# stellar_horizon/waves/bezier_horizontal.py (additive)
def path_boss_entry() -> BezierPath:
    """Dramatic S-curve from off-screen right to the boss arena (350, 135)."""
    return BezierPath(
        p0=Point(540, 60),      # off-screen right, top
        p1=Point(450, 100),     # pull left + down
        p2=Point(380, 200),     # pull further down (S-curve through)
        p3=Point(350, 135),     # final arena position
    )
```

---

## §12 · HUD

### 12.1 Layout

```
┌────────────────────────────────────────────────────────────┐
│ HP ████████░░░░  SCORE 12,450       WAVE 2/4   BOSS HP    │  <- top bar (14 px)
│                                                            │
│                                                            │
│                  (gameplay area 480x250)                   │
│                                                            │
│                                                            │
│  LIVES ❤❤❤   BOMBS ●●●   SCORE 12,450   ENEMIES 8/15      │  <- bottom bar (14 px)
└────────────────────────────────────────────────────────────┘
```

### 12.2 Components

| Element | Position | Content |
|---|---|---|
| HP bar | top-left | segmented bar (3 hearts in Phase 1) |
| Score | top-center | "12,450" |
| Wave counter | top-center-right | "WAVE 2/4" |
| Boss HP bar | top-right | only during BOSS_FIGHT, 60 segments |
| Lives | bottom-left | 3 hearts |
| Bombs | bottom-center-left | (Phase 2 only — placeholder for Phase 1) |
| Enemy counter | bottom-right | "ENEMIES 8/15" |

### 12.3 State visibility

- TITLE scene: no HUD.
- GAMEPLAY: top + bottom HUD visible.
- BOSS_INTRO: full-screen warning text + boss name + MIDI swells.
- BOSS_FIGHT: same as GAMEPLAY + boss HP bar visible.
- ACT_CLEARED: minimal HUD + "ACT 1 CLEARED" banner.
- GAME_OVER: minimal HUD + "GAME OVER" banner + score.

---

## §13 · Scenes (state machine)

### 13.1 States

```
TITLE
  │  press SPACE / ENTER
  ▼
GAMEPLAY
  │  wave_complete AND current_wave_index == len(waves) - 1 AND no enemies
  ▼
BOSS_INTRO  (2 seconds, "BOSS APPROACHING" warning + boss entry path starts)
  │  timer
  ▼
BOSS_FIGHT
  │  boss.hp <= 0
  ▼
ACT_CLEARED  (3 seconds, "ACT 1 CLEARED" banner)
  │  press SPACE → loop back to TITLE
  ▼
TITLE
  │
  │ (any time) player.lives == 0
  ▼
GAME_OVER  (retry / quit)
```

### 13.2 Scene interface

```python
# stellar_horizon/core/scene_manager.py
import pygame


class Scene:
    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...
    def update(self, dt: float, events: list[pygame.event.Event]) -> None: ...
    def draw(self, surface: pygame.Surface) -> None: ...
    def next_scene(self) -> "Scene | None": ...
```

`SceneManager` holds the current scene, calls `update(dt, events)` each frame,
calls `draw(surface)`, and on `next_scene()` swaps the scene and calls
`on_exit()` / `on_enter()`.

---

## §14 · Backgrounds (multi-ambiente)

### 14.1 Act 1 — Asteroid Belt (Phase 1)

- **Visual:** 480×270 background with 3-5 large asteroid silhouettes floating in the back. Stars in the far back. Subtle parallax on the asteroid layer (slower than game scroll).
- **Color palette:** dark navy (#0A0F1F) base, brown-gray asteroids (#4A3F35), pale stars (#F0E0C0).
- **Scroll behavior:** static (asteroids don't move). Player is on the left, enemies come from the right, so the world is "stationary" — only enemies move.

### 14.2 Act 2 — Nebula (Phase 3 placeholder)

- Static PNG, 480×270. Purple-blue gradient with stars.
- No animations needed for placeholder.

### 14.3 Act 3 — Sun Close (Phase 4 placeholder)

- Static PNG, 480×270. Yellow-red gradient with sun glow at right edge.
- No animations needed for placeholder.

### 14.4 Background implementation

```python
# stellar_horizon/ui/backgrounds.py
import pygame
from pathlib import Path


class Background:
    """Static background image. Phase 2+ can add parallax."""

    def __init__(self, image_path: Path) -> None:
        self.image = pygame.image.load(str(image_path)).convert()
        self.parallax_x = 0.0

    def update(self, dt: float, scroll_speed: float = 0.0) -> None:
        self.parallax_x = (self.parallax_x + scroll_speed * dt) % self.image.get_width()

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.image, (0, 0))
```

---

## §15 · Audio

### 15.1 MIDI player

```python
# stellar_horizon/audio/midi_player.py
import pygame


class MidiPlayer:
    """Plays MIDI files via pygame.mixer.music (which natively supports MIDI)."""

    def __init__(self) -> None:
        pygame.mixer.music.set_volume(0.6)

    def play(self, midi_path: str, loop: bool = True) -> None:
        pygame.mixer.music.load(midi_path)
        pygame.mixer.music.play(-1 if loop else 0)

    def stop(self) -> None:
        pygame.mixer.music.stop()

    def fadeout(self, ms: int = 800) -> None:
        pygame.mixer.music.fadeout(ms)
```

### 15.2 SFX (re-uses `src.audio.synth`)

```python
# stellar_horizon/audio/sfx.py
"""Maps game events to Void-Hunter synthesized SFX."""
from src.audio.synth import play_sfx, register_sfx, synth_shoot, synth_explode

# Re-register SFX under our event names:
register_sfx("player_shoot",   lambda: synth_shoot(freq=880, dur=0.06))
register_sfx("player_hit",     lambda: synth_explode(freq=120, dur=0.18))
register_sfx("enemy_shoot",    lambda: synth_shoot(freq=440, dur=0.05))
register_sfx("enemy_explode",  lambda: synth_explode(freq=200, dur=0.20))
register_sfx("boss_warning",   lambda: synth_explode(freq=80, dur=0.4))
register_sfx("boss_hit",       lambda: synth_shoot(freq=300, dur=0.04))
register_sfx("boss_explode",   lambda: synth_explode(freq=60, dur=1.0))
register_sfx("wave_clear",     lambda: synth_shoot(freq=1320, dur=0.15))
register_sfx("act_clear",      lambda: synth_explode(freq=440, dur=0.6))
register_sfx("game_over",      lambda: synth_explode(freq=80, dur=0.8))


def play_event(name: str) -> None:
    play_sfx(name)
```

---

## §16 · FX (particles + screen shake)

### 16.1 Particles (re-uses `src.systems.particle_engine`)

```python
# stellar_horizon/fx/particles.py
from src.systems.particle_engine import ParticleEngine


class FxLayer:
    def __init__(self) -> None:
        self.engine = ParticleEngine(pool_size=600)

    def emit_sparks(self, x: float, y: float, count: int = 8) -> None:
        for _ in range(count):
            self.engine.emit(0, x, y, 0, 0)  # P_SPARK

    def emit_explosion(self, x: float, y: float, scale: float = 1.0) -> None:
        # Mix of sparks + smoke for the classic 16-bit explosion
        n_sparks = int(16 * scale)
        n_smoke = int(4 * scale)
        for _ in range(n_sparks):
            self.engine.emit(0, x, y, 0, 0)  # P_SPARK
        for _ in range(n_smoke):
            self.engine.emit(2, x, y, 0, 0)  # P_SMOKE

    def update(self, dt: float) -> None:
        self.engine.update(dt)

    def draw(self, surface) -> None:
        self.engine.draw(surface)
```

### 16.2 Screen shake (Eiserloh trauma², ported)

```python
# stellar_horizon/fx/screen_shake.py
"""Eiserloh trauma² model. Same algorithm as Void-Hunter's, no import."""


class ScreenShake:
    def __init__(self, max_offset: float = 4.0, decay: float = 0.88) -> None:
        self.trauma = 0.0
        self.max_offset = max_offset
        self.decay = decay
        self.offset_x = 0.0
        self.offset_y = 0.0

    def add_trauma(self, amount: float) -> None:
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt: float) -> None:
        # trauma² for snappy feel (low trauma = subtle, high = violent)
        shake = self.trauma ** 2 * self.max_offset
        import math, random
        self.offset_x = (random.random() * 2 - 1) * shake
        self.offset_y = (random.random() * 2 - 1) * shake
        self.trauma = max(0.0, self.trauma - self.decay * dt)

    def offset(self) -> tuple[float, float]:
        return self.offset_x, self.offset_y
```

---

## §17 · Game loop & rendering

### 17.1 Fixed-timestep loop

```python
# stellar_horizon/core/game.py
import pygame
from stellar_horizon.core.scene_manager import SceneManager
from stellar_horizon.core.clock import FixedClock
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H, WINDOW_W, WINDOW_H, FPS_TARGET, FIXED_DT


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init()
        self.internal = pygame.Surface((INTERNAL_W, INTERNAL_H))
        self.window = pygame.display.set_mode(
            (WINDOW_W, WINDOW_H),
            pygame.SCALED | pygame.RESIZABLE,
        )
        pygame.display.set_caption("STELLAR HORIZON")
        self.clock = FixedClock(FPS_TARGET)
        self.scenes = SceneManager()
        self._running = True
        self._accumulator = 0.0

    def run(self) -> None:
        last = pygame.time.get_ticks() / 1000.0
        while self._running:
            now = pygame.time.get_ticks() / 1000.0
            frame_time = min(now - last, 1.0 / 30.0)  # clamp to 33ms
            last = now
            self._accumulator += frame_time
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    self._running = False
            while self._accumulator >= FIXED_DT:
                self.scenes.update(FIXED_DT, events)
                self._accumulator -= FIXED_DT
            self.internal.fill((10, 15, 31))  # dark navy
            self.scenes.draw(self.internal)
            scaled = pygame.transform.scale(self.internal, (WINDOW_W, WINDOW_H))
            self.window.blit(scaled, (0, 0))
            pygame.display.flip()
            self.clock.tick()
        pygame.quit()
```

### 17.2 Settings

```python
# stellar_horizon/settings.py
INTERNAL_W = 480
INTERNAL_H = 270
DEFAULT_SCALE = 4  # 480*4 = 1920, 270*4 = 1080
WINDOW_W = INTERNAL_W * DEFAULT_SCALE
WINDOW_H = INTERNAL_H * DEFAULT_SCALE
WINDOW_TITLE = "STELLAR HORIZON"
FPS_TARGET = 120
FIXED_DT = 1.0 / FPS_TARGET
DT_CLAMP = 1.0 / 30.0
```

---

## §18 · Testing strategy

### 18.1 Coverage gate

- **Phase 1:** ≥30% coverage.
- **Phase 2+:** scale to ≥35% (matches Void-Hunter).

### 18.2 Test files & target counts

| File | Tests | What it covers |
|---|---|---|
| `test_player.py` | 6 | WASD input → velocity, bounds, shoot cooldown, lives, take_hit, iframes |
| `test_enemy.py` | 12 | 3 types: HP, attack cooldown, telegraph, take_damage, path attachment |
| `test_boss.py` | 8 | 2-phase FSM, attack patterns, hp threshold, entry path |
| `test_bullet.py` | 5 | PlayerBullet + EnemyBullet spawn, update, hitbox, despawn |
| `test_horizontal_bezier.py` | 8 | 3 preset paths validate off-screen entry/exit, length>0, t in [0,1] |
| `test_formations_h.py` | 6 | V rotation correct, line horizontal, diamond vertex, wedge tip |
| `test_wave_manager.py` | 8 | JSON load, scheduling, current_wave, next_wave, spawn_queue |
| `test_scenes.py` | 6 | TITLE → GAMEPLAY → BOSS → GAME_OVER transitions |
| `test_hud.py` | 4 | Layout, score formatting, lives display |
| `test_midi_player.py` | 2 | Load + play + stop (with SDL_VIDEODRIVER=dummy) |
| **Total** | **~65** | |

### 18.3 Quality gates

- All tests must pass before each commit.
- No new warnings (flake8 with project config).
- Type hints on all public functions; `mypy stellar_horizon/` exit 0.
- No numpy / scipy imports.
- Internal coordinates always 480×270.
- Pygame 2.6+, Python 3.11+.

---

## §19 · Phase 1 scope and success criteria

### 19.1 Phase 1 deliverables (vertical slice)

A user can launch `python main.py` and:
1. See the TITLE screen with the STELLAR HORIZON logo and "Press SPACE to start" (MIDI title music playing).
2. Press SPACE → transition to GAMEPLAY.
3. Move the player with WASD/Arrows (8-dir, 165 px/s).
4. Hold SPACE to fire bullets (+X direction, 480 px/s, 0.10s cooldown).
5. Encounter 3-4 waves of enemies that enter from the right, top, and bottom following bezier paths.
6. See enemy types SCOUT, CRUISER, HEAVY, each with distinct HP, sprite, and attack pattern.
7. Survive 3 lives, see HUD update with score, lives, wave counter.
8. Reach the boss at the end of the 3rd-4th wave.
9. Fight ASTEROID_GUARDIAN (60 HP, 2 phases).
10. Win or lose; see ACT_CLEARED or GAME_OVER screen.
11. Retry or quit.

### 19.2 Phase 1 exit criteria

- [ ] All 65 tests pass.
- [ ] 30%+ test coverage.
- [ ] Game runs from `python main.py` with no errors.
- [ ] Window is 1920×1080 (full screen via scale detection).
- [ ] 60+ FPS sustained during gameplay.
- [ ] All 3 enemy types + boss are functional.
- [ ] 3-4 waves playable start-to-finish.
- [ ] MIDI music plays in TITLE and GAMEPLAY.
- [ ] SFX (player shoot, enemy shoot, explosions, boss warning) all play.
- [ ] Screen shake on big hits (boss damage, heavy explosion).
- [ ] No regressions in Void-Hunter (`python -m pytest tests/` in parent still passes).

### 19.3 Out of scope for Phase 1 (explicitly)

- Dash, bomb, missile, HP bar (Phase 2).
- KAMIKAZE, SNIPER enemy types (Phase 2).
- Acts 2 and 3 (Phases 3, 4).
- Roguelike mode (Phase 5).
- Leaderboards, achievements, packaging (Phase 5+).

---

## §20 · Phase 2+ roadmap

| Phase | Scope | New LOC | New tests | Notes |
|---|---|---|---|---|
| **Phase 2** | KAMIKAZE + SNIPER enemy types, dash + bomb + HP bar, score multiplier, more particle juice, screen shake on boss damage | +1,200 | +25 | Reuses all Phase 1 systems |
| **Phase 3** | Act 2 (Nebula), 4-5 waves, 1 boss (e.g. NEBULA_WRAITH), multi-ambiente parallax | +1,500 | +30 | Adds 1 background system + 1 boss |
| **Phase 4** | Act 3 (Sun Close), 5-6 waves, 1 boss (e.g. SOLAR_HYDRA, 3 phases), final boss | +1,800 | +35 | 3-phase boss FSM (port from VH) |
| **Phase 5** | Roguelike mode (imports `src.roguelike.*`), leaderboards, packaging to .exe | +800 | +20 | First external release |

**Total at full game:** ~8,150 LOC, ~180 tests (vs Void-Hunter 28k LOC, 1024 tests — STELLAR HORIZON is intentionally a tighter, more focused game).

---

## §21 · Open decisions / future questions

These are NOT blocking Phase 1. They are parked here for review after the
vertical slice is playable.

1. **HP bar with 30 HP** (VH-style) vs simple 3-life arcade. Phase 1 ships 3-life arcade. Phase 2 may add 30 HP HP bar if it feels right.
2. **Dash mechanic** — single click vs hold (BLOQUE 58.8 of VH has this nuance; we may or may not replicate it).
3. **Bomb vs missile** as the secondary attack (different feel).
4. **Boss 2-phase vs 3-phase** for Act 2 and 3 bosses.
5. **Procedural wave generation** vs hand-tuned JSON (VH has both; we start with hand-tuned).
6. **MIDI vs chiptune synthesized music** (alternative to MIDI files).
7. **Difficulty modes** (easy/normal/hard).
8. **Story/narrative elements** (currently we have no story; could add act intro/outro text).

---

## §22 · Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-08-15 | STELLAR HORIZON as the game name | User-selected, evokes horizontal flight + stars |
| 2026-08-15 | `void-hunter/stellar_horizon/` location | Library-Import (Approach A) — zero re-implementation |
| 2026-08-15 | 480×270 internal, 1920×1080 window, 4× scale | 16:9, 16-bit crunch, comfortable game design space |
| 2026-08-15 | 16-bit pixel art + MIDI | User-specified aesthetic |
| 2026-08-15 | WASD/Arrows + Spacebar | Classic horizontal shmup controls |
| 2026-08-15 | Shots L→R, enemies from right/top/bottom | User-specified |
| 2026-08-15 | Phase 1 = vertical slice (1 act, 3-4 waves, 1 boss) | Pragmatic start before scaling |
| 2026-08-15 | Player HP = 3 (arcade) | User-selected |
| 2026-08-15 | No dash, no bomb in Phase 1 | Defer to Phase 2 |
| 2026-08-15 | Act 1 = Asteroid Belt | User-selected |
| 2026-08-15 | 1 boss per act (3 total in full game) | User-selected |
| 2026-08-15 | Multi-ambiente per act background | User-selected |
| 2026-08-15 | Custom sprites (user-drawn) | User-specified |
| 2026-08-15 | Boss name default: ASTEROID_GUARDIAN | Provisional; user can change during review |

---

## §23 · References

- Void-Hunter movement package: `void-hunter/src/movement/`
- Void-Hunter audio synth: `void-hunter/src/audio/synth.py`
- Void-Hunter particle engine: `void-hunter/src/systems/particle_engine.py`
- Void-Hunter GDD: `void-hunter/docs/design/void-hunter-gdd.md`
- Void-Hunter architecture: `void-hunter/docs/ARCHITECTURE.md`

---

**End of design spec.** Awaiting user review and approval before proceeding
to the implementation plan via the writing-plans skill.
