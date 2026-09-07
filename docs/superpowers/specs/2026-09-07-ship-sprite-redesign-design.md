# 2026-09-07 — Ship Sprite Redesign (3 templates + 1 player, Metal Slug style, 16px)

**Date:** 2026-09-07
**Status:** DESIGN — pending user review
**Author:** Mavis
**GitHub:** `https://github.com/lerius700-cmyk/Void-Hunter`

---

## 1. Problem

The current ship sprites have inconsistent visual quality:

1. **Player ships are good, enemies are not.** `ship_01` (64×64 source, ~34px render) has 5 polished animations × 8 frames each (idle, rotating, propulsion, charging, damage) with cartoony personality. The 7 enemy types (`enemy_drone.png`, `enemy_scout.png`, `enemy_heavy.png`, `enemy_kamikaze.png`, `enemy_sniper.png`, `enemy_turret.png`, `enemy_cruiser.png`) are **single-frame static sprites** sized 13–24 px with no animation, no squash/stretch, no engine glow variation. They feel dead compared to the player ship.

2. **Visual hierarchy is wrong.** All 7 enemy types are visually similar (small static ships) so the player cannot tell at a glance which enemy does what. The user wants clear visual distinction between light/medium/heavy roles.

3. **No Metal Slug personality.** The reference style (Metal Slug, 1996) is famous for exaggerated animations, anticipation, follow-through, and personality in 8–12 frames. The current enemies have zero of this.

User request (Lerius, 2026-09-07, in Spanish): *"crea un plan de accion para crear nuevas imagenes, rediseñando por completo los sprites de las naves, para que sean imagenes de alta calidad, detalle y resolucion . en 16 pixeles. crea 3 modelos diferentes para las naves enemigas, y 1 para la nave del jugador. todo basandose en lo ya existente. cada Sprite debe tener su Sprite-sheet con animacion de 10 frames por sprite, para que se vean vivas las naves, y que se van moviendo de manera medio caricaturesca (tipo metal slug)."*

User clarifications (same conversation):
- **Size:** source 32×32 px, rendered at 16px in the playfield (2× supersampling, scaled DOWN with nearest-neighbor for crisp pixels).
- **Scope:** 3 templates (light/medium/heavy) covering the 7 existing enemy types as visual variants.
- **Method:** Use the user's configured AI tools (`mcode-tools connector__matrix__generate_image`) for base art, then post-process with PIL to 32×32 pixel art mapped to the project's 64-color palette. The user explicitly corrected me when I offered a menu of options ("deja de sabotearme. usa las herramientas de MAVIS de creacion de imagenes y videos").
- **Animation:** 10 frames × 4 animations (idle, thrust, damage, death) = 40 frames per ship.
- **Player ship:** Redesign `ship_01` as the new canonical; ships 02–05 remain as alternate skins.

## 2. Goal

One redesigned sprite system:

1. **3 enemy templates** (light/medium/heavy) generated via AI + post-processed to 32×32 px pixel art. Each template has 2–3 visual variants to cover the 7 existing enemy types.
2. **1 new player ship** redesigning `ship_01` with the same animation system.
3. **Animation system:** every ship has 4 animations × 10 frames = 40 frames, with idle/thrust as loops and damage/death as one-shots.
4. **Pipeline:** reproducible, AI-driven, palette-disciplined. The user can re-run any stage and get deterministic results given the same inputs.
5. **Integration:** the new sprites replace the old enemy PNGs (single-frame → animated) and the old `ship_01` (becomes the redesigned version). Game code iterates frames per ship per animation.

## 3. Non-Goals

- **No changes to enemy behavior** (movement, weapons, HP, formation, paths). Visual only.
- **No changes to player behavior** (weapons, dash, charging, damage state). Visual only — the animation states already exist; we just redesign their sprites.
- **No changes to the 4 bosses** (GOLIATH/HYDRA/PHANTOM/NEMESIS). They have their own sprite system.
- **No changes to the sub-boss** (Wolfen dart). Separate sprite (`sub_boss_up/right/left/down.png`).
- **No new palette colors.** New sprites use the existing 64-color palette in `src/utils/palette.py` for visual consistency with the rest of the game.
- **No rotation/animation transitions.** The 4 animations are independent; the game code already handles which one plays when.
- **No new gameplay states.** The 4 animations (idle, thrust, damage, death) cover all existing player/enemy states; we don't add "celebrate" or "stunned" or anything new.
- **No UI / HUD changes.** The sprite redesign is purely the ship visuals.
- **No changes to the existing `ship_02`–`ship_05` sprites.** They stay as alternate player skins; only `ship_01` gets redesigned.
- **No AI-training or fine-tuning.** We use the AI model as-is; we don't fine-tune on void-hunter assets.
- **No sprite atlas / texture packing.** Each ship has its own per-frame PNGs in a subdirectory, matching the existing layout (`ship_01/idle/frame_00.png`, etc.).

