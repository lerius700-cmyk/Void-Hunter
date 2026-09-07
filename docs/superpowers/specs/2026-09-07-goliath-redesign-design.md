# BLOQUE 60 — GOLIATH Boss Redesign + Phase 2 Escalation

**Author:** Mavis (brainstorming session 2026-09-07)
**Status:** DRAFT (awaiting user review)
**Scope:** GOLIATH only (Act 1 sub-boss). HYDRA/PHANTOM/NEMESIS stay procedural for now.

---

## 1. Problem

GOLIATH (Act 1 sub-boss) is drawn procedurally with `pygame.draw.rect` / `pygame.draw.circle` in `_draw_goliath()` (`src/ui/gameplay_runtime.py:5505`). The user reports it looks like "made in paint with squares" — no detail, no proper pixel art, no resolution. The other 3 bosses (HYDRA/PHANTOM/NEMESIS) have the same issue but are out of scope for this BLOQUE.

The 3 `boss_goliath_*.png` files in `Assets/sprites/` are **UNUSED** legacy placeholders (1.5 KB each). The procedural code never reads them.

The user also wants Phase 2 (the escalation when GOLIATH loses HP) to feel **denser, faster, more menacing** — not just "cracked armor with red glow" as it is today.

## 2. Goals

- Replace GOLIATH's procedural drawing with proper 16-bit pixel art.
- Source size 96×80 (vs current procedural ~64×60), upscale cleanly to 384×320 in the 1280×1920 display.
- 5 animations × 10 frames each = 50 frame PNGs, generated via the same AI + PIL pipeline as BLOQUE 59.
- Add Phase 2 behavior escalation:
  - Movement speed × 1.6
  - Spear throw cooldown ÷ 2
  - Red eye trail (dense, "perverso" particle stream)
  - New attack pattern: "eye laser" — straight red beam forward, like the player's charged shot but red and smaller
- All 50 frames must be 10 frames each (no deviation from 10/anim).

## 3. Non-Goals

- HYDRA / PHANTOM / NEMESIS redesign (deferred to a future BLOQUE)
- Player ship redesign (already done in BLOQUE 58.60 ship_01, BLOQUE 59 made ship_01 share the new animation system)
- BGM section change on Phase 2 (deferred)
- Bezier path intro cinematic (the `bezier_path` field exists; we'll use it but only as a simple L→R sweep, not a full cinematic — that's a future BLOQUE)

## 4. Architecture

### 4.1 Sprite pipeline (BLOQUE 60 analog of BLOQUE 59)

```
tools/redesign_bosses/
    _specs.py            # 1 boss spec: GOLIATH
    _ai_client.py        # re-export from tools/redesign_ships/_ai_client.py
    01_generate_bases.py # 5 AI generations (one per state)
    02_postprocess.py    # re-export from tools/redesign_ships/02_postprocess.py
    _animation_frames.py # boss-specific anim generators (idle bob, damage, phase2 cracked, death, intro)
    03_build_sheets.py   # 5×10 grid preview
    04_integrate.py      # copy to Assets/sprites/bosses/goliath/

Assets/sprites/bosses/goliath/
    _base/
        goliath_idle_base.png       # 1024×1024 AI output
        goliath_damage_base.png
        goliath_phase2_base.png
        goliath_death_base.png
        goliath_intro_base.png
    idle/frame_00.png .. frame_09.png     # 10 frames, 96×80, transparent BG
    damage/frame_00.png .. frame_09.png
    phase2/frame_00.png .. frame_09.png
    death/frame_00.png .. frame_09.png
    intro/frame_00.png .. frame_09.png
```

### 4.2 AI prompt template (per state)

