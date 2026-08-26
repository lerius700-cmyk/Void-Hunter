# Nebula Strip v2 — Clustered Heroes (BLOQUE 58.62)

**Date:** 2026-08-26
**Status:** Approved (user, brainstorming flow)
**Replaces:** BLOQUE 58.15 (3 large + 2 small galaxies per strip, 70 stars)
**Supersedes:** None — additive iteration on existing `ParallaxBackground` strip system
**Scope:** Single spec, single implementation plan

## Context

The user (Lerius) shipped v1.1.5 of VOID HUNTER with a new galaxy strip background
(BLOQUE 58.15). The strip rendered 3 large + 2 small galaxies per variant with 70
procedural stars. After visual review, the user reported the strip looked too empty
("se ve como asteroides sueltos" — like loose asteroids) compared to the
hand-painted reference image they provided, which has visible hero galaxy
clusters with multiple satellite galaxies.

Root cause: my initial design was 5 galaxies per strip (3 large + 2 small), spread
evenly. The reference shows clustered compositions: 1 dominant hero galaxy with
3-5 small companions around it, plus 2-3 background distant galaxies. My version
lacked the visual anchor (the hero) and the sense of "this is a solar system /
nebula region" that comes from clustering.

Additionally, my star count (70) contributed to the "asteroid field" feel because
the stars were uniformly scattered. The user explicitly identified the stars as
the "demasiada información" (too much information) in the reference.

## Goal

Replace the current strip's galaxy layout with a "clustered heroes" composition:
1 dominant hero galaxy with 3-5 small companion galaxies clustered around it,
plus 2-3 background distant galaxies for depth. Cut the star count to ~20 so the
galaxies are the visual focus, not the stars. Keep the existing per-variant
color treatment and scroll behavior.

## Non-Goals

- Change the strip dimensions (480x1440, 25 px/s scroll) — these are good
- Change the per-variant theme mapping (blue_void/teal/gold_amber/purple_dusk)
- Change the per-variant sprite tints (blue/red/cyan/violet)
- Change the glow overlay (parabolic, max_alpha=18)
- Revert the player ship to procedural — ship_01_spritesheet is the locked-in
  new model per BLOQUE 58.60

## Design

### Per-strip composition (480x1440, scroll 25 px/s)

| Element | Quantity | Radius | Position | Sprite picker |
|---|---|---|---|---|
| **Hero galaxy** | 1 | 70-90 px | Random, EDGE_PAD 200 px top/bottom | `sprite_indices[0]` (first preferred tint) |
| **Small companions** | 3-5 (uniform) | 15-30 px | 100-150 px from hero, random angle | `sprite_indices[1 % 2]` (alternate tint) |
| **Background larges** | 2-3 (uniform) | 50-70 px | Random, padding 200 px from edges + min 200 px from hero | round-robin from `sprite_indices` |
| **Procedural stars** | 20 | 1-2 px | Random | N/A (drawn as colored circles) |
| **Glow overlay** | 1 | full strip | Parabolic vertical gradient, max_alpha=18 | N/A |

**Total galaxies per strip: 6-9** (1 hero + 3-5 companions + 2-3 background).

**Total visual elements per strip: 26-30** (down from ~75 in current v1.1.5
implementation with 3+2 galaxies + 70 stars).

### Iteration support

All counts live as module-level constants at the top of `parallax.py` so the
user can tweak the design by changing numbers and re-rendering the capture:

```python
STRIP_HERO_GALAXY: int = 1
STRIP_HERO_RADIUS_MIN: int = 70
STRIP_HERO_RADIUS_MAX: int = 90
STRIP_COMPANION_GALAXIES_MIN: int = 3
STRIP_COMPANION_GALAXIES_MAX: int = 5
STRIP_COMPANION_RADIUS_MIN: int = 15
STRIP_COMPANION_RADIUS_MAX: int = 30
STRIP_COMPANION_DISTANCE_MIN: int = 100
STRIP_COMPANION_DISTANCE_MAX: int = 150
STRIP_BG_GALAXIES_MIN: int = 2
STRIP_BG_GALAXIES_MAX: int = 3
STRIP_BG_RADIUS_MIN: int = 50
STRIP_BG_RADIUS_MAX: int = 70
STRIP_BG_MIN_DISTANCE_FROM_HERO: int = 200
STRIP_PROCEDURAL_STARS: int = 20
```

This makes iteration fast: change a number, re-run the capture tool, ship frame,
user critiques, repeat.

### Per-variant (unchanged from BLOQUE 58.15)

- `_STRIP_VARIANT_THEMES = ("blue_void", "teal", "gold_amber", "purple_dusk")`
- `_STRIP_VARIANT_SPRITE_INDICES = ((0, 3), (2, 0), (1, 2), (3, 1))`
  - Each variant uses 2 of the 4 sprite tints (blue/red/cyan/violet)
- `_STRIP_VARIANT_SEEDS = (0xB0DE_0001, 0xB0DE_0002, 0xB0DE_0003, 0xB0DE_0004)`
  - Per-variant deterministic seeds so each variant is reproducible

### Iteration flow

1. Implement v2 with the constants above
2. `tools/capture_strip_variants.py` is already in place from BLOQUE 58.15 — no
   changes needed (it instantiates `ParallaxBackground`, calls `set_strip_variant`,
   then `draw()` — picks up the new layout automatically via the constants)
3. Capture all 4 variants at 4 scroll positions = 16 frames, saved to
   `release/strip_variants/`
4. I show user the captures
5. User critiques (too many/sparse companions, wrong radii, etc.) — user
   describes the change, I adjust the constants