## 4. Design

### 4.1 Sprite template taxonomy

3 enemy templates, 1 player ship, 7 enemy visual variants covering the 7 existing enemy types:

| Template | Role | Visual | Palette family | Variants (→ existing enemy type) |
|---|---|---|---|---|
| **A — Light** | Fast, agile, fragile | Small silhouette, pointy, narrow wings, 1 engine, fragile look | Cyan/electric (`c/C/i/I`) | scout, drone, kamikaze (3 variants) |
| **B — Medium** | Balanced, ranged | Medium silhouette, weapon-focused, more detail, 1–2 thrusters | Blue/void (`b/B/n/N`) | sniper, turret (2 variants) |
| **C — Heavy** | Slow, tanky, many weapons | Large silhouette, blocky, armored, multi-turret, thick hull | Red/mars (`r/R/o/O`) | heavy, cruiser (2 variants) |
| **P — Player** | Hero ship | Largest silhouette, more detail than enemies, distinctive accent: white hull (`=/-`) with gold highlights (`y/Y/a`) and red engine tips (`r/R/3`) | Mixed (white hull + gold + red) | (1 ship: ship_01 redesign) |

**Mapping total:** 3 + 2 + 2 = 7 enemy variants + 1 player = 8 ships, each with 4 animations × 10 frames = 40 frames per ship = **320 frames total** in the new system.

### 4.2 Animation specification

Each ship has 4 animations, 10 frames each:

| Animation | Loop? | What it shows | Frame-by-frame content |
|---|---|---|---|
| **idle** | yes (infinite) | Subtle bob (1 px up/down) + engine pulse (0–2 frames bright) | Frame 0 = rest, frames 1–9 = variations returning to frame 0 |
| **thrust** | yes (infinite) | Engine flare 2–3× larger, slight forward lean (1px) | Frame 0 = rest+lean, frames 1–9 = engine flare variation |
| **damage** | one-shot | Red flash + tilt left/right (2 sub-variants per hit) | Frame 0 = rest, frames 1–3 = tilt left + red flash, frames 4–6 = tilt right, frames 7–9 = return to rest |
| **death** | one-shot | Explosion sequence (debris + flash) | Frame 0 = rest, frames 1–9 = expanding debris + flash fade |

**Loop seamlessness:** for `idle` and `thrust`, frame 0 == frame 9 == frame 10 conceptually. The pipeline guarantees this by deriving frame 0 first and using it as the loop anchor.

### 4.3 Source size and rendering

- **Source PNG:** 32×32 px per frame. This is the AI-generation output and the on-disk storage.
- **Render in game:** 16×16 px per frame, scaled down with `pygame.transform.scale(surface, (16, 16))` using nearest-neighbor (default for pygame) for crisp pixels.
- **Why 32×32 source:** gives 2× the pixel budget for detail (shadows, micro-engine glow, antialias edges that read as smooth curves at 16px) compared to 16×16 source. Industry standard for 8-bit/16-bit pixel art.
- **Why 16px render:** matches the user's request and gives the game a cohesive retro feel where ships are small dots on the playfield, contrasted against the 480px-tall playfield.

### 4.4 Pipeline architecture

4 stages, each in its own script under `tools/redesign_ships/`:

