# BLOQUE 75 — Sprite pipeline migration: enemy sets into the pipeline, and the gameplay frame into a LayerStack

**Date:** 2026-10-30
**Revised:** 2026-11-02 — after an independent review (see §Revision log)
**Status:** READY FOR EXECUTION
**Author:** Lerius (idea) + Mavis (draft)
**Branch:** `bloquec-75-migration-spec` (worktree `F:\AI\MM\void-hunter\.worktrees\bloquec-75-migration-spec`)
**Base:** `bloquec-75-sprite-migration` @ `773cf08` — **merged into this branch as `ef86a95`**. The spec was first written against `e8be3a2`; see §Base drift. Never `master`, never `bloquec-67-goliath-port`.

---

## Overview

BLOQUE 74 built the sprite pipeline and proved it on exactly one set: GOLIATH, a
96×80 boss with 60 unique frames and a detectable feature (the shield plate). The
enemy art has never been through it — 8 sets, 304 frame PNGs (306 PNGs in the
tree), 34 animation directories, all read by the runtime as raw files.

This BLOQUE moves the pipeline in two phases with a verifiable gate between them:

1. **Phase 1 — the 8 enemy sets enter the pipeline.** Each set gets a hand-written
   `manifest.toml` and a generated `anchors.toml`; the auditor classifies every
   frame; the result is deterministic and reproducible. **The runtime does not
   change in Phase 1.**
2. **Phase 2 — the gameplay frame becomes a `LayerStack`.** The 30 draw operations
   of the frame loop become an ordered, declarative stack driven by a single
   `DrawContext`, with a pixel-exact golden-frame comparison as the proof that
   nothing moved.

**The decision in one sentence:** the enemy art is **not** repaired and **not**
re-registered — it is *measured and declared*, with two new manifest fields
(`distinct`, `cut_margin`) that let the auditor tell "this clip was built from 4
poses on purpose" apart from "this clip collapsed", and the Phase 2 stack is an
**orchestration refactor only**: every layer's body is the drawing code that
exists today, called with a context instead of a hand-passed `(target, shx, shy)`.

**The cheapest experiment comes first.** Phase 1 starts at **Step 0** (§Phase 1):
write **one** `scout/manifest.toml` using only the fields the auditor already
supports and run the auditor on it. That is zero new code and it is what proves
the methodology generalises — or does not. Everything after Step 0 is sized by
what Step 0 shows.

---

## Revision log (2026-11-02)

An independent reviewer audited this spec against the prompt's contract (R1-R7,
Q1-Q7, A1-A6, B1-B7, P1-P7, L1-L7) and against the code. Every finding below was
**re-verified in the repo before being applied**; the reviewer's numbers were
accepted only where a command confirmed them.

| Finding | Verdict | Resolution in this revision |
|---|---|---|
| **C1** The auditor crashes on the spec's own enemy manifests: `audit.py:175-176` calls `anim_set.part("shield_plate")` / `part("eye")` unconditionally, and `manifest.py:285-289` raises for an unknown part | **Confirmed** (reproduced) | §Phase 1: `part_or_none()` + the auditor guard + a regression test |
| **C2** The `death` clips have **4** distinct images, not 3 (`{0}` `{1,2,3}` `{4,5,6}` `{7,8,9}`) | **Confirmed** (md5 per clip) | every `death` declaration is now 4 |
| **C3** `pivot = "fixed"` has no implementation: `parts.py` contains **zero** references to `pivot`, and `_base()` always adds `body_dx/body_dy` | **Confirmed** | `src/anim/parts.py` is now in the Phase 2 file map with the exact change |
| **C4** The `mode` rules would reject GOLIATH's own manifest (no `mode`, no `on_end`) | **Confirmed** | §Phase 1: Phase 1 **parses** `mode`/`on_end` without enforcing them; the enforcement arrives in Phase 2 |
| **I1** "42 `_draw_*` methods" is **34** definitions / 42 call sites; the frame loop makes **16** calls, not 15 | **Confirmed** | corrected in 3 places |
| **I2** "every clip trips `COLAPSADO`" is **29 of the 33 live clips, 290 frames** | **Confirmed** | corrected |
| **I3** "0 px margin in 27 of 34 clips" is **29 of the 33 live clips** | **Confirmed** | corrected |
| **I4** `audit.py --json` emits no frame sizes — the canvas truth anchor was wrong | **Confirmed** | the anchor now points at the guard test, and the auditor must emit the size |
| **I5** One `DrawContext.origin` cannot be both the playfield centre and an entity position (3 scratch surfaces: 64×64, 48×48, 64×64) | **Confirmed** | `ctx.origin` = playfield centre + `ctx.with_origin(x, y)` for scratch draws |
| **I6** The golden-frame harness cannot be deterministic: **31** global `random.*` calls, only **1** seeded RNG | **Confirmed** | the harness must seed the global RNG and rebuild the scene; the determinism check becomes a gate item |
| **I7** `_sets_root()` resolves **only** `Assets/sprites/bosses` — the frozen `_MEIPASS` lookup has no enemies root | **Confirmed** | Phase 2 file map: resolve both roots, source and frozen |
| **I8** B4 pointed at a mypy delta command that does not exist | **Confirmed** | the literal command is now in the spec |
| **I9** `audit.py:258,272` default the feature sources to `"measured"`, so a featureless set's `anchors.toml` claims `eye = [0,0], eye_source = "measured"` — false provenance, and `load_anchors` would accept it | **Confirmed** | the sources default to `"missing"`; the enemy anchors' purpose is stated |
| **M1** G8's absolute count contradicts its own "must not grow" prose | Accepted | G8 is now a **failure-delta** check |
| **M2** "5 new test files" vs 6 in the table | Accepted | the count is now the real one |
| **M3** The z-table line ranges stop before the final `blit` | Accepted | corrected |
| **M4** Appendix A claimed "an empty backup dir" — no empty dir exists | Accepted | removed |
| **M5** Appendix A self-certified its own completeness | Accepted | replaced by §Open questions + a coverage table |
| **M6** The worktree table pinned a moving branch | Accepted | "as of 2026-10-30" |
| **M7** D4 described a dual-root lookup that no change implemented | Accepted | D4 now names `sets.py` and its signature |
| **Cost** Phase 1 shipped 5 new fields, 2 new tools and 8 manifests at once | Accepted | Phase 1 now ships **3** fields and 2 parsed-but-unenforced ones; `mode`/`on_end` enforcement moves to Phase 2; Step 0 proves the pipeline on one set before any tooling |

---

## Context (the real state, measured)

Every number below was measured on this branch, with the command that produces
it. Nothing here is quoted from the prompt; where the prompt and the measurement
disagree, **the measurement wins** and the disagreement is called out.

### Repository, branch and worktrees

```powershell
git branch --show-current          # master (root repo, untouched by this work)
git log --oneline -1                # a40fdaf  chore: BLOQUE 73.8 ...
git worktree list
```

| Worktree | Branch | HEAD (as of 2026-10-30) | Owner |
|---|---|---|---|
| `F:\AI\MM\void-hunter` | `master` | `a40fdaf` | the root checkout (v1.6.3, **not** the base) |
| `.worktrees\bloquec-67-goliath-port` | `bloquec-67-goliath-port` | `5d12b10` | another agent — **do not touch** |
| `.worktrees\bloquec-75-sprite-migration` | `bloquec-75-sprite-migration` | `e8be3a2` | another agent — **do not touch**. **This branch moves**: re-read its HEAD before branching. |
| `.worktrees\bloquec-75-migration-spec` | `bloquec-75-migration-spec` | `e8be3a2` | **this spec** |

`.worktrees/` is ignored (`.gitignore:138`), so no worktree content can be
committed by accident.

### Base drift (measured 2026-11-02)

This spec was written against `e8be3a2`. **While it was being reviewed, the base
branch moved to `773cf08` — 18 commits ahead**, all of them from the other
agent's repo-integrity round. What that means, measured:

```powershell
git -C <worktree> rev-list --count HEAD..bloquec-75-sprite-migration   # 18
git -C <worktree> diff --stat e8be3a2..773cf08 -- Assets/sprites/enemies   # empty
git -C <worktree> diff --stat e8be3a2..773cf08 -- src/entities/enemies src/ui/gameplay_runtime.py  # empty
```

