# VOID HUNTER — Architecture

**Status:** In-progress product. 28,066 LOC, 118 Python files, 1,024 tests.
**Last updated:** 2026-08-15

This document describes the 13 major systems that make up VOID HUNTER.
Each system has its own BLOQUE history, files, and tests.

---

## System map

```
                            ┌──────────────────────────────┐
                            │      GameplayRuntime         │  src/ui/gameplay_runtime.py
                            │      (5,773 LOC — the hub)    │  wires all systems together
                            └──────────────┬───────────────┘
                                           │
            ┌──────────────┬───────────────┼───────────────┬──────────────┐
            ▼              ▼               ▼               ▼              ▼
      ┌──────────┐  ┌──────────┐    ┌──────────┐    ┌──────────┐   ┌──────────┐
      │ Movement │  │ Entities │    │ Systems  │    │ UI/Audio │   │ Roguelike│
      │  672 LOC │  │ 1,844    │    │ 3,386    │    │ 8,996    │   │ 1,540    │
      └─────┬────┘  └────┬─────┘    └────┬─────┘    └────┬─────┘   └────┬─────┘
            │            │              │               │              │
   ┌────────┴────┐  ┌────┴─────┐  ┌─────┴──────┐  ┌─────┴──────┐  ┌────┴─────┐
   │ BezierPath  │  │  Player  │  │ WaveMgr    │  │ Scenes     │  │ Seed     │
   │ Waypoint    │  │  Enemy   │  │ Particles  │  │ HUD        │  │ RNG      │
   │ Hybrid      │  │  Boss    │  │ Scoring    │  │ Galaxy bg  │  │ LevelGen │
   │ Follower    │  │  Project │  │ EventBus   │  │ Tiling     │  │ FormGen  │
   │ Formations  │  │  …       │  │ Pool       │  │            │  │ Replay   │
   └─────────────┘  └──────────┘  └────────────┘  └────────────┘  └──────────┘
```

---

## 1. 🛩️ FlightFormations (BLOQUE 58.6x, 55, 45)

**What:** 9 preset formations that enemies spawn in.
**Where:** `src/movement/formation.py` (212 lines)
**BLOQUE history:**
- 45: act 1 formations (LINE, V, ARC, STAIRCASE)
- 55: 3 more (spiral, hilera, x)
- 58.6x: integration with paths

**9 presets** (FormationKind enum):
| Preset | Visual | Use |
|---|---|---|
| V | leader + 2 wings | Star Fox default |
| LINE | horizontal row | bullet sponge |
| DIAMOND | 4 corners | balanced |
| SQUARE | 3x3 grid | defensive |
| WEDGE | inverted V | aggressive dive |
| CIRCLE | orbital | surround |
| TRIANGLE | 3-3-1 pyramid | tactical |
| HALF_V | V wings only | flanking |
| CUSTOM | arbitrary offsets | designer-defined |

**Public API:**
```python
from src.movement import FlightFormation, FormationKind
formation = FlightFormation(FormationKind.V, count=8, spacing=18.0)
positions = formation.compute_slots()  # list of (dx, dy) offsets
```

**Tests:** `test_movement.py`, `test_formation.py` (~10 tests)

---

## 2. 📈 Bezier Curves (BLOQUE 56, 58.6x)

**What:** Cubic Bezier, waypoint, and hybrid paths for enemy motion.
**Where:**
- `src/movement/bezier.py` (95) — `BezierPath`, `Point`
- `src/movement/waypoint.py` (99) — `WaypointPath`
- `src/movement/hybrid.py` (107) — `HybridPath`
- `src/movement/follower.py` (71) — `PathFollower`

**Components:**
- `BezierPath(p0, p1, p2, p3)` — cubic Bezier with `position(t)`, `tangent(t)`
- `WaypointPath(points, speed, linger_s)` — constant speed + optional linger
- `HybridPath(segments, durations)` — concatenate bezier + waypoint
- `PathFollower(path)` — stateful, advances t over time

**Usage in waves:**
- O1: straight (no path)
- O2: bezier S-curve
- O3: waypoint zigzag
- O4: hybrid (bezier arc + waypoint + linger)
- GOLIATH entrance: bezier + linger

**Tests:** 37+ tests in `test_bezier_path.py`, `test_movement.py`

---

## 3. ✈️ Flight Paths (BLOQUE 58.6x, 45)

**What:** Per-wave procedural path specs.
**Where:** `src/movement/spec.py` (60) — `FormationPathSpec`

