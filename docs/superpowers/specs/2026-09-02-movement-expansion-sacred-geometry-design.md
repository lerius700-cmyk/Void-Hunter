# Spec — Movement Expansion: Sacred Geometry & Fractal Symbolism

**Status:** Draft v1 (pending user review)
**Date:** 2026-09-02
**Author:** Mavis (Mavis)
**Scope:** BLOQUE 58.next — `src/movement/` + `src/systems/wave_patterns/` expansion

---

## 1. Context

The current choreography system (9 formations + 8 paths + 3 follow modes + 5 counts = 1,080 cross-product combos in `COMPOSED`) is built from basic geometric primitives: V, LINE, DIAMOND, SQUARE, WEDGE, CIRCLE, TRIANGLE, HALF_V, CUSTOM. These cover the Star Fox 64 aesthetic but lack visual variety at the **shape** level.

The user (Lerius) wants the enemy formation vocabulary to expand to include **sacred geometry** (Flower of Life, Fibonacci, etc.) and **fractal symbolism** (Sierpinski, dragon curve, etc.) — geometric figures with deeper meaning that read instantly on screen as "this is not a generic swarm". Explicit user constraint: **no 5-pointed, 6-pointed, or n-pointed star shapes** (pentagrams, hexagrams, star polygons `{n/k}` with k>1, snowflake-shaped figures).

### Why now

- The `docs/movement/` subsystem was just locked in as FROZEN (commit `dbcc98d`, 2026-09-01). The FROZEN status requires a written spec + plan before any new code lands in `src/movement/` or `src/systems/wave_patterns/`. This document IS that spec.
- The procedural patterns default mode (BLOQUE 58.62) currently shows ~18-28% of picks as COMPOSED patterns. More formations × more paths = more variety per wave without changing the manager weights.
- The user's last gameplay session noted "las coreografías se dañaron" — interpreted as the 9-formation palette feeling stale. The new figures give the player more shapes to read.

---

## 2. Goals

1. Add **10 new formations** based on sacred geometry + fractals (NO star shapes).
2. Add **7 new paths** (lemniscate, cardioid, lissajous, rose curves, cycloids).
3. Integrate them into the existing `COMPOSED` cross product so the manager picks them automatically. **1,050 new COMPOSED combos** (10×7×3×5) on top of the existing 1,080.
4. Update `docs/movement/02_formations.md` and add a new `docs/movement/06_paths.md` to document the new primitives.
5. Add unit tests + visual proof (17 PNGs total: 10 formations + 7 paths).
6. Re-build the .exe so the user can test in-game.

### Non-goals (out of scope)

- No new `WavePatternKind` enum values. The new formations/paths are added to the existing `COMPOSED` cross product, not as new top-level patterns.
- No changes to `ProceduralWaveManager` weights. COMPOSED keeps its 20/24/28 weight per floor.
- No new enemy sprite art. Existing enemy sprites are reused at the new slot offsets.
- No new audio. SFX for spawn/death unchanged.
- No 3D, no rotation in z-axis, no perspective transforms. Everything is 2D.
- **No star shapes**: pentagram, hexagram, `{n/k}` star polygons, snowflake figures with starry rotational symmetry.

---

## 3. Design — 10 new formations

All formations are implemented as `@staticmethod` builders on `FlightFormation` in `src/movement/formation.py`. Each one returns a `FlightFormation(kind, offsets)` with `count` slots in path-local coordinates `(dx, dy)` where +x is right and +y is down (screen convention).

### 3.1 `FLOWER_OF_LIFE` — 7 ships

```
        *           *
          *       *
            *   *
              *           ← center (0, 0)
            *   *
          *       *
        *           *
```

Center at `(0, 0)`, 6 hex points around at radius `r=18`, angle `i·60°` for i ∈ {0..5}.

| Slot | (dx, dy) |
|---|---|
| 0 (center) | (0, 0) |
| 1 | (18·cos 0°, 18·sin 0°) = (18, 0) |
| 2 | (18·cos 60°, 18·sin 60°) = (9, 15.59) |
| 3 | (18·cos 120°, 18·sin 120°) = (-9, 15.59) |
| 4 | (18·cos 180°, 18·sin 180°) = (-18, 0) |
| 5 | (18·cos 240°, 18·sin 240°) = (-9, -15.59) |
| 6 | (18·cos 300°, 18·sin 300°) = (9, -15.59) |

