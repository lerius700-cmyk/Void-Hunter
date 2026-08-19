# 05 — Advanced Paths

The choreographic flourishes on top of the basic primitives:
`ParallelPathPair` (Star Fox 64 "pair dance") and `OrbitalPath` (the
butterfly orbit).

**Files:** `src/movement/parallel_path.py`, `src/movement/orbital_path.py`

---

## `ParallelPathPair` — SF64 pair dance (BLOQUE 58.13)

Two `HybridPath` instances that travel side-by-side with a constant
vertical offset. Used by `BEZIER_SWEEP` and `PINCER_CROSS`.

### What it solves

Star Fox 64's signature "two enemies flying in tandem" motion. Each ship
follows its own curve, but the curves are parallel — never converging or
diverging. The two ships always read as a **pair** even as they sweep
across the screen.

### Why vertical offset, not perpendicular

A true perpendicular offset would require computing the tangent at every
`t` and rotating 90° (expensive + visually identical at playfield scale).
At 320×480 with mostly horizontal motion, a **constant vertical offset**
is visually indistinguishable from a perpendicular one and 10× cheaper.

### API

```python
from src.movement.parallel_path import ParallelPathPair

# base_segments is a list of 4-tuples (p0, p1, p2, p3) of (x, y) points
pair = ParallelPathPair(
    base_segments=[
        ((310, -20), (310, 80), (220, 120), (160, 140)),  # centerline segment 1
        ((160, 140), (40, 140), (40, 280), (120, 300)),   # centerline segment 2
    ],
    base_durations=[1.5, 2.0],
    gap_px=14,  # vertical offset between the two paths
)

top = pair.get_top()  # HybridPath, offset by -7 in y
bot = pair.get_bot()  # HybridPath, offset by +7 in y
```

### Constructor logic

```python
top_segs = self._offset_segments(base_segments, -gap_px / 2.0)
bot_segs = self._offset_segments(base_segments, +gap_px / 2.0)
self._top = HybridPath(top_segs, list(base_durations))
self._bot = HybridPath(bot_segs, list(base_durations))
```

So the top path is the centerline shifted up by `gap_px/2`, the bottom
path is shifted down by `gap_px/2`. The original centerline is **not**
returned — only the two offset paths.

### Validation

- `len(base_segments) == len(base_durations)` — one duration per segment.
- `base_segments` not empty.
- `gap_px >= 0` (0 = no offset; the two paths are identical).

### When to use it

- Pair-dance patterns (`BEZIER_SWEEP` uses it).
- Pincer movements where two groups approach from opposite sides
  (`PINCER_CROSS` uses the inverse — mirror).
- Boss entrance with bodyguard.

### When NOT to use it

- A single ship (just use a `HybridPath`).
- Ship groups of 3+ — use `FlightFormation` instead.

---

## `OrbitalPath` — 4-segment bezier circle (BLOQUE 58.13)

An orbital path around a center point, approximated as 4 cubic bezier
segments. Each segment is a quarter-orbit.

Used by `OSCILLATING_BUTTERFLY` for the "butterfly" choreography.

### The bezier quarter-circle approximation

A unit circle quadrant from `(1, 0)` to `(0, 1)` can be approximated by a
cubic bezier with control points `(1, k)` and `(k, 1)`, where:

```
k = 4/3 · (√2 - 1) ≈ 0.5523
```

This produces a curve that deviates from a true circle by **< 0.02%**.
For our playfield scale (320×480) the error is sub-pixel and unnoticeable.

```
       (0, 1)
          *
         / \
        /   \
   (k, 1)    \
   *          \  (1, k)
                \
                 *
                (1, 0)
```

### API

```python
from src.movement.orbital_path import OrbitalPath

orbit = OrbitalPath(
    center=(160, 240),     # (cx, cy) orbital center
    radius_x=80,           # horizontal radius
    radius_y=60,           # vertical radius (ellipse if != radius_x)
    duration_s=6.0,        # one full orbit takes 6s
    rotation_deg=0,        # starting angle (0 = right, CCW)
)

path = orbit.get_path()  # HybridPath with 4 BezierPath segments
```

The returned `HybridPath` has 4 segments, each of duration `duration_s / 4`.
The orbit is **counter-clockwise** in screen coordinates (right → top → left
→ bottom → right).

### How it's built

```python
def _build_quarters(cx, cy, rx, ry, rotation_deg):
    rot_rad = math.radians(rotation_deg)
    kx = _K * rx
    ky = _K * ry
    # 4 quarter-arcs: (start_angle, end_angle) in degrees
    quarters = [(0, 90), (90, 180), (180, 270), (270, 360)]
    segments = []
    for start_a, end_a in quarters:
        p0 = pt(start_a)        # (cx + rx*cos(a), cy - ry*sin(a))
        p3 = pt(end_a)
        cp1, cp2 = cp_for_quarter(start_a, end_a)
        segments.append(BezierPath(p0, cp1, cp2, p3))
    return segments
```

Note the `cy - ry*sin(a)` instead of `cy + ry*sin(a)`. Screen coordinates
have `+y` going **down**, so the math-sin is negated to make the orbit
counter-clockwise in screen space (which is clockwise in math space).

### Validation

- `radius_x > 0` and `radius_y > 0`.
- `duration_s > 0`.

### When to use it

- `OSCILLATING_BUTTERFLY` patterns.
- Boss hover behavior.
- Any "dancing" motion around a fixed point.

### When NOT to use it

- Linear motion (use `BezierPath` or `WaypointPath`).
- Spirals (use a custom multi-segment `HybridPath`).

---

## How the advanced paths connect to the rest of the system

```
ParallelPathPair                  OrbitalPath
    │                                  │
    ▼                                  ▼
get_top()/get_bot()  ──►  HybridPath  ◄──  get_path()
                                  │
                                  ▼
                          PathFollower (per ship)
                                  │
                                  ▼
                          Enemy.x, Enemy.y per frame
```

- `BEZIER_SWEEP` builds a `ParallelPathPair` and gives one path to each
  of the 2 ships in the pair.
- `PINCER_CROSS` builds a `ParallelPathPair` and mirrors one side to come
  from the opposite direction.
- `OSCILLATING_BUTTERFLY` builds an `OrbitalPath` and assigns the same
  path to all ships in the formation (so they orbit together).

---

## Why no numpy / scipy

Both files use **only `math`** from the stdlib. The GDD (§0) bans
numpy/scipy in this project (only the pause lowpass in
`src/audio/synth.py` is the documented exception). Don't add numpy here.

---

## End of the movement docs

You now have the full stack:

1. **[01_movement_primitives.md](./01_movement_primitives.md)** — `BezierPath`, `WaypointPath`, `HybridPath`.
2. **[02_formations.md](./02_formations.md)** — `FlightFormation` and 9 presets.
3. **[03_path_follower.md](./03_path_follower.md)** — `PathFollower` + `FormationPathSpec`.
4. **[04_wave_patterns.md](./04_wave_patterns.md)** — 6 base + 50 COMPOSED.
5. **[05_advanced_paths.md](./05_advanced_paths.md)** — `ParallelPathPair`, `OrbitalPath`.

If you change anything in `src/movement/` or `src/systems/wave_patterns/`,
update the relevant doc and run `pytest tests/test_wave_patterns.py`.
