# BLOQUE 64 — GOLIATH 6-Animation Sprite-Sheet + Asteroid Polish

**Date:** 2026-09-08
**Status:** READY FOR EXECUTION
**Author:** Lerius (idea) + Mavis (draft)
**Branch:** master

## Overview

Three coordinated fixes + one new boss animation system, in response to live gameplay feedback (asteroids invisible, camouflaged ships not noticeable, GOLIATH needs more expressive attack animations).

1. **Asteroid visibility fix** — regenerate 5 variants at 64×64 native (was 32×32) with scale 1.5-2.5x. Asteroids now ~96-160 px on screen (30-50% of width). Greek-key band and craters finally readable.
2. **Asteroid indestructibility** — regular asteroids are obstacles, not targets. HP goes to infinity (or removed from bullet-collision check). Player must dodge, not shoot.
3. **MINE-ASTEROID HP=3 with red flash** — was 2 HP (1-hit kill). Now 3 HP with 0.2s red flash per hit so the player sees the damage progression.
4. **GOLIATH 6-animation borderless sprite-sheet** — replace the 5 BLOQUE 60 anims with 6 fresh ones, all 10 frames per anim, all with transparent backgrounds (borderless). Anim names: `phase1_idle`, `phase2_idle`, `javelin`, `laser`, `purple_bullet`, `death`.

---

## Section 1: Architecture and Order

### 4 sub-tasks, sequential because of GOLIATH state machine complexity

1. **BLOQUE 64.A — Asteroid + MINE-ASTEROID polish** (5 asteroids regen + scale + HP changes + indestructibility + red flash)
2. **BLOQUE 64.B — GOLIATH 6 fresh animations** (60 frames regen with borderless prompt + state machine mapping + drawing pipeline)

64.A must complete before 64.B (no dependency, but both touch `src/ui/gameplay_runtime.py` — split to avoid merge conflicts).

### Cross-cutting invariants

- Reuse `tools/redesign_ships/_ai_client.py` and `_transparentize_damero_after_resize` from BLOQUE 59
- Locked palette for asteroids: same 6-color brown palette from BLOQUE 61
- GOLIATH palette: existing warrior-biblical palette from BLOQUE 60 (gold/bronze/red/blue)
- All 2582 existing tests must still pass
- No regressions to gameplay

---

## Section 2: BLOQUE 64.A — Asteroid + MINE-ASTEROID Polish

### A.1 Regenerate 5 asteroid variants at 64×64

**Why:** The 32×32 sprites from BLOQUE 61 are too small to read in gameplay. At 64×64 native with scale 1.5-2.5x, asteroids are 96-160 px on a 320×480 playfield (30-50% of width). Greek-key band and craters clearly visible.

**Files:**
- Regenerate: `Assets/sprites/asteroids/round.png`, `elongated.png`, `spiked.png`, `hollowed.png`, `cracked.png` (5 × 64×64 PNGs, replacing the 32×32 versions)
- Update: `src/entities/asteroid.py` constants `ASTEROID_SPRITE_BASE_SIZE = 32` → `64`, `ASTEROID_SCALE_MIN = 0.7` → `1.5`, `ASTEROID_SCALE_MAX = 1.3` → `2.5`

**AI gen:** 5 prompts, same MINE-ASTEROID reference, but the postprocess step resizes to 64×64 instead of 32×32. Reference image: `C:\Users\Lerius\.minimax\v2\assets\2026\09\08\16-17-53-160-asset_20260908-161753-160_cfef6f1ee22b_b83348fe-image.png`

**Time:** ~15 min (5 AI gens × 3 min)

### A.2 Asteroids are indestructible

**Why:** User feedback: regular asteroids should be obstacles, not targets. MINE-ASTEROID (the camouflaged enemy) is what you shoot.

**Files:**
- Modify: `src/entities/asteroid.py` — remove `hp` field from `Asteroid` dataclass (or set default to a very large number like 9999)
- Modify: `src/ui/gameplay_runtime.py:_asteroid_bullet_collision` — remove the `hit()` call for regular asteroids (or skip if not `mine_asteroid`); only powerup drop logic for MINE-ASTEROID destroy
- Modify: `tests/test_asteroid_sprites.py` — update tests that check `hp` field (remove or skip those tests)