```
16-bit pixel art, top-down 3/4 view, facing DOWN (boss is at the top
of the playfield, looking down at the player), isolated on pure black
background, single character, sharp clean pixel edges, no anti-aliasing,
no gradients, limited palette (max 16 colors), Metal Slug aesthetic.

Character: GOLIATH — biblical giant warrior in heavy BRONZE armor with
helmet + visor, glowing RED EYES behind the slit, holding a long SPEAR
in the right hand and a round SHIELD in the left. Heavy set, imposing.

State-specific additions:
- idle:     "standing still, breathing (slight vertical bob), calm menacing pose"
- damage:   "recoiling from a hit, body tilted back, eyes flaring red, slight motion blur"
- phase2:   "armor cracked, red inner glow leaking from seams, eyes blazing red, more aggressive stance, lower body coiled"
- death:    "falling backwards, armor shattering, red energy dissipating, fragments flying"
- intro:    "mid-stride, descending from above, spear raised, dramatic entrance, red eyes first to appear"
```

The shared "16-bit pixel art, top-down 3/4 view" matches the BLOQUE 59 enemy ships so the visual language is consistent.

### 4.3 Postprocess pipeline (reused from BLOQUE 59)

- Crop bottom 15% (removes AI watermark)
- Rotate 90° CCW (AI gives facing-right; we need facing-DOWN)
- Center-crop to square
- Resize to 96×80 (NOT 32×32 — boss is bigger)
- Map pixels to the 64-color palette (`src/utils/palette.py`)
- Threshold alpha to binary (post-resize, kills LANCZOS bleed)
- New: `_transparentize_damero_after_resize_2x()` (same algorithm as BLOQUE 59, tuned for the larger boss size — distance threshold bumped from 70 to 90 to catch more of the damero after LANCZOS blends)

### 4.4 Animation generators (5 × 10 frames)

| State | Generator strategy | Why |
|-------|--------------------|-----|
| idle | Same source PNG × 10 frames, runtime applies vertical bob ±2px via sin curve | Boss is mostly static; bob sells "alive" |
| damage | Same source PNG × 10 frames, runtime applies tilt -3° to 3° oscillation + 0.06s white flash overlay | Hit reaction reads as physical recoil |
| phase2 | 10 frames from AI gen (cracked armor sequence, eyes pulsing) | Full sprite anim — phase 2 must feel different |
| death | 10 frames from AI gen (shattering + falling) | One-shot animation, plays once on `on_death` |
| intro | 10 frames from AI gen (descending stride) | Plays once on spawn, then transitions to idle |

For idle/damage (which reuse one AI image), the 10 frames are byte-identical PNGs. The motion comes from runtime transforms (bob, tilt) in `_draw_goliath()`. This matches how BLOQUE 59 ships work (1 AI image → 10 frames, animation via runtime transforms).

### 4.5 Runtime wiring

**`src/entities/enemies/boss.py`:**

```python
@dataclass
class Boss:
    # ... existing fields ...
    # BLOQUE 60: animation state machine
    animation_state: str = "idle"   # idle | damage | phase2 | death | intro
    animation_frame: int = 0
    animation_timer: float = 0.0
    ANIMATION_FRAME_DURATION: float = 0.10   # 10 fps, 1.0s per loop
    # ... existing fields ...
    
    @property
    def animation_path(self) -> str:
        return f"bosses/goliath/{self.animation_state}/frame_{self.animation_frame:02d}.png"
    
    def update_animation(self, dt: float) -> None:
        # Advance frame every ANIMATION_FRAME_DURATION
        self.animation_timer += dt
        if self.animation_timer >= self.ANIMATION_FRAME_DURATION:
            self.animation_timer = 0.0
            if self.animation_state in ("death", "intro"):
                # One-shot: hold last frame after completion
                if self.animation_frame < 9:
                    self.animation_frame += 1
            else:
                # Looping
                self.animation_frame = (self.animation_frame + 1) % 10
```

**`src/ui/gameplay_runtime.py:5505 _draw_goliath()`** rewrite:

1. Try `_load_sprite(self._boss.animation_path)` first. If found, blit it.
2. Fallback to procedural drawing (so the build doesn't break if the sprites aren't ready).
3. If phase >= 2, add a "phase 2 overlay":
   - Red eye trail (last 8 positions, fading red, density +1 per frame) — drawn AFTER the sprite as additive blend