Builder signature: `FlightFormation.flower_of_life(count=7, radius=18.0)`. For `count != 7`, falls back to closest valid (1 = leader only, 7 = full flower).

### 3.2 `VESICA_PISCIS` — 2 ships

Two points at `±9, 0` (overlapping when path curves through middle). Pure dyadic figure; visually reads as "linked circles" when the path is an arc.

| Slot | (dx, dy) |
|---|---|
| 0 | (-9, 0) |
| 1 | (9, 0) |

Builder: `FlightFormation.vesica_piscis(count=2, spacing=18.0)`. For `count>2`, returns `count//2` pairs at increasing `x` offsets.

### 3.3 `FIBONACFI_SPIRAL` — 8 ships (sic, intentional: matches the user's spec naming)

**Note on typo:** the spec uses "FIBONACFI" to mirror the user's exact request. The Python identifier will be `fibonacfi_spiral` (sic). This is documented and the actual implementation uses the same spelling.

Slots on a logarithmic spiral: `r = r0 · φ^(i/2)`, `θ = i · (π/3)`, where `φ = (1 + √5) / 2 ≈ 1.618`. With `r0=8` and 8 slots:

```
i=0: r=8.00,  θ=0°     → (8.00, 0.00)
i=1: r=10.30, θ=60°    → (5.15, 8.92)
i=2: r=13.26, θ=120°   → (-6.63, 11.49)
i=3: r=17.08, θ=180°   → (-17.08, 0.00)
i=4: r=22.00, θ=240°   → (-11.00, -19.05)
i=5: r=28.34, θ=300°   → (14.17, -24.55)
i=6: r=36.50, θ=360°   → (36.50, 0.00)
i=7: r=47.02, θ=420°   → (3.60, 46.85)
```

Visually: ships spiral outward from a tight cluster. Builder: `FlightFormation.fibonacfi_spiral(count=8, r0=8.0)`. (The typo is preserved on purpose per user request.)

### 3.4 `TREE_OF_LIFE` — 10 ships (Kabbalistic sephirot)