**Logic:**
- `_asteroid_bullet_collision` no longer iterates `self._asteroids` for damage
- `Asteroid.hit()` is no longer called for regular asteroids
- MINE-ASTEROID damage path is separate (via enemy pool) and unchanged in principle

### A.3 MINE-ASTEROID HP=3 with red flash

**Why:** User feedback: MINE-ASTEROID should resist 3 hits. Currently HP=2 (1 hit kills when vulnerable).

**Files:**
- Modify: `src/entities/enemies/enemy.py:ENEMY_CONFIGS[EnemyKind.MINE_ASTEROID].hp` from `2` to `3`
- Modify: `src/entities/enemies/enemy.py` — add `mine_hit_flash_timer: float = 0.0` field to `Enemy` dataclass
- Modify: `src/entities/enemies/enemy.py:apply_damage` for MINE_ASTEROID — when hit, set `mine_hit_flash_timer = 0.2`
- Modify: `src/entities/enemies/enemy.py:update` — tick down `mine_hit_flash_timer` per dt
- Modify: `src/ui/gameplay_runtime.py:_draw_mine_asteroid` (or wherever MINE-ASTEROID is drawn) — when `mine_hit_flash_timer > 0`, apply a red tint overlay (e.g., multiply RGB by 2 with R boosted)

### A.4 Capture script update

**File:** `tools/capture/capture_bloque_64_asteroids.py` (NEW)

**Output:** `tools/playtest_out/bloque_64_5_asteroids_64x64.png` (5 asteroids at 64×64 with scale 1.5-2.5x, confirming visibility)

### A.5 Tests (~15 new in `tests/test_bloque_64_asteroid_polish.py`)

- `test_5_asteroid_variants_64x64` — each PNG is 64×64
- `test_asteroid_scale_min_1_5`
- `test_asteroid_scale_max_2_5`
- `test_asteroid_no_hp_field` (or test_hp_default_infinity)
- `test_asteroid_bullet_collision_doesnt_damage_asteroids`
- `test_asteroid_hit_returns_false_for_indestructible`
- `test_mine_asteroid_hp_3`
- `test_mine_asteroid_hit_applies_damage`
- `test_mine_asteroid_hit_sets_flash_timer`
- `test_mine_asteroid_flash_timer_decrements`
- `test_mine_asteroid_3_hits_destroy`
- `test_asteroid_player_collision_still_works` (asteroid still damages player on contact)
- `test_mine_asteroid_closed_immune_to_damage_still_works`
- ... (~2 more)

---

## Section 3: BLOQUE 64.B — GOLIATH 6-Animation Borderless Sprite-Sheet

### B.1 Generate 60 GOLIATH frames (6 anims × 10 frames)

**Why:** Replace the 5 BLOQUE 60 anims (idle/thrust/damage/death/intro) with 6 fresh ones. The user wants: phase1_idle, phase2_idle, javelin, laser, purple_bullet, death — each as a 10-frame sequence with transparent background.

**6 animations × 10 frames = 60 PNGs** at 96×80 (GOLIATH native size, kept from BLOQUE 60).

**Output paths:**
- `Assets/sprites/bosses/goliath/phase1_idle/frame_00.png` ... `frame_09.png`
- `Assets/sprites/bosses/goliath/phase2_idle/frame_00.png` ... `frame_09.png`
- `Assets/sprites/bosses/goliath/javelin/frame_00.png` ... `frame_09.png`
- `Assets/sprites/bosses/goliath/laser/frame_00.png` ... `frame_09.png`
- `Assets/sprites/bosses/goliath/purple_bullet/frame_00.png` ... `frame_09.png`
- `Assets/sprites/bosses/goliath/death/frame_00.png` ... `frame_09.png`