```
Stage 1: 01_generate_bases.py
  Input:  template + variant list (8 ships × 1 reference pose)
  Action: call mcode-tools connector__matrix__generate_image
          for each ship, prompt for "16-bit pixel art, top-down
          3/4 view, isolated on transparent, side view, sharp edges,
          single ship, metal slug style" with template-specific details
  Output: Assets/sprites/redesign/_base/<ship>_base.png (1024×1024)
          + node_ids logged to manifest.json
  Human gate: USER REVIEWS each base image and approves before Stage 2

Stage 2: 02_postprocess.py
  Input:  Stage 1 outputs (1024×1024 PNGs)
  Action: for each base:
            1. Resize to 32×32 with PIL.Image.LANCZOS
            2. For each pixel, find nearest color in src/utils/palette.py
            3. Add alpha channel (transparent outside ship silhouette)
            4. Save as Assets/sprites/redesign/<ship>/_source.png
          Then for each (ship, animation):
            1. Generate 10 frame variations by applying small transforms
               to the source: shift ±1px for bob, color flash for damage,
               expand for thrust, scale + recolor for death debris
            2. Save per-frame PNGs: <ship>/<animation>/frame_NN.png
  Output: 8 ships × (1 source + 4×10 frames) = 328 PNGs
  Human gate: USER REVIEWS the sprite-sheet preview for each ship

Stage 3: 03_build_sheets.py
  Input:  Stage 2 per-frame PNGs
  Action: for each ship, build a combined preview sprite-sheet:
            Layout: 4 rows (idle, thrust, damage, death) × 10 cols
            Cell: 32×32 + 4px padding, label column 96px on the left
          Extend the existing tools/build_sprite_sheet.py logic
          to support 10-frame animations (currently 8).
  Output: Assets/sprites/redesign/spritesheet_<ship>.png (preview)
  Human gate: USER REVIEWS each full sprite-sheet before Stage 4

Stage 4: 04_integrate.py
  Input:  Stage 3 sprite-sheets
  Action: copy the per-frame PNGs to the live asset locations:
            Player:  Assets/sprites/player_ships/ship_01/<animation>/frame_NN.png
                     (overwrites the existing 8-frame version)
            Enemies: Assets/sprites/enemies/<kind>/<animation>/frame_NN.png
                     (new directory layout; old single-frame PNGs at
                      Assets/sprites/enemy_<variant>.png are moved to
                      archive/_legacy_sprites/ for git history)
            Game code: src/entities/enemies/enemy.py gains animation_state
                      + animation_frame fields; src/ui/gameplay_runtime.py
                      render path looks up the per-frame PNG per tick
  Output:  Live assets + code updated.
  Verification: launch the .exe, verify ships animate in the playfield
               (manual visual check by user)
```

### 4.5 AI generation prompt template

For each ship, the prompt follows a template with template-specific fills:

```
"16-bit pixel art, top-down 3/4 view, facing forward (upward in
playfield), isolated on pure black transparent background, single
spaceship, sharp clean pixel edges, no anti-aliasing, no gradients,
limited palette (max 8 colors), Metal Slug aesthetic, [TEMPLATE_FILL]
[COLOR_FILL] color scheme, [SIZE_FILL] silhouette,
game asset sprite, no background scenery"
```

**TEMPLATE_FILL examples:**
- Light: "small fast scout ship, narrow pointy wings, single thruster"
- Medium: "balanced fighter, medium wings, focused weapon hardpoint"
- Heavy: "large armored cruiser, blocky hull, multiple turrets, thick armor"
- Player: "hero ship, sleek aggressive silhouette, gold accents, prominent engine glow"

**COLOR_FILL examples:**
- Light: "cyan and electric blue"
- Medium: "navy blue and dark void"
- Heavy: "red and mars orange"
- Player: "white hull with gold highlights and red engine tips"

**SIZE_FILL examples:**
- Light: "compact, ~20×14 pixels equivalent"
- Medium: "mid-sized, ~24×18 pixels equivalent"
- Heavy: "large, ~30×22 pixels equivalent"
- Player: "heroic, ~30×24 pixels equivalent with more detail"

### 4.6 Post-processing: PIL pipeline

For each AI-generated base (1024×1024), the post-process step:

1. **Resize:** `image.resize((32, 32), Image.LANCZOS)` for smooth downscale.
2. **Palette mapping:** for each pixel, find the color in `PALETTE` (the 64-color dict in `src/utils/palette.py`) with minimum RGB Euclidean distance. Replace.
3. **Alpha:** pixels close to black (RGB sum < 30) become fully transparent. Others inherit full alpha.
4. **Save:** `Assets/sprites/redesign/<ship>/_source.png` (32×32 RGBA).

For each animation:

| Animation | Frame generation |
|---|---|
| **idle** | Start from source. For frame N (0-9): shift Y by `sin(N * π/5) * 1` pixel; engine pixel brightness varies with `cos(N * π/5)` |
| **thrust** | Start from source. Apply 1px forward lean (shift X by +1). Engine pixels become 2× larger via 3×3 dilation. Frames 1-9 alternate engine size between "small" and "large" |
| **damage** | Start from source. Frames 1-3: tint all non-outline pixels red (multiply R by 2, clamp), tilt -1px. Frames 4-6: tint red, tilt +1px. Frames 7-9: return to source with no tint |
| **death** | Start from source. Frame 0 = source. Frames 1-3: scale 1.2×, red+orange tint. Frames 4-6: scale 1.5×, debris (4 random pixels scattered), yellow tint. Frames 7-9: scale 2×, mostly transparent, dark gray specks |

