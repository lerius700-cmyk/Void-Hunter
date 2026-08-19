# 01 — Movement Primitives

The 3 building blocks everything else is made of. Understand these and the
rest of the system follows naturally.

**Files:** `src/movement/bezier.py`, `src/movement/waypoint.py`, `src/movement/hybrid.py`
**Constraint:** no numpy / scipy (GDD §0). Pure stdlib + `math`.

---

## 1. `BezierPath` — cubic bezier curve

A cubic bezier defined by 4 control points: `P0` (start), `P1`, `P2`, `P3` (end).
Parameter `t ∈ [0, 1]` walks the curve from `P0` to `P3`.

```python
from src.movement.bezier import BezierPath, Point

arc = BezierPath(
    p0=Point(300, 50),    # top right (entry)
    p1=Point(300, 200),   # pull down
    p2=Point(20, 200),    # pull down
    p3=Point(20, 380),    # bottom left (exit)
)
mid = arc.position_at(0.5)  # midpoint of the curve
tan = arc.tangent_at(0.5)   # direction at midpoint
```

### Math

```
B(t)  = (1-t)³·P0 + 3(1-t)²·t·P1 + 3(1-t)·t²·P2 + t³·P3
B'(t) = 3(1-t)²·(P1-P0) + 6(1-t)·t·(P2-P1) + 3·t²·(P3-P2)
```

The tangent is **not normalized** — its magnitude is the local "speed in
parameter space". To get a velocity in px/s, multiply by the effective speed
of the segment (`PathFollower._segment_speed()` does this for you).

### API

| Method | Returns | Notes |
|---|---|---|
| `position_at(t)` | `Point(x, y)` | Clamped to `P0` when `t≤0`, `P3` when `t≥1`. |
| `tangent_at(t)` | `Point(dx, dy)` | Unnormalized. `(P1-P0)` at `t=0`, `(P3-P2)` at `t=1`. |
| `length_estimate` (property) | `float` (px) | 16-segment polyline approximation. ~few % off. |

### When to use it

- Smooth sweeps and arcs (S-bends, J-curves, swooping entries).
- Anywhere you want a single `t → position` mapping with C¹ continuity.
- As a **building block** for `HybridPath` and `OrbitalPath`.

### When NOT to use it

- Straight lines → `WaypointPath` (cheaper, easier to reason about).
- Sharp 90° turns → `WaypointPath` (a bezier can't have a corner).
- Multi-stop routes with pauses → `WaypointPath` (has `linger_s`).

---

## 2. `WaypointPath` — straight lines with constant speed

A list of `(x, y)` waypoints the ship follows in order. Each pair of
consecutive waypoints is one straight segment. The ship moves at constant
`speed_px_s`. **Lingers** at waypoints if you want.

```python
from src.movement.waypoint import WaypointPath
from src.movement.bezier import Point

# Sharp L-turn with a 0.4s pause at the corner
route = WaypointPath(
    waypoints=[Point(20, 50), Point(20, 200), Point(280, 200)],
    speed_px_s=120.0,
    linger_s=[0.0, 0.4, 0.0],   # pause AFTER reaching each waypoint
)
print(f"traverses in {route.total_duration_s:.2f}s")
```

### API

| Member | Notes |
|---|---|
| `waypoints` | `list[Point]`. Normalized from tuples on construction. |
| `speed_px_s` | Constant for every segment. |
| `linger_s` | Per-waypoint pause, in seconds. Defaults to all 0. |
| `total_length` (property) | Pre-computed sum of segment lengths. |
| `total_duration_s` (property) | `length / speed + sum(linger)`. |
| `position_at_distance(d)` | Returns `(Point pos, Point unit_tan)`. |
| `is_complete(d)` | `True` when `d >= total_length`. |

### Pre-computed internals

- `_segment_lengths: list[float]` — one per segment.
- `_cumulative_lengths: list[float]` — `cum[i]` = distance at start of segment `i`.

These are built once in `__init__`, so `position_at_distance()` is `O(segments)`
linear scan (usually < 10 segments → negligible).

### When to use it

- Sharp turns, multi-stop routes, L-shaped paths.
- Anywhere the ship needs to **pause at a point** (boss intro, mid-wave hover).
- Backward-compat single straight line: `HybridPath.straighten(start, end)`.

### When NOT to use it

- Sweeping curves — use `BezierPath`.
- Anything where you want C¹ tangent continuity across segments.

---

## 3. `HybridPath` — concatenate bezier + waypoint

User's explicit ask: *"mix bezier for smooth sweeps, waypoints for sharp
turns, all in one continuous path"*. A `HybridPath` is exactly that: a list
of segments, each either a `BezierPath` or a `WaypointPath`, with a per-
segment duration.

```python
from src.movement.hybrid import HybridPath
from src.movement.bezier import BezierPath, Point
from src.movement.waypoint import WaypointPath

# 1) smooth bezier entry, 2) sharp L-turn with pause, 3) bezier exit
seg1 = BezierPath(Point(310, -20), Point(310, 80), Point(220, 120), Point(160, 140))
seg2 = WaypointPath(
    [Point(160, 140), Point(40, 140), Point(40, 280)],
    speed_px_s=100.0,
    linger_s=[0.0, 0.5, 0.0],
)
seg3 = BezierPath(Point(40, 280), Point(120, 300), Point(220, 360), Point(290, 420))

path = HybridPath([seg1, seg2, seg3])  # auto-uses intrinsic durations
# Or override:
# path = HybridPath([seg1, seg2, seg3], [2.0, 3.0, 1.5])

# Walk the whole path with a single t in [0, 1]
pos = path.position_at(0.5)
tan = path.tangent_at(0.5)
```

### Intrinsic durations

If you don't pass `segment_durations`, `HybridPath` uses each segment's own:

- `BezierPath` → `max(0.5, length_estimate / 80.0)` (80 px/s ≈ arcade ship speed).
- `WaypointPath` → `total_duration_s` (length/speed + lingers).

You usually want to **override** durations so the choreography feels right
(slow the bezier entry, speed up the exit).

### API

| Method | Notes |
|---|---|
| `from_segments(segments)` | Class-method shortcut. Uses intrinsic durations. |
| `total_duration_s` (property) | Sum of segment durations. |
| `position_at(t)` | Global `t` → `Point`. Dispatches to the right segment. |
| `tangent_at(t)` | Global `t` → unnormalized `Point` tangent. |
| `is_complete(t)` | `True` when `t >= 1.0`. |
| `straighten(start, end, speed_px_s)` | Static. Single-segment straight line as a `HybridPath`. |

### Internals: `_segment_for_t(t)`

Given global `t`, returns `(segment_index, local_t, distance_into_path)`.
This is what `PathFollower.update()` uses to dispatch every frame.

### When to use it

- **Every** spawnable enemy's motion path in the game.
- Multi-act choreography: entry → hover → attack → exit.
- Anywhere you want one `t → position` mapping that crosses curve types.

### When NOT to use it

- A single straight line (just use `WaypointPath` directly — save the wrapping).
- A single bezier (just use `BezierPath` directly).

---

## Coordinate convention

`+x` is right, `+y` is **down** (screen). Internal playfield is 320×480.
This matters when:

- Computing face angle: `nose_angle = math.atan2(vy, vx)` (negative angle = up).
- Interpreting "down" entries: enemy ships enter at `y < 0`, exit at `y > 480`.
- Rotating formations to follow the path tangent (rotate by `tangent` angle).

---

## Reading order

Next: **[02_formations.md](./02_formations.md)** — `FlightFormation` and the
9 preset shapes that place ships around a path's center.