**AI prompt (per anim, vary the "Anim:" line):**
```
16-bit pixel art, top-down view (strictly perpendicular, no 3/4 angle),
strictly BORDERLESS, isolated on TRANSPARENT BACKGROUND (no black square,
no dark frame, no border, no background scenery, no margin), sharp
clean pixel edges, no anti-aliasing, no gradients, limited palette
(max 16 colors), warrior-biblical aesthetic, Star Fox 64 boss style.

Character: GOLIATH — large armored biblical warrior boss, golden
bronze armor with red and blue trim, twin yellow engines on back,
6 hull panels with rivets, single cyclopean red eye, bipedal stance.

Anim: {ANIM_DESC}

Mandatory elements:
- 96x80 native size, transparent background
- All silhouette details visible at 32x24 downscale
- Sharp pixel art edges
- No anti-aliasing artifacts on the sprite boundary
- Center the character in the 96x80 frame (margin = 0)

LOCKED palette (use exact RGB values):
  gold_armor:     (220, 180,  80)
  bronze:         (160, 110,  50)
  red_accent:     (200,  60,  40)
  dark_blue:      ( 40,  50,  80)
  eye_glow_red:   (255,  80,  40)
  eye_trail:      (255, 140,  60)
  hull_dark:      ( 60,  40,  20)
  rivet:          (240, 200, 120)
```

**Per-anim descriptions:**
- `phase1_idle`: "Phase 1 idle stance, weight on right leg, weapon at rest, eye glowing softly, no attack motion"
- `phase2_idle`: "Phase 2 idle stance, more aggressive posture, red eye glowing brighter, body slightly hunched forward"
- `javelin`: "Throwing a javelin forward — arm extended, body leaning into the throw, motion blur on the javelin, frames 0-3 wind-up, 4-6 release, 7-9 follow-through"
- `laser`: "Firing eye laser — eye fully lit red, body planted, beam emanating from eye forward, frames 0-3 charge, 4-7 fire, 8-9 cool-down"
- `purple_bullet`: "Firing purple projectiles — arm raised pointing forward, purple muzzle glow, frames 0-4 charge, 5-7 fire, 8-9 recoil"
- `death`: "Death sequence — body collapsing, armor falling apart, frames 0-3 stagger, 4-6 fall, 7-9 collapse with explosion particles"

**Time:** ~18 min (6 AI gens × 3 min)

### B.2 Build sprite-sheets + integrate

**Files:**
- Generate sprite sheets: `tools/redesign_bosses/03_build_sheets.py` (updated to handle 6 anims × 10 frames at 96×80)
- Integrate: `Assets/sprites/redesign/bosses/goliath/<state>/_source.png` + anims/ (BLOQUE 60 staging)
- Drop old anims: delete `Assets/sprites/bosses/goliath/{idle,thrust,damage,intro}/` directories
- Keep `Assets/sprites/bosses/goliath/death/` (replaced with new 10 frames)
- Migrate: new `Assets/sprites/bosses/goliath/{phase1_idle,phase2_idle,javelin,laser,purple_bullet}/`

### B.3 GOLIATH state machine update

**File:** `src/entities/enemies/boss.py`

**Current state machine (BLOQUE 60):**
- `animation_state: str` with values "idle", "thrust", "damage", "death", "intro" (or "phase1_idle"/"phase2_idle" from BLOQUE 60 task 7)

**New state machine:**
- Replace anim names: "idle" → keep both phase1_idle AND phase2_idle (the boss state already tracks phase). New: `phase1_idle`, `phase2_idle`, `javelin`, `laser`, `purple_bullet`, `death`
- Each attack triggers the corresponding animation:
  - javelin throw → set `animation_state = "javelin"` for 0.5s during the throw
  - eye laser → set `animation_state = "laser"` for 0.7s during the laser
  - purple bullet burst → set `animation_state = "purple_bullet"` for 0.4s during the burst
- Between attacks, return to phase1_idle (phase 1) or phase2_idle (phase 2+)
- Death → set `animation_state = "death"` permanently

**Field changes:**
- No new fields. The `animation_state: str` already exists.
- `animation_timer: float` already exists for per-anim timing.
- `animation_path` property already handles path resolution.

### B.4 Drawing pipeline update

**File:** `src/ui/gameplay_runtime.py:_draw_goliath`

**Current state:** Mixes sprite (when available) + procedural fallback. Borderless means no black square around the sprite.

**New state:**
- All GOLIATH frames are now borderless (regenerated with explicit transparent prompt)
- The drawing code can be simplified — just blit the sprite with no procedural fallback
- The eye_trail ring buffer and procedural layers (aura, embers, greaves, torso) can be REMOVED — the sprite now has all the detail

**What gets removed:**
- Eye trail Layer 13
- All procedural fallback layers in `else:` branch of `_draw_goliath`
- The `eye_trail_positions` field on Boss dataclass (no longer needed)

