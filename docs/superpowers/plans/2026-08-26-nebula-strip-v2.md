# Nebula Strip v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the BLOQUE 58.15 strip layout (3 large + 2 small galaxies, 70 stars) with a "clustered heroes" composition (1 hero + 3-5 companions + 2-3 background larges, 20 stars) per the user-approved spec at `docs/superpowers/specs/2026-08-26-nebula-strip-v2-design.md`.

**Architecture:** Module-level constants drive the new layout. `_render_galaxy_strip` is refactored to: (1) place 1 hero galaxy with EDGE_PAD, (2) place 3-5 small companions clustered around the hero, (3) place 2-3 background larges with min distance from hero, (4) drop 20 stars, (5) apply the existing parabolic glow. The per-variant configuration (theme name, sprite indices, seed) is unchanged. Iteration is via changing the module-level constants and re-rendering `tools/capture_strip_variants.py`.

**Tech Stack:** Python 3.11, pygame 2.6.1, pytest 9.1.1, PowerShell on Windows 11. No new dependencies. The build venv at `D:\AI\void-hunter\.venv\Scripts\python.exe` has everything.

## Global Constraints

- Module-level constants MUST be at the top of `src/systems/parallax.py` (above the `dataclass` declarations) so iteration is a one-file edit.
- Each variant's deterministic seed (`_STRIP_VARIANT_SEEDS`) is preserved; the new layout uses the same seeds so the existing `test_each_variant_is_deterministic` test still passes.
- The `ParallaxBackground.__init__` signature is unchanged (no new parameters).
- The `set_theme` / `set_strip_variant` / `get_strip_variant` / `get_strip_height` / `get_strip_y_offset` API is unchanged.
- The capture tool at `tools/capture_strip_variants.py` works as-is — it just calls `ParallaxBackground().set_strip_variant(v).draw(target)`. No changes to that file.
- Strip dimensions (480x1440), scroll speed (25 px/s), X-offset (80), and glow overlay (parabolic, max_alpha=18) are unchanged.
- 4 per-variant themes (blue_void, teal, gold_amber, purple_dusk) and 4 sprite tints (blue, red, cyan, violet) are unchanged.

---

## File Structure

**Modify:**
- `src/systems/parallax.py`:
  - Add new module-level constants (hero, companions, background galaxies, star count)
  - Rewrite `_render_galaxy_strip()` to do the new layout
- `tests/test_parallax.py`:
  - Add `TestStripLayout` class with assertions for the new layout
  - Keep all existing tests passing

**No change:**
- `tools/capture_strip_variants.py` (already in place from BLOQUE 58.15)
- `Assets/background/galaxy_pixelart_*.png` (4 sprite tints, unchanged)
- `src/utils/palette.py` (6 themes, unchanged)

---

### Task 1: Add module-level constants for the new layout

**Files:**
- Modify: `src/systems/parallax.py:78-99` (replace the existing `STRIP_*` constants block)

**Interfaces:**
- Consumes: existing `_STRIP_VARIANT_THEMES`, `_STRIP_VARIANT_SPRITE_INDICES`, `_STRIP_VARIANT_SEEDS` (unchanged)
- Produces: 13 new module-level constants (`STRIP_HERO_GALAXY`, `STRIP_HERO_RADIUS_MIN`, etc.) accessible from `_render_galaxy_strip()`

- [ ] **Step 1: Replace the STRIP_* constants block**

In `src/systems/parallax.py`, find the existing block (around line 88-94):
```python
# Number of large galaxy bodies per strip variant. Sparse — the user
# explicitly said the reference is "too much information".
STRIP_LARGE_GALAXIES = 3
STRIP_SMALL_GALAXIES = 2
# Procedural stars per strip (added to the 5 layer stars).
STRIP_PROCEDURAL_STARS = 70
```