6. I re-render the captures
7. Repeat steps 4-6 until user approves

The user drives the iteration by giving visual feedback. I do not tweak the
constants without user input.

## Data flow

```
ParallaxBackground.__init__(rng_seed)
  -> _get_or_render_strip(variant)
       -> _render_galaxy_strip(theme, sprite_indices, seed)
            1. Solid bg fill (theme['bg'])
            2. Procedural stars (20, sized by roll)
            3. Hero galaxy (1, large, EDGE_PAD 200, sprite_indices[0])
            4. Small companions (3-5, within 100-150 px of hero, alternate tint)
            5. Background larges (2-3, random, min 200 px from hero)
            6. Glow overlay (parabolic, max_alpha=18)
       -> cache in self._strip_surfaces[variant]

ParallaxBackground.update(dt)
  -> advances self._strip_y_offset at GALAXY_STRIP_SPEED (25 px/s)
  -> mod GALAXY_STRIP_H (1440) for wrap

ParallaxBackground.draw(target)
  -> blits strip at (GALAXY_STRIP_X_OFFSET, -y_offset)
  -> blits strip again at (GALAXY_STRIP_X_OFFSET, -y_offset + 1440) for seamless wrap
  -> 5 layer stars (separate from strip stars)
  -> planet if any
```

## Error handling

- If no galaxy sprites are on disk (`_load_galaxy_sprites()` returns empty list),
  the strip falls back to bg fill only (existing behavior, unchanged).
- If `set_strip_variant` is called with out-of-range index, clamps to [0, 3].
- If a star color from theme swatches is missing, falls back to white.

## Testing strategy

### Unit tests (extend `tests/test_parallax.py`)

- `TestStripLayout`:
  - `test_hero_galaxy_count_is_1`: 1 hero galaxy per variant (was 3 large before)
  - `test_companion_count_in_range`: 3-5 companions per variant
  - `test_bg_galaxies_count_in_range`: 2-3 background galaxies per variant
  - `test_total_galaxies_in_range`: 6-9 total per variant
  - `test_star_count_is_20`: down from 70
  - `test_companions_within_distance_of_hero`: 100-150 px from hero
  - `test_bg_galaxies_min_distance_from_hero`: at least 200 px
- Update `test_4_variants_configured` to keep variant count = 4

### Visual verification

- `tools/capture_strip_variants.py`: render 4 variants × 4 scroll positions
  = 16 frames, save to `release/strip_variants/`
- User reviews and critiques
- Adjust constants + re-render until user approves

### Backward compat

- `ParallaxBackground.__init__` signature unchanged (no nebula_count etc.)
- `set_theme(name)` and `set_strip_variant(v)` still work
- `get_strip_variant()`, `get_strip_y_offset()`, `get_strip_height()` unchanged
- Tests that don't reference galaxy counts (TestGalaxyStrip, TestStripScroll,
  TestStripVariants, TestStripIsVisible) remain valid

## Open questions

None at this point. The user has answered:
- Too much info in the reference = the stars (not the galaxies)
- Preferred approach = clustered heroes (1 hero + 3-5 companions + 2-3 bg)
- Approved the design

## Ship analysis (locked-in, no change)

The new player ship is `ship_01_spritesheet.png`:
- 5 animations × 8 frames = 40 frames total
- Animations: IDLE, ROTATING, PROPULSION, CHARGING, DAMAGE
- Source: `Assets/sprites/player_ships/ship_01_base.png` (499 KB)
- Runtime: `Assets/sprites/player_ships/ship_01_spritesheet.png` (121 KB,
  the actual 40-frame sheet without the gallery labels)
- Integration: `d3c2ec3` (BLOQUE 58.61) + `7fd09bc` (NameError fix)
- Render scale: 0.55x via `self._player_sprite_scale` (sprite path)
- Cell inset: 1 px via `CELL_INSET` to exclude the FRAME_BORDER

The ship is correct, working, and not part of this spec. The user confirmed in
the brainstorming session that this is the locked-in new model.

## Files affected

- `src/systems/parallax.py` — add new constants, rewrite `_render_galaxy_strip()`
  to do hero + companions + background layout
- `tests/test_parallax.py` — add `TestStripLayout` class with the new assertions
- `tools/capture_strip_variants.py` — no changes; already in place and picks up
  the new layout via the constants

## Acceptance criteria

1. `pytest tests/test_parallax.py` passes all new `TestStripLayout` tests
2. `pytest` (full suite) passes (no regression; 1667+ pass expected)
3. `python tools/capture_strip_variants.py` produces 16 frames (4 variants ×
   4 scroll positions) saved to `release/strip_variants/`
4. User reviews the captures and approves the look (this is the iteration loop)
5. Visually, the strip has 1 hero galaxy + 3-5 companions clustered + 2-3
   background galaxies + ~20 stars, with the parabolic glow overlay
6. Each variant still uses 2 of the 4 sprite tints (round-robin distribution
   between hero/companions/background)
7. Each variant is deterministic (same seed → same pixels, verified by
   `test_each_variant_is_deterministic`)

## Out of scope (intentionally not in this spec)

- The cinematic video system (BLOQUE 58.59) — already shipped
- The player ship itself (BLOQUE 58.60) — already shipped
- The choreographed patterns as default mode (BLOQUE 58.62 / v1.1.5) — already shipped
- Tinting the strip based on the act (current act picks the variant) — already wired
- Per-instance jitter (BLOQUE 58.next / random offsets) — out of scope; the
  per-variant seeds give us determinism, jitter would be a separate feature
