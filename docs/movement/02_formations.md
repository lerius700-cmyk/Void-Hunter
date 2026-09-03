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

## Sacred Geometry & Fractal Presets (BLOQUE 58.next)

Ten new formations added in BLOQUE 58.next. All are 2D slot patterns
(no z-axis). Explicitly NO star shapes (excludes pentagram, hexagram,
{n/k} star polygons, snowflake-star hybrids).

### 10. `FLOWER_OF_LIFE` — center + 6 hex

7 ships: center (0, 0) + 6 hex points at radius 18, angles 0/60/120/180/240/300 deg.

Builder: `FlightFormation.flower_of_life(count=7, radius=18.0)`

### 11. `VESICA_PISCIS` — 2 ships

2 ships at (±9, 0). The dyadic sacred figure.

Builder: `FlightFormation.vesica_piscis(count=2, spacing=18.0)`

### 12. `FIBONACFI_SPIRAL` — logarithmic spiral

8 ships on a logarithmic spiral: r = 8.0 · phi^(i/2), theta = i · 60 deg, where phi = (1+sqrt(5))/2.

Builder: `FlightFormation.fibonacfi_spiral(count=8, r0=8.0)` (sic, intentional typo per user)

### 13. `TREE_OF_LIFE` — 10 Kabbalistic sephirot

3 columns x 4 rows = 10 sephirot (crown row of 3, two middle rows of 3, kingdom row of 1). Layout:
- Crown: y = -22, x in {-22, 0, 22}
- Row 2: y = 0, x in {-22, 0, 22}
- Row 3: y = 22, x in {-22, 0, 22}
- Kingdom: y = 44, x = 0

Builder: `FlightFormation.tree_of_life(count=10, spacing=22.0)`

### 14. `SIERPINSKI_TRIANGLE` — depth-2 fractal

7 ships: 3 triangle vertices + 3 midpoints of edges + 1 centroid. Triangle inscribed in a circle of radius 24.

Builder: `FlightFormation.sierpinski_triangle(count=7, radius=24.0)`

### 15. `HEX_CLOSE_PACK` — honeycomb (tighter than flower_of_life)

Same 7 hex layout as `FLOWER_OF_LIFE` but with radius=14 (tighter spacing creates a true honeycomb cell).

Builder: `FlightFormation.hex_close_pack(count=7, radius=14.0)`

### 16. `MANDALA_RINGS` — 2 concentric hex rings

12 ships: 6 inner ring at r=12 + 6 outer ring at r=24 (outer offset by 30 deg).

Builder: `FlightFormation.mandala_rings(count=12, inner_r=12.0, outer_r=24.0)`

### 17. `GOLDEN_RATIO_ROW` — accelerating horizontal row

5 ships on a horizontal line at offsets 0, phi, 2·phi, 3·phi, 4·phi (× spacing=10).

Builder: `FlightFormation.golden_ratio_row(count=5, spacing=10.0)`

### 18. `KOCH_3FOLD` — 3-fold Koch zigzag (no central peak)

7 pre-computed anchors on a 3-fold Koch curve. The 3-fold version (NOT 6-fold snowflake) is asymmetric and reads as a "fractal zigzag", not a star.

Builder: `FlightFormation.koch_3fold(count=7, scale=24.0)`

### 19. `DRAGON_CURVE` — Heighway dragon recursion

8 pre-computed anchors of the Heighway dragon curve. Reads as a "fractal staircase".

Builder: `FlightFormation.dragon_curve(count=8, scale=16.0)`

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