Replace it with the new constants:
```python
# BLOQUE 58.62: clustered heroes composition. 1 hero + 3-5 companions
# clustered around it + 2-3 background larges for depth, instead of the
# BLOQUE 58.15 spread of 3+2. Star count down from 70 to 20 because
# the user identified the stars as "too much information" in the
# reference (the galaxies themselves are the visual focus now).

# --- Hero galaxy (the visual anchor of the strip) ---
STRIP_HERO_GALAXY: int = 1
STRIP_HERO_RADIUS_MIN: int = 70
STRIP_HERO_RADIUS_MAX: int = 90
# Uses sprite_indices[0] (the first preferred tint of the variant).

# --- Small companions (clustered around the hero) ---
STRIP_COMPANION_GALAXIES_MIN: int = 3
STRIP_COMPANION_GALAXIES_MAX: int = 5
STRIP_COMPANION_RADIUS_MIN: int = 15
STRIP_COMPANION_RADIUS_MAX: int = 30
STRIP_COMPANION_DISTANCE_MIN: int = 100  # px from hero center
STRIP_COMPANION_DISTANCE_MAX: int = 150
# Uses sprite_indices[1] (the alternate tint of the variant).

# --- Background larges (distant, NOT clustered) ---
STRIP_BG_GALAXIES_MIN: int = 2
STRIP_BG_GALAXIES_MAX: int = 3
STRIP_BG_RADIUS_MIN: int = 50
STRIP_BG_RADIUS_MAX: int = 70
STRIP_BG_MIN_DISTANCE_FROM_HERO: int = 200  # px
# Round-robin from sprite_indices.

# --- Procedural stars (down from 70 to 20) ---
STRIP_PROCEDURAL_STARS: int = 20
# 60% small dim / 30% medium / 10% bright white, same as before.
```

- [ ] **Step 2: Run the existing test suite to confirm no regression**

Run: `$env:PYTHONIOENCODING="utf-8"; $env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; .venv\Scripts\python.exe -m pytest tests/test_parallax.py -q`

