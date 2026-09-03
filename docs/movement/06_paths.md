# 06 — Sacred Geometry & Fractal Paths (BLOQUE 58.next)

Seven new path classes added in BLOQUE 58.next. Each returns a
`HybridPath` of bezier segments. All paths are 2D (no z-axis), no
numpy, no star shapes (curves with sharp spikes are excluded by
construction).

**File:** `src/movement/{name}_path.py` for each.

## `LemniscatePath` — figure-8

`x(t) = a · cos(t) / (1 + sin²(t))`, `y(t) = a · sin(t) · cos(t) / (1 + sin²(t))`.

Approximated with 8 bezier segments. `scale=120` fits the 320×480
playfield with margin.

```python
from src.movement.lemniscate_path import LemniscatePath
path = LemniscatePath(scale=120.0, duration_s=6.0).get_path()
```

## `CardioidPath` — heart shape

`x(t) = a · (2·cos(t) - cos(2t))`, `y(t) = a · (2·sin(t) - sin(2t))`.

Approximated with 12 bezier segments. The cusp at t=pi is smoothed
out by the bezier control points.

```python
from src.movement.cardioid_path import CardioidPath
path = CardioidPath(scale=60.0, duration_s=5.0).get_path()
```

## `LissajousPath` — parametric sin/cos curve

`x(t) = A · sin(a·t + delta)`, `y(t) = B · sin(b·t)`.

Default: a=3, b=2, delta=pi/2 (3:2 ratio = trefoil-like, NO sharp
points). 12 segments.

```python
from src.movement.lissajous_path import LissajousPath
path = LissajousPath(a=3, b=2, duration_s=6.0).get_path()
```

## `RoseK2Path` — 4-petal rose

`r(theta) = a · cos(2·theta)`. 4 petals. 8 segments (2 per petal).

```python
from src.movement.rose_path import RoseK2Path
path = RoseK2Path(scale=80.0, duration_s=6.0).get_path()
```

## `RoseK3Path` — 3-petal rose

`r(theta) = a · cos(3·theta)`. 3 petals (NOT a 3-pointed star — the
petals are smooth lobes, no spikes). 12 segments (4 per petal).

```python
from src.movement.rose_path import RoseK3Path
path = RoseK3Path(scale=80.0, duration_s=6.0).get_path()
```

## `HypocycloidPath` — Spirograph (small circle inside big)

`x(t) = (R-r)·cos(t) + r·cos((R-r)·t/r)`, `y(t) = (R-r)·sin(t) - r·sin((R-r)·t/r)`.

Number of cusps = R/r. Default R=3r gives a 3-cusp deltoid. 6
segments per cusp.

```python
from src.movement.hypocycloid_path import HypocycloidPath
path = HypocycloidPath(R=60, r=20, duration_s=8.0).get_path()
```

## `EpicycloidPath` — small circle outside big

`x(t) = (R+r)·cos(t) - r·cos((R+r)·t/r)`, `y(t) = (R+r)·sin(t) - r·sin((R+r)·t/r)`.

When R=r, gives a cardioid (single cusp). 16 segments for the
cardioid case, 8 per cusp otherwise.

```python
from src.movement.epicycloid_path import EpicycloidPath
path = EpicycloidPath(R=30, r=30, duration_s=8.0).get_path()
```

## Why no star shapes (curve-level)

The "no stars" constraint applies to paths too. A star-shape is a
closed curve with sharp radial spikes. We verified each of the 7 new
paths has continuous tangent direction (no angle discontinuities
> 90 deg between consecutive samples). See
`tests/test_paths.py::test_paths_no_star_shapes`.