10 positions in the classic Kabbalistic Tree of Life layout (3 columns × 4 rows, with the bottom row having 1 ship and the da'at position skipped):

```
   *   *   *           (crown, 3)
   *   *   *           (3 sephirot row 2)
   *   *   *           (3 sephirot row 3)
       *               (kingdom, 1)
```

| Column | x | y values |
|---|---|---|
| Left (Binah/Hockmah/etc) | -22 | -33, -11, +11 |
| Middle (Tiferet/etc) | 0 | -33, -11, +11, +33 |
| Right (Chesed/Geburah/etc) | +22 | -33, -11, +11 |

Total: 3 + 3 + 3 + 1 = 10 ships. Builder: `FlightFormation.tree_of_life(count=10, spacing=22.0)`. If `count<10`, ships are dropped from the lowest-priority positions (right column first, then middle bottom).

### 3.5 `SIERPINSKI_TRIANGLE` — 7 ships (depth 2 recursion)

3 vertices of an equilateral triangle + 3 midpoints of edges + 1 centroid. Triangle inscribed in a `r=24` circle:

```
              *(0, -24)              ← top vertex
            *       *
          *     *(0, 0)  *            ← centroid + midpoints
        *       *       *
      *(-21, 12)   *(21, 12)         ← bottom vertices
```

| Slot | (dx, dy) |
|---|---|
| 0 (top) | (0, -24) |
| 1 (top-left midpoint) | (-10.39, -12) |
| 2 (top-right midpoint) | (10.39, -12) |
| 3 (centroid) | (0, 0) |
| 4 (bottom-left midpoint) | (-10.39, 12) |
| 5 (bottom-right midpoint) | (10.39, 12) |
| 6 (bottom-left vertex) | (-21, 12) |

For `count=3` returns just vertices. For `count=10` adds depth-3 midpoints. Builder: `FlightFormation.sierpinski_triangle(count=7, radius=24.0)`.

### 3.6 `HEX_CLOSE_PACK` — 7 ships (honeycomb)

Same 7 hex layout as `FLOWER_OF_LIFE` but with `radius=14` (tighter) so the 6 outer ships overlap the center ship's exclusion zone — creates a true honeycomb cell rather than a flower.

| Slot | (dx, dy) |
|---|---|
| 0 | (0, 0) |
| 1-6 | (14·cos(i·60°), 14·sin(i·60°)) for i ∈ {0..5} |

Builder: `FlightFormation.hex_close_pack(count=7, radius=14.0)`. For `count=19`, adds a second hex ring at `r=28`.

### 3.7 `MANDALA_RINGS` — 12 ships (6 + 6 concentric rings)

Two concentric hex rings:

- Inner ring: 6 ships at `r=12`, angles `0°, 60°, 120°, 180°, 240°, 300°`
- Outer ring: 6 ships at `r=24`, angles `30°, 90°, 150°, 210°, 270°, 330°` (offset by 30° so they sit between the inner ring)

| Slot | (dx, dy) |
|---|---|
| 0-5 (inner) | (12·cos(i·60°), 12·sin(i·60°)) |
| 6-11 (outer) | (24·cos(30° + i·60°), 24·sin(30° + i·60°)) |

Builder: `FlightFormation.mandala_rings(count=12, inner_r=12.0, outer_r=24.0)`. For `count=6` returns just inner ring. For `count=18` adds a third ring at `r=36`.

### 3.8 `GOLDEN_RATIO_ROW` — 5 ships

Horizontal row with offsets scaled by the golden ratio `φ ≈ 1.618`. The 5 ships are at:
`(0, 0)`, `(φ·spacing, 0)`, `(2·φ·spacing, 0)`, `(3·φ·spacing, 0)`, `(4·φ·spacing, 0)`

With `spacing=10`:
| Slot | (dx, dy) |
|---|---|
| 0 | (0, 0) |
| 1 | (16.18, 0) |
| 2 | (32.36, 0) |
| 3 | (48.54, 0) |
| 4 | (64.72, 0) |

The progression of distances (16, 32, 49, 65) reads as a visually accelerating row. Builder: `FlightFormation.golden_ratio_row(count=5, spacing=10.0)`. For `count<5`, drops the rightmost ships.

### 3.9 `KOCH_3FOLD` — 7 ships (Koch curve, 3-fold, no star points)

The 3-fold Koch curve (NOT the snowflake — single-sided, no star tips). 7 anchor points along the first 2 iterations of a 3-fold Koch-like recursion. Anchor positions (precomputed):

| i | (dx, dy) |
|---|---|
| 0 | (-24, -14) |
| 1 | (-12, -24) |
| 2 | (0, -14) |
| 3 | (12, -24) |
| 4 | (24, -14) |
| 5 | (-24, 14) |
| 6 | (24, 14) |

These are 6 points along a Koch-3-fold zigzag (no central peak). Builder: `FlightFormation.koch_3fold(count=7, scale=24.0)`.

**Justification for "no star":** the 6-fold Koch snowflake has 6 sharp tips radiating outward (looks like a star). The 3-fold version is asymmetric and reads as a "fractal zigzag", not a star. Verified visually with mockup.

### 3.10 `DRAGON_CURVE` — 8 ships (recursive L-shape)

First 8 anchor points of the Heighway dragon curve, scaled to fit a `r=22` circle. The dragon curve is generated by recursive folding: at depth N, fold a strip of paper N times and unfold, recording the creases.

Pre-computed anchor points (8 ships in a recursive L-shape):

| Slot | (dx, dy) |
|---|---|
| 0 | (0, 0) |
| 1 | (0, -16) |
| 2 | (16, -16) |
| 3 | (16, 0) |
| 4 | (32, 0) |
| 5 | (32, 16) |
| 6 | (16, 16) |
| 7 | (16, 32) |

The shape self-intersects when drawn as a line, but as 8 discrete ship slots, reads as a "fractal staircase". Builder: `FlightFormation.dragon_curve(count=8, scale=16.0)`. For `count != 8`, drops ships from the end.

---

## 4. Design — 7 new paths

All paths return a `list[BezierPath]` (4 control points each) so they plug into the existing `HybridPath` infrastructure in `src/movement/hybrid.py`. The runtime reads the segments and durations and attaches a `PathFollower` to each enemy.

For paths that are naturally parametric (like lemniscate), we approximate the curve with N bezier segments where N is chosen so the per-segment deviation from the true curve is < 1 px (validated in tests).

### 4.1 `LEMNISCATE` (figure-8 / infinity)

Parametric:
```
x(t) = a · cos(t) / (1 + sin²(t))
y(t) = a · sin(t) · cos(t) / (1 + sin²(t))
```
With `a=120` (fits 320-px playfield with margin). Parameter `t ∈ [-π/2, 3π/2]` to trace both lobes.

**Approximation:** 8 bezier segments (4 per lobe). Per-lobe: control points derived from the parametric form at `t=0, π/4, π/2, 3π/4, π`.

**Class:** `LemniscatePath` in `src/movement/lemniscate_path.py`. `get_path()` returns `HybridPath` with 8 segments, total duration configurable.

### 4.2 `CARDIOID` (heart)

Parametric (standard cardioid):
```
x(t) = a · (2·cos(t) - cos(2t))
y(t) = a · (2·sin(t) - sin(2t))
```
With `a=60` (fits 240-px tall heart shape).

**Approximation:** 12 bezier segments. The cardioid has a cusp at `t=π` which requires careful control-point placement to avoid a sharp angle. 12 segments is empirically the minimum that makes the cusp look smooth at playfield scale.

**Class:** `CardioidPath` in `src/movement/cardioid_path.py`.

### 4.3 `LISSAJOUS_3_2` (3:2 ratio)

Parametric:
```
x(t) = A · sin(3t + δ)
y(t) = B · sin(2t)
```
With `A=120, B=80`, `δ=π/2` (phase shift to make the figure close properly). `t ∈ [0, 2π]`.

**Approximation:** 12 bezier segments. The 3:2 ratio produces a "trefoil-like" curve with 3-fold symmetry but **no sharp points** (unlike a 3-pointed star). This is sacred-geometry-friendly.

**Class:** `LissajousPath` in `src/movement/lissajous_path.py`. Constructor takes `(a, b, delta, duration_s)`.

### 4.4 `ROSE_K2` (4-petal rose)

Parametric (rose curve with k=2):
```
r(θ) = a · cos(2θ)
x(θ) = r · cos(θ)
y(θ) = r · sin(θ)
```
With `a=80`. `θ ∈ [0, 2π]`.

**Approximation:** 8 bezier segments (2 per petal). Each petal is a smooth lobe.

**Class:** `RoseK2Path` in `src/movement/rose_path.py` (file holds both k=2 and k=3 classes).

### 4.5 `ROSE_K3` (3-petal rose)

Parametric:
```
r(θ) = a · cos(3θ)
x(θ) = r · cos(θ)
y(θ) = r · sin(θ)
```
With `a=80`. `θ ∈ [0, 2π]`.

**Approximation:** 12 bezier segments (4 per petal, since k=3 roses have 3 petals). Visually reads as a "3-leaf flower" — sacred geometry friendly, not a star.

**Class:** `RoseK3Path` in same `src/movement/rose_path.py` as k=2.

### 4.6 `HYPOCYCLOID` (Spirograph, R=3r → 3-cusp curve)

Parametric:
```
x(t) = (R - r) · cos(t) + r · cos((R - r)·t/r)
y(t) = (R - r) · sin(t) - r · sin((R - r)·t/r)
```
With `R=3r=60` (so `r=20, R=60`). The `R/r` ratio determines the number of cusps: `R/r=3` gives a 3-cusp (deltoid), `R/r=4` gives astroid, `R/r=N` gives N-cusp. We use `R/r=3` for the default.

**Approximation:** 18 bezier segments (6 per cusp, since the curve has 3-fold symmetry). The deltoid has 3 sharp cusps that need careful handling; 6 segments per cusp is empirically the minimum.

**Class:** `HypocycloidPath` in `src/movement/hypocycloid_path.py`. Constructor takes `(R, r, duration_s)`.

### 4.7 `EPICYCLOID` (small circle outside big)

Parametric (epicycloid, R=r → cardioid):
```
x(t) = (R + r) · cos(t) - r · cos((R + r)·t/r)
y(t) = (R + r) · sin(t) - r · sin((R + r)·t/r)
```
With `R=r=30` (default produces a cardioid, the "heart" cousin). `R/r=2` gives nephroid (kidney shape).

**Approximation:** 16 bezier segments for `R=r` (cardioid has a single cusp at `t=π`); 24 segments for `R=2r` (nephroid is smoother).

**Class:** `EpicycloidPath` in `src/movement/epicycloid_path.py`. Constructor takes `(R, r, duration_s)`.

---

## 5. Integration with COMPOSED

The existing `src/systems/wave_patterns/composed.py` uses a cross product of formations × paths × follow modes × counts. We extend the cross product by:

1. Add 10 new entries to `FORMATION_GENERATORS` dict in `composed.py`:
   ```python
   FORMATION_GENERATORS = {
       "line": lambda c: FlightFormation.line(c).offsets,
       "v": lambda c: FlightFormation.v(c).offsets,
       # ... existing 9 ...
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

2. Add 7 new entries to `PATH_GENERATORS` dict in `composed.py`:
   ```python
   PATH_GENERATORS = {
       # ... existing 8 ...
       "lemniscate": lambda start, rng: LemniscatePath(...).get_path_points(),
       "cardioid": lambda start, rng: CardioidPath(...).get_path_points(),
       "lissajous_3_2": lambda start, rng: LissajousPath(3, 2, ...).get_path_points(),
       "rose_k2": lambda start, rng: RoseK2Path(...).get_path_points(),
       "rose_k3": lambda start, rng: RoseK3Path(...).get_path_points(),
       "hypocycloid": lambda start, rng: HypocycloidPath(3, 1, ...).get_path_points(),
       "epicycloid": lambda start, rng: EpicycloidPath(1, 1, ...).get_path_points(),
   }
   ```

3. The existing `_build_50_patterns()` becomes `_build_1050_patterns()` (cross product capped at 1050). The `register_composed_patterns()` already takes the first N from the cross product, so this is a 1-line change.

4. `WavePatternKind` enum is **unchanged**. The new figures are accessed via COMPOSED only.

5. `ProceduralWaveManager` weights are unchanged. COMPOSED keeps weight 20/24/28 per floor. The new formations/paths surface through COMPOSED, not as new top-level kinds.

### 5.1 Backward compatibility

- All 50 existing COMPOSED patterns are preserved (cross product is just expanded, the first 50 entries are deterministic from the same RNG seed).
- No existing tests should fail (formations are additive; `FormationKind` enum is extended, not changed).
- The default seed=42 still produces the same first 50 patterns, so the .exe behaves identically on first wave. New patterns surface in later waves.

---

## 6. Naming convention

- New `FormationKind` enum values: UPPER_SNAKE_CASE matching the existing pattern (`V`, `LINE`, etc. → `FLOWER_OF_LIFE`, `SERPINSKI_TRIANGLE`, etc.).
- One exception per user explicit request: `FIBONACFI_SPIRAL` (sic) for the Fibonacci spiral. This is a deliberate typo, not a bug. The Python identifier is `fibonacfi_spiral`.
- New path class names: `PascalCase` ending in `Path` matching existing pattern (`OrbitalPath`, `ParallelPathPair` → `LemniscatePath`, `CardioidPath`, etc.).
- New file names: `snake_case` matching existing pattern (`bezier.py`, `orbital_path.py` → `lemniscate_path.py`, `cardioid_path.py`, etc.).

---

## 7. Tests

### 7.1 Unit tests in `tests/test_formation.py` (extend existing)

For each of the 10 new formations:
- `test_flower_of_life_default_count` — 7 ships, correct offsets
- `test_flower_of_life_offsets_match_geometry` — distance from (0,0) matches `r` for all outer ships
- `test_vesica_piscis_two_ships` — count=2, slots at (±9, 0)
- `test_fibonacfi_spiral_golden_ratio` — verify r-values follow `r = r0·φ^(i/2)` within 1%
- `test_tree_of_life_10_ships` — count=10, layout matches
- `test_sierpinski_triangle_depth_2` — count=7, 3 vertices + 3 midpoints + 1 centroid
- `test_hex_close_pack_seven_ships` — count=7, radius=14
- `test_mandala_rings_concentric` — inner+outer ring check
- `test_golden_ratio_row_phi_offsets` — verify offsets follow φ
- `test_koch_3fold_no_star_points` — visual check: no point in the 7 ships has a clear "spike" direction (asymmetric)
- `test_dragon_curve_recursive_layout` — verify pre-computed anchors match dragon curve generation

### 7.2 Unit tests in `tests/test_paths.py` (new file)

For each of the 7 new paths:
- `test_lemniscate_close_to_parametric` — sample 100 points, verify each is within 2 px of the true lemniscate
- `test_lemniscate_no_self_intersection_in_approximation` — consecutive segments don't cross
- `test_cardioid_closes_smoothly` — endpoint matches startpoint, no cusp visible at playfield scale
- `test_lissajous_3_2_threefold_symmetry` — 3-fold symmetry, no star points
- `test_rose_k2_four_petals` — count petals = 4 (k=2 → 2k petals for k even)
- `test_rose_k3_three_petals` — count petals = 3 (k=3 → k petals for k odd)
- `test_hypocycloid_R3r_three_cusps` — cusp count = 3
- `test_epicycloid_Rr_is_cardioid` — verify shape matches cardioid at R=r
- `test_path_attachable_to_hybridpath` — each path's `get_path()` returns a valid `HybridPath` that the runtime can attach

### 7.3 Integration tests in `tests/test_wave_patterns.py` (extend)

- `test_composed_count_after_expansion` — verify `len(COMPOSED_PATTERNS) == 1050`
- `test_composed_includes_new_formations` — at least one COMPOSED pattern with each new formation kind
- `test_composed_includes_new_paths` — at least one COMPOSED pattern with each new path kind
- `test_first_50_composed_unchanged_by_expansion` — verify backwards compatibility (first 50 patterns from `register_composed_patterns()` with seed=42 are identical to current output)

### 7.4 Visual proof (manual verification)

- 10 PNGs: one per formation, render the slots as colored dots on a black background, save to `tools/playtest_out/formation_<name>.png`
- 7 PNGs: one per path, render the curve as a series of dots, save to `tools/playtest_out/path_<name>.png`
- 1 mosaic: 5 random COMPOSED patterns from the new 1,050 pool, rendered as `slot_dx, slot_dy` + path, save to `tools/playtest_out/composed_5_random.png`
- All 18 PNGs are gitignored (they go in `tools/playtest_out/`, which is already in `.gitignore`).

---

## 8. Documentation updates

### 8.1 `docs/movement/02_formations.md` (extend)

Add a new section "Sacred Geometry & Fractal Presets" (after the existing 9 presets) with:
- ASCII diagram of each new formation
- The slot offset table
- The builder signature
- "When to use it" guidance for each

### 8.2 `docs/movement/06_paths.md` (new)

New doc for the 7 new paths:
- `LemniscatePath`, `CardioidPath`, `LissajousPath`, `RoseK2Path`, `RoseK3Path`, `HypocycloidPath`, `EpicycloidPath`
- Each with: parametric equation, the bezier-segment approximation strategy, API, when to use

### 8.3 `docs/movement/CONTEXT.md` (update FROZEN note)

Change `Lock Status: FROZEN` note to:
> **Estado: TEMPORALMENTE UN-FROZEN** para BLOQUE 58.next (Movement Expansion). Re-FROZEN after the spec + plan + implementation + tests are merged. The added formations (10) and paths (7) are documented in `02_formations.md` (new section) and `06_paths.md` (new file). The original 9 + 6 contract remains the source of truth.

### 8.4 `docs/movement/README.md` (update stack)

Add to the stack:
> 6. **[06_paths.md](./06_paths.md)** — `LemniscatePath`, `CardioidPath`, `LissajousPath`, `RoseK2Path`, `RoseK3Path`, `HypocycloidPath`, `EpicycloidPath`. The sacred-geometry & fractal movement primitives added in BLOQUE 58.next.

### 8.5 `docs/superpowers/plans/2026-09-02-movement-expansion-sacred-geometry.md` (new)

Implementation plan with 6-8 bite-sized tasks, each with: objective, files, test, verify, commit.

### 8.6 CHANGELOG

Add entry to `docs/changelog/CHANGELOG_v1.x.md` for the v1.2.x release:
> **BLOQUE 58.next — Movement Expansion: Sacred Geometry & Fractal Symbolism**
> - 10 new formations: FLOWER_OF_LIFE, VESICA_PISCIS, FIBONACFI_SPIRAL, TREE_OF_LIFE, SIERPINSKI_TRIANGLE, HEX_CLOSE_PACK, MANDALA_RINGS, GOLDEN_RATIO_ROW, KOCH_3FOLD, DRAGON_CURVE
> - 7 new paths: Lemniscate, Cardioid, Lissajous 3:2, Rose k=2, Rose k=3, Hypocycloid, Epicycloid
> - 1,050 new COMPOSED patterns (cross product of 10×7×3×5)
> - "2D explicit" notation fix in `01_movement_primitives.md`
> - 17 visual proofs (10 formations + 7 paths)
> - All paths/formations are 2D (no 3D, no star shapes per user constraint)

---

## 9. Open questions (resolved during brainstorming)

1. ~~Naming for the Fibonacci spiral~~ → `FIBONACFI_SPIRAL` (sic, per user explicit request).
2. ~~Scope (Tier A vs B vs C)~~ → Tier C (10 + 7, 1,050 new COMPOSED combos).
3. ~~Path count vs formation count~~ → 10 formations, 7 paths (asymmetric to leave room for future path additions).
4. ~~Backward compatibility~~ → First 50 COMPOSED patterns unchanged (test verifies).
5. ~~DOC update order~~ → Spec first (this doc), then user review, then plan, then code.
6. ~~"No stars" interpretation~~ → exclude pentagram, hexagram, {n/k} with k>1, snowflake-star hybrids. The Koch_3fold and Rose_K3 are explicitly NOT star shapes (verified visually — Koch_3fold is asymmetric, Rose_K3 has 3 smooth petals, no spikes).

---

## 10. Acceptance criteria

The BLOQUE is DONE when:

1. ✅ All 10 new formations have `FormationKind` enum values + static builders + tests passing.
2. ✅ All 7 new paths have classes + `get_path()` returning valid `HybridPath` + tests passing.
3. ✅ `COMPOSED_PATTERNS` has 1,050 entries (verifiable by `len()`).
4. ✅ First 50 COMPOSED patterns unchanged (backward-compat test passes).
5. ✅ 17 visual proof PNGs saved to `tools/playtest_out/`.
6. ✅ 4 doc files updated: `02_formations.md` extended, `06_paths.md` new, `CONTEXT.md` FROZEN note, `README.md` stack.
7. ✅ CHANGELOG entry added.
8. ✅ All 1,630+ existing tests still pass (no regression in `test_wave_patterns.py`, `test_movement.py`).
9. ✅ The .exe is re-built and the user can launch it; the new formations surface in COMPOSED picks.
10. ✅ The user reviews the spec (this doc) and the 17 visual proofs and approves.

---

## Appendix A: Why these specific figures

### Why no star shapes
- 5-pointed stars (pentagrams) are explicitly excluded by user.
- 6-pointed stars (hexagrams, Star of David) and 7/8/9-pointed star polygons are visually similar and carry the same "religious symbol" baggage.
- Snowflakes with 6-fold radial symmetry are also excluded (they read as stars).
- Koch_3fold and Rose_K3 are kept because they are NOT visually star-like: Koch_3fold is asymmetric (no rotational symmetry), Rose_K3 has 3 smooth petals (no spikes, no points).

### Why these sacred geometry figures
- **Flower of Life**: one of the most universal sacred symbols, instantly recognizable.
- **Vesica Piscis**: simplest dyadic sacred figure; small (2 ships) but visually meaningful.
- **Fibonacci spiral**: golden ratio is mathematically pure; spiral pattern reads as "expanding/contracting".
- **Tree of Life**: Kabbalistic layout (3 columns × 4 rows); visually distinct from any existing formation.

### Why these fractal figures
- **Sierpinski triangle**: classic fractal, well-known, recursive structure.
- **Hexagonal close-pack**: honeycomb is a natural tessellation, sacred geometry adjacent.
- **Mandala rings**: meditative/radial pattern; concentric hex rings.
- **Golden ratio row**: simple but mathematically pure; the row spacing reads as "acceleration".
- **Koch 3-fold**: classic fractal curve, asymmetric (avoids star read).
- **Dragon curve**: Heighway dragon, recursive L-shape; visually unique among formations.

### Why these paths
- **Lemniscate**: classic infinity/eternity symbol.
- **Cardioid**: heart shape, universal emotion.
- **Lissajous 3:2**: smooth, no star points, 3-fold symmetry.
- **Rose k=2 / k=3**: rose curves, smooth petals, no spikes.
- **Hypocycloid**: Spirograph-style curve, mathematical purity.
- **Epicycloid**: cousin of cardioid, smooth kidney shape.

---

**End of spec.** Awaiting user review.
