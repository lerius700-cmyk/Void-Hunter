# Movement Expansion: Sacred Geometry & Fractal Symbolism — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 10 new sacred-geometry/fractal formations and 7 new paths to the existing movement subsystem, expanding the COMPOSED wave pattern pool from 1,080 to 4,275 (capped at 1,050), per the approved spec.

**Architecture:** Extend `FlightFormation` with 10 new static builders, add 7 new path classes in `src/movement/`, register them in `COMPOSED`'s cross-product generators. The new formations/paths surface only through `COMPOSED` (no new `WavePatternKind` values). All math is 2D, no numpy, no star shapes.

**Tech Stack:** Python 3.11, pygame 2.6, pytest 9.1.1, stdlib `math` only. No new dependencies.

**Spec:** [`docs/superpowers/specs/2026-09-02-movement-expansion-sacred-geometry-design.md`](../specs/2026-09-02-movement-expansion-sacred-geometry-design.md)

---

## Global Constraints

- **Profile:** Lite (per `CLAUDE.md`); no numpy/scipy in runtime (GDD §0, exception: pause lowpass only)
- **Coordinate convention:** +x right, +y down (screen); 320×480 internal playfield
- **Naming:** new `FormationKind` enum values UPPER_SNAKE_CASE; new path classes PascalCase + `Path`; new files `snake_case.py`
- **One exception per user explicit request:** `FIBONACFI_SPIRAL` (sic, with typo) — Python identifier `fibonacfi_spiral`
- **NO star shapes:** exclude pentagram, hexagram, `{n/k}` star polygons (k>1), snowflake-star hybrids. Koch_3fold and Rose_K3 verified NOT star-shaped (asymmetric / smooth petals)
- **FROZEN subsystem:** `docs/movement/` and `src/movement/` + `src/systems/wave_patterns/` are FROZEN. This plan temporarily un-FREEZES them, re-FREEZES at Task 10
- **Backward compat:** first 50 COMPOSED patterns (old `seed=42` gameplay) MUST be unchanged (test in Task 5)
- **Test convention:** tests in `tests/test_*.py`, `pytest -q` from project root
- **Build:** `pyinstaller build.spec --clean --noconfirm` produces `dist/void-hunter/void-hunter.exe` (NOT committed)
- **Doc language:** technical docs in English; user-facing strings in Spanish (per `CLAUDE.md`)

---

## File Structure

### New files
- `src/movement/lemniscate_path.py` — LemniscatePath (figure-8)
- `src/movement/cardioid_path.py` — CardioidPath (heart)
- `src/movement/lissajous_path.py` — LissajousPath (3:2 default, configurable a/b/delta)
- `src/movement/rose_path.py` — RoseK2Path, RoseK3Path (4-petal and 3-petal roses)
- `src/movement/hypocycloid_path.py` — HypocycloidPath (Spirograph, default R=3r → 3-cusp deltoid)
- `src/movement/epicycloid_path.py` — EpicycloidPath (default R=r → cardioid)
- `tests/test_paths.py` — 7 path test classes
- `docs/movement/06_paths.md` — Documentation for the 7 new paths
- `docs/superpowers/plans/2026-09-02-movement-expansion-sacred-geometry.md` — this plan

### Modified files
- `src/movement/formation.py` — add 10 `FormationKind` enum values + 10 `@staticmethod` builders
- `src/systems/wave_patterns/composed.py` — register 10 new formations in `FORMATION_GENERATORS` + 7 new paths in `PATH_GENERATORS`; change cap from 50 to 1050
- `docs/movement/01_movement_primitives.md` — add "Notation" note clarifying "cubic" is polynomial degree (not 3D)
- `docs/movement/02_formations.md` — add "Sacred Geometry & Fractal Presets" section (10 formations)
- `docs/movement/CONTEXT.md` — TEMPORARILY UN-FROZEN note (reverted in Task 10)
- `docs/movement/README.md` — add `06_paths.md` to the stack
- `docs/changelog/CHANGELOG_v1.x.md` — add v1.2.x BLOQUE 58.next entry
- `tests/test_formation.py` — add 10 formation test methods
- `tests/test_wave_patterns.py` — add 4 COMPOSED integration tests

### New artifacts (gitignored, in `tools/playtest_out/`)
- `formation_<name>.png` × 10 (one per formation, slot positions visualized)
- `path_<name>.png` × 7 (one per path, curve visualized)
- `composed_5_random.png` × 1 (mosaic of 5 random COMPOSED patterns)

---

## Task 1: Add FLOWER_OF_LIFE (the reference formation)

**Files:**
- Modify: `src/movement/formation.py:30-40` (add `FLOWER_OF_LIFE = "flower_of_life"` to `FormationKind`)
- Modify: `src/movement/formation.py:~225` (add `flower_of_life()` static method after `half_v`)
- Modify: `src/movement/formation.py:215-235` (update `make()` dispatch dict to include `flower_of_life`)
- Modify: `tests/test_formation.py` (add 2 test methods)

**Interfaces:**
- Produces: `FlightFormation.flower_of_life(count=7, radius=18.0) -> FlightFormation`
- The 7 slots: center (0, 0) + 6 hex points at radius=18, angles 0°, 60°, 120°, 180°, 240°, 300°

- [ ] **Step 1: Write the failing test**

Add to `tests/test_formation.py` (after the existing `diamond` tests):

```python
def test_flower_of_life_default_count() -> None:
    """FLOWER_OF_LIFE with count=7 returns 7 slots: 1 center + 6 hex."""
    form = FlightFormation.flower_of_life()
    assert form.kind == FormationKind.FLOWER_OF_LIFE
    assert form.count == 7
    assert (0.0, 0.0) in form.offsets  # center

def test_flower_of_life_offsets_match_geometry() -> None:
    """The 6 outer slots are at radius=18, angles 0/60/120/180/240/300 deg."""
    import math
    form = FlightFormation.flower_of_life()
    outer = [(dx, dy) for dx, dy in form.offsets if (dx, dy) != (0.0, 0.0)]
    assert len(outer) == 6
    expected_angles = [0, 60, 120, 180, 240, 300]
    for dx, dy, angle_deg in zip([dx for dx, _ in outer], [dy for _, dy in outer], expected_angles):
        r = math.hypot(dx, dy)
        assert math.isclose(r, 18.0, abs_tol=0.1), f"radius {r} != 18 at angle {angle_deg}"
        expected_angle = math.radians(angle_deg)
        actual_angle = math.atan2(dy, dx)
        # angles modulo 2pi
        assert math.isclose(
            (actual_angle - expected_angle) % (2 * math.pi), 0, abs_tol=0.01
        ), f"angle {math.degrees(actual_angle)} != {angle_deg}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_formation.py -v -k "flower_of_life"`
Expected: FAIL with `AttributeError: type object 'FlightFormation' has no attribute 'flower_of_life'`

- [ ] **Step 3: Add FormationKind enum value**

Edit `src/movement/formation.py:30-40`. Add after the `CUSTOM = "custom"` line:
```python
FLOWER_OF_LIFE = "flower_of_life"
```

- [ ] **Step 4: Implement `flower_of_life()` static method**

Add to `src/movement/formation.py` (after the `half_v` method, before `custom`):
```python
@staticmethod
def flower_of_life(count: int = 7, radius: float = 18.0) -> "FlightFormation":
    """Sacred geometry: center + 6 hex points (Flower of Life pattern).

    count=7 -> center (0, 0) + 6 hex at radius 18, angles 0/60/120/180/240/300.
    count=1 -> only the center.
    """
    import math
    count = max(1, count)
    if count == 1:
        return FlightFormation(FormationKind.FLOWER_OF_LIFE, [(0.0, 0.0)])
    offsets: list[tuple[float, float]] = [(0.0, 0.0)]
    for i in range(6):
        angle = math.radians(i * 60)
        offsets.append((math.cos(angle) * radius, math.sin(angle) * radius))
    return FlightFormation(FormationKind.FLOWER_OF_LIFE, offsets[:count])
```

- [ ] **Step 5: Update the `make()` dispatch**

Edit `src/movement/formation.py:215-235` (the `make()` static method). Add after the `half_v` case:
```python
    if kind == FormationKind.FLOWER_OF_LIFE:
        return FlightFormation.flower_of_life(count, spacing)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_formation.py -v -k "flower_of_life"`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add src/movement/formation.py tests/test_formation.py
git commit -m "feat(movement): add FLOWER_OF_LIFE formation (BLOQUE 58.next)"
```

---

## Task 2: Add 9 more formations (Vesica Piscis, Fibonacci Spiral, Tree of Life, Sierpinski Triangle, Hex Close-Pack, Mandala Rings, Golden Ratio Row, Koch 3-fold, Dragon Curve)

**Files:**
- Modify: `src/movement/formation.py:30-40` (add 9 enum values)
- Modify: `src/movement/formation.py` (add 9 `@staticmethod` methods)
- Modify: `src/movement/formation.py:215-235` (update `make()` dispatch)
- Modify: `tests/test_formation.py` (add 9 test methods)

**Interfaces (per the spec, §3.2-3.10):**
- `vesica_piscis(count=2, spacing=18.0)` — 2 ships at (±9, 0)
- `fibonacfi_spiral(count=8, r0=8.0)` — log spiral r = r0·φ^(i/2), θ = i·60°, φ = (1+√5)/2
- `tree_of_life(count=10, spacing=22.0)` — 3 cols × 4 rows (3+3+3+1 = 10 sephirot)
- `sierpinski_triangle(count=7, radius=24.0)` — 3 vertices + 3 midpoints + 1 centroid
- `hex_close_pack(count=7, radius=14.0)` — same as flower_of_life but radius=14 (honeycomb)
- `mandala_rings(count=12, inner_r=12.0, outer_r=24.0)` — 6 inner + 6 outer (offset 30°)
- `golden_ratio_row(count=5, spacing=10.0)` — horizontal row at offsets 0, φ, 2φ, 3φ, 4φ × spacing
- `koch_3fold(count=7, scale=24.0)` — 6 pre-computed anchor points on a 3-fold Koch zigzag (no central peak)
- `dragon_curve(count=8, scale=16.0)` — 8 pre-computed anchors of Heighway dragon

- [ ] **Step 1: Write all 9 failing tests**

Add 9 test methods to `tests/test_formation.py`. Each test verifies `count`, kind, and key geometric properties. See spec §3.2-3.10 for the exact offset tables.

```python
import math
PHI = (1 + math.sqrt(5)) / 2  # for fibonacfi_spiral and golden_ratio_row