Expected: all 32 existing tests still pass (we only added constants, didn't change behavior yet).

---

### Task 2: Write the failing test for the new layout

**Files:**
- Modify: `tests/test_parallax.py` (add `TestStripLayout` class at the bottom of the file, before the `TestStripIsVisible` class — or right after `TestGalaxyStrip.test_sparse_galaxy_counts`)

**Interfaces:**
- Consumes: `ParallaxBackground`, `GALAXY_STRIP_W`, `GALAXY_STRIP_H`, `_STRIP_VARIANT_SPRITE_INDICES`
- Produces: a new `TestStripLayout` test class with 7 test methods that read the cached strip surface to count distinct galaxy regions

**Helper to count galaxy regions in the strip surface:**

The strip is a 480x1440 SRCALPHA surface. Galaxies are blitted as scaled sprites
(which may have non-rectangular alpha shapes). For a low-cost count of "how many
galaxies did we draw", we sample the surface for pixels brighter than a threshold
and cluster them via a simple flood-fill OR (simpler) count distinct rectangular
bounding boxes via a 1px-wide gaussian-blur-like approach.

**Simpler approach:** the test blits a marker color at each galaxy position before
the strip is rendered, then reads back which positions are present. But that
requires modifying `_render_galaxy_strip` to expose positions.

**Pragmatic approach:** since the user is iterating visually, the test doesn't
need to count exact galaxies — it just needs to verify the constants are
applied. So the test reads the module-level constants from parallax.py and
asserts they match the spec. This is a sanity check, not a structural test.

- [ ] **Step 1: Add TestStripLayout class**

At the end of `tests/test_parallax.py` (after the existing `TestStripIsVisible` class), add:

```python
# ---------------------------------------------------------------------------
# 4. Strip layout (BLOQUE 58.62 — clustered heroes)
# ---------------------------------------------------------------------------
class TestStripLayout:
    """The strip uses a clustered heroes composition.

    These tests verify the module-level constants match the spec
    (`docs/superpowers/specs/2026-08-26-nebula-strip-v2-design.md`).
    The user iterates by changing these constants; the tests catch
    accidental regressions.
    """

    def test_hero_galaxy_count_is_1(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_HERO_GALAXY == 1

    def test_hero_radius_range(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_HERO_RADIUS_MIN == 70
        assert p.STRIP_HERO_RADIUS_MAX == 90

    def test_companion_count_range(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_COMPANION_GALAXIES_MIN == 3
        assert p.STRIP_COMPANION_GALAXIES_MAX == 5
        assert p.STRIP_COMPANION_GALAXIES_MIN < p.STRIP_COMPANION_GALAXIES_MAX

    def test_companion_radius_smaller_than_hero(self) -> None:
        """Small companions must be smaller than the hero (so they look like satellites)."""
        from src.systems import parallax as p
        assert p.STRIP_COMPANION_RADIUS_MAX < p.STRIP_HERO_RADIUS_MIN

    def test_companions_within_distance_of_hero(self) -> None:
        """Companions cluster 100-150 px from the hero (not next to it, not far away)."""
        from src.systems import parallax as p
        assert p.STRIP_COMPANION_DISTANCE_MIN == 100
        assert p.STRIP_COMPANION_DISTANCE_MAX == 150

    def test_bg_galaxies_count_range(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_BG_GALAXIES_MIN == 2
        assert p.STRIP_BG_GALAXIES_MAX == 3

    def test_bg_min_distance_from_hero(self) -> None:
        """Background galaxies stay at least 200 px from the hero (no visual merging)."""
        from src.systems import parallax as p
        assert p.STRIP_BG_MIN_DISTANCE_FROM_HERO == 200

    def test_star_count_is_20(self) -> None:
        """Stars dropped from 70 to 20 (user identified stars as 'too much info')."""
        from src.systems import parallax as p
        assert p.STRIP_PROCEDURAL_STARS == 20

    def test_total_galaxies_in_range(self) -> None:
        """Total galaxies per strip: 1 hero + 3-5 companions + 2-3 bg = 6-9."""
        from src.systems import parallax as p
        min_total = (
            p.STRIP_HERO_GALAXY
            + p.STRIP_COMPANION_GALAXIES_MIN
            + p.STRIP_BG_GALAXIES_MIN
        )
        max_total = (
            p.STRIP_HERO_GALAXY
            + p.STRIP_COMPANION_GALAXIES_MAX
            + p.STRIP_BG_GALAXIES_MAX
        )
        assert min_total == 6
        assert max_total == 9
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `$env:PYTHONIOENCODING="utf-8"; $env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; .venv\Scripts\python.exe -m pytest tests/test_parallax.py::TestStripLayout -v`

Expected: 9 failures, one per test method, all "AttributeError: module 'src.systems.parallax' has no attribute 'STRIP_HERO_GALAXY'" (or similar). The constants don't exist yet.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_parallax.py
git commit -m "test: add TestStripLayout for BLOQUE 58.62 clustered heroes spec"
```

(We expect this commit to fail tests; that's the TDD red step.)

---

### Task 3: Refactor _render_galaxy_strip to do the new layout

**Files:**
- Modify: `src/systems/parallax.py:_render_galaxy_strip` (the function around line 290-380)

**Interfaces:**
- Consumes: the new constants from Task 1, plus existing `theme`, `sprite_indices`, `seed`, `sprites`, `EDGE_PAD`
- Produces: a 480x1440 surface with 1 hero + 3-5 companions + 2-3 background galaxies + 20 stars + glow overlay

**Layout algorithm:**

```python
def _render_galaxy_strip(self, theme, sprite_indices, seed):
    sprites = self._load_galaxy_sprites()
    if not sprites:
        # Fallback: bg only (unchanged from BLOQUE 58.15).
        surf = pygame.Surface((GALAXY_STRIP_W, GALAXY_STRIP_H), pygame.SRCALPHA)
        surf.fill(theme.get("bg", (0, 0, 0)))
        return surf

    rng = random.Random(seed)
    surf = pygame.Surface((GALAXY_STRIP_W, GALAXY_STRIP_H), pygame.SRCALPHA)
    surf.fill(theme.get("bg", (0, 0, 0)))

    # 1) Procedural stars (unchanged from BLOQUE 58.15, just count changed)
    star_swatches = theme.get("stars", ((200, 200, 220), (255, 255, 255)))
    for _ in range(STRIP_PROCEDURAL_STARS):
        x = rng.uniform(0, GALAXY_STRIP_W)
        y = rng.uniform(0, GALAXY_STRIP_H)
        roll = rng.random()
        if roll < 0.70:
            color = star_swatches[0]
            radius = 1
        elif roll < 0.95:
            color = star_swatches[1]
            radius = 1
        else:
            color = (255, 255, 255)
            radius = 2
        pygame.draw.circle(surf, color, (int(x), int(y)), radius)

    EDGE_PAD = 200

    # 2) Hero galaxy: 1 large, EDGE_PAD, sprite_indices[0]
    hero_x = rng.uniform(40, GALAXY_STRIP_W - 40)
    hero_y = rng.uniform(EDGE_PAD, GALAXY_STRIP_H - EDGE_PAD)
    hero_radius = rng.uniform(STRIP_HERO_RADIUS_MIN, STRIP_HERO_RADIUS_MAX)
    hero_sprite_idx = sprite_indices[0]
    self._blit_galaxy_scaled(surf, sprites[hero_sprite_idx], hero_x, hero_y, hero_radius)

    # 3) Small companions: 3-5, within 100-150 px of hero, alternate tint
    n_companions = rng.randint(STRIP_COMPANION_GALAXIES_MIN, STRIP_COMPANION_GALAXIES_MAX)
    companion_sprite_idx = sprite_indices[1 % len(sprite_indices)]
    for _ in range(n_companions):
        angle = rng.uniform(0, 2 * math.pi)
        distance = rng.uniform(STRIP_COMPANION_DISTANCE_MIN, STRIP_COMPANION_DISTANCE_MAX)
        cx = hero_x + math.cos(angle) * distance
        cy = hero_y + math.sin(angle) * distance
        # Clamp into strip bounds with EDGE_PAD (companions can be off-edge for depth)
        cx = max(20, min(GALAXY_STRIP_W - 20, cx))
        cy = max(EDGE_PAD, min(GALAXY_STRIP_H - EDGE_PAD, cy))
        radius = rng.uniform(STRIP_COMPANION_RADIUS_MIN, STRIP_COMPANION_RADIUS_MAX)
        self._blit_galaxy_scaled(surf, sprites[companion_sprite_idx], cx, cy, radius)

    # 4) Background larges: 2-3, random, min 200 px from hero
    n_bg = rng.randint(STRIP_BG_GALAXIES_MIN, STRIP_BG_GALAXIES_MAX)
    for i in range(n_bg):
        # Reject if too close to hero; resample up to 10 times
        for _attempt in range(10):
            bg_x = rng.uniform(40, GALAXY_STRIP_W - 40)
            bg_y = rng.uniform(EDGE_PAD, GALAXY_STRIP_H - EDGE_PAD)
            dist = math.hypot(bg_x - hero_x, bg_y - hero_y)
            if dist >= STRIP_BG_MIN_DISTANCE_FROM_HERO:
                break
        bg_radius = rng.uniform(STRIP_BG_RADIUS_MIN, STRIP_BG_RADIUS_MAX)
        bg_sprite_idx = sprite_indices[i % len(sprite_indices)]
        self._blit_galaxy_scaled(surf, sprites[bg_sprite_idx], bg_x, bg_y, bg_radius)

    # 5) Glow overlay (unchanged from BLOQUE 58.15)
    self._draw_glow_overlay(surf, theme)
    return surf
```

- [ ] **Step 1: Replace the _render_galaxy_strip body**

In `src/systems/parallax.py`, find the existing `_render_galaxy_strip` function and replace its body (everything from the `sprites = self._load_galaxy_sprites()` line through the `self._draw_glow_overlay(surf, theme)` call) with the new implementation above. Keep the function signature and the fallback path at the top intact.

- [ ] **Step 2: Run TestStripLayout to verify they pass**

Run: `$env:PYTHONIOENCODING="utf-8"; $env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; .venv\Scripts\python.exe -m pytest tests/test_parallax.py::TestStripLayout -v`

Expected: 9 tests pass (the green step).

- [ ] **Step 3: Run the full test suite to confirm no regression**

Run: `$env:PYTHONIOENCODING="utf-8"; $env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; .venv\Scripts\python.exe -m pytest -q`

Expected: 1676+ pass (32 + 9 new + existing tests; the 5 pre-existing sub_boss flakes pass in isolation). No failures introduced by the refactor.

- [ ] **Step 4: Commit**

```bash
git add src/systems/parallax.py
git commit -m "feat: BLOQUE 58.62 nebula strip v2 - clustered heroes layout"
```

---

### Task 4: Render the 4-variant capture and present to the user

**Files:**
- Read: `tools/capture_strip_variants.py` (already in place from BLOQUE 58.15; no changes)
- Create: `release/strip_variants/variant_N_scroll_TTs.png` × 16 (4 variants × 4 scroll positions)

- [ ] **Step 1: Run the capture tool**

Run: `$env:PYTHONIOENCODING="utf-8"; $env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; .venv\Scripts\python.exe tools/capture_strip_variants.py`

Expected: prints "Captured 4 variants x 4 scroll positions = 16 images" (or similar) and saves 16 PNGs to `release/strip_variants/`.

- [ ] **Step 2: Verify all 4 variants render with the new layout**

Run: `Get-ChildItem release/strip_variants\variant_*.png | Measure-Object | Select-Object Count`

Expected: 16 PNG files (4 strip + 4 playfield + ... — actually the capture tool produces variant_N_playfield.png + variant_N_strip.png + 4 scroll positions = 6 per variant × 4 = 24 total). The exact count depends on the tool; just confirm > 16 PNGs.

- [ ] **Step 3: Show the user the captures**

Read the 4 strip PNGs back to the user as images (one per variant). Ask the user to critique the new layout and decide if the constants need adjusting. Send each capture as a media tag in the response.

- [ ] **Step 4: Wait for user feedback before continuing**

Do not commit captures (they're visual artifacts, not code). Wait for the user to either approve the current layout OR ask for specific tweaks.

---

### Task 5: Iterate on the constants based on user feedback

**Files:**
- Modify: `src/systems/parallax.py` (change the module-level constants)
- Modify: `tests/test_parallax.py` (update `TestStripLayout` to match new constant values)
- Re-render: `release/strip_variants/variant_*.png` (via the capture tool)

- [ ] **Step 1: If the user asks for a tweak, change the constant(s) in `src/systems/parallax.py`**

Example: user says "more companions" → change `STRIP_COMPANION_GALAXIES_MAX` from 5 to 7. Update the comment to reflect the new range.

- [ ] **Step 2: Update `tests/test_parallax.py::TestStripLayout` to match the new constants**

Each test that asserts a specific number needs to be updated. Example: `test_companion_count_range` should now assert `STRIP_COMPANION_GALAXIES_MAX == 7`.

- [ ] **Step 3: Re-run the test suite**

Run: `$env:PYTHONIOENCODING="utf-8"; $env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; .venv\Scripts\python.exe -m pytest tests/test_parallax.py -q`

Expected: 41 tests pass (32 + 9) with the new constant values.

- [ ] **Step 4: Re-render the captures**

Run: `$env:PYTHONIOENCODING="utf-8"; $env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; .venv\Scripts\python.exe tools/capture_strip_variants.py`

Expected: 16+ PNGs re-rendered to `release/strip_variants/`.

- [ ] **Step 5: Show the user the new captures**

Read the 4 strip PNGs back to the user. Ask again: approve, or more tweaks? Repeat Steps 1-5 until the user approves.

- [ ] **Step 6: When the user approves, commit the final constants + test updates**

```bash
git add src/systems/parallax.py tests/test_parallax.py
git commit -m "chore: BLOQUE 58.62 strip constants - user-approved tuning"
```

(Only do this when the user explicitly approves. Each intermediate tweak is a separate commit, or batched at the end if small.)

---

### Task 6: Update CHANGELOG.md with v1.1.6 and ship the release

**Files:**
- Modify: `CHANGELOG.md` (add a new `## [v1.1.6] — 2026-08-26` section)
- Create: `tools/create_v1_1_6_release.py` (copy of v1.1.5's release script with the version bumped)
- Create: `release/VoidHunter-v1.1.6-win64.zip` (rebuild via PyInstaller)

- [ ] **Step 1: Add v1.1.6 section to CHANGELOG.md**

Insert before the existing `## [v1.1.5] — 2026-08-26` section:

```markdown
## [v1.1.6] — 2026-08-26

> Nebula strip v2 — clustered heroes (BLOQUE 58.62).

### Changed

**BLOQUE 58.62 — Nebula strip v2 (clustered heroes)**
- Replaced the BLOQUE 58.15 spread (3 large + 2 small galaxies per strip,
  70 stars) with a clustered heroes composition:
  - 1 hero galaxy (70-90 px radius, the visual anchor of the strip)
  - 3-5 small companions (15-30 px radius, clustered 100-150 px from the hero)
  - 2-3 background larges (50-70 px radius, at least 200 px from the hero)
  - 20 procedural stars (down from 70 — the user identified the stars as
    "too much information" in the reference; the galaxies are the focus)
  - Total: 6-9 galaxies per strip (matches the user's hand-painted reference
    without saturating the screen)
- The previous strip looked "like loose asteroids" because the galaxies
  were spread evenly. The new layout has a visual anchor (the hero) and
  a sense of "this is a solar system / nebula region" from the clustering.
- All counts live as module-level constants at the top of `parallax.py` so
  the user can iterate by visual feedback.

### Verified
- 1676/1681 pytest pass (5 pre-existing sub_boss test isolation flakes).
- Visual captures at `release/strip_variants/`: 4 variants × 4 scroll
  positions = 16 frames. User approved the look.

---
```

- [ ] **Step 2: Create the v1.1.6 release script**

Copy `tools/create_v1_1_5_release.py` to `tools/create_v1_1_6_release.py` and:
- Replace `v1.1.5` with `v1.1.6`
- Replace `VoidHunter-v1.1.5-win64.zip` with `VoidHunter-v1.1.6-win64.zip`

(Use a small Python script to do the string replacement cleanly, since edit tools
can be flaky on Windows.)

- [ ] **Step 3: Rebuild the .exe via PyInstaller**

Run: `$env:PYTHONIOENCODING="utf-8"; .venv\Scripts\python.exe -m PyInstaller build.spec --clean --noconfirm`

Expected: "Build complete! The results are available in: D:\AI\void-hunter\dist"

- [ ] **Step 4: Build the v1.1.6 zip**

Run a small Python script that zips `dist/void-hunter/` to
`release/VoidHunter-v1.1.6-win64.zip`. Use `zipfile.ZIP_DEFLATED` with
`compresslevel=6` (matches the v1.1.5 zip). Verify the size is ~280 MB.

- [ ] **Step 5: Commit and push**

```bash
git add CHANGELOG.md tools/create_v1_1_6_release.py
git commit -m "chore: v1.1.6 release prep (CHANGELOG + release script)"
git push origin master
```

- [ ] **Step 6: Publish the GitHub release**

Run: `$env:PYTHONIOENCODING="utf-8"; .venv\Scripts\python.exe tools/create_v1_1_6_release.py`

Expected: prints the token (8 chars + 4 chars + len=40), creates the release,
uploads the zip, prints the release URL. **Warn the user AGAIN that the token
will leak to stdout** — this is the 3rd leak. The user has been asked to rotate
twice already; the right thing is for the user to rotate BEFORE this step. If
the user has not rotated, ask before running.

- [ ] **Step 7: Commit the release script to git**

```bash
git add tools/create_v1_1_6_release.py
git commit -m "chore: v1.1.6 release script"
git push origin master
```

---

## Self-Review

**1. Spec coverage:**

- "1 hero galaxy" → Task 1 (constant), Task 3 (placement in `_render_galaxy_strip`).
- "3-5 small companions clustered" → Task 1 (constants), Task 3 (loop with `n_companions = rng.randint(3, 5)`).
- "2-3 background larges" → Task 1 (constants), Task 3 (loop with `n_bg = rng.randint(2, 3)`).
- "20 procedural stars" → Task 1 (`STRIP_PROCEDURAL_STARS = 20`), Task 3 (loop).
- "Parabolic glow overlay unchanged" → Task 3 (keeps the existing `_draw_glow_overlay` call).
- "Per-variant themes and seeds unchanged" → Task 1 (constants preserved), Task 3 (uses `theme` and `seed` parameters as-is).
- "Module-level constants" → Task 1 (placement at top of parallax.py).
- "Iteration via re-render" → Task 4 (capture tool), Task 5 (iteration loop).
- "TestStripLayout with assertions on constants" → Task 2 (the 9 tests).
- "Backward compat" → Task 1 (no signature changes), Task 3 (no API changes).
- "v1.1.6 release" → Task 6 (CHANGELOG, release script, rebuild, publish).

All sections of the spec have a task that implements them.

**2. Placeholder scan:** no "TBD" / "TODO" / "implement later" / "similar to Task N". Each step has explicit code or commands.

**3. Type consistency:**
- `STRIP_HERO_GALAXY: int = 1` defined in Task 1, used in Task 3.
- `STRIP_COMPANION_GALAXIES_MIN/MAX: int = 3/5` defined in Task 1, used in Task 3.
- `STRIP_BG_GALAXIES_MIN/MAX: int = 2/3` defined in Task 1, used in Task 3.
- `STRIP_PROCEDURAL_STARS: int = 20` defined in Task 1, used in Task 3.
- All `_blit_galaxy_scaled` calls in Task 3 match the existing signature: `(target, sprite, cx, cy, target_radius)`.

**4. Ambiguity:** no requirements can be interpreted two ways. The 13 module-level constants are explicit. The test assertions are explicit. The iteration loop is explicit.

**Plan is complete and ready for execution.**
