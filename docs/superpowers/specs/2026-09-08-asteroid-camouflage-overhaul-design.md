# Asteroid Camouflage Overhaul — BLOQUE 61/62/63 Design

**Date:** 2026-09-08
**Status:** READY FOR REVIEW
**Author:** Lerius (idea) + Mavis (draft)
**Branch:** master
**Aesthetic anchor:** MINE-ASTEROID reference image (user-provided 2026-09-08)

---

## Overview

Three coordinated BLOQUEs that overhaul the visual + gameplay relationship between asteroids and a new camouflage enemy. Together they:

1. **BLOQUE 61** — Replace the procedural asteroid generator with 5 AI-generated 16-bit sprites inspired by the user-provided MINE-ASTEROID reference image. All 5 variants are lookalikes of the MINE-ASTEROID closed state, guaranteeing perfect camouflage.
2. **BLOQUE 62** — Regenerate all 8 ships (1 player + 7 enemies) with strict top-down perspective (no 3/4 angle) so every ship reads as a bird's-eye view at the same perspective.
3. **BLOQUE 63** — Add `EnemyKind.MINE_ASTEROID`, a new enemy that uses the asteroid aesthetic as camouflage: it drifts like a regular asteroid, opens to fire when in range, then closes and continues drifting.

The aesthetic anchor is the MINE-ASTEROID sprite the user provided on 2026-09-08: brown rocky body, Greek-key stripe across the equator with 5-6 square teeth, 1-3 craters, hidden gun revealed when the two halves split horizontally.

---

## Section 1: Architecture and Order

### BLOQUE dependency graph

```
BLOQUE 61 (asteroid sprites)  ─┐
                                ├──>  BLOQUE 63 (MINE-ASTEROID enemy)
BLOQUE 62 (top-down ships)    ─┘
```

- BLOQUE 61 → BLOQUE 63: the MINE-ASTEROID `closed` sprite reuses one of the 5 asteroid variants from BLOQUE 61 (the `round` variant is the proposed canonical).
- BLOQUE 62 → BLOQUE 63: BLOQUE 63 builds on the top-down perspective validated in BLOQUE 62.
- BLOQUE 61 and BLOQUE 62 are independent and could be parallelized, but the recommended order is sequential so visual validation happens incrementally.

### Execution order: 61 → 62 → 63

1. **BLOQUE 61 first** — establishes the new asteroid aesthetic. Validating 5 visually distinct lookalike variants before investing ~24 min in AI regen of ships avoids cascading rework.
2. **BLOQUE 62 second** — ships regenerated with already-validated style and the prompt that was updated today to drop "3/4 angle".
3. **BLOQUE 63 last** — depends on sprites from 61 and perspective from 62. Doing it last means we have a stable asset pipeline to attach the new enemy to.

### What is NOT changed (preserved across all 3 BLOQUEs)

- Game loop, scene manager, audio system, HUD, BGM
- Roguelike seed and level generation
- Formation system, bezier paths
- GOLIATH boss state machine (already top-down, BLOQUE 60)
- Powerup drop rate (30%) and base distribution (BOMB/HP/WEAPON/SCORE)
- Bullet-asteroid collision (1-3 HP)
- WINDOW_TITLE regex (relaxed in BLOQUE 60)
- `audio_status.log` path fix (BLOQUE 60 main.py)
- Test framework (pytest), all 2491 existing tests must still pass

### What IS changed

- `src/entities/asteroid.py` (procedural → sprite loader)
- `Assets/sprites/asteroids/` (NEW directory, 5 PNGs)
- `tools/redesign_ships/01_generate_bases.py` (prompt header already updated today, no further change)
- `Assets/sprites/redesign/_base/{enemy_*,ship_01}_base.png` (regenerated)
- `Assets/sprites/player_ships/ship_01/<state>/frame_NN.png` (regenerated)
- `Assets/sprites/enemies/<kind>/<state>/frame_NN.png` (regenerated for 7 enemies)
- `src/entities/enemies/enemy.py` (new `EnemyKind.MINE_ASTEROID` + state machine)
- `src/systems/projectile.py` (new `BULLET_ENEMY_MINE` kind)
- `src/systems/wave_manager.py` (MINE-ASTEROID spawn pool)

### Testing strategy (consistent with BLOQUE 59/60)

Each BLOQUE adds its own `tests/test_bloque_NN_*.py` with ~20-25 tests:
- Unit tests for new code paths
- Integration tests for state machines + collision
- Visual verification via capture scripts that produce PNGs at key states