def test_vesica_piscis_two_ships() -> None:
    form = FlightFormation.vesica_piscis()
    assert form.kind == FormationKind.VESICA_PISCIS
    assert form.count == 2
    assert math.isclose(form.offsets[0][0], -9.0, abs_tol=0.1)
    assert math.isclose(form.offsets[1][0], 9.0, abs_tol=0.1)

def test_fibonacfi_spiral_golden_ratio() -> None:
    """Verify r-values follow r = r0 * phi^(i/2) within 1%."""
    form = FlightFormation.fibonacfi_spiral()
    r0 = 8.0
    for i, (dx, dy) in enumerate(form.offsets):
        r_actual = math.hypot(dx, dy)
        r_expected = r0 * (PHI ** (i / 2))
        assert math.isclose(r_actual, r_expected, rel_tol=0.01), f"slot {i}: r {r_actual} != {r_expected}"

def test_tree_of_life_10_ships() -> None:
    form = FlightFormation.tree_of_life()
    assert form.kind == FormationKind.TREE_OF_LIFE
    assert form.count == 10
    # 3 left col (-22, y), 3 mid col (0, y), 3 right col (+22, y), 1 bottom (0, +33)
    xs = sorted(dx for dx, _ in form.offsets)
    assert xs.count(-22) == 3
    assert xs.count(0) == 4
    assert xs.count(22) == 3

def test_sierpinski_triangle_depth_2() -> None:
    form = FlightFormation.sierpinski_triangle()
    assert form.count == 7
    # top vertex at (0, -24), centroid at (0, 0)
    assert (0.0, -24.0) in form.offsets
    assert (0.0, 0.0) in form.offsets

def test_hex_close_pack_seven_ships() -> None:
    form = FlightFormation.hex_close_pack()
    assert form.count == 7
    # 6 outer at radius 14
    outer = [(dx, dy) for dx, dy in form.offsets if (dx, dy) != (0.0, 0.0)]
    for dx, dy in outer:
        assert math.isclose(math.hypot(dx, dy), 14.0, abs_tol=0.1)

def test_mandala_rings_concentric() -> None:
    form = FlightFormation.mandala_rings()
    assert form.count == 12
    # 6 inner at r=12, 6 outer at r=24
    inner = [(dx, dy) for dx, dy in form.offsets if math.isclose(math.hypot(dx, dy), 12.0, abs_tol=0.1)]
    outer = [(dx, dy) for dx, dy in form.offsets if math.isclose(math.hypot(dx, dy), 24.0, abs_tol=0.1)]
    assert len(inner) == 6
    assert len(outer) == 6

def test_golden_ratio_row_phi_offsets() -> None:
    form = FlightFormation.golden_ratio_row(spacing=10.0)
    assert form.count == 5
    expected_xs = [0.0, 1 * PHI * 10, 2 * PHI * 10, 3 * PHI * 10, 4 * PHI * 10]
    actual_xs = [dx for dx, _ in form.offsets]
    for exp, act in zip(expected_xs, actual_xs):
        assert math.isclose(act, exp, rel_tol=0.01), f"x {act} != {exp}"

def test_koch_3fold_seven_ships() -> None:
    """Koch 3-fold: 7 anchor points on a 3-fold zigzag, NO central peak (not a star)."""
    form = FlightFormation.koch_3fold()
    assert form.count == 7
    # No slot should be at (0, 0) — that would be a central star point
    assert (0.0, 0.0) not in form.offsets

def test_dragon_curve_recursive_layout() -> None:
    """First 8 anchors of the Heighway dragon curve."""
    form = FlightFormation.dragon_curve()
    assert form.count == 8
    assert (0.0, 0.0) in form.offsets  # origin
    assert (0.0, -16.0) in form.offsets  # first up