**Wave spec format:**
```python
{
  "enemies": ["SCOUT", "SCOUT", "CRUISER"],
  "formation": "v",
  "path": {
    "kind": "hybrid",
    "segments": [
      {"kind": "bezier", "p0": [0, 0], "p1": [50, 30], ...},
      {"kind": "waypoint", "points": [[100, 100], [200, 200]]}
    ]
  }
}
```

**Test:** `test_movement_wave_integration.py`

---

## 4. 👥 Leader Following (BLOQUE 47, 58.54, 48)

**What:** Squadron system where N followers replay the leader's path with time delay.
**Where:** `src/entities/enemies/enemy.py` (squadron_id, squadron_origin_x, squadron_time_offset, squadron_age)

**Flow:**
1. Leader spawns with `squadron_id` = 0, `squadron_time_offset` = 0
2. Follower spawns with `squadron_id` = 0, `squadron_time_offset` = 0.3s
3. Each frame, leader's `squadron_age` advances
4. Follower starts with `squadron_age = -time_offset` (in the past)
5. All enemies replay the same Y trajectory, offset in time

**BLOQUE 58.54:** forced to straight line (no serpentine).
```python
e.x = e.squadron_origin_x
e.y = 16.0 + age * squadron_y_speed
```

**Test:** `test_movement_enemy.py`

---

## 5. 🎲 ROGUELIKE (BLOQUE 57)

**What:** Full roguelike mode with deterministic procedural generation.
**Where:** `src/roguelike/` (12 files, 1,540 lines)

**Components:**

| File | LOC | Purpose |
|---|---|---|
| `seed.py` | 93 | Seed for the run |
| `rng.py` | 140 | Deterministic RNG |
| `run.py` | 202 | Run state (lives, score, upgrades) |
| `level_generator.py` | 196 | Procedural level generation |
| `formation_generator.py` | 266 | Procedural formation generation |
| `integration.py` | 135 | Glue with non-roguelike code |
| `telemetry.py` | 112 | Kills, perfect, time, score tracking |
| `replay.py` | 125 | Replay-from-seed (opt-in) |
| `boss_pool.py` | 70 | Procedural boss selection |
| `powerup_pool.py` | 48 | Power-up pool |
| `anti_stuck.py` | 95 | Anti-stuck detection |

**Activation:** `python main.py --roguelike <seed>`

**Test:** ~10 tests in `test_roguelike.py`, etc.

---

## 6. 🛡️ Boss FSM (BLOQUE 51-53, 58.37)

**4 bosses**, each with multi-phase FSM:

| Boss | BLOQUE | Style |
|---|---|---|
| **HYDRA** | 58.37 | multi-head Star Fox design |
| **PHANTOM** | 58.37 | stealthy |
| **NEMESIS** | 58.37 | aggressive |
| **GOLIATH** | 51-53 | biblical giant, shield + spear |

**GOLIATH phases:**
- 51: redesign as giant warrior
- 52: spear throw with serpentine motion + split-on-destroy
- 53a: shield charge (20 hits) + 1s charged laser
- 53b: HP bar (30 max + segments)
- 53c: gold rings (Star Fox) with one-time HP double
- 53d: tech upgrades (GOLIATH_SUMMON at sec 60)

**Where:** `src/entities/bosses/`

---

## 7. ⚔️ Weapon System (BLOQUE 6+7, 39)

**3 paths × 3 levels:**

| Path | L1 | L2 | L3 |
|---|---|---|---|
| Standard | single shot | double shot | triple spread |
| Plasma | single plasma | double plasma | continuous beam (BLOQUE 37) |
| Missile | single homing | double homing | triple homing |

**L3 plasma beam (BLOQUE 37):** held LMB charges, releases a continuous saw beam.

**Homing missile (BLOQUE 39):** B/L key, follows mouse, explodes on contact.

**State machine:** weapon level-up detection (BLOQUE 24).

**Where:** `src/entities/weapons/`

---

## 8. 🏃 Player FSM (BLOQUE 6+7, 58.8)

**7 states:** IDLE, MOVE, DASH, PROPULSION, HIT, DEAD, RESPAWN

**DASH vs PROPULSION** (BLOQUE 58.8):
- Single click = DASH (short, snappy)
- Hold >0.6s = PROPULSION (sustained, Tron trail)
- Both share overheat bar (BLOQUE 58.8)

**Where:** `src/entities/player/`

---

## 9. Tron Trail (BLOQUE 58.11, 58.22-58.31)

**What:** Continuous polyline trail behind the player in PROPULSION state.
**Effect:** **3x bullet damage** to enemies that touch the trail.

