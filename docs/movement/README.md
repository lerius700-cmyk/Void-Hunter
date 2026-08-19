# Ship Movement — the choreography system

This folder documents **how enemy ships move** in VOID HUNTER. Movement
is the soul of the game: the way ships sweep, swirl, snake, and dance
is what makes the combat feel like Star Fox 64 instead of a generic
shoot-em-up.

If you (human or AI) are about to change anything in `src/movement/`
or `src/systems/wave_patterns/`, **read this first**. These are FROZEN
subsystems — see `../ARCHITECTURE.md`.

## Why this folder exists

The user (Lerius) explicitly asked for these docs after a session
where the movement system was almost lost. The code is still 100%
intact (`src/movement/` has 8 modules, `src/systems/wave_patterns/`
has 6 base + 1 composed = 56 patterns), but the **intent** and
**design** of the movement was never written down. This folder fixes
that.

## The stack (read in this order)

1. **[01_movement_primitives.md](./01_movement_primitives.md)** — the
   3 building blocks: `BezierPath`, `WaypointPath`, `HybridPath`.
   Understand these and the rest follows naturally.

2. **[02_formations.md](./02_formations.md)** — `FlightFormation` and
   the 9 preset shapes (V, LINE, DIAMOND, SQUARE, WEDGE, CIRCLE,
   TRIANGLE, HALF_V, CUSTOM). How groups of ships are arranged.

3. **[03_path_follower.md](./03_path_follower.md)** — `PathFollower`
   and `FormationPathSpec`. The bridge between a path + formation and
   spawnable enemies.

4. **[04_wave_patterns.md](./04_wave_patterns.md)** — the 6 base
   patterns (BEZIER_SWEEP, V_FORMATION, LEADER_FOLLOWER_CHAIN,
   DICE_FIVE_GRID, PINCER_CROSS, OSCILLATING_BUTTERFLY) and the 50
   COMPOSED patterns. How the manager picks one.

5. **[05_advanced_paths.md](./05_advanced_paths.md)** — `ParallelPathPair`
   (pair dance) and `OrbitalPath` (butterfly orbit). The choreographic
   flourishes.

## Source code map

```
src/movement/
├── __init__.py          # public API: BezierPath, PathFollower, FlightFormation, etc.
├── bezier.py            # BezierPath + Point (cubic curve math)
├── waypoint.py          # WaypointPath (constant-speed waypoints)
├── hybrid.py            # HybridPath (concatenate bezier + waypoint)
├── follower.py          # PathFollower (stateful, advances t over time)
├── formation.py         # FlightFormation + FormationKind (9 presets)
├── spec.py              # FormationPathSpec (path + formation -> spawnable enemies)
├── parallel_path.py     # ParallelPathPair (SF64 pair dance)
└── orbital_path.py      # OrbitalPath (4-segment bezier circle)

src/systems/wave_patterns/
├── base.py                       # WavePatternKind, WavePattern, SpawnedShip
├── bezier_sweep.py               # BEZIER_SWEEP — pair dance on a random bezier
├── v_formation.py                # V_FORMATION — rigid V shape
├── leader_chain.py               # LEADER_FOLLOWER_CHAIN — bezier snake
├── dice_grid.py                  # DICE_FIVE_GRID — 5 ships in dice-5 layout
├── pincer_cross.py               # PINCER_CROSS — 2 mirror beziers from sides
├── oscillating_butterfly.py      # OSCILLATING_BUTTERFLY — orbital dance
├── composed.py                   # COMPOSED — 50 (formation, path, follow) combos
├── manager.py                    # ProceduralWaveManager (picks + registers)
└── runtime.py                    # spawn_pattern_wave, spawn_solo_ship, etc.
```

## Why NO numpy

The GDD (§0) explicitly bans numpy/scipy. The only numpy consumer in
the whole project is the **pause lowpass** in `src/audio/synth.py`
(added in BLOQUE 58.14 with a documented exception). Everything in
`src/movement/` is **pure stdlib + math**. Don't add numpy here.

## Contract (don't break)

| Method | What it promises |
|---|---|
| `BezierPath.position_at(t)` | Returns the curve point at `t in [0, 1]`. |
| `BezierPath.tangent_at(t)` | Returns the unnormalized tangent at `t`. |
| `PathFollower.update(dt)` | Returns `(Point pos, Point vel)`. `(0, 0)` when complete. |
| `FlightFormation.offsets` | list of (dx, dy) tuples, one per slot. |
| `HybridPath.position_at(t)` | Walks all segments; returns the global position. |

If you change any of these signatures, **every wave pattern breaks
silently** (the patterns read `result.ships[*].extra` to know what
kind of path to attach). Always run `pytest tests/test_wave_patterns.py`
after touching movement code.