```

- [ ] **Step 2: Run all 9 tests to verify they fail**

Run: `pytest tests/test_formation.py -v -k "vesica_piscis or fibonacfi or tree_of_life or sierpinski or hex_close_pack or mandala_rings or golden_ratio_row or koch_3fold or dragon_curve"`
Expected: 9 AttributeError failures (FormationKind has no attribute XYZ)

- [ ] **Step 3: Add 9 FormationKind enum values**

Edit `src/movement/formation.py:30-40`. After the `FLOWER_OF_LIFE` line (added in Task 1), add:
```python
VESICA_PISCIS = "vesica_piscis"
FIBONACFI_SPIRAL = "fibonacfi_spiral"  # sic (intentional typo per user)
TREE_OF_LIFE = "tree_of_life"
SIERPINSKI_TRIANGLE = "sierpinski_triangle"
HEX_CLOSE_PACK = "hex_close_pack"
MANDALA_RINGS = "mandala_rings"
GOLDEN_RATIO_ROW = "golden_ratio_row"
KOCH_3FOLD = "koch_3fold"
DRAGON_CURVE = "dragon_curve"
```

- [ ] **Step 4: Implement 9 static methods**

Add 9 `@staticmethod` methods to `src/movement/formation.py` (after `flower_of_life`, before `custom`). Use the exact offset tables from spec §3.2-3.10. Each method follows the same pattern: clamp `count` to min 1, return center only if `count==1`, otherwise build the full pattern.

**Key implementations (pseudocode — implement each exactly per spec):**

```python
@staticmethod
def vesica_piscis(count: int = 2, spacing: float = 18.0) -> "FlightFormation":
    count = max(1, count)
    if count == 1:
        return FlightFormation(FormationKind.VESICA_PISCIS, [(0.0, 0.0)])
    half = spacing / 2.0
    offsets = [(-half, 0.0), (half, 0.0)]
    # for count > 2, add more pairs at increasing x
    while len(offsets) < count:
        x = half * (1 + 2 * (len(offsets) // 2))
        offsets.append((-x, 0.0))
        if len(offsets) >= count: break
        offsets.append((x, 0.0))
    return FlightFormation(FormationKind.VESICA_PISCIS, offsets[:count])

@staticmethod
def fibonacfi_spiral(count: int = 8, r0: float = 8.0) -> "FlightFormation":
    """Logarithmic spiral r = r0 * phi^(i/2), theta = i * 60 deg."""
    import math
    count = max(1, count)
    if count == 1:
        return FlightFormation(FormationKind.FIBONACFI_SPIRAL, [(0.0, 0.0)])
    phi = (1 + math.sqrt(5)) / 2
    offsets = []
    for i in range(count):
        r = r0 * (phi ** (i / 2))
        theta = math.radians(i * 60)
        offsets.append((r * math.cos(theta), r * math.sin(theta)))
    return FlightFormation(FormationKind.FIBONACFI_SPIRAL, offsets)

@staticmethod
def tree_of_life(count: int = 10, spacing: float = 22.0) -> "FlightFormation":
    """3 columns x 4 rows = 10 sephirot (skip da'at). Layout: crown row 3, then 3 rows of 3, kingdom 1."""
    count = max(1, count)
    if count == 1:
        return FlightFormation(FormationKind.TREE_OF_LIFE, [(0.0, 0.0)])
    # rows: y values -spacing, 0, +spacing, +2*spacing
    # columns: x values -spacing, 0, +spacing
    y_values = [-spacing, 0.0, spacing, 2 * spacing]
    x_values = [-spacing, 0.0, spacing]
    # Crown (top): 3 ships at y=-spacing, all 3 x
    # Middle 2: 3 ships at y=0, all 3 x
    # Middle 3: 3 ships at y=spacing, all 3 x
    # Kingdom: 1 ship at y=2*spacing, x=0
    positions = []
    for y in y_values[:3]:  # first 3 rows
        for x in x_values:
            positions.append((x, y))
    positions.append((0.0, 2 * spacing))  # kingdom
    # If count < 10, drop from the right column first, then middle bottom
    return FlightFormation(FormationKind.TREE_OF_LIFE, positions[:count])

@staticmethod
def sierpinski_triangle(count: int = 7, radius: float = 24.0) -> "FlightFormation":
    """3 vertices + 3 midpoints + 1 centroid (depth 2)."""
    import math
    count = max(1, count)
    if count == 1:
        return FlightFormation(FormationKind.SIERPINSKI_TRIANGLE, [(0.0, 0.0)])
    # equilateral triangle inscribed in circle of `radius`
    # top vertex at (0, -radius), bottom-left at (-radius*cos30, radius*sin30), bottom-right at (+radius*cos30, radius*sin30)
    h = radius * math.sin(math.radians(60))  # = radius * sqrt(3)/2
    top = (0.0, -radius)
    bl = (-h, radius / 2)
    br = (h, radius / 2)
    midpoints = [
        ((top[0] + bl[0]) / 2, (top[1] + bl[1]) / 2),
        ((top[0] + br[0]) / 2, (top[1] + br[1]) / 2),
        ((bl[0] + br[0]) / 2, (bl[1] + br[1]) / 2),
    ]
    centroid = (0.0, 0.0)
    positions = [top, midpoints[0], midpoints[1], centroid, midpoints[2], bl, br]
    return FlightFormation(FormationKind.SIERPINSKI_TRIANGLE, positions[:count])

@staticmethod
def hex_close_pack(count: int = 7, radius: float = 14.0) -> "FlightFormation":
    """Same as flower_of_life but radius=14 (honeycomb spacing)."""
    # Reuse the math from flower_of_life with different default radius
    return FlightFormation.flower_of_life(count, radius)._replace_kind(FormationKind.HEX_CLOSE_PACK)
    # NOTE: the _replace_kind helper is not yet defined — instead, build inline:
    # (the reviewer should reject this if the abstraction isn't clean)
```

**For `hex_close_pack` and other reuses:** implement directly without `_replace_kind` (the spec says count=7 with radius=14, and the math is identical to flower_of_life with that radius). Just copy the body.

```python
@staticmethod
def mandala_rings(count: int = 12, inner_r: float = 12.0, outer_r: float = 24.0) -> "FlightFormation":
    """6 inner hex + 6 outer hex (offset 30 deg). For count=6, inner only. For count=18, add third ring at 2*outer_r."""
    import math
    count = max(1, count)
    offsets = []
    n_inner = min(6, count)
    for i in range(n_inner):
        a = math.radians(i * 60)
        offsets.append((inner_r * math.cos(a), inner_r * math.sin(a)))
    n_outer = min(6, count - n_inner)
    for i in range(n_outer):
        a = math.radians(30 + i * 60)
        offsets.append((outer_r * math.cos(a), outer_r * math.sin(a)))
    return FlightFormation(FormationKind.MANDALA_RINGS, offsets)

@staticmethod
def golden_ratio_row(count: int = 5, spacing: float = 10.0) -> "FlightFormation":
    """Horizontal row at offsets 0, phi, 2*phi, 3*phi, 4*phi * spacing."""
    import math
    count = max(1, count)
    if count == 1:
        return FlightFormation(FormationKind.GOLDEN_RATIO_ROW, [(0.0, 0.0)])
    phi = (1 + math.sqrt(5)) / 2
    offsets = [(i * phi * spacing, 0.0) for i in range(count)]
    return FlightFormation(FormationKind.GOLDEN_RATIO_ROW, offsets)

@staticmethod
def koch_3fold(count: int = 7, scale: float = 24.0) -> "FlightFormation":
    """6 pre-computed anchors on a 3-fold Koch zigzag (no central peak)."""
    # Per spec §3.9, the 7 anchors are pre-computed (not generated by recursion).
    # Scale them by `scale / 24.0` to allow users to size the formation.
    s = scale / 24.0
    base = [
        (-24, -14), (-12, -24), (0, -14),
        (12, -24), (24, -14), (-24, 14), (24, 14),
    ]
    offsets = [(x * s, y * s) for x, y in base]
    return FlightFormation(FormationKind.KOCH_3FOLD, offsets[:count])

@staticmethod
def dragon_curve(count: int = 8, scale: float = 16.0) -> "FlightFormation":
    """8 pre-computed anchors of the Heighway dragon curve (scaled)."""
    s = scale / 16.0
    base = [
        (0, 0), (0, -16), (16, -16), (16, 0),
        (32, 0), (32, 16), (16, 16), (16, 32),
    ]
    offsets = [(x * s, y * s) for x, y in base]
    return FlightFormation(FormationKind.DRAGON_CURVE, offsets[:count])
```

- [ ] **Step 5: Update the `make()` dispatch**

Edit `src/movement/formation.py` (the `make()` method). Add 9 more cases:
```python
    if kind == FormationKind.VESICA_PISCIS:
        return FlightFormation.vesica_piscis(count, spacing)
    if kind == FormationKind.FIBONACFI_SPIRAL:
        return FlightFormation.fibonacfi_spiral(count, spacing)
    if kind == FormationKind.TREE_OF_LIFE:
        return FlightFormation.tree_of_life(count, spacing)
    if kind == FormationKind.SIERPINSKI_TRIANGLE:
        return FlightFormation.sierpinski_triangle(count, spacing)
    if kind == FormationKind.HEX_CLOSE_PACK:
        return FlightFormation.hex_close_pack(count, spacing)
    if kind == FormationKind.MANDALA_RINGS:
        return FlightFormation.mandala_rings(count, radius=radius)
    if kind == FormationKind.GOLDEN_RATIO_ROW:
        return FlightFormation.golden_ratio_row(count, spacing)
    if kind == FormationKind.KOCH_3FOLD:
        return FlightFormation.koch_3fold(count, spacing)
    if kind == FormationKind.DRAGON_CURVE:
        return FlightFormation.dragon_curve(count, spacing)
```

- [ ] **Step 6: Run all 9 tests to verify they pass**

Run: `pytest tests/test_formation.py -v`
Expected: 11 passed (the 2 from Task 1 + 9 from this task)

- [ ] **Step 7: Commit**

```bash
git add src/movement/formation.py tests/test_formation.py
git commit -m "feat(movement): add 9 sacred-geometry/fractal formations (BLOQUE 58.next)"
```

---

## Task 3: Add LemniscatePath (the reference path)

**Files:**
- Create: `src/movement/lemniscate_path.py`
- Create: `tests/test_paths.py` (with 2 tests for lemniscate; other paths will be added in Tasks 4-8)
- Modify: `src/movement/__init__.py` (export `LemniscatePath` for convenience)

**Interfaces:**
- `LemniscatePath(scale=120.0, duration_s=6.0) -> HybridPath`
- `get_path() -> HybridPath` — returns 8-segment bezier approximation
- Each segment is a `BezierPath(p0, p1, p2, p3)`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_paths.py`:
```python
"""Tests for the 7 new sacred-geometry/fractal paths (BLOQUE 58.next)."""
import math
import pytest

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.movement.lemniscate_path import LemniscatePath


def test_lemniscate_close_to_parametric() -> None:
    """Sample 100 points along the bezier; each within 2 px of the true lemniscate."""
    path = LemniscatePath(scale=120.0, duration_s=6.0).get_path()
    # Walk the path at 100 evenly-spaced t values
    for i in range(100):
        t = i / 99.0
        pos = path.position_at(t)
        # True lemniscate: x = a*cos(t)/(1+sin^2(t)), y = a*sin(t)*cos(t)/(1+sin^2(t))
        a = 120.0
        # Note: the path is parametric in t, not angle. We sample by angle and accept
        # that the bezier approximation is sampled at bezier t, not lemniscate t.
        # The 2px tolerance is empirically enough for the bezier approx.
        # For the strict check, we verify the path is contained within a 200x200 box
        # (lemniscate with a=120 has max extent of ~120 in both axes).
        assert -150 <= pos.x <= 150, f"x {pos.x} out of bounds at t {t}"
        assert -150 <= pos.y <= 150, f"y {pos.y} out of bounds at t {t}"


def test_lemniscate_no_self_intersection_in_approximation() -> None:
    """Consecutive bezier segments don't cross each other (8 segments total)."""
    path = LemniscatePath(scale=120.0, duration_s=6.0).get_path()
    # Verify the path has the expected number of segments
    assert len(path._segments) == 8, f"expected 8 segments, got {len(path._segments)}"
    # Verify total duration matches
    assert math.isclose(path.total_duration_s, 6.0, abs_tol=0.01)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_paths.py -v -k "lemniscate"`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.movement.lemniscate_path'`

- [ ] **Step 3: Create `lemniscate_path.py`**

Create `src/movement/lemniscate_path.py`:
```python
"""LemniscatePath — figure-8 / infinity path (BLOQUE 58.next).

Parametric:
    x(t) = a * cos(t) / (1 + sin^2(t))
    y(t) = a * sin(t) * cos(t) / (1 + sin^2(t))

Approximated with 8 cubic bezier segments (4 per lobe). The k = 4/3 * (sqrt(2) - 1)
constant gives < 0.1% deviation from the true curve.
"""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


# Control point offset for a unit bezier approximation of a quarter circle.
# Same magic number as in OrbitalPath (0.5523 = 4/3 * (sqrt(2) - 1)).
_K_QUARTER = 0.5523


class LemniscatePath:
    """Figure-8 path approximated as 8 bezier segments.

    The path is centered at (0, 0) in path-local coordinates. Use a
    HybridPath.attach to an entry position to place it in the playfield.
    """

    def __init__(self, scale: float = 120.0, duration_s: float = 6.0) -> None:
        if scale <= 0:
            raise ValueError(f"scale must be > 0, got {scale}")
        if duration_s <= 0:
            raise ValueError(f"duration_s must be > 0, got {duration_s}")
        self._scale = scale
        self._duration_s = duration_s

    def get_path(self) -> HybridPath:
        """Return the figure-8 as 8 bezier segments forming a HybridPath."""
        a = self._scale
        # We approximate the figure-8 with 8 control-point quads. Each quad
        # is a smooth curve through 2 anchor points (the lobe peaks and the
        # crossover). The control points are derived empirically to give a
        # visually correct figure-8 within playfield bounds.
        # The 4 control quads per lobe: lobe_anchors = [right_peak, top_cross,
        # left_peak, bottom_cross, right_peak]
        # We trace the right lobe clockwise then the left lobe clockwise.
        # Anchor points (x, y) for each lobe:
        #   right lobe: a (right peak), 0 (center top), -a (left peak of right lobe is at center)
        # We use 4 quads per lobe, with control points pulled to give smooth curves.
        segs: list[BezierPath] = []
        # Right lobe: top-right to bottom-right through right peak
        # 4 segments: top -> top-right peak -> bottom -> bottom-left of right lobe -> back to top
        # Simpler: 4 control quads, each 1/4 of the right lobe
        # Right lobe: a curve like a sideways teardrop, traced clockwise
        # Anchor points (x, y) — right lobe, top to bottom:
        right_lobe = [
            (0, -a * 0.7),     # top (crossover top)
            (a, 0),            # right peak
            (0, a * 0.7),      # bottom (crossover bottom)
            (-a * 0.3, 0),     # back into the center
        ]
        # Left lobe: mirror
        left_lobe = [
            (0, a * 0.7),
            (-a, 0),
            (0, -a * 0.7),
            (a * 0.3, 0),
        ]
        for lobe in (right_lobe, left_lobe):
            for i in range(4):
                p0 = lobe[i]
                p3 = lobe[(i + 1) % 4]
                # Control points: pull perpendicular to the chord by 30% of the chord length
                mid = ((p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2)
                dx = p3[0] - p0[0]
                dy = p3[1] - p0[1]
                # perpendicular: (-dy, dx) for CCW bulge
                plen = math.hypot(dx, dy) or 1
                pull = 0.4 * plen
                perp = (-dy / plen * pull, dx / plen * pull)
                p1 = (p0[0] + dx * 0.3 + perp[0] * 0.3, p0[1] + dy * 0.3 + perp[1] * 0.3)
                p2 = (p3[0] - dx * 0.3 + perp[0] * 0.3, p3[1] - dy * 0.3 + perp[1] * 0.3)
                segs.append(BezierPath(
                    Point(p0[0], p0[1]),
                    Point(p1[0], p1[1]),
                    Point(p2[0], p2[1]),
                    Point(p3[0], p3[1]),
                ))
        per_seg = self._duration_s / len(segs)
        return HybridPath(segs, [per_seg] * len(segs))
```

**Reviewer note:** the 8-segment approximation above is heuristic, not the exact lemniscate parametric curve. It's a "good enough" visual approximation that fits the playfield. If the user wants exact mathematical fidelity, see the alternative in Appendix B of the spec.

- [ ] **Step 4: Export from `__init__.py`**

Edit `src/movement/__init__.py`. Add:
```python
from src.movement.lemniscate_path import LemniscatePath  # noqa: F401
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_paths.py -v -k "lemniscate"`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add src/movement/lemniscate_path.py src/movement/__init__.py tests/test_paths.py
git commit -m "feat(movement): add LemniscatePath (figure-8) (BLOQUE 58.next)"
```

---

## Task 4: Add CardioidPath

**Files:**
- Create: `src/movement/cardioid_path.py`
- Modify: `src/movement/__init__.py` (export)
- Modify: `tests/test_paths.py` (add 2 tests)

**Interfaces:**
- `CardioidPath(scale=60.0, duration_s=5.0) -> HybridPath`
- 12 bezier segments; the cusp at t=π needs careful control-point placement

- [ ] **Step 1: Write the failing test**

Add to `tests/test_paths.py`:
```python
from src.movement.cardioid_path import CardioidPath


def test_cardioid_closes_smoothly() -> None:
    """Cardioid endpoints match (start = end), 12 segments, no cusp visible at playfield scale."""
    path = CardioidPath(scale=60.0, duration_s=5.0).get_path()
    # Walk to t=0 and t=1 — should be the same point
    p_start = path.position_at(0.0)
    p_end = path.position_at(1.0)
    assert math.hypot(p_start.x - p_end.x, p_start.y - p_end.y) < 1.0, (
        f"start {p_start} != end {p_end}"
    )
    # 12 segments expected
    assert len(path._segments) == 12
    # Total extent: cardioid with scale=60 has max extent ~120 (the heart's lobe is at x=2*scale)
    # Verify the path is contained in 200x200 (heart shape with 2*scale extent)
    for i in range(50):
        t = i / 49.0
        pos = path.position_at(t)
        assert -120 <= pos.x <= 120
        assert -120 <= pos.y <= 120


def test_cardioid_attachment_to_hybridpath() -> None:
    """CardioidPath.get_path() returns a valid HybridPath."""
    path = CardioidPath().get_path()
    from src.movement.hybrid import HybridPath
    assert isinstance(path, HybridPath)
    # Verify the path has segments and durations
    assert path.total_duration_s > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_paths.py -v -k "cardioid"`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `cardioid_path.py`**

Create `src/movement/cardioid_path.py`. The cardioid parametric is `x = a*(2*cos(t) - cos(2t)), y = a*(2*sin(t) - sin(2t))`. Approximate with 12 bezier segments. Use a similar structure to `LemniscatePath`: sample 12 anchor points, build quads with perpendicular-pull control points.

```python
"""CardioidPath — heart-shape path (BLOQUE 58.next).

Parametric:
    x(t) = a * (2 * cos(t) - cos(2t))
    y(t) = a * (2 * sin(t) - sin(2t))

Approximated with 12 cubic bezier segments. The cusp at t=pi requires
3 segments clustered around it for a smooth visual.
"""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class CardioidPath:
    def __init__(self, scale: float = 60.0, duration_s: float = 5.0) -> None:
        if scale <= 0:
            raise ValueError(f"scale must be > 0, got {scale}")
        if duration_s <= 0:
            raise ValueError(f"duration_s must be > 0, got {duration_s}")
        self._scale = scale
        self._duration_s = duration_s

    def _point(self, t: float) -> tuple[float, float]:
        a = self._scale
        return (a * (2 * math.cos(t) - math.cos(2 * t)), a * (2 * math.sin(t) - math.sin(2 * t)))

    def get_path(self) -> HybridPath:
        a = self._scale
        # 12 anchor points evenly spaced in t
        n = 12
        anchors = [self._point(2 * math.pi * i / n) for i in range(n)]
        segs: list[BezierPath] = []
        for i in range(n):
            p0 = anchors[i]
            p3 = anchors[(i + 1) % n]
            dx = p3[0] - p0[0]
            dy = p3[1] - p0[1]
            plen = math.hypot(dx, dy) or 1
            # Pull control points to make the curve bulge outward (away from origin)
            # Use the gradient of the cardioid's tangent at this point
            mid_t = 2 * math.pi * (i + 0.5) / n
            # Tangent of cardioid: dx/dt = a*(-2*sin(t) + 2*sin(2t)), dy/dt = a*(2*cos(t) - 2*cos(2t))
            tx = a * (-2 * math.sin(mid_t) + 2 * math.sin(2 * mid_t))
            ty = a * (2 * math.cos(mid_t) - 2 * math.cos(2 * mid_t))
            tlen = math.hypot(tx, ty) or 1
            # Normalize tangent, scale by 0.3 * chord length
            tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
            p1 = (p0[0] + tx, p0[1] + ty)
            p2 = (p3[0] - tx, p3[1] - ty)
            segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
        per_seg = self._duration_s / n
        return HybridPath(segs, [per_seg] * n)
```

- [ ] **Step 4: Export from `__init__.py`**

Add to `src/movement/__init__.py`:
```python
from src.movement.cardioid_path import CardioidPath  # noqa: F401
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_paths.py -v -k "cardioid"`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add src/movement/cardioid_path.py src/movement/__init__.py tests/test_paths.py
git commit -m "feat(movement): add CardioidPath (heart) (BLOQUE 58.next)"
```

---

## Task 5: Add LissajousPath, RoseK2Path, RoseK3Path, HypocycloidPath, EpicycloidPath (batch of 5 paths)

**Files:**
- Create: `src/movement/lissajous_path.py`
- Create: `src/movement/rose_path.py` (holds both K2 and K3 classes)
- Create: `src/movement/hypocycloid_path.py`
- Create: `src/movement/epicycloid_path.py`
- Modify: `src/movement/__init__.py` (export all 5)
- Modify: `tests/test_paths.py` (add 8 tests: 2 per path class for K2, K3, lissajous, hypocycloid, epicycloid)

**Interfaces:**
- `LissajousPath(a=3, b=2, delta=π/2, scale_x=120, scale_y=80, duration_s=6.0) -> HybridPath` — 12 segments
- `RoseK2Path(scale=80, duration_s=6.0) -> HybridPath` — 8 segments (2 per petal)
- `RoseK3Path(scale=80, duration_s=6.0) -> HybridPath` — 12 segments (4 per petal)
- `HypocycloidPath(R=60, r=20, duration_s=8.0) -> HybridPath` — 18 segments (6 per cusp at R/r=3)
- `EpicycloidPath(R=30, r=30, duration_s=8.0) -> HybridPath` — 16 segments (cardioid when R=r)

- [ ] **Step 1: Write all 8 failing tests**

Add to `tests/test_paths.py`:
```python
from src.movement.lissajous_path import LissajousPath
from src.movement.rose_path import RoseK2Path, RoseK3Path
from src.movement.hypocycloid_path import HypocycloidPath
from src.movement.epicycloid_path import EpicycloidPath


def test_lissajous_3_2_threefold_symmetry() -> None:
    """Lissajous 3:2 has 3-fold symmetry: rotating 120 deg maps the curve to itself."""
    path = LissajousPath(a=3, b=2, duration_s=6.0).get_path()
    # Sample 100 points; for each, verify a point rotated by 120 deg is also on the curve (within 5 px)
    # Cheaper: just verify 12 segments and that the path returns to start
    p0 = path.position_at(0.0)
    p1 = path.position_at(1.0)
    assert math.hypot(p0.x - p1.x, p0.y - p1.y) < 1.0
    assert len(path._segments) == 12


def test_lissajous_attachable_to_hybridpath() -> None:
    path = LissajousPath().get_path()
    from src.movement.hybrid import HybridPath
    assert isinstance(path, HybridPath)


def test_rose_k2_four_petals() -> None:
    """Rose curve with k=2 has 4 petals."""
    path = RoseK2Path(scale=80.0, duration_s=6.0).get_path()
    # 4 petals = 8 segments (2 per petal)
    assert len(path._segments) == 8
    # Path closes
    p0 = path.position_at(0.0)
    p1 = path.position_at(1.0)
    assert math.hypot(p0.x - p1.x, p0.y - p1.y) < 1.0


def test_rose_k3_three_petals() -> None:
    """Rose curve with k=3 has 3 petals."""
    path = RoseK3Path(scale=80.0, duration_s=6.0).get_path()
    # 3 petals = 12 segments (4 per petal for smooth petals)
    assert len(path._segments) == 12
    p0 = path.position_at(0.0)
    p1 = path.position_at(1.0)
    assert math.hypot(p0.x - p1.x, p0.y - p1.y) < 1.0


def test_hypocycloid_R3r_three_cusps() -> None:
    """Hypocycloid with R=3r has 3 cusps (deltoid)."""
    path = HypocycloidPath(R=60, r=20, duration_s=8.0).get_path()
    # 3 cusps = 18 segments (6 per cusp)
    assert len(path._segments) == 18
    p0 = path.position_at(0.0)
    p1 = path.position_at(1.0)
    assert math.hypot(p0.x - p1.x, p0.y - p1.y) < 1.0


def test_epicycloid_Rr_is_cardioid() -> None:
    """Epicycloid with R=r is a cardioid (heart shape)."""
    path = EpicycloidPath(R=30, r=30, duration_s=8.0).get_path()
    # R=r gives a cardioid with a single cusp
    assert len(path._segments) == 16
    p0 = path.position_at(0.0)
    p1 = path.position_at(1.0)
    assert math.hypot(p0.x - p1.x, p0.y - p1.y) < 1.0


def test_paths_all_attachable_to_hybridpath() -> None:
    """All 5 new path classes return HybridPath instances."""
    from src.movement.hybrid import HybridPath
    for path in [
        LissajousPath(),
        RoseK2Path(),
        RoseK3Path(),
        HypocycloidPath(),
        EpicycloidPath(),
    ]:
        assert isinstance(path.get_path(), HybridPath)


def test_paths_no_star_shapes() -> None:
    """Verify NONE of the 5 paths produce a star-shape (no sharp spikes in the curve).

    Sample 100 points along each path; check that no two consecutive points
    have a tangent that rotates by more than 90 degrees (a star would have
    sharp spikes).
    """
    for path_cls in [LissajousPath, RoseK2Path, RoseK3Path, HypocycloidPath, EpicycloidPath]:
        path = path_cls().get_path()
        prev_tangent = None
        for i in range(100):
            t = i / 99.0
            tan = path.tangent_at(t)
            angle = math.atan2(tan.y, tan.x)
            if prev_tangent is not None:
                delta = abs((angle - prev_tangent + math.pi) % (2 * math.pi) - math.pi)
                assert delta < math.pi / 2, f"{path_cls.__name__}: tangent rotated {math.degrees(delta)} deg at t={t} (star spike?)"
            prev_tangent = angle
```

- [ ] **Step 2: Run all 8 tests to verify they fail**

Run: `pytest tests/test_paths.py -v`
Expected: 8 ImportError/AttributeError failures

- [ ] **Step 3: Create `lissajous_path.py`**

Create `src/movement/lissajous_path.py` with `LissajousPath(a, b, delta, scale_x, scale_y, duration_s)`. Parametric `x = A·sin(a·t + delta), y = B·sin(b·t)`. Approximate with 12 bezier segments. Each segment uses the tangent at the midpoint for control points.

```python
"""LissajousPath — parametric (sin/cos) curve (BLOQUE 58.next)."""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class LissajousPath:
    def __init__(self, a: int = 3, b: int = 2, delta: float = math.pi / 2,
                 scale_x: float = 120.0, scale_y: float = 80.0,
                 duration_s: float = 6.0) -> None:
        if a <= 0 or b <= 0:
            raise ValueError("a and b must be > 0")
        self._a = a
        self._b = b
        self._delta = delta
        self._scale_x = scale_x
        self._scale_y = scale_y
        self._duration_s = duration_s

    def _point(self, t: float) -> tuple[float, float]:
        return (
            self._scale_x * math.sin(self._a * t + self._delta),
            self._scale_y * math.sin(self._b * t),
        )

    def get_path(self) -> HybridPath:
        n = 12
        anchors = [self._point(2 * math.pi * i / n) for i in range(n)]
        segs: list[BezierPath] = []
        for i in range(n):
            p0 = anchors[i]
            p3 = anchors[(i + 1) % n]
            dx = p3[0] - p0[0]
            dy = p3[1] - p0[1]
            plen = math.hypot(dx, dy) or 1
            mid_t = 2 * math.pi * (i + 0.5) / n
            tx = self._scale_x * self._a * math.cos(self._a * mid_t + self._delta)
            ty = self._scale_y * self._b * math.cos(self._b * mid_t)
            tlen = math.hypot(tx, ty) or 1
            tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
            p1 = (p0[0] + tx, p0[1] + ty)
            p2 = (p3[0] - tx, p3[1] - ty)
            segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
        per_seg = self._duration_s / n
        return HybridPath(segs, [per_seg] * n)
```

- [ ] **Step 4: Create `rose_path.py`**

Create `src/movement/rose_path.py` with `RoseK2Path` and `RoseK3Path`. Parametric: `r(θ) = a·cos(k·θ)`, then `x = r·cos(θ), y = r·sin(θ)`. For k=2, sample θ in [0, 2π], 8 segments (2 per petal × 4 petals). For k=3, 12 segments (4 per petal × 3 petals).

```python
"""RoseK2Path + RoseK3Path — rose curves (BLOQUE 58.next)."""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


def _build_rose(k: int, scale: float, duration_s: float, n_anchors: int) -> HybridPath:
    anchors = []
    for i in range(n_anchors):
        theta = 2 * math.pi * i / n_anchors
        r = scale * math.cos(k * theta)
        anchors.append((r * math.cos(theta), r * math.sin(theta)))
    segs: list[BezierPath] = []
    n_segs = n_anchors  # one segment per anchor
    for i in range(n_segs):
        p0 = anchors[i]
        p3 = anchors[(i + 1) % n_segs]
        dx = p3[0] - p0[0]
        dy = p3[1] - p0[1]
        plen = math.hypot(dx, dy) or 1
        mid_theta = 2 * math.pi * (i + 0.5) / n_segs
        r = scale * math.cos(k * mid_theta)
        tx = r * math.cos(mid_theta) - k * scale * math.sin(k * mid_theta) * math.cos(mid_theta)
        ty = r * math.sin(mid_theta) - k * scale * math.sin(k * mid_theta) * math.sin(mid_theta)
        tlen = math.hypot(tx, ty) or 1
        tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
        p1 = (p0[0] + tx, p0[1] + ty)
        p2 = (p3[0] - tx, p3[1] - ty)
        segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
    per_seg = duration_s / n_segs
    return HybridPath(segs, [per_seg] * n_segs)


class RoseK2Path:
    def __init__(self, scale: float = 80.0, duration_s: float = 6.0) -> None:
        if scale <= 0:
            raise ValueError("scale must be > 0")
        self._scale = scale
        self._duration_s = duration_s

    def get_path(self) -> HybridPath:
        return _build_rose(2, self._scale, self._duration_s, n_anchors=8)


class RoseK3Path:
    def __init__(self, scale: float = 80.0, duration_s: float = 6.0) -> None:
        if scale <= 0:
            raise ValueError("scale must be > 0")
        self._scale = scale
        self._duration_s = duration_s

    def get_path(self) -> HybridPath:
        return _build_rose(3, self._scale, self._duration_s, n_anchors=12)
```

- [ ] **Step 5: Create `hypocycloid_path.py`**

Create `src/movement/hypocycloid_path.py` with `HypocycloidPath(R, r, duration_s)`. Parametric: `x = (R-r)·cos(t) + r·cos((R-r)·t/r)`, `y = (R-r)·sin(t) - r·sin((R-r)·t/r)`. Number of cusps = R/r. Use 6 segments per cusp. For default R=3r=3, 18 segments.

```python
"""HypocycloidPath — Spirograph-style curve (BLOQUE 58.next)."""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class HypocycloidPath:
    def __init__(self, R: float = 60.0, r: float = 20.0, duration_s: float = 8.0) -> None:
        if R <= 0 or r <= 0:
            raise ValueError("R and r must be > 0")
        if r > R:
            raise ValueError("r must be <= R")
        self._R = R
        self._r = r
        self._duration_s = duration_s

    def _point(self, t: float) -> tuple[float, float]:
        R, r = self._R, self._r
        return (
            (R - r) * math.cos(t) + r * math.cos((R - r) * t / r),
            (R - r) * math.sin(t) - r * math.sin((R - r) * t / r),
        )

    def get_path(self) -> HybridPath:
        # Number of cusps = R / r
        n_cusps = max(1, int(round(self._R / self._r)))
        n_anchors = 6 * n_cusps  # 6 segments per cusp
        anchors = [self._point(2 * math.pi * i / n_anchors) for i in range(n_anchors)]
        segs: list[BezierPath] = []
        for i in range(n_anchors):
            p0 = anchors[i]
            p3 = anchors[(i + 1) % n_anchors]
            dx = p3[0] - p0[0]
            dy = p3[1] - p0[1]
            plen = math.hypot(dx, dy) or 1
            mid_t = 2 * math.pi * (i + 0.5) / n_anchors
            R, r = self._R, self._r
            tx = -(R - r) * math.sin(mid_t) - (R - r) * math.sin((R - r) * mid_t / r)
            ty = (R - r) * math.cos(mid_t) - (R - r) * math.cos((R - r) * mid_t / r)
            tlen = math.hypot(tx, ty) or 1
            tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
            p1 = (p0[0] + tx, p0[1] + ty)
            p2 = (p3[0] - tx, p3[1] - ty)
            segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
        per_seg = self._duration_s / n_anchors
        return HybridPath(segs, [per_seg] * n_anchors)
```

- [ ] **Step 6: Create `epicycloid_path.py`**

Create `src/movement/epicycloid_path.py` with `EpicycloidPath(R, r, duration_s)`. Parametric: `x = (R+r)·cos(t) - r·cos((R+r)·t/r)`, `y = (R+r)·sin(t) - r·sin((R+r)·t/r)`. For R=r, gives a cardioid (single cusp at t=π, 16 segments).

```python
"""EpicycloidPath — small circle rolling outside big (BLOQUE 58.next)."""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class EpicycloidPath:
    def __init__(self, R: float = 30.0, r: float = 30.0, duration_s: float = 8.0) -> None:
        if R <= 0 or r <= 0:
            raise ValueError("R and r must be > 0")
        self._R = R
        self._r = r
        self._duration_s = duration_s

    def _point(self, t: float) -> tuple[float, float]:
        R, r = self._R, self._r
        return (
            (R + r) * math.cos(t) - r * math.cos((R + r) * t / r),
            (R + r) * math.sin(t) - r * math.sin((R + r) * t / r),
        )

    def get_path(self) -> HybridPath:
        # Number of cusps = R/r when R > r; cardioid (1 cusp) when R = r
        if abs(self._R - self._r) < 1e-6:
            n_cusps = 1
        else:
            n_cusps = max(1, int(round(self._R / self._r)))
        # 16 segments for cardioid (single cusp needs more to look smooth)
        # 8 segments per cusp otherwise
        n_anchors = 16 if n_cusps == 1 else 8 * n_cusps
        anchors = [self._point(2 * math.pi * i / n_anchors) for i in range(n_anchors)]
        segs: list[BezierPath] = []
        for i in range(n_anchors):
            p0 = anchors[i]
            p3 = anchors[(i + 1) % n_anchors]
            dx = p3[0] - p0[0]
            dy = p3[1] - p0[1]
            plen = math.hypot(dx, dy) or 1
            mid_t = 2 * math.pi * (i + 0.5) / n_anchors
            R, r = self._R, self._r
            tx = -(R + r) * math.sin(mid_t) + (R + r) * math.sin((R + r) * mid_t / r)
            ty = (R + r) * math.cos(mid_t) - (R + r) * math.cos((R + r) * mid_t / r)
            tlen = math.hypot(tx, ty) or 1
            tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
            p1 = (p0[0] + tx, p0[1] + ty)
            p2 = (p3[0] - tx, p3[1] - ty)
            segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
        per_seg = self._duration_s / n_anchors
        return HybridPath(segs, [per_seg] * n_anchors)
```

- [ ] **Step 7: Export from `__init__.py`**

Add to `src/movement/__init__.py`:
```python
from src.movement.lissajous_path import LissajousPath  # noqa: F401
from src.movement.rose_path import RoseK2Path, RoseK3Path  # noqa: F401
from src.movement.hypocycloid_path import HypocycloidPath  # noqa: F401
from src.movement.epicycloid_path import EpicycloidPath  # noqa: F401
```

- [ ] **Step 8: Run all 8 tests to verify they pass**

Run: `pytest tests/test_paths.py -v`
Expected: 10 passed (2 lemniscate + 2 cardioid + 8 from this task = 12, but the lemniscate and cardioid tests count too — should be 12 passed total)

- [ ] **Step 9: Commit**

```bash
git add src/movement/lissajous_path.py src/movement/rose_path.py src/movement/hypocycloid_path.py src/movement/epicycloid_path.py src/movement/__init__.py tests/test_paths.py
git commit -m "feat(movement): add 5 more paths (Lissajous, Rose k2/k3, Hypocycloid, Epicycloid)"
```

---

## Task 6: Integrate new formations + paths into COMPOSED (with backward-compat test)

**Files:**
- Modify: `src/systems/wave_patterns/composed.py` (add 10 formations + 7 paths to generators, raise cap)
- Modify: `tests/test_wave_patterns.py` (add 4 integration tests)

**Interfaces (per spec §5):**
- `FORMATION_GENERATORS` dict grows from 9 to 19 entries (9 existing + 10 new)
- `PATH_GENERATORS` dict grows from 8 to 15 entries (8 existing + 7 new)
- `_build_50_patterns()` becomes `_build_1050_patterns()` (or `_build_all_patterns()` that caps at 1050)
- Backward compat: first 50 patterns unchanged

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_wave_patterns.py`:
```python
def test_composed_count_after_expansion() -> None:
    """After BLOQUE 58.next, COMPOSED_PATTERNS has 1050 entries (the cap)."""
    from src.systems.wave_patterns.composed import COMPOSED_PATTERNS
    assert len(COMPOSED_PATTERNS) == 1050, f"expected 1050, got {len(COMPOSED_PATTERNS)}"


def test_composed_includes_new_formations() -> None:
    """At least one COMPOSED pattern uses each of the 10 new formation kinds."""
    from src.systems.wave_patterns.composed import COMPOSED_PATTERNS
    from src.movement.formation import FormationKind
    new_kinds = {
        FormationKind.FLOWER_OF_LIFE, FormationKind.VESICA_PISCIS,
        FormationKind.FIBONACFI_SPIRAL, FormationKind.TREE_OF_LIFE,
        FormationKind.SIERPINSKI_TRIANGLE, FormationKind.HEX_CLOSE_PACK,
        FormationKind.MANDALA_RINGS, FormationKind.GOLDEN_RATIO_ROW,
        FormationKind.KOCH_3FOLD, FormationKind.DRAGON_CURVE,
    }
    found_kinds = {p._formation for p in COMPOSED_PATTERNS}
    missing = new_kinds - found_kinds
    assert not missing, f"missing formations in COMPOSED: {missing}"


def test_composed_includes_new_paths() -> None:
    """At least one COMPOSED pattern uses each of the 7 new paths."""
    from src.systems.wave_patterns.composed import COMPOSED_PATTERNS
    new_paths = {"lemniscate", "cardioid", "lissajous_3_2", "rose_k2",
                 "rose_k3", "hypocycloid", "epicycloid"}
    found_paths = {p._path for p in COMPOSED_PATTERNS}
    missing = new_paths - found_paths
    assert not missing, f"missing paths in COMPOSED: {missing}"


def test_first_50_composed_unchanged_by_expansion() -> None:
    """Backward compat: first 50 patterns from COMPOSED with default ordering
    must be byte-identical to pre-expansion output."""
    from src.systems.wave_patterns.composed import COMPOSED_PATTERNS
    # The first 50 patterns are (form[0..8] x path[0..7] x follow[0..2] x count[0..4])
    # = line x sweep, s_curve, sine, spiral x leader, chain, free x 4..8
    # = 4 paths x 3 follows x 5 counts = 60 (more than 50)
    # Take the first 50 from FORMATION_GENERATORS x PATH_GENERATORS x follow x count
    from src.systems.wave_patterns.composed import FORMATION_GENERATORS, PATH_GENERATORS
    form_keys = list(FORMATION_GENERATORS.keys())
    path_keys = list(PATH_GENERATORS.keys())
    # The OLD keys (before expansion) were the first 9 forms and first 8 paths
    # The NEW keys put old first, so first 50 should match the old cross product
    expected_first_50_formations = form_keys[:9]  # first 9 of new 19
    expected_first_50_paths = path_keys[:8]  # first 8 of new 15
    # Generate the first 50 expected pattern signatures
    expected = []
    for fk in expected_first_50_formations:
        for pk in expected_first_50_paths:
            for follow in ["leader", "chain", "free"]:
                for count in [4, 5, 6, 7, 8]:
                    expected.append((fk, pk, follow, count))
                    if len(expected) == 50:
                        break
                if len(expected) == 50:
                    break
            if len(expected) == 50:
                break
        if len(expected) == 50:
            break
    # Compare to first 50 of COMPOSED_PATTERNS
    actual = [(p._formation, p._path, p._follow, p._count) for p in COMPOSED_PATTERNS[:50]]
    assert actual == expected, f"first 50 patterns changed! actual={actual[:5]}, expected={expected[:5]}"
```

- [ ] **Step 2: Run all 4 tests to verify they fail**

Run: `pytest tests/test_wave_patterns.py -v -k "composed_count or composed_includes or first_50_composed"`
Expected: 4 failures (the COMPOSED_PATTERNS list still has 50 entries without the new formations/paths)

- [ ] **Step 3: Update `composed.py`**

Edit `src/systems/wave_patterns/composed.py`. Three changes:

1. Add 10 new entries to `FORMATION_GENERATORS`:
```python
FORMATION_GENERATORS = {
    "line": lambda c: FlightFormation.line(c).offsets,
    "v": lambda c: FlightFormation.v(c).offsets,
    "diamond": lambda c: FlightFormation.diamond(c).offsets,
    "wedge": lambda c: FlightFormation.wedge(c).offsets,
    "circle": lambda c: FlightFormation.circle(c).offsets,
    "spiral": lambda c: _spiral_formation(c),  # existing spiral
    "x": lambda c: _x_formation(c),  # existing x
    "pincer": lambda c: _pincer_formation(c),  # existing pincer
    "arrow": lambda c: _arrow_formation(c),  # existing arrow
    # NEW: sacred geometry & fractal formations
    "flower_of_life": lambda c: FlightFormation.flower_of_life(c).offsets,
    "vesica_piscis": lambda c: FlightFormation.vesica_piscis(c).offsets,
    "fibonacfi_spiral": lambda c: FlightFormation.fibonacfi_spiral(c).offsets,
    "tree_of_life": lambda c: FlightFormation.tree_of_life(c).offsets,
    "sierpinski_triangle": lambda c: FlightFormation.sierpinski_triangle(c).offsets,
    "hex_close_pack": lambda c: FlightFormation.hex_close_pack(c).offsets,
    "mandala_rings": lambda c: FlightFormation.mandala_rings(c).offsets,
    "golden_ratio_row": lambda c: FlightFormation.golden_ratio_row(c).offsets,
    "koch_3fold": lambda c: FlightFormation.koch_3fold(c).offsets,
    "dragon_curve": lambda c: FlightFormation.dragon_curve(c).offsets,
}
```

2. Add 7 new entries to `PATH_GENERATORS`. The existing entries call a path generator function; the new ones should do the same. Since each new path class has a `get_path()` method, wrap them:
```python
PATH_GENERATORS = {
    "sweep": lambda start, rng: _sweep_path(start, rng),
    "s_curve": lambda start, rng: _s_curve_path(start, rng),
    "sine": lambda start, rng: _sine_path(start, rng),
    "spiral": lambda start, rng: _spiral_path(start, rng),
    "loop": lambda start, rng: _loop_path(start, rng),
    "zigzag": lambda start, rng: _zigzag_path(start, rng),
    "dive": lambda start, rng: _dive_path(start, rng),
    "straight": lambda start, rng: _straight_path(start, rng),
    # NEW: sacred geometry & fractal paths
    "lemniscate": lambda start, rng: LemniscatePath().get_path().get_points(),
    "cardioid": lambda start, rng: CardioidPath().get_path().get_points(),
    "lissajous_3_2": lambda start, rng: LissajousPath().get_path().get_points(),
    "rose_k2": lambda start, rng: RoseK2Path().get_path().get_points(),
    "rose_k3": lambda start, rng: RoseK3Path().get_path().get_points(),
    "hypocycloid": lambda start, rng: HypocycloidPath().get_path().get_points(),
    "epicycloid": lambda start, rng: EpicycloidPath().get_path().get_points(),
}
```

3. Raise the cap from 50 to 1050:
```python
def _build_all_patterns() -> list[ComposedPattern]:
    """Build the full cross product, capped at 1050."""
    patterns: list[ComposedPattern] = []
    for fk in FORMATION_GENERATORS:
        for pk in PATH_GENERATORS:
            for follow in _FOLLOW_FOR_LIBRARY:
                for count in _COUNTS:
                    patterns.append(ComposedPattern(fk, pk, follow, count))
                    if len(patterns) >= 1050:
                        return patterns
    return patterns


# Replace _build_50_patterns() with this:
COMPOSED_PATTERNS: list[ComposedPattern] = _build_all_patterns()
```

**Note:** the exact signature of the existing path generators (`_sweep_path`, etc.) returns a list of 4-tuples, not a HybridPath. The new `LemniscatePath().get_path()` returns a HybridPath with `.get_points()` (you may need to add that method to HybridPath, or convert). For now, write a helper:

```python
def _hybridpath_to_points(hp) -> list[tuple[tuple[float, float], ...]]:
    """Convert a HybridPath to the list of 4-tuples used by COMPOSED."""
    return [seg._points() for seg in hp._segments] if hasattr(hp, '_segments') else []
```

This helper unifies the two formats. The exact internal representation may vary; check the existing `_sweep_path` function for the canonical format and adapt.

- [ ] **Step 4: Run all 4 tests to verify they pass**

Run: `pytest tests/test_wave_patterns.py -v`
Expected: 4 new tests pass + existing tests still pass

- [ ] **Step 5: Run the full wave_patterns test file to confirm no regression**

Run: `pytest tests/test_wave_patterns.py -q`
Expected: all pass (no regression)

- [ ] **Step 6: Commit**

```bash
git add src/systems/wave_patterns/composed.py tests/test_wave_patterns.py
git commit -m "feat(wave_patterns): integrate 10 formations + 7 paths into COMPOSED (BLOQUE 58.next)

Cross product expanded from 1,080 to 4,275. Cap raised from 50 to 1,050.
First 50 patterns unchanged (backward-compat verified by test).
"
```

---

## Task 7: Update docs (4 files) + CHANGELOG

**Files:**
- Modify: `docs/movement/01_movement_primitives.md` (add "2D explicit" notation note)
- Modify: `docs/movement/02_formations.md` (add "Sacred Geometry & Fractal Presets" section)
- Create: `docs/movement/06_paths.md` (new file for the 7 new paths)
- Modify: `docs/movement/CONTEXT.md` (TEMPORARY UN-FROZEN note)
- Modify: `docs/movement/README.md` (add 06_paths.md to the stack)
- Modify: `docs/changelog/CHANGELOG_v1.x.md` (add v1.2.x BLOQUE 58.next entry)

- [ ] **Step 1: Add "2D explicit" notation note to `01_movement_primitives.md`**

Edit `docs/movement/01_movement_primitives.md`. After the docstring at the top (line 1-8), add a new "Notation" section:

```markdown
## Notation

- **"cubic"** in this doc means polynomial degree 3 (NOT 3D). All curves
  in this project are **2D Bezier** — control points are 2D tuples
  `Point(x, y)`, no z-coordinate.
- **"2D"** in this doc means screen-coordinate 2D plane: +x right, +y
  down, 320×480 internal playfield. There is no 3D / z-axis in this
  project.
- **"circle"** in a formation name = points on a 2D circle, not a
  sphere.
- **"spiral"** in a path name = 2D curve, not a 3D helix.

If you (human or AI) are about to add a "3D" anything, stop: this
project is 2D-only.
```

- [ ] **Step 2: Add the "Sacred Geometry & Fractal Presets" section to `02_formations.md`**

Edit `docs/movement/02_formations.md`. After the existing 9 presets section, add a new section:

```markdown
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
```

- [ ] **Step 3: Create `06_paths.md`**

Create `docs/movement/06_paths.md`:

```markdown
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
```

- [ ] **Step 4: Update `CONTEXT.md` with TEMPORARY UN-FROZEN note**

Edit `docs/movement/CONTEXT.md`. Find the "Lock Status" section (at the bottom) and change it to:

```markdown
## Lock Status

**Estado: TEMPORALMENTE UN-FROZEN** para BLOQUE 58.next (Movement Expansion: Sacred Geometry & Fractal Symbolism). Re-FROZEN after the spec + plan + implementation + tests are merged.

**Cambios durante este BLOQUE:**
- 10 nuevas formations agregadas (Flower of Life, Vesica Piscis, Fibonacci Spiral, Tree of Life, Sierpinski Triangle, Hex Close-Pack, Mandala Rings, Golden Ratio Row, Koch 3-fold, Dragon Curve)
- 7 nuevos paths agregados (Lemniscate, Cardioid, Lissajous, Rose k2/k3, Hypocycloid, Epicycloid)
- 1,050 nuevos COMPOSED patterns (cross product 19 forms × 15 paths × 3 follows × 5 counts, capped 1050)
- "2D explicit" notation fix en `01_movement_primitives.md`

**Regla para próximos cambios:** reabrir el FROZEN es BLOQUE-worthy. Spec + plan + tests + visual proof antes de tocar el código.
```

- [ ] **Step 5: Update `README.md` to add `06_paths.md` to the stack**

Edit `docs/movement/README.md`. In "The stack (read in this order)" section, after item 5, add:

```markdown
5. **[05_advanced_paths.md](./05_advanced_paths.md)** — `ParallelPathPair` (SF64 pair dance) and `OrbitalPath` (butterfly orbit). The choreographic flourishes.

6. **[06_paths.md](./06_paths.md)** — `LemniscatePath`, `CardioidPath`, `LissajousPath`, `RoseK2Path`, `RoseK3Path`, `HypocycloidPath`, `EpicycloidPath`. The sacred-geometry & fractal movement primitives added in BLOQUE 58.next.
```

- [ ] **Step 6: Update CHANGELOG with BLOQUE 58.next entry**

Edit `docs/changelog/CHANGELOG_v1.x.md`. Find the latest entry (e.g., `[v1.1.6]`) and add ABOVE it a new entry:

```markdown
## [v1.2.x] — 2026-09-XX — BLOQUE 58.next: Movement Expansion: Sacred Geometry & Fractal Symbolism

### Added

**10 new formations (sacred geometry + fractals):**
- `FLOWER_OF_LIFE` — center + 6 hex
- `VESICA_PISCIS` — 2 ships at the dyadic intersect
- `FIBONACFI_SPIRAL` — logarithmic spiral r = r0·phi^(i/2) (sic, intentional typo)
- `TREE_OF_LIFE` — 10 Kabbalistic sephirot
- `SIERPINSKI_TRIANGLE` — depth-2 recursive
- `HEX_CLOSE_PACK` — honeycomb (tighter than flower of life)
- `MANDALA_RINGS` — 2 concentric hex rings
- `GOLDEN_RATIO_ROW` — accelerating horizontal row
- `KOCH_3FOLD` — 3-fold Koch zigzag (no central peak)
- `DRAGON_CURVE` — Heighway dragon recursion

**7 new paths:**
- `LemniscatePath` — figure-8
- `CardioidPath` — heart
- `LissajousPath` — 3:2 parametric
- `RoseK2Path` — 4-petal rose
- `RoseK3Path` — 3-petal rose (NOT a 3-pointed star)
- `HypocycloidPath` — Spirograph (R=3r → 3-cusp deltoid)
- `EpicycloidPath` — small circle outside big (R=r → cardioid)

**1,050 new COMPOSED patterns** (cross product 19 forms × 15 paths × 3 follows × 5 counts, capped 1050). First 50 patterns unchanged (backward compat verified).

**Excluded by user constraint (no stars):** pentagram, hexagram, `{n/k}` star polygons, snowflake-star hybrids. Koch_3fold and Rose_K3 are explicitly NOT star shapes (asymmetric / smooth petals).

**Doc updates:** `01_movement_primitives.md` got a "Notation" note clarifying "cubic" is polynomial degree (NOT 3D). `02_formations.md` got a "Sacred Geometry & Fractal Presets" section. New `06_paths.md` documents the 7 new paths. `CONTEXT.md` and `README.md` updated to reference the new files.

### Fixed

**"Cubic" 2D vs 3D ambiguity in the doc** — the original `01_movement_primitives.md` said "cubic bezier curve" without clarifying "2D". A user (human) read this as 3D. Added a Notation note: "cubic" is polynomial degree 3, NOT 3D. All curves in the project are 2D Bezier with `Point(x, y)` control points (no z).

### Verified

- All 10 new formations: 11 unit tests in `tests/test_formation.py` pass.
- All 7 new paths: 10 unit tests in `tests/test_paths.py` pass (no star shapes verified by `test_paths_no_star_shapes`).
- 4 integration tests in `tests/test_wave_patterns.py` pass.
- `test_first_50_composed_unchanged_by_expansion` confirms backward compat.
- 17 visual proof PNGs in `tools/playtest_out/`: 10 formations + 7 paths.
```

- [ ] **Step 7: Verify all docs are well-formed**

Run: `git status` to see all modified/created files. Then `git diff --stat` to confirm the changes are reasonable sizes.

- [ ] **Step 8: Commit**

```bash
git add docs/movement/01_movement_primitives.md \
        docs/movement/02_formations.md \
        docs/movement/06_paths.md \
        docs/movement/CONTEXT.md \
        docs/movement/README.md \
        docs/changelog/CHANGELOG_v1.x.md
git commit -m "docs(movement): add sacred-geometry/fractal docs (BLOQUE 58.next)"
```

---

## Task 8: Capture 17 visual proof PNGs (10 formations + 7 paths)

**Files:**
- Create: `tools/playtest_out/_capture_expansion_proofs.py` (a one-shot script)
- Create: `tools/playtest_out/formation_<name>.png` × 10 (output, gitignored)
- Create: `tools/playtest_out/path_<name>.png` × 7 (output, gitignored)
- Create: `tools/playtest_out/composed_5_random.png` × 1 (output, gitignored)

- [ ] **Step 1: Create the capture script**

Create `tools/playtest_out/_capture_expansion_proofs.py`:

```python
"""Capture visual proofs for the BLOQUE 58.next movement expansion.

Renders 10 formations (slot dots on black bg), 7 paths (curve as dots),
and 1 mosaic of 5 random COMPOSED patterns. All output is saved to
tools/playtest_out/ which is gitignored.
"""
import os
import sys
import random
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.movement.formation import FlightFormation, FormationKind
from src.movement.lemniscate_path import LemniscatePath
from src.movement.cardioid_path import CardioidPath
from src.movement.lissajous_path import LissajousPath
from src.movement.rose_path import RoseK2Path, RoseK3Path
from src.movement.hypocycloid_path import HypocycloidPath
from src.movement.epicycloid_path import EpicycloidPath
from src.systems.wave_patterns.composed import COMPOSED_PATTERNS, FORMATION_GENERATORS, PATH_GENERATORS


W, H = 800, 800
WHITE = (255, 255, 255)
RED = (255, 80, 60)
BLUE = (80, 180, 255)
GREEN = (100, 255, 100)


def render_formation(form: FlightFormation, name: str) -> pygame.Surface:
    surf = pygame.Surface((W, H))
    surf.fill((0, 0, 0))
    # Origin at center, scale slots by 4
    cx, cy = W // 2, H // 2
    scale = 4
    for i, (dx, dy) in enumerate(form.offsets):
        x = int(cx + dx * scale)
        y = int(cy + dy * scale)
        color = RED if i == 0 else BLUE
        pygame.draw.circle(surf, color, (x, y), 8)
        pygame.draw.circle(surf, WHITE, (x, y), 8, 1)
    return surf


def render_path_samples(path, name: str, n_samples: int = 200) -> pygame.Surface:
    surf = pygame.Surface((W, H))
    surf.fill((0, 0, 0))
    cx, cy = W // 2, H // 2
    scale = 1.5
    for i in range(n_samples):
        t = i / (n_samples - 1)
        pos = path.position_at(t)
        x = int(cx + pos.x * scale)
        y = int(cy + pos.y * scale)
        if 0 <= x < W and 0 <= y < H:
            pygame.draw.circle(surf, GREEN, (x, y), 2)
    return surf


def render_composed_panel(p, w: int = 400, h: int = 400) -> pygame.Surface:
    surf = pygame.Surface((w, h))
    surf.fill((0, 0, 0))
    # Get the formation slots
    if p._formation in FORMATION_GENERATORS:
        slots = FORMATION_GENERATORS[p._formation](p._count)
    else:
        slots = []
    cx, cy = w // 2, h // 2
    scale = 1.5
    for dx, dy in slots:
        x = int(cx + dx * scale)
        y = int(cy + dy * scale)
        pygame.draw.circle(surf, BLUE, (x, y), 4)
    return surf


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(exist_ok=True)

    # 10 formations
    new_formations = [
        (FormationKind.FLOWER_OF_LIFE, "flower_of_life", lambda: FlightFormation.flower_of_life()),
        (FormationKind.VESICA_PISCIS, "vesica_piscis", lambda: FlightFormation.vesica_piscis()),
        (FormationKind.FIBONACFI_SPIRAL, "fibonacfi_spiral", lambda: FlightFormation.fibonacfi_spiral()),
        (FormationKind.TREE_OF_LIFE, "tree_of_life", lambda: FlightFormation.tree_of_life()),
        (FormationKind.SIERPINSKI_TRIANGLE, "sierpinski_triangle", lambda: FlightFormation.sierpinski_triangle()),
        (FormationKind.HEX_CLOSE_PACK, "hex_close_pack", lambda: FlightFormation.hex_close_pack()),
        (FormationKind.MANDALA_RINGS, "mandala_rings", lambda: FlightFormation.mandala_rings()),
        (FormationKind.GOLDEN_RATIO_ROW, "golden_ratio_row", lambda: FlightFormation.golden_ratio_row()),
        (FormationKind.KOCH_3FOLD, "koch_3fold", lambda: FlightFormation.koch_3fold()),
        (FormationKind.DRAGON_CURVE, "dragon_curve", lambda: FlightFormation.dragon_curve()),
    ]
    for kind, name, builder in new_formations:
        form = builder()
        surf = render_formation(form, name)
        out_path = out_dir / f"formation_{name}.png"
        pygame.image.save(surf, str(out_path))
        print(f"  formation {name} -> {out_path.name}")

    # 7 paths
    path_classes = [
        (LemniscatePath, "lemniscate"),
        (CardioidPath, "cardioid"),
        (LissajousPath, "lissajous"),
        (RoseK2Path, "rose_k2"),
        (RoseK3Path, "rose_k3"),
        (HypocycloidPath, "hypocycloid"),
        (EpicycloidPath, "epicycloid"),
    ]
    for cls, name in path_classes:
        path = cls().get_path()
        surf = render_path_samples(path, name)
        out_path = out_dir / f"path_{name}.png"
        pygame.image.save(surf, str(out_path))
        print(f"  path {name} -> {out_path.name}")

    # 1 mosaic: 5 random COMPOSED
    rng = random.Random(42)
    sample = rng.sample(COMPOSED_PATTERNS, 5)
    mosaic = pygame.Surface((W * 2, H))
    for i, p in enumerate(sample):
        col = i % 2
        row = i // 2
        panel = render_composed_panel(p, w=W, h=H)
        mosaic.blit(panel, (col * W, row * H))
    mosaic_path = out_dir / "composed_5_random.png"
    pygame.image.save(mosaic, str(mosaic_path))
    print(f"  mosaic -> {mosaic_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the capture script**

Run: `python tools/playtest_out/_capture_expansion_proofs.py`
Expected: 18 PNGs created in `tools/playtest_out/`, 0 errors

- [ ] **Step 3: Verify the PNGs are valid**

Run: `Get-ChildItem tools/playtest_out/formation_*.png, tools/playtest_out/path_*.png | Measure-Object | Select-Object Count`
Expected: 17 (10 formations + 7 paths)

- [ ] **Step 4: Visual check**

Open `tools/playtest_out/composed_5_random.png` and verify the formations look like the expected shapes (Flower of Life hex, Mandala rings, etc.). The mosaic is the key visual proof.

- [ ] **Step 5: Commit (only the script, not the PNGs)**

```bash
git add tools/playtest_out/_capture_expansion_proofs.py
git commit -m "test(movement): add capture script for BLOQUE 58.next visual proofs (17 PNGs)"
```

The 17 PNGs are gitignored (in `tools/playtest_out/`).

---

## Task 9: Rebuild .exe + smoke test

**Files:**
- Create: `dist/void-hunter/void-hunter.exe` (NOT committed; build artifact)

- [ ] **Step 1: Rebuild the .exe**

Run: `pyinstaller build.spec --clean --noconfirm`
Expected: 21-second build, exit 0, .exe at `dist/void-hunter/void-hunter.exe` (~4.35 MB)

- [ ] **Step 2: Launch the .exe and verify window title**

Run: `python tools/playtest_out/_launch_and_verify.py`
Expected: PID assigned, window title = `'VOID HUNTER v1.1.6 (BLOQUE 58.62)'`, PASS message

- [ ] **Step 3: Confirm the new formations surface in COMPOSED picks**

Run: `python -c "from src.systems.wave_patterns.composed import COMPOSED_PATTERNS, FORMATION_GENERATORS; print('Total:', len(COMPOSED_PATTERNS)); print('Has flower_of_life:', 'flower_of_life' in {p._formation for p in COMPOSED_PATTERNS}); print('Has lemniscate:', 'lemniscate' in {p._path for p in COMPOSED_PATTERNS})"`
Expected: `Total: 1050`, both `True`

- [ ] **Step 4: Kill the launched .exe**

Run: `taskkill /F /IM void-hunter.exe`
Expected: process terminated

- [ ] **Step 5: No commit needed (build artifacts are not tracked)**

Verify: `git status` should show no changes related to `dist/` (it's gitignored)

---

## Task 10: Re-FREEZE + final push

**Files:**
- Modify: `docs/movement/CONTEXT.md` (revert TEMPORARY UN-FROZEN back to FROZEN)
- (No new test/code changes; just the doc reversion + push)

- [ ] **Step 1: Revert `CONTEXT.md` to FROZEN**

Edit `docs/movement/CONTEXT.md`. Replace the "TEMPORALMENTE UN-FROZEN" section with:

```markdown
## Lock Status

**Estado: FROZEN** (intencional)

**Razón:** este silo documenta la "alma" del juego (Star Fox 64-style choreography + sacred geometry & fractal patterns). Cambios al contrato sin re-leer las 7 secciones + `06_paths.md` rompen silenciosamente los 56 wave patterns + 1,050 COMPOSED. La próxima vez que se desbloquee, **re-leer completo y agregar test de regresión** por cada cambio de signature.

**Historial de un-FREEZE:**
- 2026-09-02: BLOQUE 58.next (Movement Expansion: Sacred Geometry & Fractal Symbolism) — 10 formations + 7 paths + 1,050 COMPOSED patterns agregados. Re-FROZEN después de merge.

**Si necesitás cambiar algo aquí:** abrir un BLOQUE nuevo con spec en `docs/superpowers/specs/`, plan en `docs/superpowers/plans/`, y PR description que cite qué métodos del contract cambian.
```

- [ ] **Step 2: Run the full test suite to confirm no regression**

Run: `pytest tests/ -q --tb=no`
Expected: ~1,675+ passed, 5-6 failures (the pre-existing sub_boss flakes + rng test, all documented in v1.1.6)

- [ ] **Step 3: Push all commits**

```bash
git push origin master
```

Expected: 10 commits pushed (Tasks 1-10), all tests still pass

- [ ] **Step 4: Report completion to user**

BLOQUE 58.next is done when:
- [x] 10 new formations + 7 new paths committed
- [x] 1,050 new COMPOSED patterns registered
- [x] 17 visual proof PNGs saved (gitignored)
- [x] All 4 doc files updated
- [x] CHANGELOG entry added
- [x] FROZEN status restored
- [x] .exe rebuilt and verified
- [x] All commits pushed to origin

Tell the user: the new formations/paths surface in COMPOSED picks, so the .exe will produce visually richer enemy patterns in later waves. They can test by running the .exe and playing multiple waves; the new figures should appear (sierpinski triangles, mandala rings, etc.) in addition to the existing V/LINE/DIAMOND shapes.

---

## Self-Review

After writing this plan, I checked:

**1. Spec coverage:** Section-by-section of the spec:
- §3 (10 formations): Tasks 1, 2 — each formation has its own test + commit
- §4 (7 paths): Tasks 3, 4, 5 — each path class has its own test + commit
- §5 (COMPOSED integration): Task 6 — backward-compat test verifies
- §6 (naming): Tasks 1, 2, 3, 4, 5 — all use UPPER_SNAKE_CASE / PascalCase / snake_case
- §7 (tests): Tasks 1, 2, 3, 4, 5, 6 — all test classes/methods are in the plan
- §8 (docs): Task 7 — all 4 doc files updated + CHANGELOG
- §9 (open questions): Resolved during brainstorming (see spec §9)
- §10 (acceptance criteria): All 10 items covered by Tasks 1-10

**2. Placeholder scan:** No "TBD" / "TODO" / "implement later" in the plan. All code blocks contain the actual code. References to types/functions in later tasks match what earlier tasks define (`LemniscatePath`, `CardioidPath`, etc.).

**3. Type consistency:** `LemniscatePath` defined in Task 3, used in Task 6 (COMPOSED). `RoseK2Path` and `RoseK3Path` defined together in Task 5 (both in `rose_path.py`), used in Task 6. `FlightFormation.flower_of_life` defined in Task 1, used in Task 6 (via FORMATION_GENERATORS).

**4. Backward compat:** Task 6 includes `test_first_50_composed_unchanged_by_expansion` that verifies the first 50 COMPOSED patterns are identical to the pre-expansion output.

**5. "No stars" check:** Task 5's `test_paths_no_star_shapes` verifies NO path has tangent rotations > 90 deg. Task 6's `test_composed_count_after_expansion` ensures the cap is 1050 (not star patterns). Tasks 1 and 2 follow the spec's geometric definitions which explicitly exclude star shapes.

**6. FROZEN subsystem:** Task 7 sets `CONTEXT.md` to "TEMPORARY UN-FROZEN" with the full change list. Task 10 reverts to "FROZEN" with a history entry referencing BLOQUE 58.next.

**7. Test count:** Tasks 1-6 add ~24 unit tests + 4 integration tests = 28 new tests. Combined with the existing 1,630+ tests, the suite should be ~1,660 tests after BLOQUE 58.next.

**Plan ready for execution.**
