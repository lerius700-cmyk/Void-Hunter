# 04 — Wave Patterns

The "what kind of wave is this" layer on top of paths and formations. A
`WavePattern` is a **deterministic recipe** for spawning a group of ships
given a seeded RNG and a difficulty level. The runtime converts the
pattern's output into `Enemy` objects with attached paths.

**Files:** `src/systems/wave_patterns/*.py`

---

## `WavePatternKind` enum — 7 kinds

```python
class WavePatternKind(Enum):
    BEZIER_SWEEP = "bezier_sweep"
    V_FORMATION = "v_formation"
    LEADER_FOLLOWER_CHAIN = "leader_chain"
    DICE_FIVE_GRID = "dice_five_grid"
    PINCER_CROSS = "pincer_cross"
    OSCILLATING_BUTTERFLY = "oscillating_butterfly"
    COMPOSED = "composed"  # 50 pre-defined combinations
```

The first 6 are "base" patterns with hand-tuned logic. The 7th is
**data-driven**: when the manager rolls `COMPOSED`, it picks one of 50
pre-defined `(formation, path, follow, count)` combinations at random.

---

## `SpawnedShip` — the output unit

Each pattern's `generate()` returns a `list[SpawnedShip]`:

```python
@dataclass(frozen=True)
class SpawnedShip:
    spawn_x: float       # initial position
    spawn_y: float
    t_offset: float      # seconds (so the leader can be 0.5s ahead)
    slot: int            # formation slot index
    color: tuple[int, int, int] | None  # RGB tint for trail/sprite
    is_leader: bool      # True for the front ship (gets a glow ring)
    extra: dict[str, Any]  # pattern-specific data
```

`extra` carries the path/formation/follow data the runtime needs to
attach the right `PathFollower`. The `segments` and `segment_durations`
keys are read by `runtime.attach_multi_segment_path` (BLOQUE 58.12).

---

## `WavePatternResult` — the wrapper

```python
@dataclass
class WavePatternResult:
    ships: list[SpawnedShip]
    kind: WavePatternKind
    difficulty: PatternDifficulty  # EASY | MEDIUM | HARD
    duration_s: float
    seed_used: int  # for replay determinism
```

The runtime reads this, creates one `Enemy` per ship, attaches the right
`PathFollower` from `extra`, and schedules them at their `t_offset`.

---

## The 6 base patterns

Each is one file in `src/systems/wave_patterns/`. They all inherit from
`WavePattern` and implement `generate(rng, level, enemy_kind)`.

### 1. `BEZIER_SWEEP`

A pair dance on a random bezier curve. Two parallel hybrid paths (uses
`ParallelPathPair` — see `05_advanced_paths.md`). Spawns 2 ships.

### 2. `V_FORMATION`

A rigid V shape with fixed slot offsets. Ships follow a single bezier
entry arc. Spawns 3-7 ships depending on `level`.

### 3. `LEADER_FOLLOWER_CHAIN`

A leader + history queue. The leader spawns first and follows a bezier;
followers spawn with `t_offset = i * 0.15` and follow the same path
staggered. Visually reads as a "snake".

### 4. `DICE_FIVE_GRID`

5 ships in the dice-5 pattern (4 corners + center). They sweep in on a
bezier with the formation intact.

### 5. `PINCER_CROSS`

Two mirror bezier curves entering from opposite sides of the screen
(`ParallelPathPair` style). Ships cross paths in the middle.

### 6. `OSCILLATING_BUTTERFLY`

Ships orbit a center point using `OrbitalPath` (4-segment bezier
approximation of a circle). Sinusoidal "dancing" motion. See
`05_advanced_paths.md`.

---

## `COMPOSED` — 50 choreographed patterns (BLOQUE 58.14.7)

The user asked for **50 new patterns** that combine formations, paths,
and follow modes. The implementation is **data-driven**:

```python
# composed.py
COMPOSED_PATTERNS: list[ComposedPattern] = _build_50_patterns()  # exactly 50
```

### The 3 axes

| Axis | Values | Source |
|---|---|---|
| **Formation** | line, v, diamond, wedge, circle, spiral, x, pincer, arrow | `FORMATION_GENERATORS` dict (9 entries) |
| **Path** | sweep, s_curve, sine, spiral, loop, zigzag, dive, straight | `PATH_GENERATORS` dict (8 entries) |
| **Follow** | leader, chain, free | hardcoded `_FOLLOW_FOR_LIBRARY` |
| **Count** | 4, 5, 6, 7, 8 | hardcoded `_COUNTS` |

The first 50 of the cross product are taken: `9 × 8 × 3 × 5 = 1080` combos,
capped at 50.

### How a `ComposedPattern` generates ships