---

## Section 2: BLOQUE 61 — Asteroid Visual Overhaul

### Goal

Replace the procedural asteroid generator in `src/entities/asteroid.py` with 5 AI-generated 32×32 sprites that match the MINE-ASTEROID aesthetic. All 5 variants are MINE-ASTEROID closed lookalikes with distinct shapes — perfect camouflage guarantee.

### Asset generation

- 5 prompts, each generating a MINE-ASTEROID closed variant with a distinct shape:
  - `round` — squat potato, lots of craters (the canonical MINE-ASTEROID, becomes BLOQUE 63's `closed` sprite)
  - `elongated` — horizontal stretched, single big Greek-key band
  - `spiked` — 3-4 mineral protrusions sticking out
  - `hollowed` — one big crater on one side (hint of the MINE-ASTEROID `open` state without the ship)
  - `cracked` — one diagonal surface crack running across the body
- Reference image: MINE-ASTEROID.png (user-provided) passed to mcode-tools as a style anchor
- Resolution: 1024×1024 base AI image → LANCZOS resize to 32×32
- Background: pure black, transparentized via `_transparentize_damero_after_resize` (existing helper from BLOQUE 59, already exposed and tested)
- Output: `Assets/sprites/asteroids/<variant>.png` (5 PNGs total)
- AI generation time: ~3 min × 5 = ~15 min total

### Code changes (`src/entities/asteroid.py`)

`Asteroid` dataclass:

```python
@dataclass
class Asteroid:
    x: float
    y: float
    radius: int  # kept for backward compat (collision math), but visually ignored
    hp: int
    drift_vx: float = 0.0
    drift_vy: float = 30.0
    # REMOVED: rotation, rotation_speed (no in-game rotation)
    # NEW:
    variant: int = 0          # 0-4 index into _ASTEROID_SPRITES
    scale: float = 1.0        # 0.7-1.3 from spawn
    hidden_powerup: Optional[PowerupKind] = None
    powerup_dropped: bool = False
    active: bool = True
```

Functions:
- `_make_asteroid_sprite(radius, rng)` → **REMOVED** (no more procedural generation)
- NEW `_load_asteroid_sprite(variant: int) -> pygame.Surface`: lazy load + cache of 5 PNGs from `Assets/sprites/asteroids/`. Returns the surface at base 32×32.
- `draw_asteroid(target, ast)`: blit at `(x, y)` without rotation, using `variant` and `scale`
- `spawn_asteroid(rng, x=-1, y=-1)`: pick `variant=rng.randint(0, 4)`, `scale=rng.uniform(0.7, 1.3)`. `radius` defaults to `int(16 * scale)` for collision math.

### What does NOT change in `asteroid.py`

- `PowerupKind` enum
- `Powerup` dataclass (powerup drops)
- `pick_random_powerup` (weighted distribution)
- `hit()` method (HP logic)
- `update(dt)` for x/y drift
- `is_off_screen()` method
- `_BROWN_*` constants (no longer used, can stay as dead code for now)

### Visual verification

`tools/capture/capture_bloque_61_asteroids.py`:
- Spawn one of each variant (5 total) at evenly spaced positions
- Capture PNG: `tools/playtest_out/bloque_61_5_variants.png`
- Visually confirm: 5 visually distinct MINE-ASTEROID closed shapes, all with brown rocky + Greek-key band + craters

### Tests (NEW: `tests/test_asteroid_sprites.py`, ~20 tests)

- `test_5_variant_files_exist`: 5 PNGs in `Assets/sprites/asteroids/`
- `test_each_variant_is_32x32`: each PNG is exactly 32×32 pixels
- `test_each_variant_has_transparent_background`: alpha=0 on majority of edge pixels
- `test_spawn_picks_variant_in_0_to_4`: 1000 spawns, all variants 0-4
- `test_spawn_picks_scale_in_0_7_to_1_3`: 1000 spawns, all scales in range
- `test_asteroid_dataclass_no_rotation_field`: `rotation` and `rotation_speed` removed
- `test_draw_asteroid_loads_correct_variant`: `draw_asteroid` blits the PNG for `ast.variant`
- `test_draw_asteroid_applies_scale`: rendered surface size == 32 × scale
- `test_no_pygame_rotate_call`: `pygame.transform.rotate` is NOT invoked in `draw_asteroid`
- `test_powerup_drop_rate_unchanged`: 1000 spawns, ~30% have `hidden_powerup`
- `test_collision_unchanged`: `hit(damage)` and `is_off_screen` still work
- `test_spawn_no_visual_difference_in_render`: 5 spawned asteroids render to 5 distinct surfaces
- `test_asteroid_variants_share_palette`: 5 PNGs use overlapping brown colors (sanity check)

---

## Section 3: BLOQUE 62 — Full Top-Down Ship Pass

### Goal

Regenerate all 8 ship bases (1 player + 7 enemies) with the updated prompt (no 3/4 angle) so every ship reads as a bird's-eye view at the same perspective.

### Ships to regenerate (8 total)

- Player: `ship_01`
- Enemies: `scout`, `drone`, `interceptor`, `fighter`, `turret`, `warship`, `cruiser`

### Pipeline (existing from BLOQUE 59, prompt already updated today)

1. `tools/redesign_ships/01_generate_bases.py` — runs mcode-tools with the updated `PROMPT_TEMPLATE`
2. `tools/redesign_ships/02_postprocess.py` — transparentize damero, LANCZOS resize to 30×24
3. `tools/redesign_ships/_animation_frames.py` — 5 anims × 10 frames (idle/thrust/damage/death/extra)
4. `tools/redesign_ships/03_build_sheets.py` — sprite sheet assembly
5. `tools/redesign_ships/04_integrate.py` — moves PNGs to `Assets/sprites/{player_ships,enemies}/`

### Prompt header (already updated today, no further change)

```python
PROMPT_TEMPLATE = (
    "16-bit pixel art, STRICT TOP-DOWN VIEW (perpendicular, no 3/4 angle) "
    "viewed from directly above the ship. The ship's NOSE points DOWN "
    "toward the bottom of the image. WINGS spread OUT to the left and "
    "right sides of the image. ENGINES at the TOP of the image (rear of "
    "ship). COCKPIT/CANOPY visible on the upper body. Single isolated "
    "ship on pure black background. "
    "Sharp clean pixel edges, no anti-aliasing, no gradients, limited "
    "palette (max 8 colors), Metal Slug aesthetic. "
    "Character: {FILL}. "
)
```

For the player ship (`ship_01`), the existing infrastructure already handles the `face_down=False` case: the prompt is mirrored so the NOSE points UP (player flies up, enemies fly down).

### Code changes

- `tools/redesign_ships/_ship_specs.py`: confirm `face_down=True` for all 7 enemy specs, `face_down=False` for player
- `tools/redesign_ships/01_generate_bases.py`: `PROMPT_TEMPLATE` already updated today, no further change needed
- `tools/redesign_ships/02_postprocess.py`: already supports `face_down` parameter, no change
- `src/ui/scenes.py:_load_sprite`: no change (already handles 5 anims × 10 frames)
- `Assets/sprites/redesign/_base/{enemy_*,ship_01}_base.png`: **REGENERATED** (8 PNGs)
- `Assets/sprites/player_ships/ship_01/<state>/frame_NN.png`: **REGENERATED** (40 PNGs)
- `Assets/sprites/enemies/<kind>/<state>/frame_NN.png`: **REGENERATED** (7 × 40 = 280 PNGs)

### Time estimate

~3 min × 8 = ~24 min AI generation + ~5 min postprocess + ~5 min integrate = ~35 min total

### Visual verification

`tools/capture/capture_bloque_62_ships.py`:
- Render player + 7 enemies in a 4×2 grid
- Capture PNG: `tools/playtest_out/bloque_62_8_ships.png`
- Visually confirm: all 8 ships have NOSE on the correct side (down for enemies, up for player) and consistent top-down perspective

### Tests (NEW: `tests/test_ship_perspective.py`, ~25 tests)

- `test_no_3_4_in_manifest`: `tools/redesign_ships/manifest.json` prompts do NOT contain "3/4"
- `test_no_3_4_in_ship_specs`: `_ship_specs.py` prompts do NOT contain "3/4"
- `test_no_3_4_in_postprocess_module`: `02_postprocess.py` does not contain "3/4"
- `test_no_3_4_in_generate_bases`: `01_generate_bases.py` does not contain "3/4"
- `test_all_8_ship_bases_exist`: 8 base PNGs regenerated with current timestamps
- `test_player_ship_anim_frames`: `ship_01/<state>/frame_NN.png` for 5 states × 10 frames
- `test_enemy_ship_anim_frames`: 7 enemies each have 5 anims × 10 frames
- `test_enemy_sprite_faces_down`: heuristic check — brightest "nose" pixel at y > 50% of image
- `test_player_sprite_faces_up`: heuristic check — brightest "nose" pixel at y < 50% of image
- `test_sprite_sheet_count`: 5 sprite sheets exist in `Assets/sprites/ships/`
- `test_enemy_face_down_flag`: `_ship_specs.py` has `face_down=True` for all 7 enemies
- `test_player_face_down_flag_false`: player spec has `face_down=False`
- `test_collision_unaffected`: enemy hitboxes unchanged (24×24)
- `test_player_movement_unaffected`: player movement code untouched
- ... (~10 more for edge cases and integration)

---

## Section 4: BLOQUE 63 — MINE-ASTEROID as EnemyKind

### Goal

Add a new enemy that uses the asteroid aesthetic as camouflage: it looks identical to a regular asteroid, opens to fire when it reaches the upper portion of the playfield (shortly after entering the visible area), then closes and continues drifting. The tension is the camouflage: the player must shoot asteroids to find the MINE-ASTEROID, but is rewarded when they do.

### Assets (depends on BLOQUE 61)

- **closed**: REUSE the `round` variant from BLOQUE 61 (one of the 5 asteroid PNGs). Path: `Assets/sprites/enemies/mine_asteroid/closed/frame_00.png` = a copy or symlink of `Assets/sprites/asteroids/round.png`.
- **opening** (3 frames): NEW AI gen — same outline as `closed` but with the horizontal seam starting to split, gun barrel partially visible. Paths: `opening/frame_00..02.png`.
- **open** (1 frame): NEW AI gen — the two halves separated by ~30% of asteroid diameter, gun barrel fully visible pointing down, cockpit + thrusters visible inside the seam. Path: `open/frame_00.png`.
- **closing** (3 frames): mirror of opening for symmetry. Paths: `closing/frame_00..02.png`.
- **death** (10 frames): asteroid halves fly apart in 10 frames, ship explodes in the middle, fragments scatter. Paths: `death/frame_00..09.png`.

Time: ~3 min × 3 AI gens (opening/open/closing share the open as a guide, so we batch the 3 together) + ~5 min postprocess + death 10 frames = ~14 min total.

### Code changes

**`src/entities/enemies/enemy.py`:**

```python
class EnemyKind(Enum):
    SCOUT = "scout"
    DRONE = "drone"
    INTERCEPTOR = "interceptor"
    FIGHTER = "fighter"
    TURRET = "turret"
    WARSHIP = "warship"
    CRUISER = "cruiser"
    MINE_ASTEROID = "mine_asteroid"  # NEW (BLOQUE 63)
```

State machine for MINE_ASTEROID:

| State | Duration | Behavior | Bullet collision | Player collision |
|-------|----------|----------|------------------|------------------|
| `closed` | indefinite | Drift down like asteroid | NO (immune) | YES (damage) |
| `opening` | 0.5s | Transition frames, no fire | YES (vulnerable) | YES |
| `open` | 0.3s | Fire 3 bullets in fan pattern | YES (vulnerable) | YES |
| `closing` | 0.5s | Transition frames, no fire | YES (vulnerable) | YES |
| `closed` (post-cycle) | indefinite | Drift down, has_opened=True (no re-trigger) | NO | YES |

Trigger: state transitions from `closed` to `opening` when `y < OPENING_Y_THRESHOLD` AND `has_opened == False`. The default threshold is **`OPENING_Y_THRESHOLD = 200`** (the upper portion of the playfield, near where the MINE-ASTEROID spawns). This was the user's explicit choice in brainstorming: the MINE-ASTEROID opens shortly after entering the visible area, fires down at the player (who is at the bottom of the screen), then closes and continues drifting off-screen. The threshold is a named constant so it can be tuned in one place.

**`Enemy` dataclass additions (for MINE_ASTEROID only):**

```python
state: str = "closed"             # "closed" | "opening" | "open" | "closing"
state_timer: float = 0.0
has_opened: bool = False
mine_variant: int = 0            # 0-4, mirrors Asteroid.variant for closed-state visual
```

**`update(dt)` for MINE_ASTEROID (logic sketch):**

```python
if self.kind == EnemyKind.MINE_ASTEROID:
    if self.state == "closed":
        if not self.has_opened and self.y < OPENING_Y_THRESHOLD:  # y < 200 = upper playfield
            self.state = "opening"
            self.state_timer = 0.0
    elif self.state == "opening":
        self.state_timer += dt
        if self.state_timer >= 0.5:
            self.state = "open"
            self.state_timer = 0.0
            self._fire_mine_bullets()
    elif self.state == "open":
        self.state_timer += dt
        if self.state_timer >= 0.3:
            self.state = "closing"
            self.state_timer = 0.0
    elif self.state == "closing":
        self.state_timer += dt
        if self.state_timer >= 0.5:
            self.state = "closed"
            self.state_timer = 0.0
            self.has_opened = True
```

**`_fire_mine_bullets()`:** 3 bullets at angles `0°`, `±15°` from straight down, speed 80 px/s, kind `BULLET_ENEMY_MINE`.

**HP:** 2 (1 hit destroys when vulnerable). When `state == "closed"`, `hit()` returns `False` (immune, no damage applied).

**Powerup drop:** 50% chance on destroy. Pool = `BOMB | HP | WEAPON` (no SCORE — the camo tension is the reward, not the points).

**`src/systems/projectile.py`:** add `BULLET_ENEMY_MINE = "bullet_enemy_mine"` to projectile kinds. Color: dark gray (gun color), small (2×4 px).

**`src/entities/asteroid.py` integration:** MINE-ASTEROIDs spawn from the SAME pool as asteroids but with `kind=EnemyKind.MINE_ASTEROID` discriminator. Visually identical to asteroids when `closed`.

**`src/systems/wave_manager.py`:** in `spawn_wave()`, allocate 1/8 of "obstacle" spawns to `EnemyKind.MINE_ASTEROID`. The remaining 7/8 are regular `Asteroid` instances.

### What does NOT change

- All existing enemy kinds (scout, drone, etc.) — MINE_ASTEROID is purely additive
- Player weapons, bullet pool, score system
- BGM, sound effects (no new SFX for opening/closing; can add later)
- Existing `Asteroid.update()` x/y drift (reused for MINE-ASTEROID)

### Visual verification

`tools/capture/capture_bloque_63_mine_asteroid.py`:
- Spawn 1 MINE-ASTEROID + 3 regular asteroids
- Capture sequence: t=0 (closed/camo), t=2s (opening), t=2.5s (open + fire), t=3s (closing)
- PNGs: `tools/playtest_out/bloque_63_mine_asteroid_{closed,opening,open,closing}.png`
- Visually confirm: closed looks like asteroid, open shows gun, transitions smooth

### Tests (NEW: `tests/test_mine_asteroid.py`, ~25 tests)

- `test_mine_asteroid_kind_in_enum`: `EnemyKind.MINE_ASTEROID` exists with value "mine_asteroid"
- `test_mine_asteroid_default_state_closed`: new instance has `state="closed"`
- `test_mine_asteroid_default_has_opened_false`: `has_opened=False` initially
- `test_state_transitions_on_y_threshold`: crossing `y=OPENING_Y_THRESHOLD` (200) triggers `opening`
- `test_opening_to_open_after_0_5s`: state timer
- `test_open_to_closing_after_0_3s`: state timer
- `test_closing_to_closed_after_0_5s`: state timer
- `test_has_opened_prevents_reopen`: after full cycle, no second opening
- `test_fire_spawns_3_bullets`: `_fire_mine_bullets` adds 3 to projectile pool
- `test_fire_bullets_fan_pattern`: bullets at `0°`, `±15°` from straight down
- `test_closed_immune_to_bullets`: `hit()` returns False when `state=="closed"`
- `test_open_vulnerable_to_bullets`: 1 hit destroys when vulnerable
- `test_hp_starts_at_2`: `Enemy(hp=2)` for MINE_ASTEROID kind
- `test_player_collision_damage`: player takes damage on contact in any state
- `test_50_percent_powerup_drop`: 1000 destroys, ~50% drop rate
- `test_powerup_pool_excludes_score`: only BOMB/HP/WEAPON in drop pool
- `test_spawn_mixes_with_asteroids`: wave spawner produces 1/8 MINE_ASTEROID
- `test_sprite_closed_equals_asteroid_round`: closed frame == BLOQUE 61 `round` PNG (byte-equal or alpha-equal)
- `test_sprite_open_shows_gun`: open frame has visible gun barrel (heuristic: dark gray pixels in center)
- `test_5_state_directories_exist`: closed/opening/open/closing/death in `Assets/sprites/enemies/mine_asteroid/`
- `test_bullet_kind_registered`: `BULLET_ENEMY_MINE` in projectile kinds
- ... (~5 more for state machine edge cases and integration)

---

## Cross-cutting

### TDD workflow (per task)

Following the BLOQUE 59/60 pattern:
1. Write failing tests for the new code (red)
2. Run tests to confirm they fail
3. Implement the minimum code to pass
4. Refactor + run capture script for visual confirmation
5. Commit + push

### Commit cadence

Per user preference: **just commit + push per task, NO auto version bump, NO auto zip, NO auto build.** User controls release cadence.

### Commit message format

`feat: BLOQUE 61 ...` / `fix: BLOQUE 61 ...` / `chore: BLOQUE 61 ...`
`feat: BLOQUE 62 ...` / `fix: BLOQUE 62 ...` / `chore: BLOQUE 62 ...`
`feat: BLOQUE 63 ...` / `fix: BLOQUE 63 ...` / `chore: BLOQUE 63 ...`

### CHANGELOG

Add a section per BLOQUE to `docs/changelog/CHANGELOG_v1.x.md` summarizing what shipped.

---

## Acceptance criteria

### BLOQUE 61
- 5 asteroid variants in `Assets/sprites/asteroids/`, each 32×32, transparent background, visually distinct, all MINE-ASTEROID closed lookalikes
- `src/entities/asteroid.py` uses the new sprite loader (no more procedural generation)
- All 20+ tests in `tests/test_asteroid_sprites.py` pass
- 2491 existing tests still pass
- Visual capture `tools/playtest_out/bloque_61_5_variants.png` shows 5 distinct variants

### BLOQUE 62
- 8 ships regenerated with the updated prompt (no 3/4 angle)
- All 25+ tests in `tests/test_ship_perspective.py` pass
- Visual capture `tools/playtest_out/bloque_62_8_ships.png` shows consistent top-down perspective
- 2491 existing tests still pass

### BLOQUE 63
- `EnemyKind.MINE_ASTEROID` works end-to-end
- Camouflage is effective: closed MINE-ASTEROID is visually identical to a regular asteroid
- State machine functional: closed → opening → open → closing → closed (no re-open)
- All 25+ tests in `tests/test_mine_asteroid.py` pass
- 2491 existing tests still pass
- Visual captures show all 4 states (closed/opening/open/closing)

---

## Out of scope

- New boss types (PHANTOM, NEMESIS redesigns) — separate BLOQUEs
- Sound effects for MINE-ASTEROID opening/closing/gun fire — can be added in a future polish pass
- Music changes — no change
- Player ability to "scan" asteroids for MINE-ASTEROIDs (e.g., a tooltip on hover) — design exploration, not implementation
- Online leaderboards, achievements, save games
- Re-tuning difficulty / wave balance after adding MINE-ASTEROIDs — can be done after the visual + behavior work ships

---

## Risks

- **AI gen inconsistency**: 5 variants may not be visually distinct enough → mitigation: prompt emphasis on shape difference, can iterate on individual variants
- **Rotation drop may affect gameplay feel**: players may miss the spinning → mitigation: add subtle vertical bob (1-2 px) if playtest reveals it
- **MINE-ASTEROID detection breaks camo**: if closed-state sprite differs slightly from `round` asteroid, camo is broken → mitigation: reuse the EXACT same PNG (byte-equal or symlink), do not regenerate
- **Player ship regeneration changes the look from current**: this is intentional (full top-down pass) but may surprise users → mitigation: capture before/after PNGs to show the difference is intentional
- **AI gen time**: ~50 min total across the 3 BLOQUEs is non-trivial → mitigation: parallelize where independent (BLOQUE 61+62 base gens), batch dispatch via mcode-tools

---

## Open questions

None. All design decisions resolved through the brainstorming session on 2026-09-08:

| Question | Decision |
|----------|----------|
| Scope decomposition | 3 BLOQUEs separated (61/62/63) |
| Variant composition | 5 closed variants + open state separate (BLOQUE 63) |
| Rotation in-game | Drop rotation, static asteroids |
| Variant source | Regenerate 5 NEW using MINE-ASTEROID as style reference |
| Sprite size | 32×32 native + runtime scale 0.7-1.3x |
| Lookalike level | All 5 = MINE-ASTEROID closed with different shapes (perfect camo) |
| MINE-ASTEROID behavior | Passive mimic + active when attacking (opens at upper playfield, y < 200) |