4. If phase >= 2 and `on_phase_transition == 2`, trigger eye laser attack: spawn a red beam projectile (5 px wide, 360 px long, moves down at 200 px/s, lifetime 1.5s) every 3s on top of the normal attack pattern.

**`src/ui/gameplay_runtime.py:5278` dispatch:**

```python
if self._boss.id == BossId.GOLIATH:
    self._draw_goliath(target, ox, oy)
else:
    self._draw_boss_simple(target, ox, oy)  # HYDRA/PHANTOM/NEMESIS unchanged
```

No change to the dispatch — only `_draw_goliath()` is rewritten.

### 4.6 Phase 2 behavior changes

Three concrete behavior deltas, all driven by `self._boss.phase >= 2`:

| Change | Where | Effect |
|--------|-------|--------|
| **Speed × 1.6** | `_check_phase()` | Override `cfg.speed` in `update()` when `phase >= 2`. Pseudocode: `effective_speed = cfg.speed * (1.6 if phase >= 2 else 1.0)`. The sin oscillation amplitude stays the same; the frequency of `move_t` is what scales up (boss sweeps the arena faster). |
| **Spear cooldown ÷ 2** | `select_attack()` | Pseudocode: `self.fire_cd = cfg.attack_cooldown_s * (0.5 if phase >= 2 else 1.0)`. The boss throws the spear twice as often. |
| **Eye trail** | `_draw_goliath()` | Ring buffer of 8 recent (x, y) positions. Each frame, push current, pop oldest. Draw 8 red dots (radius 2 → 0.5, alpha 200 → 30) along the trail. Visual: "dense, perverso" as the user described. |
| **Eye laser attack** | `_draw_goliath()` + `_spawn_boss_attack()` | New attack index 9 = "eye laser". Every 3s in phase 2, spawn a red beam (5px wide, 360px long, downward, 200 px/s, lifetime 1.5s, damages player on contact). Beam is a red rectangle with a brighter red core and white center pixel. This is the player's charged shot but red and from above. |

### 4.7 Phase 1 behavior (unchanged)

Phase 1 keeps the existing procedural visual *if* the new sprites fail to load. Once the new sprites are in place, phase 1 uses the new `idle` sprite with the bob.

The user's design adds: **Phase 2 must feel like a "different boss"** — not just a recolor. The eye trail + faster movement + new attack + new sprite all combine to that.

## 5. Files to create / modify

**New files:**
- `tools/redesign_bosses/_specs.py` (~40 LOC)
- `tools/redesign_bosses/01_generate_bases.py` (~80 LOC, mirrors ship version)
- `tools/redesign_bosses/_animation_frames.py` (~100 LOC)
- `tools/redesign_bosses/03_build_sheets.py` (~50 LOC)
- `tools/redesign_bosses/04_integrate.py` (~40 LOC)
- `Assets/sprites/bosses/goliath/_base/*.png` (5 × 1024×1024 AI outputs, NOT committed, regenerable)
- `Assets/sprites/bosses/goliath/{idle,damage,phase2,death,intro}/frame_00..09.png` (50 files, committed)
- `tests/test_redesign_bosses.py` (~15 tests: spec presence, animation_frame advance, death/intro one-shot, speed scaling, fire_cd scaling, animation_path string format)

**Modified files:**
- `tools/redesign_ships/02_postprocess.py` — extract `_transparentize_damero_after_resize()` into a function with a `distance_threshold` parameter (default 70 for ships, 90 for bosses) so both can call it
- `src/entities/enemies/boss.py` — add animation state, speed scaling, fire_cd scaling in phase 2
- `src/ui/gameplay_runtime.py:_draw_goliath()` — rewrite to load sprite first, add phase 2 overlays (eye trail, eye laser)
- `src/ui/gameplay_runtime.py:_spawn_boss_attack()` — add attack index 9 (eye laser) for GOLIATH only in phase 2
- `build.spec` — already includes `Assets/sprites/`, no change needed