All transforms are deterministic given the same source PNG. Pipeline outputs are byte-identical on re-run.

### 4.7 Integration with existing game code

- **Player ship:** existing code at `src/entities/player/` reads from `Assets/sprites/player_ships/ship_01/<animation>/frame_NN.png`. The integration just overwrites those PNGs with the new 10-frame versions. The code path is unchanged.
- **Enemies:** the current game treats enemies as static single-frame sprites. To make them animate, the code at `src/entities/enemies/enemy.py` (and `src/ui/gameplay_runtime.py`) needs a small change:
  - Add an `animation_state: str` field to the Enemy (default "idle").
  - Add an `animation_frame: int` field (0–9), updated each tick.
  - In the render path, look up the current frame PNG: `Assets/sprites/enemies/<kind>/<animation_state>/frame_<animation_frame:02d>.png`.
  - On hit, transition to "damage" animation; on death, transition to "death"; on thruster/dash, transition to "thrust".
- **Ship selector:** the existing player ship selector in the title screen lists 5 ships. The redesign of `ship_01` means ship_01 looks different. Ships 02–05 keep their current sprites. No code change needed in the selector.

### 4.8 Testing

`tests/test_redesign_sprites.py` (new file):

- **test_all_8_ships_have_4_animations:** assert each of the 8 ships has `idle/`, `thrust/`, `damage/`, `death/` directories under its path.
- **test_each_animation_has_10_frames:** assert each animation directory has `frame_00.png` through `frame_09.png` (no gaps).
- **test_each_frame_is_32x32_rgba:** open each frame, assert size = (32, 32) and mode = "RGBA".
- **test_each_frame_uses_only_palette_colors:** for each frame, assert every pixel's RGB is in the 64-color palette's RGB set (with tolerance ±2 for LANCZOS rounding).
- **test_idle_loop_seamless:** assert frame 0 == frame 9 of idle (pixel-perfect equality). Same for thrust.
- **test_spritesheet_dimensions:** assert each generated sprite-sheet PNG is exactly (LABEL_WIDTH + 10 * 32 + padding, 4 * 32 + padding).
- **test_integration_copied_assets:** assert the live asset locations (`Assets/sprites/player_ships/ship_01/...` and `Assets/sprites/enemies/...`) are populated with the new frames.
- **test_enemy_animation_state_machine:** unit test the new `animation_state` field on Enemy: hit → damage, death → death, dash → thrust, default → idle.

Existing test suite must remain green: 1,630/1,630 pass on the changed code paths (the 6 pre-existing failures stay pre-existing).

### 4.9 Updated build.spec

The current `build.spec` (commit `0999c2f`) uses onefile mode and bundles `Assets/sprites/player_ships/ship_01_spritesheet.png` through `ship_05_spritesheet.png`. The new system replaces ship_01's per-frame PNGs but keeps the sprite-sheet preview. **No change to build.spec needed** — the existing datas entry already covers the player ship directory.

The new enemy animation directories (e.g., `Assets/sprites/enemies/enemy_scout/idle/frame_00.png`) need a new datas entry to be bundled:

```python
(str(PROJECT_ROOT / "Assets" / "sprites" / "enemies"), "Assets/sprites/enemies"),
```

This is the only build.spec change.

## 5. Risks

- **AI generation variability.** `connector__matrix__generate_image` may produce inconsistent results across runs. Mitigation: Stage 1 has a "user review" gate after each base. The pipeline stores the node_id + prompt + seed, so any base can be regenerated. The user can also provide a hand-drawn base if AI output is unsatisfactory.

- **Palette mapping artifact.** LANCZOS downscale from 1024→32 produces pixels that are not exactly in the 64-color palette. The nearest-color mapping can create banding. Mitigation: use a tolerance of ±2 in the test, and allow small dithering in the post-process (Floyd-Steinberg) if visual quality requires it.

- **Animation frame continuity.** Procedural frame generation (idle bob, thrust variation) may produce visible "jumps" between frames. Mitigation: the user reviews the sprite-sheet preview after Stage 3; if a frame looks off, we can re-generate that specific frame with a tweak.

- **File size growth.** Currently the .exe is 266 MB. Adding 7 enemy ships × 40 frames × ~80 bytes per PNG = ~22 KB per ship = ~22 KB total. Negligible. The .exe won't grow meaningfully.

