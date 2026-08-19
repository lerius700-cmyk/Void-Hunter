# 02 — Formations

How groups of ships are arranged around a path's center. A `FlightFormation`
is a set of `(dx, dy)` slot offsets; when the path's center is at `(cx, cy)`,
each ship sits at `(cx + dx, cy + dy)`.

**File:** `src/movement/formation.py`
**Coordinate convention:** 320×480 internal playfield, `+x` right, `+y` down.

---

## `FormationKind` enum

```python
class FormationKind(str, Enum):
    V = "v"
    LINE = "line"
    DIAMOND = "diamond"
    SQUARE = "square"
    WEDGE = "wedge"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    HALF_V = "half_v"
    CUSTOM = "custom"
```

9 presets. `CUSTOM` is for user-defined slot offsets (from JSON, level data,
or inline).

---

## `FlightFormation`

A `FlightFormation` is **just a list of offsets** plus a `kind` tag:

```python
class FlightFormation:
    kind: FormationKind
    offsets: list[tuple[float, float]]  # one per ship, in path-local frame
    count: int  # == len(offsets)
```

That's it. The "magic" is in the 9 static builders below.

### Common API

| Builder | Signature | Notes |
|---|---|---|
| `FlightFormation.v(count, spacing=18)` | 3–13 ships | Leader at `(0, 0)`, wings flare back-and-down. |
| `FlightFormation.line(count, spacing=22)` | 1+ ships | Horizontal row centered on (0, 0). |
| `FlightFormation.diamond(count, spacing=20)` | 1, 5, 9, 13... | Layered rings. |
| `FlightFormation.square(count, spacing=22)` | 1+ ships | Corners + center, then midpoints. |
| `FlightFormation.wedge(count, spacing=18)` | 3+ ships | Right-pointing `>` (V mirrored). |
| `FlightFormation.circle(count, radius=24)` | 2+ ships | N slots around a circle. |
| `FlightFormation.triangle(count, spacing=18)` | 1+ ships | Triangle pointing down. 1+2+3+... rows. |
| `FlightFormation.half_v(count, spacing=18)` | 1+ ships | Half-chevron. Leader + right wing only. |
| `FlightFormation.custom(offsets)` | ≥1 | Pass your own `[(dx, dy), ...]`. |

Plus a dispatch: `FlightFormation.make(kind, count, spacing, radius)`.

---

## The 9 presets in detail

### 1. `V` — chevron pointing down

```
        *
      *   *
    *       *
  *           *
```

Leader at `(0, 0)`. Wings go back-and-down at `±spacing, spacing`,
`±2·spacing, 2·spacing`, etc. Default `spacing=18`.

```python
form = FlightFormation.v(count=5)  # 5 slots
# offsets: [(0,0), (-18, 18), (18, 18), (-36, 36), (36, 36)]
```

### 2. `LINE` — horizontal row

```
    *   *   *   *   *
```

Centered on (0, 0). Default `spacing=22`.

```python
form = FlightFormation.line(count=5)
# offsets: [(-44, 0), (-22, 0), (0, 0), (22, 0), (44, 0)]
```

### 3. `DIAMOND` — 1 + 4·k layers

```
        *
      *   *
    *   *   *
      *   *
        *
```

Count must be 1, 5, 9, 13, ... (1 + 4·k layers). `spacing` is the layer
distance.

```python
form = FlightFormation.diamond(count=5)  # leader + ring 1
# [(0,0), (0,-20), (20,0), (0,20), (-20,0)]
```

### 4. `SQUARE` — corners + center, then midpoints

```
    *-------*
    |   *   |
    *-------*
```

count ≤ 5: 4 corners + center. count > 5: edge midpoints between corners.

```python
form = FlightFormation.square(count=5, spacing=22)
# [(0,0), (-22,-22), (22,-22), (22,22), (-22,22)]
```

### 5. `WEDGE` — right-pointing `>` (V mirrored)

```
*
*
*       *
*           *
*
```

Leader at the left tip. Wings flare right-and-up/down.

```python
form = FlightFormation.wedge(count=5)  # 5 slots, leader at (0,0)
# [(0,0), (18, -18), (18, 18), (36, -36), (36, 36)]
```

### 6. `CIRCLE` — N around a ring

```
        *
    *       *
        *
    *       *
        *
```

`radius` is the orbital radius. N slots evenly spaced.

```python
form = FlightFormation.circle(count=6, radius=24)
```

### 7. `TRIANGLE` — 1+2+3+... rows pointing down

```
        *
      *   *
    *   *   *
  *   *   *   *
```

Row 0: 1 slot, row 1: 2, row 2: 3, ...

```python
form = FlightFormation.triangle(count=6)
# 1+2+3 rows = 6 slots
```

### 8. `HALF_V` — leader + right wing only

```
*
*   *
*       *
*           *
```

Use when you want the formation to bias one direction. Mirror by negating
all `dx` values after construction if you need the other side.

### 9. `CUSTOM` — your own offsets

```python
form = FlightFormation.custom([(0, 0), (-30, 10), (30, 10), (-60, 20), (60, 20)])
# any shape, any count
```

---

## How slots connect to paths

A formation **does not own a path**. The path is a separate `HybridPath`.
The connection happens in `FormationPathSpec` (see `03_path_follower.md`):

```
    FlightFormation  +  HybridPath  ->  FormationPathSpec  ->  list[Enemy]
         (slots)         (motion)         (bridge)              (spawnable)
```

For each slot `(dx, dy)`, the spec creates one `PathFollower` attached to the
**same** path, and the enemy's `attach_path(follower, slot_dx=dx, slot_dy=dy)`
makes the follower offset by `(dx, dy)` from the path's center.

This means **every ship in a formation follows the same path**, just offset
by the formation's slots. The shape holds together because every ship has
the same `t` parameter at every moment (the `PathFollower` is per-ship, but
all start at the same `t_offset` and advance at the same rate).

---

## Reading order

Next: **[03_path_follower.md](./03_path_follower.md)** — `PathFollower` and
`FormationPathSpec`, the bridge that makes a path + formation into spawnable
enemies.