**Deleted (after new assets are confirmed good):**
- `Assets/sprites/boss_goliath_*.png` (3 UNUSED placeholders, 4.7 KB)
- `Assets/sprites/boss_simple_hydra.png` (1 UNUSED placeholder, 250 bytes)

**NOT deleted (kept as backup until user confirms):**
- `Assets/sprites/_backup_broken_damero/` (320 PNGs)

## 6. Tests (BLOQUE 60)

`tests/test_redesign_bosses.py` (15 tests):

```python
# Spec + assets
def test_goliath_spec_exists(): ...
def test_goliath_spec_has_5_states(): ...
def test_goliath_idle_base_png_exists(): ...   # checks _base/goliath_idle_base.png
def test_goliath_intro_base_png_exists(): ...
def test_goliath_idle_has_10_frames(): ...
def test_goliath_phase2_has_10_frames(): ...   # 10 frames per anim contract
def test_goliath_intro_has_10_frames(): ...
def test_goliath_frames_are_transparent_corners(): ...

# Animation state machine
def test_boss_starts_in_idle(): ...
def test_boss_advances_frame_on_update(): ...
def test_intro_is_oneshot_holds_frame_9(): ...
def test_death_is_oneshot_holds_frame_9(): ...
def test_idle_loops_back_to_frame_0(): ...
def test_boss_animation_path_format(): ...

# Phase 2 behavior
def test_phase2_speed_is_1_6x(): ...
def test_phase2_fire_cd_is_halved(): ...
```

Existing boss tests in `tests/test_boss.py` continue to pass (procedural fallback path).

## 7. Acceptance criteria

1. **Visual:** Game shows GOLIATH with proper 16-bit pixel art, not procedural rectangles.
2. **Size:** Visual footprint ~96×80 (scaled to 384×320 on display), bigger and more imposing than the current 64×60.
3. **Animations:** 5 distinct states × 10 frames each = 50 frames. Each state has 10 frames (user requirement).
4. **Phase 2 escalation:** When GOLIATH crosses to phase 2:
   - Speed visibly faster (sin oscillation 1.6x frequency)
   - Red eye trail visible (8-position fade, dense)
   - Eye laser fires every 3s (red beam, 5px wide, downward)
   - Spear throws 2x more often
5. **Backward compatible:** If `Assets/sprites/bosses/goliath/<state>/frame_00.png` is missing, the procedural drawing still works (graceful fallback).
6. **All 50 frames:** `Assets/sprites/bosses/goliath/{idle,damage,phase2,death,intro}/frame_00.png` through `frame_09.png` exist with transparent corners.
7. **No alpha = 0.5 bleed:** All 50 frames have binary alpha (0 or 255), no LANCZOS residue.
8. **Tests:** 15 new tests pass; all 1,647 existing tests still pass (1,630 base + 17 BLOQUE 59).
9. **Visual evidence:** Capture script in `tools/capture/capture_goliath_phase1.py` and `capture_goliath_phase2.py` produce PNGs showing the new sprites in both phases; user confirms visually before commit.

## 8. Out of scope (deferred)

- HYDRA / PHANTOM / NEMESIS redesign (separate BLOQUE if user wants)
- Hand-painted detail pass (Aseprite) — AI is good enough; revisit if user dislikes AI output
- BGM tempo change on Phase 2 transition (the boss has `bgm_tempo_mult` field, NEMESIS uses it; GOLIATH could too, but defer)
- Full intro cinematic with bezier path (defer; use simple anchor spawn for now)
- Recolor of unused `Assets/sprites/_backup_broken_damero/` (delete when user confirms BLOQUE 59 fix is good)

## 9. Open questions

None — all answered in this brainstorming session.

## 10. Plan reference

Implementation plan will be written by `superpowers:writing-plans` after this design is approved.