| Area the spec measures | Changed by the 18 commits? | Consequence |
|---|---|---|
| **The enemy art** (`Assets/sprites/enemies/**`) | **no — byte-identical** | every art measurement in this spec (canvas, md5 groups, margins, heights, registration) **still holds exactly** |
| `src/entities/enemies/enemy.py`, `src/ui/gameplay_runtime.py` | **no** | the runtime facts (12.5 FPS, the loop/reset rule, the mine's state machine, the 16 draw calls) still hold |
| `tools/sprite_pipeline/audit.py` | **no** | C1 (the `part()` crash) and I9 (the false provenance) were still present in the base; **F11 (the CRLF write) has since been fixed by `f0a97f1`** |
| `src/anim/manifest.py` | +11/−2 | the `loaded_set` cache is now keyed by the **resolved** root instead of `None`. This *helps* §I7: a second root (the enemies tree) gets its own cache entry, so no cache-key conflict. |
| `tools/sprite_pipeline/verify_contract.py` | +23/−4 | the guard now catches an audit exception and **reports** it instead of dying. C1's crash therefore surfaces as a reported failure — but the crash itself is still in `audit_set`, so the Phase 1 fix is still needed. |
| `tests/` | +847/−91 | the suite grew; the baseline numbers below are stale for the new base |
| `src/anim/` (rest), `tools/sprite_pipeline/` (rest) | no | — |

**Two consequences — both already handled:**

1. **The baseline was re-measured on the merged tree.** The numbers in
   §Baseline were measured on `e8be3a2`. The base's own `.synapse` reported
   *"Suite 2.930 pass + 1 fail pre-existente (test_paths_no_star_shapes)"* on
   `773cf08` — and **that count is wrong**. Measured on the merged tree
   (`ef86a95`):

   ```
   2 failed, 2935 passed, 7 skipped in 71.63s
   FAILED tests/test_paths.py::test_paths_no_star_shapes
   FAILED tests/test_sprite_pipeline_run.py::test_the_fix_run_changes_no_file
   ```

   The second failure was the **CRLF bug** (F11): `audit.py` and
   `tests/test_sprite_pipeline_run.py` were byte-identical between the two
   bases, `Path.write_text(..., encoding="utf-8")` writes **CRLF** on Windows
   (verified in isolation: `write_text('a\nb\n')` → `b'a\r\nb\r\n'` on Python
   3.12.10), and the shipped `anchors.toml` blob has **0 CR**.

   **Since then the release line fixed it**: `f0a97f1` passes
   `newline="\n"` to `write_anchors` and pins it with two tests, and
   `a70673c` merged that into this branch. F11 is satisfied — **Phase 1 must
   not rewrite `write_anchors`**. The current baseline is
   **1 failed, 2 941 passed, 6 skipped**, and the one failure is the
   pre-existing Lissajous geometry assertion.
2. **This branch now contains the whole base, and the release line's fixes.**
   The merge `ef86a95` brought `773cf08` in with no conflicts; `a70673c`
   brought the release line's LF fix (`f0a97f1`) in the same way. The
   implementation starts from the merged tree, and the baseline to compare
   against is the one in §Baseline.

### The enemy art

```powershell
Get-ChildItem Assets\sprites\enemies -Directory | ForEach-Object { $_.Name }
Get-ChildItem Assets\sprites\enemies -Recurse -Filter 'frame_*.png' | Measure-Object
Get-ChildItem Assets\sprites\enemies -Directory | Get-ChildItem -Directory | Measure-Object
```

| Metric | Measured | Prompt said | Verdict |
|---|---|---|---|
| Sets | **8** | 8 | ✅ |
| `frame_*.png` | **304** (298 live + 6 in `_backup_pre_bloque_65`) | 304 | ✅ |
| Animation directories | **34** (33 live + 1 archive dir) | 34 | ✅ |
| Total PNGs in the tree | **306** (304 frames + 2 loose reference PNGs) | — | — |
| Live clips | **33** (28 ship clips + 5 mine clips) | — | new fact |
| Distinct images (live) | **79** | — | new fact |

### The canvas is 32×32 — **not** the hitbox, **not** what the prompt's table says

Measured with `pygame.Surface.get_size()` on every frame:

| Set | Frames | Surface size | Note |
|---|---|---|---|
| `cruiser`, `drone`, `heavy`, `kamikaze`, `scout`, `sniper`, `turret` | 280 | **32×32** (every frame of every clip) | uniform |
| `mine_asteroid` — `closed`, `open`, `open1`, `open2` | 8 | **64×64** | the mine is twice the size of a ship |
| `mine_asteroid` — `death` | 10 | **32×32** | ⚠️ **the set mixes two canvas sizes** |

> **The prompt's "canvas declarado" column does not hold the canvas — it holds
> the hitbox.** It lists `14×10` for `cruiser`, `18×12` for `heavy`, `10×10` for
> `kamikaze`, `12×8` for `scout`. Those are the **`ENEMY_CONFIGS` hitboxes**,
> copied into the table — the exact mistake F1 warns about, and the one the
> prompt's own §3.2 forbids. The measured sprite canvas of all seven ships is
> **32×32**. The hitboxes are:

| Kind | Hitbox (`ENEMY_CONFIGS`) | Measured canvas | Ratio |
|---|---|---|---|
| `scout` | 12×8 | 32×32 | 2.67× / 4.0× |
| `cruiser` | 14×10 | 32×32 | 2.29× / 3.2× |
| `heavy` | 18×12 | 32×32 | 1.78× / 2.67× |
| `kamikaze` | 10×10 | 32×32 | 3.2× / 3.2× |
| `drone` | 8×8 | 32×32 | 4.0× / 4.0× |
| `sniper` | 16×8 | 32×32 | 2.0× / 4.0× |
| `turret` | 12×12 | 32×32 | 2.67× / 2.67× |
| `mine_asteroid` | 16×16 | 64×64 (32×32 in `death`) | 4.0× / 4.0× |

**Decision: the manifest declares the CANVAS; the hitbox stays in
`ENEMY_CONFIGS` and never enters the manifest.** They are two different things
and the compositor needs only the canvas (the blit geometry). A new guard test
asserts `hitbox ≤ canvas` for every set (F1's mitigation).

### The enemy clips are **built from repeated poses** — this is the central fact

Measured with `Get-FileHash -Algorithm MD5` over every clip directory:

| Clip | Frames | **Distinct images** | md5 groups |
|---|---|---|---|
| `idle` (all 7 ships) | 10 | **3** | `{0,5,9}` `{1,2,3,4}` `{6,7,8}` |
| `thrust` (all 7 ships) | 10 | **1** | all ten identical |
| `damage` (all 7 ships) | 10 | **3** | `{0,1,2,3}` `{4,5,6}` `{7,8,9}` |
| `death` (all 7 ships) | 10 | **4** | `{0}` `{1,2,3}` `{4,5,6}` `{7,8,9}` |
| `mine_asteroid/closed` | 5 | **5** | all unique — 5 *variants*, not a sequence |
| `mine_asteroid/death` | 10 | **1** | all ten identical |
| `mine_asteroid/open`, `open1`, `open2` | 1 each | 1 | single frames |
| `_backup_pre_bloque_65/{closing,opening}` | 3 each | 1 | all three identical |

The auditor's `COLAPSADO` state is *"duplicate md5 inside a clip"* and is a
**FAIL**. Run as-is over the enemy art, **29 of the 33 live clips trip it — 290
frames**. The mine's four variant/state clips have no duplicates and do not
trip it.

That is a false positive: the enemy art was authored by cycling 1–4 poses to
fill ten slots at 12.5 FPS, which is exactly how the runtime plays it.

> **The pose order is irregular and must not be "cleaned up".** `scout/idle` in
> playback order is `A,B,B,B,B,A,C,C,C,A` (A = frames 0/5/9, B = 1–4, C = 6–8).
> De-duplicating the playback into a 3-frame cycle would change the animation
> and break B2. **De-duplication is explicitly out of scope** (see N2).

### The silhouette touches the canvas edge — by design

Measured min margin (alpha > 32): **0 px in 29 of the 33 live clips**. The only
clips above zero are `drone/damage` (3), `drone/idle` (2), `drone/thrust` (3)
and `mine_asteroid/open` (1). The `scout` sprite's wings span the full 32 px of
the canvas; the art is *tight*, not botched (verified by eye on
`Assets/sprites/enemies/scout/idle/frame_00.png`).

The auditor flags `CORTADO` below **2 px** (`CORTADO_MARGIN` in
`src/anim/measure.py`) → **FAIL**, and the repair **re-pads the PNG**, which
would (a) rewrite curated art bytes (R1) and (b) move the ship inside its
canvas, i.e. relative to its hitbox (A5).

### Measured registration (why the enemy sets will use a **fixed** pivot)

Alpha-weighted centroid offset from the canvas centre, per clip. The extremes
are what the decision needs; the full table is reproducible with the command
below.

| Set | max \|dx\| | max \|dy\| | Worst clip |
|---|---|---|---|
| `scout` | 1.38 | 3.60 | `death` (dy) |
| `cruiser` | 1.44 | 3.60 | `death` (dy) |
| `drone` | 1.39 | 3.70 | `idle` (dy) |
| `heavy` | 1.36 | 3.60 | `death` (dy) |
| `kamikaze` | 1.46 | 3.60 | `death` (dy) |
| `sniper` | 0.95 | 3.60 | `death` (dy) |
| `turret` | 1.09 | 3.60 | `death` (dy) |
| `mine_asteroid` | 1.88 | 5.06 | `closed` (dy) |

The enemy art is already centred to within **≤ 1.5 px in x** and **≤ 3.7 px in y**
(ships), while GOLIATH's AI art was off by **−16…+20 px**. Applying the measured
correction to the enemies would move the ship by up to 3.7 px relative to its
hitbox — and B2 requires **pixel-identical** frames. Hence: the enemy sets
declare `pivot = "fixed"` at the canvas centre.

Reproduce with:

```powershell
python -c "import os;os.environ['SDL_VIDEODRIVER']='dummy';import pygame;pygame.init();pygame.display.set_mode((1,1));from pathlib import Path;r=Path('Assets/sprites/enemies');[print(p.parent.name+'/'+p.parent.parent.name,p.stat().st_size) for p in []]"
#   -> the per-frame centroid: use the alpha-weighted centroid of
#      src/anim/measure.py::alpha_centroid over every frame of the clip
```

### Measured scale (the basis for `scale_tolerance`, P5)

Silhouette height per frame (alpha > 32), median, and worst relative deviation
from the median:

| Set | `idle` heights | `thrust` | `damage` | `death` heights | worst deviation |
|---|---|---|---|---|---|
| `cruiser` | 30–32 (median 31) | 32 | 32 | 32×7, 21×3 | 0.3438 (`death`) |
| `drone` | 20 | 20 | 20 | 20,23×3,30×3,21×3 | 0.3043 (`death`) |
| `heavy` | 28–29 (median 29) | 29 | 29 | 29,31×3,32×3,21×3 | 0.3226 (`death`) |
| `kamikaze` | 27–28 (median 28) | 28 | 28 | 28,30×3,32×3,21×3 | 0.3000 (`death`) |
| `scout` | 25 | 25 | 25 | 25,27×3,31×3,21×3 | 0.2222 (`death`) |
| `sniper` | 24–25 (median 25) | 25 | 25 | 25,27×3,30×3,21×3 | 0.2222 (`death`) |
| `turret` | 25 | 26 | 25 | 25,29×3,32×3,21×3 | 0.2759 (`death`) |
| `mine_asteroid` | `closed` 49–59 (median 56) | — | — | `death` 32 | 0.1250 (`closed`) |

The `death` clips shrink the ship on purpose (32 → 21 px): that is the
animation, not a defect, and it is why the death clips need a loose tolerance.

### The runtime today (the facts Phase 1 must not break, Phase 2 must preserve)

| Fact | Where |
|---|---|
| `ANIMATION_FRAME_DURATION = 0.08` → **12.5 FPS**, `animation_frame` 0..9 | `src/entities/enemies/enemy.py:407` |
| `animation_state` ∈ `idle`, `thrust`, `damage`, `death` | `enemy.py:401-406` |
| `idle` and `thrust` **loop** (`animation_frame %= 10`) | `enemy.py:712-713` |
| `damage` and `death` are one-shots that **return to idle** (they do *not* hold on the last frame) | `enemy.py:714-717` |
| The sprite path is `enemies/<kind>/<animation_state>/frame_<NN>.png` | `enemy.py:486` |
| The mine overrides the path: `closed` (by `mine_variant` 0..4), `open1`, `open2`, `open3` → the `open/` directory | `enemy.py:459-485` |
| The blit is **centred on the entity**: `blit_x = e.x - w//2` after `pygame.transform.scale(sprite, w*1.05)` | `gameplay_runtime.py:5313-5345` |
| The hit flash is a **shape-aware white overlay built from the sprite's own alpha**, at `HIT_FLASH_OPACITY` | `gameplay_runtime.py:5331-5338` |
| The red telegraph lives in `_draw_enemy` — the **procedural fallback**, used only when the sprite is missing | `gameplay_runtime.py:4910+` |
| GOLIATH is the only set that already goes through the pipeline (`ClipPlayer`) | `src/ui/scenes.py:198-217`, `gameplay_runtime.py:6097` |
| The scratch surfaces are 64×64 (player), 48×48 (enemy), 64×64 (sub-boss), and each procedural draw computes `offset = size//2 - entity_pos` | `gameplay_runtime.py:360,411,412,5351-5353` |
| The runtime uses the **global** RNG in 31 screen-affecting places; only `_asteroid_rng = random.Random(0xA57E2012)` is seeded | `gameplay_runtime.py:352` + 31 `random.*` call sites |
| `_sets_root()` resolves **only** `Assets/sprites/bosses` (source and `_MEIPASS`) | `src/anim/manifest.py:34-44` |
| `build.spec` bundles `Assets/sprites` wholesale → the new TOMLs **do** ship inside the `.exe` | `build.spec:44` |

> **Correction to the prompt:** the prompt says the telegraph and the damage
> flash are both overlays in `_draw_enemy`. Only the **telegraph** is
> (`_draw_enemy`, the procedural fallback). The **damage flash** is in
> `_draw_enemy_scaled`, the sprite path, and every enemy that has art *does*
> get it. The spec below treats them accordingly.

### The three loose pieces of `mine_asteroid`

| Piece | What it is | Read by |
|---|---|---|
| `_backup_pre_bloque_65/{closing,opening}/` (6 frames, 3 each) | the pre-BLOQUE-65 opening/closing clips | nothing in `src/`; `tests/test_mine_asteroid.py:584-599` (`test_opening_directory_removed`, `test_closing_directory_removed`) asserts `closing/` and `opening/` are **not** at the top level |
| `_new_reference_closed.png` (194×181, 49 626 B) | the user's new reference art for the closed state | `tools/postprocess_mine_asteroid_bloque_65.py`, `tools/generate_mine_asteroid_intermediates_bloque_65.py` — **generator inputs** |
| `_new_reference_open.png` (205×172, 51 055 B) | the user's new reference art for the open state | same two tools — **generator inputs** |
| `closed/frame_00.png` | **byte-equal to `Assets/sprites/asteroids/round.png`** (the camo) | the game, via `mine_variant` |

There is **no empty directory** under `Assets/sprites/enemies` — the archive
directory holds two sub-directories with 3 frames each.

### The pipeline today

| Module | LOC | Role |
|---|---|---|
| `src/anim/manifest.py` | 432 | `load_set`, `AnimSet`, `Clip`, `Part`, `DetectRule` |
| `src/anim/measure.py` | 367 | pixel primitives, `CORTADO_MARGIN = 2` |
| `src/anim/parts.py` | 187 | `draw_part`, `shield_ellipse_rect` |
| `src/anim/anchors.py` | 123 | `load_anchors` |
| `src/anim/clip.py` | 108 | `ClipPlayer` |
| **total `src/anim/`** | **1 217** | |
| `tools/sprite_pipeline/audit.py` | 619 | measure + classify + `write_anchors` |
| `tools/sprite_pipeline/verify_contract.py` | 223 | the contract guard |
| `tools/sprite_pipeline/repair.py` | 159 | deterministic repairs (mirror / re-pad) |
| `tools/sprite_pipeline/run.py` | 141 | validate → audit → repair → re-audit → anchors |
| `tools/sprite_pipeline/__init__.py` | 31 | `ensure_display` |
| **total `tools/sprite_pipeline/`** | **1 173** | |

The LOC counts are **total lines** (blanks included), measured on the base
`773cf08`:

```powershell
git show 773cf08:src/anim/manifest.py | Measure-Object -Line
```

> The first draft of this spec quoted **non-blank** line counts (1 016 /
> 997), which is a different metric. The table above is the comparable one.

The auditor's 7 states (`tools/sprite_pipeline/audit.py`):

| State | FAIL? | Meaning |
|---|---|---|
| `COLAPSADO` | **FAIL** | duplicate md5 inside a clip — the animation became a still |
| `CORTADO` | **FAIL** | the silhouette comes closer than 2 px to a canvas edge |
| `LADO_EQUIVOCADO` | **FAIL** | a sided feature is on the wrong side |
| `FIRMA_AMBIGUA` | warn | the feature's colour signature is ambiguous |
| `AUSENTE` | warn | a declared feature is missing from the frame |
| `FUERA_DE_RANGO` | warn | the feature sits outside the declared range |
| `ESCALADO` | warn | the silhouette height deviates from the clip median |

### Baseline (measured, not quoted)

```powershell
python tools\sprite_pipeline\verify_contract.py goliath    # CONTRACT OK, exit 0
python -m pytest tests\ --tb=no                            # 69.5 s
```

| Result | Value |
|---|---|
| Suite (on `e8be3a2`, when this spec was written) | 2 failed, 2 898 passed, 6 skipped (2 906 total) |
| Suite (on the merged tree `ef86a95`) | 2 failed, 2 935 passed, 7 skipped (2 944 total, 71.6 s) |
| **Suite (on `ddb135c`, the current head)** — **the baseline to use** | **1 failed, 2 941 passed, 6 skipped** |
| The one failure | `tests/test_paths.py::test_paths_no_star_shapes` — pre-existing, documented in `CLAUDE.md`, **out of scope** |
| The CRLF failure | **ALREADY FIXED UPSTREAM.** `f0a97f1` (merged into this branch by `a70673c`) passes `newline="\n"` to `write_anchors` and pins it with two tests (`test_the_generated_anchors_use_lf_line_endings`, `test_the_repository_declares_lf_for_the_toml`). F11 is satisfied — **do not rewrite `write_anchors`**. |
| `verify_contract.py goliath` (merged tree) | `CONTRACT OK`, exit 0 |
| `git status --short` after the suite | **clean** — the suite writes nothing into the tree (L7 holds on the base) |

> **Failure 2 is a real Windows bug, found while writing this spec.**
> `write_anchors` does `path.write_text(rendered, encoding="utf-8")`
> (`tools/sprite_pipeline/audit.py:542`). With Python's default newline
> translation, that writes **CRLF** on Windows. The committed `anchors.toml` is
> **LF** (measured: 0 CR, 607 LF). So every `--fix` rewrites the file with
> different bytes even though the content is identical — the text comparison
> used by the freshness guard passes (universal newlines) while the byte
> comparison fails. On Linux the same code is a no-op. A3 ("byte-identical")
> is therefore **not true today on Windows**, and the fix is one argument:
> `newline="\n"`.

| Other guard | Result |
|---|---|
| `python -m mypy src\anim\` | **could not run**: `No module named mypy` — mypy is in `requirements-dev.txt` but is not installed in this environment. The gate must install it (`python -m pip install -r requirements-dev.txt`); this spec does not install anything. |
| `GameState` count | 15 (`src/core/scene_manager.py`) |
| `def _draw_*` methods in `gameplay_runtime.py` | **34** (42 `self._draw_*` **call sites** in the whole file) |
| `self._draw_*` calls **inside the frame loop** (3969-4165) | **16** |
| Draw operations inside the frame loop | **31** (the background + the 30 below) |

---

## What is NOT done (and why)

| # | Excluded | Reason |
|---|---|---|
| N1 | **Regenerating, redrawing, mirroring or re-padding any enemy PNG** | R1. The art is user-approved. The repair's PNG-writing states (`CORTADO`, `LADO_EQUIVOCADO`) are made structurally unreachable for the enemy sets (below). |
| N2 | **De-duplicating the animation playback** | The pose order is irregular (`A,B,B,B,B,A,C,C,C,A`); a 3-frame cycle would change the animation and break B2. |
| N3 | **Applying the measured registration to the enemy sprites** | It would move the ships by up to 3.7 px relative to their hitboxes. The enemy sets use `pivot = "fixed"`. |
| N4 | **Moving the telegraph or the damage flash into the manifest** | They are runtime overlays, not sprite features. Measuring pixels that are not in the art is meaningless. |
| N5 | **Changing `ENEMY_CONFIGS` (hitboxes, HP, fire rates) or the enemy state machine** | A5: the game must play the same. |
| N6 | **Deleting `_backup_pre_bloque_65/` or the 2 reference PNGs** | The project does not delete art. They stay on disk, excluded from discovery by the rules in §Phase 1. |
| N7 | **The `master` branch, `bloquec-67-goliath-port`, and the other agents' worktrees** | R3 + the multi-agent rule. |
| N8 | **The background (`ParallaxBackground`) and the other 14 scenes** | The background has its own scroll/update path; the other scenes have no playfield. |
| N9 | **The player sprite path (rotation + 0.55 scale), the procedural enemy fallback drawing, and the HUD's internals** | Phase 2 is an orchestration refactor: the layer bodies are the code that exists today. |
| N10 | **`sub_boss`, `carrier`, `mini_drone`** | They have **no sprite set** (`sub_boss` keeps its own 4-direction sprites; the others are procedural). There is nothing to migrate. |
| N11 | **HYDRA, PHANTOM, NEMESIS** | No sprite sets at all — drawn procedurally (`_draw_boss_simple`). |
| N12 | **The `.exe` / PyInstaller build** | `build.spec:44` bundles `Assets/sprites` wholesale, so the new TOMLs ship with no `build.spec` change; rebuilding the `.exe` is the user's call. |
| N13 | **Changing GOLIATH's manifest, anchors or shield constants** | `DX=0, DY=3, RX=11, RY=17, R=11, RX_SCALE=0.78` are user-approved and the oval is invisible by design (R2). Every pipeline change must be **backward compatible with GOLIATH's manifest**. |
| N14 | **Enforcing `mode` / `on_end` in the Phase 1 loader** | They have no Phase 1 consumer in the pipeline; enforcing them would reject GOLIATH's manifest (C4). The enforcement is Phase 2 work. |

---

## Phase 1 — The enemy sets enter the pipeline

### Step 0 — the zero-code experiment (do this FIRST)

Before writing any tooling, prove the pipeline works on an enemy set with **the
fields it already understands**:

1. Write `Assets/sprites/enemies/scout/manifest.toml` with **only** what the
   shipped GOLIATH manifest uses: `[meta]` (name, version, canvas, anchor) and
   `[[clips]]` (id, dir, frames, fps, loop). One `[[parts]]` entry with
   `draw = "frames"`.
2. Run:
   ```powershell
   python tools\sprite_pipeline\audit.py scout --root Assets\sprites\enemies
   ```
3. **Go/no-go:**
   * **No-go** if the auditor raises on a set without `shield_plate` / `eye`
     parts (the C1 defect, confirmed in this repo). Fix the auditor first —
     it is a 3-line change — then continue.
   * **No-go** if the report shows the `COLAPSADO` findings the art genuinely
     has (it will: 4 clips × 10 frames). That is the expected outcome and the
     reason `distinct` exists; it is **not** a reason to stop.
   * **Go** when the auditor produces a report and the only findings are the
     ones the art really has.

Step 0 costs one file and one command. It is where the methodology either
generalises or does not.

### What changes

**Phase 1 touches no runtime code.** The enemy sets keep being read as raw PNGs
by `Enemy.animation_path` / `_get_enemy_sprite`, exactly as today. Phase 1 adds
the *declaration* and the *measurement*; Phase 2 is where the runtime starts
reading them.

| Change | Kind | Why |
|---|---|---|
| 8 × `Assets/sprites/enemies/<kind>/manifest.toml` | new | the declaration of each set |
| 8 × `Assets/sprites/enemies/<kind>/anchors.toml` | new, generated | the measurement of each set |
| `src/anim/manifest.py` | modified | 3 new optional fields + 2 parsed-but-unenforced ones; **`part_or_none()`** |
| `src/anim/measure.py` | modified | `effective_cut_margin(anim_set)` — one shared source for the auditor and the repair (P6) |
| `tools/sprite_pipeline/audit.py` | modified | honours `distinct` and `cut_margin`; tolerates a set with no detected features (C1); reports the frame size and the registration; **writes LF** (`newline="\n"`) |
| `tools/sprite_pipeline/repair.py` | modified | reads the effective margin; never writes for the enemy sets |
| `tools/sprite_pipeline/sets.py` | new | set discovery |
| `tools/sprite_pipeline/gate.py` | new | the Phase 1 gate, one command |
| **7** new test files | new | the guards (below) |
| `tests/test_sprite_pipeline_run.py` | modified | the pre-existing Windows failure becomes green |

### The manifest fields this BLOQUE adds

**Phase 1 ships 3 new fields.** All are optional and default to today's
behaviour, so GOLIATH's manifest keeps working **unmodified** (N13).

| Field | Scope | Default | Meaning | Phase |
|---|---|---|---|---|
| `meta.cut_margin` | set | `CORTADO_MARGIN` (2) | the minimum px the silhouette must keep from every canvas edge. `0` = the art may touch the edge. | 1 |
| `clip.distinct` | clip | *unset* | the number of **distinct source images** the clip is built from. When unset, the old rule applies (any duplicate md5 → `COLAPSADO`). | 1 |
| `clip.canvas` | clip | `meta.canvas` | the canvas of this clip, when it differs from the set's (the mine's `death`). | 1 |
| `clip.mode` | clip | `"sequence"` | `sequence` \| `variants` \| `state` \| `archive` — the **documentation** of what the clip is. **Parsed but NOT enforced in Phase 1** (N14). | 2 |
| `clip.on_end` | clip | derived from `loop` | `loop` \| `hold` \| `reset` — what happens when the clip ends. **Parsed but NOT enforced in Phase 1** (N14). | 2 |

**Why `mode` and `on_end` are parsed but not enforced in Phase 1:**

* They have **no consumer in the pipeline**. The Phase 1 auditor does not need
  to know that `closed` holds 5 alternatives rather than a sequence: the
  `distinct` declaration already covers the state that would fire.
* Enforcing them in the Phase 1 loader would **reject GOLIATH's own manifest**,
  which declares 7 clips with `fps`/`loop` and no `mode`/`on_end` — the loader
  would raise, `scenes.py::_load_manifest()` would return `None`, and the boss
  would silently lose its compositor (C4).
* They are still **verified in Phase 1**, by a test rather than by the loader:
  `tests/test_enemy_clip_semantics.py` asserts that the declared `mode` and
  `on_end` match what the runtime actually does (`mine_variant` indexing, the
  one-shot that returns to idle). A declaration that does not match the runtime
  is a red test.

**The precedence rule that keeps GOLIATH safe:** the loader applies **no**
validation to a clip that does not declare `mode`. A clip that declares it is
validated only from Phase 2 on, and the rules are: `variants` → `distinct` must
equal `frames`; `state` → `frames = 1`; `sequence` → `fps` and `on_end`
present. `on_end` is derived from the existing `loop` flag when absent
(`loop = true` → `loop`, else → `hold`), so GOLIATH's `death` keeps holding on
frame 9 and the enemies' `damage`/`death` declare `reset`.

#### The two declarations that make the auditor honest about the enemy art

1. **`distinct`** turns `COLAPSADO` from "there is a duplicate" into "the clip's
   distinct-image count **does not match** what the manifest declares". A clip
   that declares `distinct = 4` and measures 4 is healthy; one that measures 3
   has collapsed further than declared → **FAIL**. A clip that declares `4` and
   measures 5 has a **stale declaration** → also **FAIL** (the manifest must
   describe the art).
2. **`cut_margin = 0`** acknowledges that the enemy art is authored tight to its
   canvas. It is a property of the **art**, not of the pipeline — GOLIATH's 2 px
   rule exists because the AI generator drew the boss's limbs past the canvas.
   The auditor still **reports** the measured minimum margin per clip, so the
   tightness stays visible; it simply stops being a FAIL.

> **Why the enemy sets can never be "repaired".** `repair.py` writes PNGs only
> for `CORTADO` and `LADO_EQUIVOCADO`. With `cut_margin = 0` the first can
> never fire, and with no `sided` feature declared the second can never fire
> either. So on an enemy set the repair has **nothing to write** — A4 holds by
> construction, not by convention. A guard test proves it on every run.

### The manifest per set — a complete, real example

`Assets/sprites/enemies/scout/manifest.toml`:

```toml
# SPEC of the animation set. Hand-edited.
# Verified by: tools/sprite_pipeline/audit.py
# Design: docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md
#
# The canvas is the SPRITE canvas, measured (32x32), NOT the hitbox
# (ENEMY_CONFIGS says 12x8). See the spec, "Context".
#
# L1: no multi-line inline table. Every inline table stays on ONE line.

[meta]
name        = "SCOUT"
version     = 1
canvas      = [32, 32]      # every frame of every clip
anchor      = [16, 16]      # the canvas centre: the sprite is blitted centred on the entity
cut_margin  = 0             # the enemy art is authored tight to its canvas

[[clips]]
id       = "idle"
dir      = "idle"
frames   = 10
fps      = 12.5             # ANIMATION_FRAME_DURATION = 0.08 in the runtime
distinct = 3                # 10 frames built from 3 source poses (md5 measured)
mode     = "sequence"       # Phase 1: documentation only. Enforced in Phase 2.
on_end   = "loop"           # Phase 1: documentation only. Enforced in Phase 2.
scale_tolerance = 0.10      # measured deviation 0.0000 -> the 0.10 floor applies

[[clips]]
id       = "thrust"
dir      = "thrust"
frames   = 10
fps      = 12.5
distinct = 1                # all ten frames are the same pose
mode     = "sequence"
on_end   = "loop"
scale_tolerance = 0.10

[[clips]]
id       = "damage"
dir      = "damage"
frames   = 10
fps      = 12.5
distinct = 3
mode     = "sequence"
on_end   = "reset"         # one-shot, then back to idle (the runtime's behaviour today)
scale_tolerance = 0.10

[[clips]]
id       = "death"
dir      = "death"
frames   = 10
fps      = 12.5
distinct = 4                # frame_00 alone + three poses of three
mode     = "sequence"
on_end   = "reset"         # one-shot, then back to idle
scale_tolerance = 0.45      # measured deviation 0.2222 -> margin 2.0x

[[parts]]
id    = "body"
draw  = "frames"
pivot = "fixed"            # the canvas centre: the measured registration is NOT applied
z     = 0
```

`Assets/sprites/enemies/mine_asteroid/manifest.toml` — the special one:

```toml
# MINE_ASTEROID. Four visual states, one of them with five variants,
# and a death clip the runtime never plays. See the spec, Phase 1.

[meta]
name        = "MINE_ASTEROID"
version     = 1
canvas      = [64, 64]      # the open/closed states; the death art is 32x32 (declared below)
anchor      = [32, 32]
cut_margin  = 0

[[clips]]
id       = "closed"
dir      = "closed"
frames   = 5
distinct = 5                # 5 different asteroid looks, indexed by mine_variant
mode     = "variants"       # alternatives, not a sequence
scale_tolerance = 0.25      # measured deviation 0.1250 -> margin 2.0x

[[clips]]
id       = "open1"
dir      = "open1"
frames   = 1
distinct = 1
mode     = "state"
scale_tolerance = 0.10

[[clips]]
id       = "open2"
dir      = "open2"
frames   = 1
distinct = 1
mode     = "state"
scale_tolerance = 0.10

[[clips]]
id       = "open3"
dir      = "open"           # the terminal state reuses the `open/` directory (BLOQUE 65)
frames   = 1
distinct = 1
mode     = "state"
scale_tolerance = 0.10

[[clips]]
id       = "death"
dir      = "death"
frames   = 10
fps      = 12.5
distinct = 1
mode     = "archive"        # dead art: `Enemy.animation_path` never returns it
canvas   = [32, 32]         # this clip's art is 32x32, not the set's 64x64
scale_tolerance = 0.10

[[parts]]
id    = "body"
draw  = "frames"
pivot = "fixed"
z     = 0
```

#### Why `mine_asteroid/death` is `mode = "archive"`

`Enemy.animation_path` (`enemy.py:459-485`) returns the **mine state** path for
every frame of the mine's life — `closed/`, `open1/`, `open2/` or `open/` — and
**never** the `death/` directory, not even when `animation_state == "death"`.
The 10 death frames are on disk, they are 32×32 while the mine is 64×64, and
**the runtime never draws them**.

| Option | Verdict |
|---|---|
| Make the runtime play the death clip | **Rejected.** The mine would visibly shrink from 64×64 to 32×32 while dying — a visual regression (B2) and an art decision nobody asked for. |
| Delete the death directory | **Rejected.** N6 — the project does not delete art, and the directory is the only record that the mine once had a death animation. |
| **Declare it as `mode = "archive"`** | **Chosen.** The pipeline measures it, the manifest documents it, and the runtime keeps not playing it. |

The same reasoning applies to `_backup_pre_bloque_65/{closing,opening}`: they
are **not** a set and **not** clips. They stay on disk as the pre-BLOQUE-65
record. Discovery excludes them by the rules below.

### The per-set declaration table (all 8 sets)

`fps = 12.5` for every ship clip. `on_end`: `idle`/`thrust` → `loop`,
`damage`/`death` → `reset`. `distinct`: `idle` 3, `thrust` 1, `damage` 3,
`death` **4** for every ship.

| Set | `meta.canvas` | `meta.anchor` | `cut_margin` | pivot | `scale_tolerance` per clip |
|---|---|---|---|---|---|
| `scout` | 32×32 | 16,16 | 0 | fixed | idle 0.10 · thrust 0.10 · damage 0.10 · death **0.45** |
| `cruiser` | 32×32 | 16,16 | 0 | fixed | idle 0.10 · thrust 0.10 · damage 0.10 · death **0.70** |
| `drone` | 32×32 | 16,16 | 0 | fixed | idle 0.10 · thrust 0.10 · damage 0.10 · death **0.65** |
| `heavy` | 32×32 | 16,16 | 0 | fixed | idle 0.10 · thrust 0.10 · damage 0.10 · death **0.65** |
| `kamikaze` | 32×32 | 16,16 | 0 | fixed | idle 0.10 · thrust 0.10 · damage 0.10 · death **0.60** |
| `sniper` | 32×32 | 16,16 | 0 | fixed | idle 0.10 · thrust 0.10 · damage 0.10 · death **0.45** |
| `turret` | 32×32 | 16,16 | 0 | fixed | idle 0.10 · thrust 0.10 · damage 0.10 · death **0.60** |
| `mine_asteroid` | 64×64 | 32,32 | 0 | fixed | closed **0.25** · open/open1/open2 0.10 · death 0.10 (32×32 canvas) |

**The tolerance rule (P5 — justified by the margin, not inherited):**

```
scale_tolerance = ceil_to_0.05( max( 2.0 × worst_measured_relative_deviation , 0.10 ) )
```

* `worst_measured_relative_deviation` = `max(|height - median(heights)|) / median(heights)` over the clip's frames, measured with the table above.
* `2.0 ×` is the **margin**: every declared tolerance is at least twice the worst measured deviation, so a real art change has to be twice as bad as anything the art has ever shown before the guard fires.
* The `0.10` floor keeps a constant-height clip from becoming a knife-edge (one pixel of drift on a 25 px ship is 4 %, below 10 %).
* The death clips need a loose tolerance because the death animation **deliberately shrinks the sprite** (32 → 21 px). That is the animation, not a defect.

Reproduce the table with:

```powershell
python tools\sprite_pipeline\audit.py scout --root Assets\sprites\enemies --json
```

### Set discovery (the CLI's "where do sets live")

The CLI already accepts `--root`, "the directory that HOLDS the sets"
(`run.py:58-64`, `audit.py:549-557`), and `load_set(name, root)` resolves
`root / name / manifest.toml`. The first enemy set therefore needs **no new
mechanism at all**:

```powershell
python tools\sprite_pipeline\run.py scout --root Assets\sprites\enemies
```

What is added is a **single, explicit discovery rule** in a new
`tools/sprite_pipeline/sets.py`:

| Rule | Statement |
|---|---|
| D1 | A directory is a **set** iff it contains a `manifest.toml`. Nothing else is a set. |
| D2 | A directory whose name starts with `_` is **never** a set (this is what excludes `_backup_pre_bloque_65`). |
| D3 | A PNG that is not named `frame_*.png` is **not a frame** (this is what excludes `_new_reference_closed.png` / `_new_reference_open.png`). |
| D4 | The two roots are `Assets/sprites/bosses` (GOLIATH) and `Assets/sprites/enemies` (the 8 sets). `sets.py` resolves a set name against **both**, in that order, and returns the first hit. `--root` overrides it. The signature is `resolve_set(name: str, root: Path \| None = None) -> Path`; `run.py` / `audit.py` / `verify_contract.py` call it instead of building `root / name` themselves. |
| D5 | The 2 reference PNGs are **generator inputs** and stay where they are. They are not read by the game and not by the pipeline. |
| D6 | `sets.py` must **degrade, not crash** (L5): a malformed `manifest.toml` raises `tomllib.TOMLDecodeError`, which is a `ValueError` and **not** a `ManifestError`. `resolve_set` catches `(OSError, ValueError)` and reports the set as unreadable — it must never take the game loop down. |

D1 + D2 + D3 are the whole exclusion story: the backup directory has no
manifest, the loose PNGs are not frames, and both are invisible to discovery.
There is no "is this a real set?" heuristic to get wrong.

### The auditor must tolerate a set with no detected features (C1)

The shipped auditor assumes every set has GOLIATH's features:

```python
# tools/sprite_pipeline/audit.py:175-176
shield_part = anim_set.part("shield_plate")   # raises ManifestError if absent
eye_part = anim_set.part("eye")               # raises ManifestError if absent
# tools/sprite_pipeline/audit.py:154 (inside _clip_probe_columns)
rule = anim_set.part("shield_plate").detect   # same problem
```

`manifest.py:285-289` raises for an unknown part id, so **a body-only enemy
manifest crashes the auditor before it measures a single frame**. The Phase 1
change:

| File | Change |
|---|---|
| `src/anim/manifest.py` | add `part_or_none(part_id: str) -> Part | None` — the non-raising sibling of `part()` |
| `tools/sprite_pipeline/audit.py` | use `part_or_none` at lines 154, 175 and 176. The rest of the function already guards with `rule is not None` / `eye_part.detect is not None` (lines 207, 259, 273), so the `None` path is already handled — the crash is only the *lookup*. |

The **sources** must also stop lying. Today `audit.py:258` and `:272` default
`eye_source` / `shield_source` to `"measured"`, and `render_anchors_toml`
writes `eye = [0, 0]` when the eye is `None`. For a set with no `eye` part that
produces `eye = [0, 0], eye_source = "measured"` — a **false provenance**, and
`load_anchors` would accept it as a real eye anchor (the "eye laser launched
from the corner of the canvas" hazard the module's own docstring warns about).

Phase 1 change: the sources default to **`"missing"`**, and `"measured"` is set
only inside the branch where the detector actually found the feature. A
featureless set then bakes `eye = [0, 0], eye_source = "missing"` — an
unresolved feature, which every consumer already tolerates.

### What the implementer must decide, and how

| # | Decision | How it is decided | Answer in this spec |
|---|---|---|---|
| 1 | The canvas of each set | measure the PNG surface | 32×32 (ships), 64×64 / 32×32 (mine) — measured above |
| 2 | The fps | read the runtime constant | 12.5 (`ANIMATION_FRAME_DURATION = 0.08`) |
| 3 | `loop` / `on_end` | read the runtime's advance rule | `idle`/`thrust` loop; `damage`/`death` **reset** to idle |
| 4 | `scale_tolerance` | the formula above, applied to the measured heights | the per-clip table above |
| 5 | `side_tolerance` | **not applicable** | the enemy sets have no sided feature; the field stays at the default and no `detect` rule is declared |
| 6 | Features to detect | none | the enemy sprites have no detectable feature (no plate, no eye). `[[parts]]` declares only `body`. `on_missing` does not apply (P3): with no feature to interpolate, there is nothing to reconstruct. |
| 7 | The telegraph / damage flash | not in the manifest | runtime overlays (N4). In Phase 2 the flash becomes a **layer**, not a `Part`. |
| 8 | `distinct` per clip | md5 count | the table above |
| 9 | `mode` per clip | the runtime's use of the directory | sequence / variants / state / archive |
| 10 | The pivot | the runtime's blit | `fixed` at the canvas centre |
| 11 | The backup and the 2 reference PNGs | D2/D3/D5 | stay on disk, excluded from discovery |
| 12 | The `mine_asteroid/death` clip | the runtime never plays it | `mode = "archive"` |
| 13 | Whether the enemy `anchors.toml` files are needed at all | what Phase 2 reads | **yes, but only for the body offset**: with `pivot = "fixed"` the applied offset is `(0,0)`, so the table's body offsets are zero by definition and its real content is the *provenance* (which feature was measured where). The registration measurement lives in the **audit report**, not in the table. Phase 2 reads the enemy tables for the frame's presence and the applied offset. |

### The 7 auditor states mapped to the enemy case (Q4)

| State | What it means for an enemy set | Expected? | Resolution |
|---|---|---|---|
| `COLAPSADO` | a clip's distinct-image count ≠ the declared `distinct` | **Yes, expected** — 29 of 33 live clips repeat poses | **declared**: `distinct` per clip. The state only fires when the art disagrees with the manifest. |
| `CORTADO` | the silhouette is closer than `cut_margin` to an edge | **Yes, expected** — 29 of 33 live clips touch the edge by design | **declared**: `cut_margin = 0`. The measured margin is still reported. |
| `LADO_EQUIVOCADO` | a sided feature is on the wrong side | **Never** — the enemy sets declare no `sided` feature and no `detect` rule | Nothing to declare. |
| `FIRMA_AMBIGUA` | a feature's colour signature is ambiguous | **Never** — no feature is declared | Nothing to declare. |
| `AUSENTE` | a declared feature is missing | **Never** — no feature is declared | Nothing to declare. |
| `FUERA_DE_RANGO` | a feature is outside its declared range | **Never** — no feature is declared | Nothing to declare. |
| `ESCALADO` | the silhouette height deviates from the clip median | **Only in `death`** — the death animation shrinks the ship on purpose | **declared**: a loose `scale_tolerance` per death clip, justified by the measured deviation. |

**Result: an enemy set audits to 0 FAIL with 0 WARN** — the only states that
*can* fire are the two that the manifest declares, and the declarations match
the measured art.

### The guards (new tests)

| Test | Asserts |
|---|---|
| `tests/test_enemy_manifest_matches_assets.py` | every set has a `manifest.toml`; every declared clip's dir exists; the frame count matches; **every frame's surface size equals the clip's effective canvas** (`clip.canvas` or `meta.canvas`; the mine's `death` included) |
| `tests/test_enemy_anchors_are_fresh.py` | re-rendering `anchors.toml` produces no diff — the file is not stale (and the comparison is **text**, never a write: L7) |
| `tests/test_enemy_set_discovery.py` | discovery finds exactly 8 sets; `_backup_pre_bloque_65` and the 2 loose PNGs are not sets and not frames (D1-D3); a malformed manifest degrades instead of crashing (D6/L5) |
| `tests/test_enemy_hitbox_is_not_the_canvas.py` | for every kind, `ENEMY_CONFIGS.width ≤ canvas.width` and `height ≤ canvas.height` (F1) |
| `tests/test_enemy_art_is_untouched.py` | after a full `--fix` run on a **copy** of every enemy set, every PNG's md5 is unchanged (A4, R1) |
| `tests/test_enemy_clip_semantics.py` | `distinct` matches the measured md5 count; `mode` matches the runtime's use; `on_end` matches the runtime's advance rule |
| `tests/test_audit_runs_on_a_featureless_set.py` | the auditor measures a set that declares only a `body` part, with no `shield_plate` and no `eye` (the C1 regression) |

---

## The gate

**Phase 2 does not start until this gate passes.** The gate is one command:

```powershell
python tools\sprite_pipeline\gate.py
```

It prints `PHASE 1 GATE OK` (exit 0) or `PHASE 1 GATE FAILED:` followed by the
list of failed items (exit 1). It runs every check below and reports **all**
failures, not just the first.

| # | Check | Command / method | Pass condition |
|---|---|---|---|
| G1 | Every enemy set audits clean | `run.py <set> --root Assets\sprites\enemies --json` for the 8 sets | `failures == []` and `warnings == []` |
| G2 | The anchors are fresh | re-render and compare **as a string** (never write) | byte-identical to the committed file |
| G3 | The anchors are deterministic | render twice, compare the bytes | identical |
| G4 | The art is untouched | md5 of every PNG before/after a `--fix` run **on a copy** | identical |
| G5 | GOLIATH is unharmed | `verify_contract.py goliath` | `CONTRACT OK`, exit 0 |
| G6 | The manifests match the assets | the new guard tests | green |
| G7 | The hitbox is not the canvas | the new guard test | green |
| G8 | The suite does not regress | `python -m pytest tests\ --tb=no` | **a delta check, not an absolute count**: the number of failures must not grow beyond the baseline (2), and `test_the_fix_run_changes_no_file` must be **green** after this phase. An absolute count would break the gate the moment another agent adds a test. |
| G9 | The mypy gate is clean | `python -m mypy src\anim\` | `Success: no issues found` (mypy must be installed: `python -m pip install -r requirements-dev.txt`) |
| G10 | GOLIATH's manifest is untouched | `git diff --stat Assets\sprites\bosses\goliath\` | empty |
| G11 | The working tree is clean after the gate | `git status --short` | empty (the gate must not rewrite committed artifacts — L7) |
| G12 | The auditor tolerates a featureless set | the new guard test | green (the C1 regression) |
| G13 | The capture harness is deterministic | capture the same frame twice with `tools\capture\layerstack_frames.py` | the two PNGs are **byte-identical**; a non-deterministic capture fails the gate before the golden set is trusted (F19). Part of Phase 2's gate, run when the harness exists. |

**If the gate fails:** Phase 2 does not start. The failing item is fixed in
Phase 1 — **except** G8's `test_paths_no_star_shapes`, which is documented as
pre-existing in `CLAUDE.md` and is explicitly out of scope (it must simply not
get worse: the count of failures must not grow).

### Phase 1 acceptance criteria

| # | Criterion | How the gate proves it |
|---|---|---|
| A1 | At least 1 enemy set enters the pipeline with `manifest.toml` + `anchors.toml` and 0 FAIL | **All 8** sets do — G1 |
| A2 | `audit.py` runs over an enemy set without changing GOLIATH's behaviour | G5 + G10 (GOLIATH's manifest is not modified; its contract still passes) |
| A3 | The regenerated `anchors.toml` is byte-identical across two runs | G3 — **and this requires the `newline="\n"` fix**, which is why that fix is in this phase |
| A4 | The enemy frames do not change bytes | G4 |
| A5 | The hitboxes and the collision do not change | Phase 1 changes no runtime code at all; G6/G7 assert the canvas and the hitbox stay separate |
| A6 | The pipeline runs with no network, no AI and no clock | the pipeline imports only `pygame`, `tomllib`, `hashlib`, `statistics`, `pathlib`, `argparse`, `json`, `os`, `sys` — the gate asserts that no other import appears in `src/anim/` and `tools/sprite_pipeline/`: `python -c "import ast,pathlib;[print(p) for p in pathlib.Path('tools/sprite_pipeline').glob('*.py') for n in ast.walk(ast.parse(p.read_text(encoding='utf-8'))) if isinstance(n,(ast.Import,ast.ImportFrom))]"` → no `requests`, `urllib`, `socket`, `openai`, `anthropic`, `datetime`, `time`. `datetime`/`time` are banned because they would break R7's determinism. |

---

## Phase 2 — The gameplay frame becomes a `LayerStack`

### What changes

Phase 2 is an **orchestration refactor**. No drawing code changes: every layer
is the drawing code that exists today, called with a context. The frame loop
keeps its exact draw order, and the proof is a pixel comparison.

| Change | Kind |
|---|---|
| `src/render/__init__.py`, `src/render/layer.py` | new — `Layer`, `LayerStack`, `DrawContext` |
| `src/ui/gameplay_layers.py` | new — the layer factory: one entry per draw operation, in the measured order |
| `src/ui/gameplay_runtime.py` | modified — the frame loop becomes: build the context → `stack.render(target, ctx)` |
| `src/entities/enemies/enemy.py` | modified — the animation timing comes from the manifest (`fps`, `on_end`) instead of the hardcoded `ANIMATION_FRAME_DURATION` |
| `src/ui/gameplay_runtime.py` (sprite path) | modified — the enemy sprite is fetched through the pipeline (`ClipPlayer`) instead of the raw PNG path |
| `src/anim/parts.py` | modified — **the `fixed` pivot** (see below) |
| `src/anim/clip.py` | modified — `on_end = "reset"`, and the per-clip canvas |
| `src/anim/manifest.py` | modified — enforce `mode`/`on_end`, resolve the enemies root (source and `_MEIPASS`) |
| `tests/test_layer_stack_order.py` | new |
| `tests/test_layer_stack_renders_identical_frames.py` | new — the golden comparison |
| `tools/golden/layerstack/*.png` | new — the "before" frames, committed |
| `tools/capture/layerstack_frames.py` | new — the deterministic capture harness |

**Constraints on the new package (R4 + L6):**

* `src/render/` is **stdlib + pygame only** (R4). No numpy, no new dependency.
* `src/render/` **must not import `src/ui/` or `src/entities/`** (L6): the mypy gate covers `src/`, and importing `src/ui/` drags its ~145 pre-existing errors into the `src/ranim/` gate. `src/render/` depends on `src/anim/` only; the game-specific layers live in `src/ui/gameplay_layers.py` and may import the runtime.
* Every new public function carries type annotations (`mypy strict = true`).

### The abstract `Layer`

```python
@dataclass(frozen=True)
class Layer:
    """One draw operation of the gameplay frame.

    id      stable identity: the golden-frame test and the order guard
            name layers by what they draw ("enemies", "boss", "hud").
    z       the global order. The stack sorts by z with a STABLE sort, so
            two layers with the same z keep their insertion order.
    draw    the drawing body. It receives the target and the context.
    visible whether the layer draws at all this frame (a layer may be
            skipped without removing it from the stack).
    """
    id: str
    z: int
    draw: Callable[[pygame.Surface, DrawContext], None]
    visible: bool = True
```

* A layer has **identity** (`id`), an **order** (`z`) and a **draw**.
* **Animation is optional**: a layer may carry a `ClipPlayer` and a clip id
  (the enemy layer does), but the stack does not require it. The `Part`
  hierarchy of BLOQUE 74 is the *inside* of an animated layer; `Layer` is the
  *outside* — one layer draws many parts, or none.
* `z` is an `int`, not a float, and not a string: the order is total and
  explicit.

### `LayerStack`

```python
class LayerStack:
    """The ordered set of layers that compose one frame.

    The stack owns the ORDER and nothing else. It never draws a layer
    itself, never mutates a layer and never reorders at runtime: the
    order is fixed at build time and asserted by a guard test.
    """
    def __init__(self, layers: Sequence[Layer]) -> None: ...
    def render(self, target: pygame.Surface, ctx: DrawContext) -> None: ...
```

* `render` walks the layers in `z` order (stable) and calls `draw(target, ctx)`.
* The stack is built **once** per scene entry and reused every frame; only the
  context changes.
* A layer that needs per-frame state (e.g. "the enemies layer draws the pool
  that is alive right now") reads it from the runtime through the closure the
  factory captures — the stack stays a dumb, ordered container.

### `DrawContext`

```python
@dataclass(frozen=True)
class DrawContext:
    """Everything a layer needs to know about WHERE and WHEN it draws.

    origin  the world point that maps to the CENTRE of the target surface.
            For the playfield: the centre of the 320x480 internal surface.
    scale   the uniform scale of the target. 1.0 for the internal surface.
    time    seconds since the scene started (the current `self._t`).
    shake   the screen-shake offset (shx, shy), already computed.
    size    the target's size (INTERNAL_W, INTERNAL_H) for the playfield.
    """
    origin: tuple[float, float]
    scale: float
    time: float
    shake: tuple[int, int]
    size: tuple[int, int]

    def with_origin(self, x: float, y: float) -> "DrawContext":
        """A copy whose origin is another world point.

        The procedural fallback draws into a scratch surface centred on the
        entity: the scratch is 64x64 (player), 48x48 (enemy) or 64x64
        (sub-boss), and the current code computes
        `offset = scratch_size // 2 - entity_pos` per entity
        (gameplay_runtime.py:5351-5353). `with_origin` replaces that
        arithmetic: the layer asks for a context centred on the entity and
        the scratch draw becomes ordinary code.
        """
        return replace(self, origin=(x, y))
```

* It replaces the hand-passed `(target, shx, shy)` and the scratch-surface
  `offset_x/offset_y` trick: a layer draws at `world_pos + ctx.shake`, or at
  `world_pos - ctx.origin` when it draws into a scratch surface whose centre
  is the origin.
* **One origin, two uses.** `ctx.origin` is the playfield centre for the main
  target; `ctx.with_origin(e.x, e.y)` is the entity-centred context for a
  scratch draw. A single frozen field cannot be both, which is why the
  method exists instead of a second field.
* **`scale` stays 1.0 and the internal resolution stays 320×480.** The window
  scaling still happens in `Game._present()` — the stack never touches it
  (F6). A guard test asserts `ctx.size == (320, 480)`.
* `time` is the scene clock, not the wall clock: the pipeline stays
  deterministic (R7).

### The `fixed` pivot (C3) — the one compositor change Phase 2 needs

`src/anim/parts.py` contains **zero** references to `pivot` today: `Part.pivot`
is parsed (`manifest.py:240`) and never read. `_base()` (lines 82-96) always
adds `anchor.body_dx / body_dy`:

```python
return (ox - canvas[0] // 2 + anchor.body_dx,
        oy - canvas[1] // 2 + anchor.body_dy)
```

For this art the baked offsets are **not zero** (`body_dy = round(16 − centroid_y)`:
`drone/idle` ≈ −4, `cruiser/idle` ≈ +2), so drawing the enemies through
`ClipPlayer` without a pivot change would move every ship by 1–4 px relative to
its hitbox — and the golden comparison would report thousands of differing
pixels.

**The Phase 2 change in `src/anim/parts.py`:** `_base()` ignores the measured
offset when the part's pivot is `"fixed"`:

```python
# the applied offset is zero for a fixed pivot: the sprite is blitted
# centred on the entity, exactly as the runtime does today.
applied = (0, 0) if part.pivot == "fixed" else (anchor.body_dx, anchor.body_dy)
```

The **measured** offset is not lost: it stays in the anchors table (it is the
measurement) and in the audit report; the pivot decides whether it is
**applied**. GOLIATH's `pivot = "centroid"` behaviour is unchanged.

### The order (the part that must not change)

The frame loop (`src/ui/gameplay_runtime.py:3969-4165`) performs **31 draw
operations**: the background (3969-3971) plus the **30** below, which become the
stack with these exact `z` values.

| z | Layer | Today | Source |
|---|---|---|---|
| — | *(background: parallax + galaxy)* | **outside the stack**, drawn before it | 3969-3971 |
| 0 | `ambient_dust` | `self._draw_ambient_dust(target)` | 3973 |
| 1 | `player_damage_flash` | inline full-screen red | 3978-3982 |
| 2 | `powerups` | inline loop | 3985-4026 |
| 3 | `enemies` | inline loop → `self._draw_enemy_scaled` | 4028-4031 |
| 4 | `asteroids_and_powerups` | `self._draw_asteroids_and_powerups(target)` | 4035 |
| 5 | `leader_glows` | `draw_leader_glows(...)` | 4039-4044 |
| 6 | `boss` | `self._draw_boss(target, shx, shy)` | 4046-4047 |
| 7 | `boss_spears` | inline loop → `self._draw_boss_spear` | 4049-4051 |
| 8 | `shield_laser` | `self._draw_shield_laser(target, shx, shy)` | 4054-4055 |
| 9 | `shockwaves` | inline loop | 4057-4066 |
| 10 | `bomb_bursts` | inline loop | 4068-4072 |
| 11 | `bullets` | `self._draw_bullets_with_glow(target, shx, shy)` | 4074 |
| 12 | `missiles` | `self._draw_missiles(target, shx, shy)` | 4076 |
| 13 | `tron_trail` | `self._tron_trail.draw(target, (shx, shy))` | 4085-4086 |
| 14 | `player_afterimage` | `self._draw_player_afterimage(target, shx, shy)` | 4093-4094 |
| 15 | `player` | `self._draw_player_scaled(target, shx, shy)` | 4096-4100 |
| 16 | `continuous_laser` | `self._draw_continuous_laser(target, shx, shy)` | 4103 |
| 17 | `reticle` | `self._draw_reticle(target, shx, shy)` | 4105-4106 |
| 18 | `bomb_flash` | inline full-screen white | 4108-4112 |
| 19 | `particles` | `self._particles.draw(target, (shx, shy))` | 4114 |
| 20 | `score_popups` | `self._draw_score_popups(target, shx, shy)` | 4116 |
| 21 | `wave_indicator` | `self._draw_wave_indicator(target)` | 4118 |
| 22 | `play_area_frame` | `self._draw_play_area_frame(target)` | 4120 |
| 23 | `hud` | `self._hud.draw(target, ...)` | 4126-4127 |
| 24 | `pattern_banner` | inline | 4129-4138 |
| 25 | `screen_flash` | inline full-screen | 4140-4144 |
| 26 | `charge_release_flash` | inline full-screen | 4146-4150 |
| 27 | `pickup_flash` | inline full-screen | 4152-4156 |
| 28 | `level_up_flash` | inline full-screen | 4158-4162 |
| 29 | `speed_lines` | `self._draw_speed_lines(target)` | 4164-4165 |
| — | *(render-timing debug log)* | **not a draw** | 4167+ |

**Three explicit decisions about scope (the prompt requires them):**

| Thing | In or out | Why |
|---|---|---|
| **The background** (`ParallaxBackground` + the galaxy strip) | **OUT** — drawn before the stack | It has its own update and scroll state, it is the only thing that must be behind everything, and the prompt states it does not go through the compositor. Its place is documented: "the stack's backdrop". |
| **The HUD** | **IN**, at `z = 23` | It is drawn *inside* the playfield sequence — between the play-area frame and the pattern banner, and **after** it come the full-screen flashes. Moving it out of the stack would change the frame (B2). The HUD's own drawing does not change; the layer just calls `self._hud.draw(...)` at the same point. |
| **Bullets, player, particles, the full-screen flashes, the speed lines** | **IN** | They are part of the measured order and of the proof. Their *bodies* do not change. |
| **The debug render-timing log** | **OUT** | It is not a draw; it is a log line. |
| **The other 14 scenes** (TITLE, CINEMATIC, GALLERY, …) | **OUT** | They have no playfield and no frame stack. The stack is a property of `GameplayRuntime`. |

### The boundary with the `SceneManager`

**This is a suggestion, not a decision — the user decides.**

**Recommendation: the `LayerStack` is a concept *inside* a scene, NOT a
generalization of the `SceneManager`.**

| | `SceneManager` / `GameState` | `LayerStack` |
|---|---|---|
| Cardinality | exactly **one** state is active | **many** layers are active at once |
| Meaning | *which screen am I in* | *in what order this screen paints* |
| Lifetime | a scene transition swaps it | it lives for the whole scene |
| Count today | 15 `GameState` | 30 layers, one stack |

Generalising the `SceneManager` into layers would mean turning 15 mutually
exclusive states into 15 × N simultaneous layers — a combinatorial model with no
new capability, and it would blur the one question the `SceneManager` answers
well ("what is on screen right now?"). The `LayerStack` answers a different
question ("in what order?").

**Proposed boundary:** the `SceneManager` remains the only owner of *which
state is active*; the `LayerStack` is the only owner of *the order inside the
active state*. A scene that has a stack owns one; the other 14 keep their
current draw paths. If the user prefers the generalization, the blast radius is
the `SceneManager` and all 15 scenes — which is why this spec only recommends.

### The no-regression mechanism (B2, Q5)

**The proof is a pixel comparison, never an opinion.**

1. **Capture harness** — `tools/capture/layerstack_frames.py` renders the
   gameplay scene **deterministically**. The runtime uses the **global** RNG in
   31 screen-affecting places (`random.uniform`, `random.random`,
   `random.shuffle`) and seeds only `_asteroid_rng`, so the harness must:
   * call `random.seed(N)` with a fixed N **before** the scene is built,
   * **rebuild the scene** for every capture (a reused scene keeps its own
     RNG state and its entity positions),
   * advance by a fixed `dt` per tick, never by wall-clock time,
   * and draw a scripted input sequence.
   It writes the internal 320×480 frames to `tools/golden/layerstack/<name>.png`.
2. **Self-check first** — before the golden set is trusted, the harness
   captures the **same** frame twice and asserts the two PNGs are byte-identical.
   If they are not, the capture is not deterministic and the golden comparison
   is meaningless. **This check is a gate item (G13), not a fallback.**
3. **The golden set** — at least 5 frames covering the states that matter:
   a frame with enemies on screen, a frame with the boss, a frame with the
   mine in its `open3` state, a frame with the player firing, and a frame with
   the HUD populated. The "before" frames are **committed** on the Phase 2
   branch, before the refactor.
4. **The test** — `tests/test_layer_stack_renders_identical_frames.py`
   re-captures and compares **pixel by pixel** (RGB + alpha, exact equality).
   **0 differing pixels** is the pass condition; the test prints the number of
   differing pixels and the first differing coordinate when it fails.
5. **The structural guard** — `tests/test_layer_stack_order.py` asserts the
   layer ids and their `z` values against the table above. A reorder fails
   even if the pixels happen to match (e.g. two layers that draw the same
   pixels).

### The frozen build (I7)

`_sets_root()` (`manifest.py:34-44`) resolves **only** `Assets/sprites/bosses`,
in source *and* in the frozen `_MEIPASS`. `build.spec:44` bundles
`Assets/sprites` wholesale, so the new enemy TOMLs **do** ship inside the
`.exe` — but a Phase 2 reader would look for them under `bosses/`.

**Phase 2 change in `src/anim/manifest.py`:** the set-name resolution goes
through `sets.py::resolve_set`, which tries `Assets/sprites/bosses/<name>` and
then `Assets/sprites/enemies/<name>`, in both the source tree and `_MEIPASS`.
One probe, two roots — the same rule the audio and the tiling image already use
(`src/audio/music.py`, `src/ui/tiling_image.py`).

### Phase 2 acceptance criteria

| # | Criterion | How it is proven |
|---|---|---|
| B1 | The frame is composed from the `LayerStack`, not from the `self._draw_*` list | The frame loop contains one `stack.render(target, ctx)` call; the **16** `self._draw_*` calls of the loop are gone from the loop body (they live in the layer factory) |
| B2 | The draw order is **identical**, proven by frame comparison | the golden-frame test: **0 differing pixels** over the 5 captured frames + the structural order guard |
| B3 | The HUD and the background have a defined place | the HUD is `z = 23` (in the stack); the background is documented as the stack's backdrop, drawn before it |
| B4 | `mypy src\anim\` stays at 0 errors and the error delta in `src/ui/` / `src/entities/` does not grow | `python -m mypy src\anim\ src\render\` → 0 errors. The delta: `python -m mypy src\ui\ src\entities\ 2>&1 \| Select-String 'error:' \| Measure-Object` — record N before the change, N' after, require **N' ≤ N**. (`src\render\` must not import `src\ui\`: L6.) |
| B5 | The suite does not get worse | the baseline on the merged tree is **2 failed, 2 935 passed, 7 skipped**. The failure count must **drop by one** (the Windows newline failure is fixed in Phase 1) and must not grow afterwards; `test_paths_no_star_shapes` remains, documented as pre-existing. The count is a **delta against that baseline**, not an absolute number. |
| B6 | The enemies keep their exact animation timing | the enemy layer reads `fps` and `on_end` from the manifest; a test asserts 12.5 FPS, `loop` for `idle`/`thrust`, `reset` for `damage`/`death` |
| B7 | The enemies keep their exact pixels | the golden-frame test covers a frame with enemies; the enemy sprite path is `pivot = "fixed"` at the canvas centre, i.e. the same centred blit as today |

---

## Risks and mitigations

### FMEA

| # | Mode of failure | Prob. | Impact | Mitigation | How it is verified |
|---|---|---|---|---|---|
| F1 | The canvas is confused with `ENEMY_CONFIGS`' hitbox | ~~High~~ **now low** | High | the spec separates them and tabulates both; the manifest declares the measured canvas only | `tests/test_enemy_hitbox_is_not_the_canvas.py`: `hitbox ≤ canvas` per kind |
| F2 | GOLIATH's tolerances are inherited without measuring | **Low** | High | P5: the rule is a formula over the measured deviations, applied per clip; `side_tolerance` is not used at all | the per-clip tolerance table + the audit JSON |
| F3 | The registration is broken and the runtime compensates badly | **Low** | High | the enemy sets use `pivot = "fixed"`: the registration is **measured and reported**, never applied, so a bad registration cannot move a ship | the measured registration table + the golden frames |
| F4 | A 1-frame clip (`open`, `open1`, `open2`) breaks the animation advance | Medium | Medium | the clip advance clamps to `frames - 1`; `mode = "state"` clips have no advance at all | `tests/test_enemy_clip_semantics.py`: a 1-frame clip never advances past 0 |
| F5 | The `LayerStack` reorders the frame and the game looks different | Medium | **Critical** | B2: the order is a fixed table, asserted by a guard test, and proven by a pixel comparison | `tests/test_layer_stack_renders_identical_frames.py` (0 differing pixels) + `tests/test_layer_stack_order.py` |
| F6 | The `DrawContext` changes the scale and everything looks small or huge | Medium | **Critical** | one origin and one scale; the internal resolution stays 320×480; the window scaling stays in `Game._present()` | a test asserting `ctx.size == (320, 480)` and `ctx.scale == 1.0` |
| F7 | The asset migration rewrites PNG bytes | Low | **Critical** (R1) | the pipeline writes no PNG for the enemy sets (the two PNG-writing states are structurally unreachable) | `tests/test_enemy_art_is_untouched.py` (md5 before/after) + gate G4 |
| F8 | The auditor reports permanent FAILs over the enemies and blocks the pipeline | **High without this spec** | Medium | the two declarations (`distinct`, `cut_margin`) make the measured art auditable; every state is either declared or unreachable | gate G1: 0 FAIL **and** 0 WARN on all 8 sets |
| F9 | `_backup_pre_bloque_65` or the 2 loose PNGs sneak in as a set | Medium | Low | discovery is `manifest.toml` + the `_` prefix + the `frame_*.png` name (D1-D3) | `tests/test_enemy_set_discovery.py` |
| F10 | Phase 2 grows without limit and drags the whole game in | Medium | High | the scope table: 30 layers in, the background and the other 14 scenes out, the layer bodies unchanged | the file map + the layer table |
| F11 | **The `--fix` run rewrites `anchors.toml` with CRLF on Windows** | **High (measured)** | Medium | `write_anchors` writes with `newline="\n"`; the committed file is LF | `tests/test_sprite_pipeline_run.py::test_the_fix_run_changes_no_file` goes green; gate G3 |
| F12 | **The anchors are regenerated by a test against the real tree** (L7) | Medium | High | the freshness check compares **strings** and never writes; the `--fix` gate runs on a **copy** | `tests/test_enemy_anchors_are_fresh.py` + gates G2/G4/G11 (`git status` must be clean after the gate) |
| F13 | The mine's `death` art starts being drawn and the mine shrinks | Low | Medium | `mode = "archive"`: the runtime never selects it | a test asserting the mine's drawn surface is 64×64 in every state |
| F14 | The enemy animation is "cleaned up" into a 3-frame cycle | Medium | High | N2 forbids it explicitly; the pose order is documented as irregular | the golden frames (the idle animation is on screen) + the review of the manifest's `distinct` declaration |
| F15 | The `mypy` gate cannot be run (the tool is not installed) | **High (measured)** | Medium | the gate lists the install command; the spec does not install anything on its own | the gate reports "mypy missing" as a failed item, not as a pass |
| F16 | A second agent touches the same worktree or branch | Low | High | one worktree + one branch per agent; the base is `bloquec-75-sprite-migration`; the other worktrees are never touched | `git worktree list` before starting |
| F17 | **The auditor crashes on a featureless set** (C1) | **Certain without the fix** | High | `part_or_none()` + the `None` path in `audit.py` | gate G12 + `tests/test_audit_runs_on_a_featureless_set.py` |
| F18 | **The anchors of a featureless set claim a measured feature at (0,0)** (I9) | **Certain without the fix** | High | the sources default to `"missing"`; `"measured"` only when the detector found it | the freshness test's golden content + `load_anchors` accepting it as unresolved |
| F19 | The golden capture is not deterministic (31 global RNG uses) | **High without the fix** | **Critical** (B2) | seed the global RNG, rebuild the scene per capture, fixed `dt`, plus a self-check | gate G13 (two captures byte-identical) before the golden set is trusted |
| F20 | The new enemy manifests are not found in the frozen build | Medium | High | `sets.py::resolve_set` probes both roots, source and `_MEIPASS` | a test that resolves a set name under a fake `_MEIPASS`-like root |
| F21 | **The branch falls behind the base** (it was 18 commits behind when this revision was written) | **Handled** | High | the base was merged in (`ef86a95`, no conflicts) and the baseline was re-measured on the merged tree. The art measurements survived the move (the enemy art is byte-identical); the baseline numbers did not, and were replaced | §Base drift + §Baseline: the baseline is now the merged tree's |

---

## Verification

Every command, with the output it must produce. Run from the repository root
of the worktree.

```powershell
# --- the pipeline is healthy before anything starts -------------------------
python tools\sprite_pipeline\verify_contract.py goliath
#   -> CONTRACT OK
#   -> exit 0

python -m pytest tests\ --tb=no
#   -> 2 failed, 2935 passed, 7 skipped
#   -> the two failures are test_paths_no_star_shapes (pre-existing) and
#      test_the_fix_run_changes_no_file (the Windows newline bug, fixed in Phase 1)

# --- Phase 1, step 0: the zero-code experiment ------------------------------
python tools\sprite_pipeline\audit.py scout --root Assets\sprites\enemies
#   -> a report on the art as it is (the COLAPSADO findings are expected)

# --- the enemy sets (Phase 1) ----------------------------------------------
python tools\sprite_pipeline\run.py scout --root Assets\sprites\enemies
#   -> scout: 0/40 frames with findings (0 FAIL, 0 WARN), 0 findings
python tools\sprite_pipeline\run.py scout --root Assets\sprites\enemies --json
#   -> "failures": [], "warnings": []

python tools\sprite_pipeline\gate.py
#   -> PHASE 1 GATE OK
#   -> exit 0

git diff --stat Assets\sprites\enemies\
#   -> empty: not one PNG was rewritten (A4)

git status --short
#   -> only the new manifest.toml / anchors.toml files and the modified sources

# --- the type gate ----------------------------------------------------------
python -m mypy src\anim\
#   -> Success: no issues found in 6 source files
#   (Phase 2 adds: python -m mypy src\anim\ src\render\)

# --- the frame (Phase 2) ----------------------------------------------------
python tools\capture\layerstack_frames.py --out tools\golden\layerstack
python -m pytest tests\test_layer_stack_renders_identical_frames.py tests\test_layer_stack_order.py
#   -> 0 differing pixels over the golden frames
```

### Truth anchors

| Claim | Anchor |
|---|---|
| 8 sets, 304 frames, 34 animation dirs | `Get-ChildItem Assets\sprites\enemies -Directory \| Measure-Object` |
| The canvas is 32×32 | the **guard test** `tests/test_enemy_manifest_matches_assets.py` (the auditor emits no sizes today — I4; the Phase 1 change adds the size to the report) |
| The hitbox is not the canvas | `Select-String -Path src\entities\enemies\enemy.py -Pattern '_EnemyConfig\(' -Context 0,3` |
| The distinct-image counts | the md5 grouping; reproduced by `Get-FileHash -Algorithm MD5` per clip directory, asserted by `tests/test_enemy_clip_semantics.py` |
| The 7 auditor states | `Select-String -Path tools\sprite_pipeline\audit.py -Pattern 'STATES = \(' -Context 0,10` |
| The draw order | `Select-String -Path src\ui\gameplay_runtime.py -Pattern '^\s*self\._draw_'` + the 30-row table above (34 methods, 42 call sites, 16 in the loop) |
| The 15 `GameState` | `Select-String -Path src\core\scene_manager.py -Pattern '^\s+[A-Z_]+ = "'` |
| The suite baseline | `python -m pytest tests\ --tb=no` |
| The pipeline's health | `python tools\sprite_pipeline\verify_contract.py goliath` |
| The art is untouched | `git diff --stat Assets\sprites\enemies\` → empty |
| The manifest hash is over normalized text | `src/anim/manifest.py` (`_normalized_text`); R6 |
| The frozen lookup path | `src/anim/manifest.py::_sets_root`; `build.spec:44` |

---

## File map

### Phase 1

| File | Action | Why |
|---|---|---|
| `Assets/sprites/enemies/scout/manifest.toml` | create | the declaration of the set (Step 0 writes this one first) |
| `Assets/sprites/enemies/cruiser/manifest.toml` | create | " |
| `Assets/sprites/enemies/drone/manifest.toml` | create | " |
| `Assets/sprites/enemies/heavy/manifest.toml` | create | " |
| `Assets/sprites/enemies/kamikaze/manifest.toml` | create | " |
| `Assets/sprites/enemies/sniper/manifest.toml` | create | " |
| `Assets/sprites/enemies/turret/manifest.toml` | create | " |
| `Assets/sprites/enemies/mine_asteroid/manifest.toml` | create | " |
| `Assets/sprites/enemies/*/anchors.toml` (8) | create, **generated** | the measurement of each set |
| `src/anim/manifest.py` | modify | `cut_margin`, `distinct`, `clip.canvas`; parse `mode`/`on_end` without enforcing them; **`part_or_none()`** |
| `src/anim/measure.py` | modify | `effective_cut_margin(anim_set)` — the single source for the auditor and the repair (P6) |
| `tools/sprite_pipeline/audit.py` | modify | honour `distinct` and `cut_margin`; tolerate a set with no detected features (C1); default the feature sources to `"missing"` (I9); report the frame size and the registration; **write LF** (`newline="\n"`) |
| `tools/sprite_pipeline/repair.py` | modify | read the effective margin; never write a PNG for the enemy sets |
| `tools/sprite_pipeline/sets.py` | create | the discovery rules D1-D6 |
| `tools/sprite_pipeline/gate.py` | create | the Phase 1 gate (one command, all checks) |
| `tests/test_enemy_manifest_matches_assets.py` | create | the manifest ↔ assets guard |
| `tests/test_enemy_anchors_are_fresh.py` | create | the freshness guard (string comparison, never writes) |
| `tests/test_enemy_set_discovery.py` | create | D1-D3 + D6 |
| `tests/test_enemy_hitbox_is_not_the_canvas.py` | create | F1 |
| `tests/test_enemy_art_is_untouched.py` | create | A4 / R1 |
| `tests/test_enemy_clip_semantics.py` | create | `distinct`, `mode`, `on_end` vs the runtime |
| `tests/test_audit_runs_on_a_featureless_set.py` | create | the C1 regression |
| `tests/test_sprite_pipeline_run.py` | modify | the Windows newline failure goes green |
| `Assets/sprites/enemies/mine_asteroid/_backup_pre_bloque_65/**` | **untouched** | N6 — excluded by D2 |
| `Assets/sprites/enemies/mine_asteroid/_new_reference_*.png` | **untouched** | N6 — generator inputs, excluded by D3/D5 |
| `Assets/sprites/bosses/goliath/**` | **untouched** | N13 — GOLIATH is the control group |
| `src/ui/**`, `src/entities/**` | **untouched** | Phase 1 changes no runtime code |

### Phase 2

| File | Action | Why |
|---|---|---|
| `src/render/__init__.py` | create | the new package (stdlib + pygame only; must not import `src/ui/`) |
| `src/render/layer.py` | create | `Layer`, `LayerStack`, `DrawContext` |
| `src/ui/gameplay_layers.py` | create | the 30 layers, in the measured order |
| `src/ui/gameplay_runtime.py` | modify | the frame loop becomes `stack.render(target, ctx)`; the enemy sprite path goes through the pipeline |
| `src/entities/enemies/enemy.py` | modify | `fps` / `on_end` come from the manifest |
| `src/anim/parts.py` | modify | **the `fixed` pivot**: `_base()` ignores the measured offset when `part.pivot == "fixed"` |
| `src/anim/clip.py` | modify | `on_end = "reset"`; use the clip's canvas, not `self.set.canvas` |
| `src/anim/manifest.py` | modify | enforce `mode`/`on_end` (N14 ends here); resolve the enemies root, source and `_MEIPASS` (I7) |
| `tools/capture/layerstack_frames.py` | create | the deterministic capture harness (seeds the global RNG, rebuilds the scene) |
| `tools/golden/layerstack/*.png` | create | the "before" frames (committed) |
| `tests/test_layer_stack_order.py` | create | the structural order guard |
| `tests/test_layer_stack_renders_identical_frames.py` | create | the pixel comparison (B2) |
| `src/core/scene_manager.py` | **untouched** | the boundary is a recommendation (see §Phase 2) |
| `src/ui/scenes.py` | **untouched** | GOLIATH's path already works |

### Documentation to update with the implementation

| File | Action |
|---|---|
| `docs/superpowers/CONTEXT.md` | add the Phase 1/2 plan row when the plan exists |
| `.synapse` | update `short_term_memory` with the Phase 1 result |
| `docs/handoffs/` | a handoff when the phase lands (the repo is the only channel between agents) |

---

## Open questions (for the user, not for the implementer)

These are the decisions the spec deliberately leaves to the owner. Everything
else in this document is decided.

| # | Question | The spec's recommendation |
|---|---|---|
| Q1 | Is the `LayerStack` a concept inside a scene, or a generalization of the `SceneManager`? | **Inside a scene.** The `SceneManager` owns *which screen*; the stack owns *in what order*. |
| Q2 | Do all 8 enemy sets ship in Phase 1, or one set first (then the gate, then the other 7)? | **All 8**, because they are structurally identical (the mine is the only special case) and the gate already audits all of them. If the implementer wants a smaller first slice, `scout` alone is a valid Phase 1a. |
| Q3 | Is the mine's `death` art ever going to be played? | **Not in this BLOQUE.** It is declared `archive`; making it visible is an art decision, not a pipeline one. |
| Q4 | Should the golden frames be committed to the repo, or generated on demand? | **Committed.** Without them, B2 is not reproducible on another machine. |
| Q5 | Should the `LayerStack` be a general engine (as the BLOQUE 74 spec anticipated) or a gameplay-scene feature? | **Gameplay-scene feature first.** `src/render/` stays generic; the game-specific layers live in `src/ui/`. |

---

## Coverage

| Requirement | Status | Where |
|---|---|---|
| R1 no art regen | covered | N1, N6, F7, A4 |
| R2 GOLIATH constants | covered | N13, §Phase 1 "the new fields" |
| R3 master not the base | covered | header, N7 |
| R4 stdlib + pygame in `src/` | covered | §Phase 2 constraints, A6 |
| R5 mypy delta | covered | B4, G9 |
| R6 normalised hash | covered | §Truth anchors |
| R7 headless + deterministic | covered | A6, G13, §DrawContext |
| Q1 phases + gate | covered | §The gate |
| Q2 every decision has a reason | covered | §What the implementer must decide |
| Q3 verifiable claims | covered | §Truth anchors, §Revision log |
| Q4 the 7 states mapped | covered | §The 7 auditor states |
| Q5 visual-regression proof | covered | §The no-regression mechanism |
| Q6 explicit exclusions | covered | N1-N14 |
| Q7 actionable without context | covered | §Step 0, the decision tables, the file maps |
| A1-A6 | covered | §Phase 1 acceptance criteria |
| B1-B7 | covered | §Phase 2 acceptance criteria |
| P1 registration measured | covered | §Measured registration, N3 |
| P2 detection robustness | covered by exclusion | §The 7 auditor states |
| P3 interpolation default | covered | §The 7 auditor states, decision #6 |
| P4 side probe | covered by exclusion | §The 7 auditor states |
| P5 margin-justified tolerance | covered | §The tolerance rule |
| P6 shared threshold | covered | `effective_cut_margin` |
| P7 verifiable determinism | covered | G3, §Truth anchors |
| L1 no multi-line inline table | covered | the manifest example's header |
| L2 `(0,0)` is truthy | covered | §C1/I9: the sources default to `"missing"` |
| L3 `statistics.median` | covered | §The tolerance rule (the median of the heights) |
| L4 hash stability | covered | §Truth anchors |
| L5 narrow except | covered | D6 |
| L6 mypy gate scope | covered | §Phase 2 constraints (`src/render/` must not import `src/ui/`) |
| L7 no writes in tests | covered | G2, G4, G11, F12 |
| FMEA (≥6 modes) | covered | 20 modes |
| Anti-patterns | covered | N1-N14 + the decision tables |