**What gets kept:**
- Sprite blit
- Phase-based eye color (red glow in phase 2)
- HP bar overlay
- Damage flash on hit

### B.5 Tests (~20 new in `tests/test_bloque_64_goliath.py`)

- `test_6_anim_directories_exist`
- `test_each_anim_has_10_frames`
- `test_each_frame_is_96x80`
- `test_each_frame_has_transparent_background` (no opaque pixels on edges)
- `test_no_3_4_in_goliath_prompts`
- `test_goliath_state_machine_phase1_idle_default`
- `test_goliath_state_machine_phase2_idle_in_phase2`
- `test_javelin_attack_sets_animation_state`
- `test_laser_attack_sets_animation_state`
- `test_purple_bullet_attack_sets_animation_state`
- `test_death_sets_animation_state`
- `test_animation_state_returns_to_idle_after_attack`
- `test_no_eye_trail_field_on_boss` (removed)
- `test_no_procedural_fallback_in_draw_goliath`
- ... (~6 more)

### B.6 Capture scripts

**File:** `tools/capture/capture_bloque_64_goliath.py` (NEW)

**Output:**
- `tools/playtest_out/bloque_64_goliath_phase1_idle.png` — GOLIATH in phase 1 idle
- `tools/playtest_out/bloque_64_goliath_phase2_idle.png` — GOLIATH in phase 2 idle
- `tools/playtest_out/bloque_64_goliath_javelin.png` — mid-javelin-throw
- `tools/playtest_out/bloque_64_goliath_laser.png` — mid-laser-fire
- `tools/playtest_out/bloque_64_goliath_purple_bullet.png` — mid-bullet-burst
- `tools/playtest_out/bloque_64_goliath_death.png` — death sequence final frame
- `tools/playtest_out/bloque_64_goliath_spritesheet.png` — 6×10 grid of all 60 frames (for the user's reference)

---

## Section 4: Acceptance Criteria

### BLOQUE 64.A
- 5 asteroid variants exist as 64×64 PNGs in `Assets/sprites/asteroids/`
- Asteroids render at 96-160 px on screen (30-50% of width)
- Regular asteroids are INDESTRUCTIBLE (bullets pass through, no HP damage)
- MINE-ASTEROID has HP=3, takes 3 hits to destroy
- MINE-ASTEROID shows red flash (0.2s) on each hit
- All 15 new tests pass + 2582 existing pass

### BLOQUE 64.B
- 60 GOLIATH frames exist (6 anims × 10 frames at 96×80)
- All frames have transparent backgrounds (borderless)
- GOLIATH animates fluidly through phase1_idle → javelin/laser/purple_bullet → phase1_idle
- In phase 2+, animates through phase2_idle → attacks → phase2_idle
- Death animation plays once and stops
- No procedural fallback layers in `_draw_goliath`
- All 20 new tests pass + existing GOLIATH tests still pass

---

## Out of scope

- New BGM (the user didn't ask)
- SFX for GOLIATH attacks (not in this BLOQUE)
- New boss types (PHANTOM, NEMESIS, HYDRA) — separate BLOQUEs
- Player ship variant updates (BLOQUE 62 already done)
- Asteroid rotation (already removed in BLOQUE 61)

---

## Risks

- **AI gen inconsistency**: 60 frames of GOLIATH may not be visually consistent. Mitigation: use the same MINE-ASTEROID reference image + warrior-biblical prompt header for all 6 anims.
- **Borderless not perfect**: AI may still leave a faint dark frame around the silhouette. Mitigation: use `_transparentize_damero_after_resize` as fallback in postprocess.
- **Asteroid indestructibility breaks powerup balance**: regular asteroids were a powerup source (30% drop). If they're indestructible, the player never gets powerups from them. Mitigation: keep the 30% powerup-on-destroy for now (asteroids are still "destroyed" in the sense of `active=False` after enough damage) OR move powerup drops to MINE-ASTEROID only (which is 50% per spec). User chose indestructibility, so we go with that — but document the trade-off.
- **GOLIATH state machine changes might break existing boss fight code**: The Boss dataclass + state machine is used by HYDRA, PHANTOM, NEMESIS too. Mitigation: keep the existing `animation_state: str` field generic; only change the string values that GOLIATH uses. Other bosses keep their old strings.