```python
def generate(self, rng, level, enemy_kind):
    form_fn = FORMATION_GENERATORS[self._formation]
    path_fn = PATH_GENERATORS[self._path]
    slots = form_fn(self._count)               # [(dx, dy), ...]
    entry_x = rng.uniform(48, INTERNAL_W - 48) # random entry side
    entry_y = -20.0
    path_pts = path_fn((entry_x, entry_y), rng) # list of points
    # Convert consecutive 4-point groups into bezier segments
    segments = []
    for i in range(0, len(path_pts) - 3):
        segments.append((path_pts[i], path_pts[i+1], path_pts[i+2], path_pts[i+3]))
    duration_s = 8.0
    seg_durs = [duration_s / len(segments)] * len(segments)
    ships = []
    for i, (dx, dy) in enumerate(slots):
        is_leader = (i == 0) and (self._follow in ("leader", "chain"))
        t_off = i * 0.15 if self._follow == "chain" else 0.0
        ships.append(SpawnedShip(
            spawn_x=entry_x + dx,
            spawn_y=entry_y + dy,
            t_offset=t_off,
            slot=i,
            color=(255, 200, 80) if is_leader else (200, 160, 220),
            is_leader=is_leader,
            extra={
                "formation": self._formation,
                "path": self._path,
                "follow": self._follow,
                "segments": segments,
                "segment_durations": seg_durs,
            },
        ))
    return WavePatternResult(...)
```

The `segments` / `segment_durations` keys are exactly what
`runtime.attach_multi_segment_path` reads. So the path the ships follow
is a `HybridPath` built from these segments.

### Follow modes

- **leader** — one ship is the leader, others are at the same `t` but
  offset by the formation. Visually: tight formation.
- **chain** — each ship is `t_offset = i * 0.15` behind the previous.
  Visually: stretched snake.
- **free** — no follow constraint, just same path with slot offsets.
  Visually: loose group.

---

## `ProceduralWaveManager` — the picker

`ProceduralWaveManager` is the system that decides which pattern fires
next. It's seeded for reproducibility and weights by floor.

### Constructor

```python
mgr = ProceduralWaveManager(seed=42, floor=1, log_path="logs/patterns.log")
mgr.register_composed_patterns()  # populate the 50 COMPOSED entries
```

If you don't call `register_composed_patterns()`, COMPOSED picks fall back
to `BEZIER_SWEEP` (graceful degradation).

### Weighted pool per floor

```python
# Floor 1
[
    (V_FORMATION, 20),
    (DICE_FIVE_GRID, 18),
    (LEADER_FOLLOWER_CHAIN, 16),
    (BEZIER_SWEEP, 16),
    (PINCER_CROSS, 12),
    (OSCILLATING_BUTTERFLY, 18),
    (COMPOSED, 20),
]
# Floor 2
[(V_FORMATION, 16), (DICE_FIVE_GRID, 16), (LEADER_FOLLOWER_CHAIN, 16),
 (BEZIER_SWEEP, 16), (PINCER_CROSS, 16), (OSCILLATING_BUTTERFLY, 20),
 (COMPOSED, 24)]
# Floor 3+ (roughly equal, COMPOSED preferred)
[(V_FORMATION, 16), (DICE_FIVE_GRID, 16), (LEADER_FOLLOWER_CHAIN, 16),
 (BEZIER_SWEEP, 16), (PINCER_CROSS, 16), (OSCILLATING_BUTTERFLY, 20),
 (COMPOSED, 28)]
```

`COMPOSED` has the **highest single weight** in every pool. That's the
point: the 50 patterns get meaningful screen time (~18-28% of picks).

### `pick_pattern(level, enemy_kind)` — the main API

```python
result = mgr.pick_pattern(level=2, enemy_kind="SCOUT")
# result.ships -> list[SpawnedShip]
# result.kind, result.difficulty, result.duration_s, result.seed_used
```

Algorithm:

1. Get the weighted pool for the current floor.
2. Filter out the **previous** kind (anti-stuck: avoid immediate repeats).
3. Build a flat list (each kind repeated by its weight) and `rng.choice`.
4. If the kind is `COMPOSED`, pick a specific instance from the 50-entry
   registered pool. Otherwise, `_make_pattern(kind)` instantiates a fresh
   one.
5. Call `pattern.generate(rng, level, enemy_kind)`.
6. Log to `patterns.log`.

### `SoloEnemySpawner` — 1 ship every 5s

Separate from the formations. Spawns a single red "straggler" every
`interval_s` seconds during a wave.

```python
spawner = SoloEnemySpawner(interval_s=5.0)
# Each frame:
new_ships = spawner.update(dt, rng)
for s in new_ships:
    spawn_solo_ship(pool, s)
```

Solo ships have `color=(255, 80, 60)` (red), `is_leader=True`, and a
short `segments=[(p0, cp1, mid, end)]` with `segment_durations=[4.0]`
(cross the screen in 4s).

---

## Runtime wiring

`gameplay_runtime.py::enable_procedural_patterns()` is the entry point:

```python
def enable_procedural_patterns(seed: int, floor: int) -> ProceduralWaveManager:
    mgr = ProceduralWaveManager(seed=seed, floor=floor)
    mgr.register_composed_patterns()  # 50 patterns
    return mgr
```

Then each frame, `_spawn_procedural_patterns()` calls `mgr.pick_pattern()`
and `spawner.update(dt, rng)`.

---

## Reading order

Next: **[05_advanced_paths.md](./05_advanced_paths.md)** — `ParallelPathPair`
(SF64 pair dance) and `OrbitalPath` (4-segment bezier circle for the
butterfly orbit).