**Iterations:** 7 BLOQUES (22-31) to get from rotated bars → continuous polyline → ultra-thin → spectral multi-streak.

**Where:** `src/entities/player/`

---

## 10. HUD System (BLOQUE 58.14, 58.15, 58.16, 58.41)

**At BOTTOM** of the screen (BLOQUE 58.7ab fix).

**Components:**
- Score (bottom-right)
- Lives (bottom-left, segmented)
- HP bar (30 max, segments)
- Bombs → Missiles (counter)
- Overheat bar (DASH/PROPULSION)
- Tech upgrades tracker
- Score popups + damage popups
- Boss HP bar (when in boss fight)
- Sub-boss warning (top-center, during SUB_BOSS_INTRO)

**Fixed row height 14px** (BLOQUE 58.15) to prevent overlap.

**Where:** `src/ui/hud.py` (404 lines)

---

## 11. Music + SFX (BLOQUE 13+14, 45, 53, 57)

**24 synthesized SFX** (no external files):
- engine_hum, enemy_shoot, player_shoot, explosion, hit, etc.
- boss_warning, level_up, multiplier_up, act_clear

**2 streaming BGM tracks** (162 MB total):
- Title screen: `pantalla principal.wav` (6.2 min)
- Gameplay: `keep kept - Lerius - soundtrack gameplay.wav` (5.5 min)

**Streaming, not loaded into RAM** (BLOQUE 58.45) — preserves memory.

**Voice clips (BLOQUE 58.53):** added 4 SAPI voices (pantalla_principal, gameplay, jefe, act_cleared). **REMOVED in BLOQUE 58.59** (robotic quality).

**Where:** `src/audio/` (5 files, 1,420 lines)

---

## 12. Visual Juice (25+ systems)

Comprehensive juice library. See `docs/CHANGELOG_v1.x.md` for full history.

| Category | Systems |
|---|---|
| Particles | 18 kinds, P_SPARK, P_GLOW, P_SMOKE, P_FIRE |
| Screen effects | shake, hitstop, slow-mo, screen flash, shockwave |
| Player effects | dash afterimage (8 ghosts), propulsion wake (6 particles/engine), Tron trail, hit sparks, death ring |
| Bullet effects | trails, glow, muzzle flash, charge release |
| Boss effects | entry warning border, phase burst, death stages |
| Pickup effects | pickup flash, level-up flash, speed lines |
| HUD popups | damage popups, score popups, HP/bombs animations |
| Death | ring, boss death stages, sub-boss flash |
| Misc | engine smoke, dash stars, wing lights, ambient dust |

---

## 13. Star Fox Style (BLOQUE 58.36-58.36h)

**Window:** 320×480 portrait, centered, scaled to fill monitor height.

**Mouse reticle:** 1:1 with game coordinates (no scaling mismatch).

**Sprite scale:** 0.75 (BLOQUE 35).

**Nose lerp:** 180 deg/s for snappy mouse follow.

**Player + enemies:** Star Fox 64 inspired designs.

**Where:** `src/ui/` (5 files, 7,751 lines — including gameplay_runtime)

---

## State management

**Game states** (`src/core/scene_manager.py`):
- TITLE
- GAMEPLAY
- BOSS_INTRO
- BOSS_FIGHT
- SUB_BOSS_INTRO
- ACT_CLEARED
- GAME_OVER
- PAUSED

**Scene transitions:** explicit `transition_to(state)` callback from runtime.

**BLOQUE 58.57 lesson:** `SceneManager` does NOT auto-call `on_enter` on initial state. Must be triggered explicitly (in `Game.__init__`).

---

## File organization

```
src/
├── audio/        5 files, 1,420 lines  (synth + streaming BGM)
├── core/         5 files, 874 lines    (settings, scene_manager, event_bus)
├── entities/     7 files, 1,844 lines  (player, enemies, boss, projectile)
├── movement/     7 files, 672 lines    (BezierPath, formations, paths)
├── roguelike/   12 files, 1,540 lines  (seed, RNG, level gen, replay)
├── systems/     15 files, 3,386 lines  (wave, particles, scoring, pool)
├── ui/           5 files, 7,751 lines  (gameplay_runtime, scenes, HUD)
└── utils/        3 files, 206 lines    (math, paths, logging)
```

**Total: 60 source files, ~17,700 LOC** (excluding tests)

**`gameplay_runtime.py` is 5,773 LOC** — the largest file. Refactor pending
(see [ROADMAP.md](./ROADMAP.md)).

---

*Last updated: 2026-08-15*