- **Integration regression.** Changing enemy rendering from static PNG to per-frame lookup could break the existing rendering path. Mitigation: the integration test `test_enemy_animation_state_machine` covers the state transitions, and the visual verification (launch .exe, see ships animate) is the final gate.

- **8-bit aesthetic drift.** The 64-color palette was designed for an 8-bit aesthetic (per `palette.py` docstring: "Shovel Knight postmortem 2014: 54-color global palette is standard; we go to 64 for the 6 themes × 10 accents + 4 universal"). If the AI generates colors outside this palette, the post-process forces them into palette, but the result may look "muted" compared to the AI's original. This is intentional — the user wants the 8-bit feel preserved.

- **Time cost.** 8 ships × 1 base image each = 8 AI generations (~30-60s each = 4-8 min total for Stage 1, not counting user review). Plus post-process (~1 min/ship), sprite-sheet build (~1 min/ship), integration (~1 min). Total wall-clock: ~30-60 min for the whole pipeline, with the bottleneck being the user review gates (Stage 1 review of 8 images, Stage 3 review of 8 sprite-sheets).

## 6. Acceptance criteria

The work is DONE when ALL of these are true:

1. ✅ All 8 ships (3 enemy templates + 1 player) have 4 animations × 10 frames = 40 frames each, at 32×32 source size, in `Assets/sprites/redesign/`.
2. ✅ Each frame uses only colors from the 64-color palette (verified by test).
3. ✅ Each sprite-sheet preview (`Assets/sprites/redesign/spritesheet_<ship>.png`) is generated and visually approved by the user.
4. ✅ The 4 player ship animations match the existing state machine (idle when stationary, thrust when dashing, damage when hit, death when dying).
5. ✅ The 3 enemy templates' variants are visually distinguishable in-game at 16px render size (light = small/pointy/cyan, medium = mid-sized/navy, heavy = large/blocky/red).
6. ✅ Existing test suite remains green: 1,630/1,630 pass on changed code paths. New tests in `tests/test_redesign_sprites.py` all pass.
7. ✅ Live assets in `Assets/sprites/player_ships/ship_01/` and `Assets/sprites/enemies/` are updated and the game launches showing the new sprites (verified by user).
8. ✅ Old single-frame enemy PNGs are moved to `archive/_legacy_sprites/` (not deleted — git history is preserved).
9. ✅ The .exe rebuilds successfully with the new build.spec entry for `Assets/sprites/enemies/`, size grows by < 1 MB.
10. ✅ CHANGELOG entry added in `docs/changelog/CHANGELOG_v1.x.md` describing the sprite redesign as BLOQUE 59 (or whatever next number).

## 7. Open questions

None at design time. All 5 foundational questions were answered in the brainstorming session:
- Size: 32×32 source / 16px render
- Scope: 3 templates + variants covering 7 enemy types
- Method: mcode-tools (AI) + PIL (post-process)
- Animation: 4 animations × 10 frames
- Player: redesign ship_01 as canonical

## 8. Verification plan

After implementation, the user (Lerius) verifies by:

1. **Visual:** launches the rebuilt .exe (`dist/void-hunter.exe`), plays Act 1, confirms ships animate (idle bob, thrust flare on dash, damage flash on hit, death explosion). Captures 3-5 PNGs from key moments for the CHANGELOG.
2. **Test:** `python -m pytest tests/test_redesign_sprites.py -v` — all new tests pass.
3. **Test:** `python -m pytest tests/ -q` — full suite still 1,630/1,630 (excluding 6 pre-existing).
4. **Regression:** the 3 visual captures from BLOQUE 58.next (`tools/playtest_out/leader_hp_wave1_vs_wave10.png`, etc.) still match expected behavior (the visual tests don't depend on ship sprites but on layout/positions).

## 9. Out of scope (for follow-up BLOQUES)

- **Ship rotation animations** (e.g., 8 directional sprites per ship) — current ships face forward only.
- **Particle effects on engine glow** — currently static pixels; could become animated particles.
- **Damage state variations** (e.g., 3 hit tiers with progressive visual damage) — current "damage" is binary.
- **Custom player ship skins** beyond the 5 existing — the ship selector currently shows 5; new skins would be a separate feature.
- **Boss sprite redesign** — 4 bosses have their own pipeline; separate BLOQUE.
- **Sub-boss sprite redesign** — Wolfen dart has directional sprites; separate BLOQUE.

---

*Spec author: Mavis · 2026-09-07*
*User review pending. After approval, transition to `superpowers:writing-plans` for the implementation plan.*
