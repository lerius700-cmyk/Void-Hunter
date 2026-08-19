# 03 — Path Follower & Spec

The bridge between a path + formation and the actual `Enemy` objects the
game spawns. Two classes:

- `PathFollower` (stateful, advances `t` over time)
- `FormationPathSpec` (recipe: formation + path → list of enemies)

**Files:** `src/movement/follower.py`, `src/movement/spec.py`

---

## `PathFollower` — the stateful engine

A `PathFollower` is what each `Enemy` holds. Every frame, the game calls
`follower.update(dt)` and gets back `(position, velocity)`. The follower
advances its internal `t` by `dt / total_duration_s`.

```python
from src.movement.follower import PathFollower
from src.movement.hybrid import HybridPath
from src.movement.bezier import BezierPath, Point

path = HybridPath([
    BezierPath(Point(310, -20), Point(310, 80), Point(220, 120), Point(160, 140))
])

follower = PathFollower(path)

# In your game loop:
x, y, vx, vy = follower.update(dt)
enemy.x, enemy.y = x, y
enemy.nose_angle = math.atan2(vy, vx)  # face the motion direction
```

### API

| Member | Notes |
|---|---|
| `path: HybridPath` | The motion path. |
| `t: float` (property) | Current parameter in `[0, 1]`. |
| `is_complete: bool` (property) | `True` once `t >= 1`. |
| `update(dt)` | Advances by `dt`, returns `(Point pos, Point vel)`. |
| `reset()` | Restarts the path (e.g., for chained waves). |
| `t_offset: float` (init arg) | Initial offset in **seconds**, not `t`. |

### The `t_offset` parameter (for staggered entries)

Use this when a formation's ships should spawn at the same time but appear
at different points along the path:

```python
# 5 ships entering a 6s path at 0s, 1.2s, 2.4s, 3.6s, 4.8s
offsets = [i * 1.2 for i in range(5)]
followers = [PathFollower(path, t_offset=t) for t in offsets]
```

When `t_offset > total_duration_s`, the follower starts as `is_complete=True`
(useful for "this slot is currently off-screen").

### How velocity is computed

`update()` does:

```python
new_t = self._t + dt / self.path.total_duration_s
pos = self.path.position_at(self._t)
tan = self.path.tangent_at(self._t)
speed = self._segment_speed()  # px/s for the current segment
return pos, Point(tan.x * speed, tan.y * speed)
```

The returned velocity is in **px/s** (after `speed` scaling). This is what
the enemy uses to compute its face angle: `nose_angle = atan2(vy, vx)`.

### `is_complete` behavior

Once `t >= 1.0`, the follower is "done". Subsequent `update(0)` or
`update(dt)` returns the last position with velocity `(0, 0)`. The game
typically destroys the enemy at this point.

`_segment_speed()` for the current segment:

- `WaypointPath` → `seg.speed_px_s`.
- `BezierPath` → `seg.length_estimate / self.path.segment_durations[idx]`.

This means a `BezierPath` with duration 2s and length 160px gives speed
80 px/s — matching the 80px/s default from `HybridPath._intrinsic_duration()`.

---

## `FormationPathSpec` — the recipe

A `FormationPathSpec` is the unit the wave generator emits. It says:
*"spawn N enemies, each following this path, offset by this formation's
slots, with this stagger"*.

```python
from src.movement.spec import FormationPathSpec
from src.movement.formation import FlightFormation, FormationKind
from src.movement.hybrid import HybridPath
from src.entities.enemies.enemy import Enemy, EnemyKind

spec = FormationPathSpec(
    formation=FlightFormation.v(count=5, spacing=20),
    path=some_hybrid_path,
    enemy_kind=EnemyKind.SCOUT,
    spawn_interval_s=0.15,  # 0.15s between successive ships
    spawn_t0_s=0.0,
)
enemies = spec.build()  # list[Enemy], each with attached PathFollower
```

### API

| Field | Type | Notes |
|---|---|---|
| `formation` | `FlightFormation` | The shape. |
| `path` | `HybridPath` | The motion path. |
| `enemy_kind` | `Optional[EnemyKind]` | What kind of enemy each slot is. |
| `spawn_interval_s` | `float` | Default 0.15. Time between successive slots. |
| `spawn_t0_s` | `float` | Default 0. Global wave-time offset. |
| `spawn_stagger` | `list[float]` | Optional per-slot override of spawn times. |

### `build()`

Materializes the recipe into a `list[Enemy]`:

```python
def build(self) -> list[Enemy]:
    n = self.formation.count
    enemies = []
    for i, (dx, dy) in enumerate(self.formation.offsets):
        e = Enemy()
        e.on_spawn()
        e.kind = self.enemy_kind or EnemyKind.SCOUT
        follower = PathFollower(self.path)  # each slot gets its own follower
        e.attach_path(follower, slot_dx=dx, slot_dy=dy)
        enemies.append(e)
    return enemies
```

Returned enemies are **not** `active=True` — the wave manager is expected
to flip `active` when it spawns them at the right time (matched to
`spawn_timestamps()`).

### `spawn_timestamps()`

The `t0` (relative to wave start) when each slot should spawn. Defaults to
`[i * spawn_interval_s for i in range(n)]`.

```python
spec.spawn_timestamps()  # [0.0, 0.15, 0.30, 0.45, 0.60] for 5 ships
```

If you pass a custom `spawn_stagger`, those override the interval.

### Important: each slot has its own follower

`build()` creates **N separate `PathFollower` instances** all pointing at
the same `HybridPath`. This is on purpose:

- The follower's internal `t` is per-ship — you can pause one without
  affecting the others.
- A bug in one follower's state doesn't corrupt the formation.
- The wave manager can replace one enemy's path at runtime (e.g., boss
  transformation) without touching the others.

All followers start at `t=0` and advance at the same rate, so the formation
visually holds together. (The formation shape is implicit in the
`slot_dx`, `slot_dy` offsets — it doesn't need to be enforced by the
followers.)

---

## End-to-end: spec → spawn → tick

```python
# 1. Build a path (entry arc + L-turn + exit dive)
path = HybridPath([entry_arc, l_turn, exit_dive], [2.0, 1.5, 1.0])

# 2. Pick a formation
form = FlightFormation.v(count=5)

# 3. Build a spec
spec = FormationPathSpec(
    formation=form, path=path,
    enemy_kind=EnemyKind.SCOUT,
    spawn_interval_s=0.15,
)

# 4. Materialize
enemies = spec.build()

# 5. Spawn on schedule
for i, e in enumerate(enemies):
    t_spawn = i * 0.15
    scheduler.schedule(t_spawn, e.activate)

# 6. Tick each frame
for e in enemies:
    if e.active and e.follower:
        x, y, vx, vy = e.follower.update(dt)
        e.x, e.y = x, y
        e.angle = math.atan2(vy, vx)
```

---

## Reading order

Next: **[04_wave_patterns.md](./04_wave_patterns.md)** — the 6 base wave
patterns + 50 composed, and how `ProceduralWaveManager` picks one.
