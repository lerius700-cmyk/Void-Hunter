# Architecture — what to build on, what not to touch

This document is the **contract** between the foundation (BLOQUE 0-58.14)
and anyone (human or AI) building new features on top.

## TL;DR

- **`master` is the integration branch.** Every commit must keep
  `pytest` green. The GitHub Actions CI in `.github/workflows/test.yml`
  enforces this on every push.
- **Pixel art assets are user-provided.** Don't synthesize AI
  replacements. Use the `Assets/background/galaxy_pixelart_*.png`
  variants as the nebula source of truth.
- **The wave system is the most stable thing.** `ParallaxBackground`,
  `ProceduralWaveManager`, `BombBurst`, `SoloEnemySpawner`, and the 5
  base patterns are FROZEN — they have a contract, they have tests, and
  changing them is a major version bump.
- **The 50 composed patterns are data-driven.** They live in
  `src/systems/wave_patterns/composed.py::COMPOSED_PATTERNS` and are
  picked at random by the manager. Don't add a new "kind" to the enum
  — instead, add new formations/paths/follows to the generator.

## Frozen subsystems (do not refactor without a major version bump)

### 1. `ParallaxBackground` (`src/systems/parallax.py`)

**Contract:** Renders the game's background (stars + nebulae + planets)
in a single `draw(target)` call per frame. Public methods:
- `__init__(width, height, rng_seed, stars_per_layer, nebula_count,
   nebula_radius_min, nebula_radius_max, spawn_planets)`
- `update(dt)` — scrolls stars, drifts nebulae, rotates planet rings.
- `draw(target)` — blits cached surfaces.
- `set_theme(name)` — re-tints stars for a new act.
- `release_all()` — reset on scene transition.

**What you can do:**
- Pass different `nebula_count` / `nebula_radius_*` to get a different
  look (title screen uses dense, gameplay uses sparse).
- Add new `WavePatternKind` values, but the parallax doesn't need to
  change.

**What you can't do without a major version:**
- Change the internal star/nebula representation (we have tests that
  lock the count and the per-frame cost).
- Remove the AI galaxy sprite fallback (it's the safety net if the
  pixel art sprites are deleted).

### 2. `ProceduralWaveManager` (`src/systems/wave_patterns/manager.py`)

**Contract:** Picks a `WavePattern` for the current wave based on floor,
seed, and (anti-stuck) history. Public methods:
- `__init__(seed, floor, log_path)` — RNG + history.
- `set_floor(floor)`, `get_floor()`.
- `pick_pattern(level, enemy_kind)` → `WavePatternResult`.
- `register_composed_patterns()` → `int` (count registered).
- `composed_pool_size()` → `int`.

**What you can do:**
- Add new `WavePatternKind` enum values.
- Tweak the weights in `_WEIGHTED_POOL` / `_EQUAL_WEIGHT`.
- Add new patterns to `COMPOSED_PATTERNS` (data-only, no API change).

**What you can't do:**
- Change the anti-stuck filter (test_floor_1_no_immediate_repeat).
- Change the deterministic seed→sequence contract (test_deterministic_same_seed).

### 3. Base patterns (`src/systems/wave_patterns/{bezier_sweep,v_formation,leader_chain,dice_grid,pincer_cross,oscillating_butterfly}.py`)

**Contract:** Each implements `WavePattern.generate(rng, level, enemy_kind)`
→ `WavePatternResult`. The result's `ships[*].extra` dict carries
pattern-specific data that `runtime.py` consumes.

**The keys that runtime.py reads are:**
- `p0, p1, p2, p3` (single bezier segment)
- `segments, segment_durations` (multi-segment path)
- `parallel_pair, side` (parallel pair dance)
- `orbital` (oscillating butterfly)

**New patterns must use one of these key sets.** Adding a new key
without updating `runtime.py` = silent failure (ship spawns but doesn't move).

### 4. `BombBurst` (`src/fx/bomb_burst.py`)

**Contract:** A `BombBurst(cx, cy, seed=0xB0FB)` instance, life 0.4s,
3 concentric soft rings (yellow → orange → red). Public methods:
- `update(dt)`, `draw(target)`, `is_alive` property.

**What you can do:**
- Tweak the 3 colors (`_HOT_COLOR`, `_BOMB_COLOR`, `_RIM_COLOR`).
- Change the life duration (`LIFE_S`).
- Add a 4th ring with the same `(surf, size, max_alpha, color)` tuple.

**What you can't do without a major version:**
- Change the public method names (called from `gameplay_runtime.py`).

### 5. `SoloEnemySpawner` (`src/systems/wave_patterns/composed.py`)

**Contract:** `SoloEnemySpawner(interval_s=5.0)`, `update(dt, rng)` →
`list[SpawnedShip]`, `reset()`. Each ship has `extra.segments` (single
bezier) so `runtime.spawn_solo_ship` attaches the path.

**What you can do:**
- Change the interval (5s default).
- Add a tint or color override.

**What you can't do without a major version:**
- Change `update()` return type from `list[SpawnedShip]`.

### 6. `WavePatternKind` enum (`src/systems/wave_patterns/base.py`)

**Contract:** 7 values (5 base + OSCILLATING_BUTTERFLY + COMPOSED).
The `composed.py` and `manager.py` both use this enum; adding a value
without updating them breaks the wire.

**What you can do:**
- Add a new value here, but you must also:
  1. Add a factory in `ProceduralWaveManager._make_pattern()`.
  2. Add it to the weighted pools.
  3. Add a test in `test_wave_patterns.py::test_floor_5_includes_all`
     (which already uses `len(WavePatternKind)`).

## What the agent (or human) building new features can rely on

1. **All public methods in the frozen subsystems are tested.**
   - `pytest tests/test_bloque_58_10.py` — floor/pattern tests
   - `pytest tests/test_wave_patterns.py` — wave manager
   - `pytest tests/test_bloque_58_14.py` — pause lowpass
   - `pytest tests/test_audio_synth.py` — audio SFX/BGM

2. **If you add code that breaks these tests, CI fails on push.**
   Don't push to master without running `pytest` locally first.
   Setup: `tools/setup_build_venv.bat` (Windows) or
   `python -m pip install -r requirements.txt -r requirements-dev.txt`
   (Linux/macOS).

3. **The `WavePatternResult` and `SpawnedShip` dataclasses are
   stable.** Their fields are part of the public API.

## Release process

1. Update `CHANGELOG.md` with a new `[vX.Y.Z]` section.
2. Run the full pytest locally. Must be 100% green.
3. Commit everything.
4. `git tag -a vX.Y.Z -m "..."` and `git push origin vX.Y.Z`.
5. Build the .exe: `pyinstaller build.spec --clean -y`
   (use `.build-venv`).
6. Create a GitHub Release with the .exe attached and the CHANGELOG
   section as release notes.

The user controls when a release happens — not every commit.

## What this doc is NOT

- It's NOT a tutorial. Use the existing code + tests as reference.
- It's NOT a design spec for NEW features. For new features, write
  a spec in `docs/superpowers/specs/` first.
- It's NOT a changelog. See `CHANGELOG.md` for that.

Last updated: 2026-08-18 (BLOQUE 58.14.6-8 + wire)
