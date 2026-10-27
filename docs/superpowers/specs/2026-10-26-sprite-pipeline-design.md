# BLOQUE 74 — Sprite Pipeline: declarative animation manifest, auditor, and layered compositor

**Date:** 2026-10-26
**Status:** READY FOR EXECUTION
**Author:** Lerius (idea) + Mavis (draft)
**Branch:** `bloquec-74-sprite-pipeline` (from tag `v1.7.2` = `f4600ae`)
**Base:** v1.4.0 line (BLOQUE 71) + GOLIATH + post-cinematic menu (BLOQUE 67)

---

## Overview

GOLIATH's animation works, but it works **by accident**. The runtime measures
sprite pixels at runtime to compensate for an AI generator that drew ten
different characters per animation. The compensation is scattered across
three functions in `src/ui/scenes.py`, the tuning constants live in
`src/ui/gameplay_runtime.py`, and the animation timing lives in
`src/entities/enemies/boss.py` — none of it declared anywhere.

This spec replaces that with a **declarative pipeline**:

1. **A manifest** (`manifest.toml`) that declares the clips, the layers, the
   anchors, and the detection rules for every animatable feature.
2. **An auditor** that measures every frame, classifies it into one of seven
   explicit states, and fails the build when a set is broken.
3. **A repair pass** that fixes what is fixable, at the layer where it belongs
   (build-time PNG edit vs. baked anchor data).
4. **A layered compositor** (`src/anim/`) that draws a boss from the manifest
   instead of from hand-written `if` branches.

The measurement moves **out of the runtime and into the build**. The runtime
reads a table instead of scanning pixels, the result is reviewable in a text
file, and the pieces that fall out are the seed of a purpose-built 2D engine.

The end goal the user named: *"un motor gráfico con pygame en 2D y que no
tengamos nada que envidiarle a los motores 2D de pixelart como Godot y
Unity."* This spec is step 1 of that. It does not attempt to be Godot.

---

## Problem

### Evidence: six failure modes, measured

All numbers below were measured against the 60 GOLIATH frames
(6 clips × 10 frames, canvas 96×80) with a read-only analysis pass.

| # | Failure mode | Metric | Status today |
|---|---|---|---|
| 1 | **Positional misregistration** — the sprite sits at a different offset inside its canvas in every frame | centroid offset spans **−16 … +20 px** across the 60 frames | fixed at runtime by centroid correction |
| 2 | **Canvas clipping** — the silhouette touches the canvas edge | min margin now 2 px (was 0) | fixed by re-padding + guard test |
| 3 | **Animation never ticked** — `Boss.update_animation()` had no caller anywhere in `src/` | 0 callers | fixed in BLOQUE 73.5 |
| 4 | **Feature absent** — the AI drew a different character, so the shield plate is not in the frame | **7 / 60 frames** have no measurable plate | **NOT fixed** |
| 5 | **Scale drift** — the boss changes size between frames | silhouette *area* spread: idle 10%, javelin 35%, purple_bullet 35%. Area is pose-dominated, so the pipeline measures bbox *height* instead (§2.4) | **NOT fixed** |
| 6 | **Baked art** — the eye beam is painted into the sprite | `laser/f05`: 411 beam-coloured px vs a ~45 px baseline | **NOT fixed** |

Modes 1–3 were solved. **Modes 4–6 are half the problem and they are art
problems, not code problems.** Every attempt to solve them inside the
renderer has produced a fallback constant — the shield ellipse falls back to
a hardcoded `(60.5, 40.5, 8.5, 10.5)` whenever the plate cannot be found.

### Evidence: the seven failures have three distinct causes

The user's initial hypothesis was that the frames were **clipped by the
canvas**. That is measurably false: in all seven failing frames there are
**14–42 px of empty canvas** where the plate should be. Nothing is clipped.

| Frames | Cause | Proof |
|---|---|---|
| `javelin/f03`, `purple_bullet/f06` | **The character is drawn turned around** — the plate is on the LEFT | plate centroid at col **27.9** and **31.1**, vs 48.9–53.2 in every healthy frame |
| `laser/f04`, `purple_bullet/f08` | **The baked beam poisons the detection** | the detector reports the plate at col 53.4 and **65.7** — it is measuring the beam |
| `javelin/f04`, `javelin/f07`, `laser/f07` | The plate sits at the edge of the valid range and is rejected | plate centroid at col 46.6, 47.5, 49.4 |

### The latent bug behind the second cause

The shield plate is located by a brass colour signature:

```python
if r > 185 and g > 145 and b < 130 and r > b + 70:
```

Two of the four baked eye-beam colours **satisfy that signature**:

```
(255, 220, 80) -> collides: True
(240, 200, 120) -> collides: True
```

`_measure_shield_lobe()` already carries a `drop_warm` guard for exactly this.
`get_sprite_arm_anchor()` in the same module **does not**, so it latches onto
the beam. This is a real bug in shipped code, not a hypothetical.

### Why this is a tooling problem, not a content problem

HYDRA, PHANTOM and NEMESIS have **no sprite sets at all** — they are drawn
procedurally with pygame primitives (`_draw_boss_simple`). GOLIATH is the
only boss with generated art. Whatever process produced GOLIATH will be run
three more times. Without a pipeline, the same three root causes (character
inconsistency, scale drift, baked effects) get rediscovered three more times.

---

## Goals

1. A **declared** contract for every animated set: clips, fps, loop mode,
   layers, anchors, detection rules.
2. An **auditor** that classifies each frame into one of seven explicit states
   and fails loudly, so a broken set can never enter the repo unnoticed.
3. **Deterministic, idempotent repairs** at the layer where each failure is
   actually fixable.
4. **Zero pixel scanning in the runtime** — anchors are baked at build time.
5. The migration of GOLIATH as the **proof** that the pipeline works on a real
   60-frame set.
6. A `src/anim/` package whose shape anticipates a 2D engine.

## Non-goals (explicit)

- **No visual editor.** A GUI to pose frames is a different product. The
  pipeline is headless, auditable and testable.
- **No 3D, no shaders, no IK/bones, no `.tscn`-style scene format.**
- **No AI calls.** The pipeline never regenerates art. Regeneration is a human
  decision, made from the auditor's report.
- **No change to the GOLIATH shield constants.** `DX=0, DY=3, RX=11, RY=17,
  R=11` and `RX_SCALE=0.78` are user-approved and are moved into the manifest
  verbatim, not retuned.
- **Not a Godot replacement.** The engine work is phase 2 and phase 3 (§9).

---

## Design

### 2.1 Two files per animated set

```
Assets/sprites/bosses/goliath/
  manifest.toml     <- hand-edited. The spec of the set.
  anchors.toml      <- GENERATED by the auditor. Never hand-edited.
  phase1_idle/frame_00.png … frame_09.png
  phase2_idle/…
  javelin/…
  laser/…
  purple_bullet/…
  death/…
```

`manifest.toml` is hand-edited because it encodes intent (which side the
shield is on, how a feature is recognised, what to do when it is missing).
`anchors.toml` is generated because it encodes measurement, and measurement
must be reproducible.

Both land inside `Assets/sprites/`, which `build.spec` already bundles
wholesale — **no `build.spec` change is required**, and both files ship
inside the `.exe`.

`tomllib` is stdlib in Python 3.11, so the format adds **zero dependencies**
(the project rule is stdlib-only, with a single documented numpy exception).

### 2.2 `manifest.toml`

```toml
# Assets/sprites/bosses/goliath/manifest.toml
# SPEC of the animation set. Hand-edited.
# Verified by: tools/sprite_pipeline/audit.py
# Design: docs/superpowers/specs/2026-10-26-sprite-pipeline-design.md

[meta]
name    = "GOLIATH"
version = 1
canvas  = [96, 80]      # every frame of every clip
anchor  = [48, 40]      # where the boss sits in the world
sided   = "right"       # the shield is ALWAYS on the right arm

[[clips]]
id     = "phase1_idle"
dir    = "phase1_idle"
frames = 10
fps    = 10
loop   = true

[[clips]]
id     = "phase2_idle"
dir    = "phase2_idle"
frames = 10
fps    = 10
loop   = true

[[clips]]
id     = "javelin"
dir    = "javelin"
frames = 10
fps    = 10
loop   = true

[[clips]]
id     = "laser"
dir    = "laser"
frames = 10
fps    = 10
loop   = true

[[clips]]
id     = "purple_bullet"
dir    = "purple_bullet"
frames = 10
fps    = 10
loop   = true

[[clips]]
id     = "death"
dir    = "death"
frames = 10
fps    = 10
loop   = false          # one-shot: holds on frame 9

# ---------------------------------------------------------------------
# Parts. Each part is something the compositor knows how to draw.
#
#   draw = "frames"      one PNG per frame of the current clip
#   draw = "ellipse"     procedural primitive (the invisible shield oval)
#   draw = "point"       an anchor only, draws nothing (the eye)
#   draw = "procedural"  runtime-generated effect; never baked into art
#
#   pivot = "centroid"   auto: alpha-weighted centroid of the silhouette
#   pivot = "detect"     auto: the detection rule declared below
#   pivot = "fixed"      an explicit (x, y)
#
#   on_missing = "interpolate" | "fallback" | "skip"
# ---------------------------------------------------------------------

[[parts]]
id    = "body"
draw  = "frames"
pivot = "centroid"
z     = 0

[[parts]]
id    = "shield_plate"
draw  = "ellipse"
pivot = "detect"
z     = 1
offset = [0, 3]         # GOLIATH_SHIELD_DX / GOLIATH_SHIELD_DY
scale  = [0.78, 1.0]    # GOLIATH_SHIELD_RX_SCALE
detect = { method = "shape", band = [28, 54], side = "right", min_col = 50, ranges = { rx = [6.5, 11.0], ry = [9.0, 13.0] }, exclude = [[255, 220, 80], [240, 200, 120]], probe = { method = "color", r_min = 185, g_min = 145, b_max = 130, r_minus_b_min = 70 } }
on_missing = "interpolate"

[[parts]]
id    = "eye"
draw  = "point"
pivot = "detect"
z     = 2
detect = { method = "color", head_band = [0, 30], col_range = [24, 70], r_min = 170, rg_min = 70 }
on_missing = "interpolate"

[[parts]]
id    = "fx_eye_beam"
draw  = "procedural"
z     = 3
```

#### Detection rule semantics

`detect.method = "shape"` — the plate shares its palette with the body
(`160,110,50`), so colour cannot identify it. The rule walks the declared
vertical `band`, takes **the last contiguous run of solid pixels in each
row**, requires that run to start at or after `min_col`, and collects the
pixels into an ellipse. A measurement is accepted only when
`ranges.rx` and `ranges.ry` hold; otherwise the frame is reported
`FUERA_DE_RANGO`.

`detect.method = "color"` — the eye is the only saturated red cluster in the
head band. The rule selects pixels with `r >= r_min` and `r - g >= rg_min`
inside `head_band` × `col_range` and takes their centroid.

`detect.exclude` — colours that **must not** count as the feature. Both
`[255,220,80]` and `[240,200,120]` satisfy the brass signature; excluding
them is what stops the detector from measuring the baked beam. It is applied
to **both** the measurement and the probe. A detection whose pixels overlap
an excluded colour is reported `FIRMA_AMBIGUA`.

`detect.side` — the expected side of the feature, relative to the canvas
centre. A detection on the other side is reported `LADO_EQUIVOCADO`.

`detect.probe` — a **cheap colour signature used only to answer "which side
is the feature on?"**, independent of how the feature is measured. It exists
because the shape rule cannot detect the side error: when the character is
drawn turned around, the shape rule still finds *a* solid run at the right of
the band (the arm), measures a plausible-looking ellipse, and never notices
that the plate moved to the left.

The probe finds the plate's brass pixels wherever they are and reports their
centroid column. Measured on today's assets, that column is **48.9–53.2** in
every healthy frame and **27.9 / 31.1** in `javelin/f03` and
`purple_bullet/f06` — the two frames where the character is turned around.
The side check is `probe column > canvas centre` (48), which is why the
healthy band straddles 48 rather than sitting above `min_col` — `min_col`
governs the shape rule, the probe has its own test.

### 2.3 `anchors.toml` — the baked measurement

```toml
# Assets/sprites/bosses/goliath/anchors.toml
# GENERATED by tools/sprite_pipeline/audit.py --write-anchors
# DO NOT HAND-EDIT: tests/test_anchors_are_fresh.py fails if this is stale.

[meta]
generated_by = "tools/sprite_pipeline/audit.py"
manifest_sha256 = "…"

[[anchors]]
clip  = "javelin"
frame = 3
body_dx = 20            # the 20 px jump the centroid cancels
body_dy = 4
eye    = [33, 21]
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "interpolated"   # "measured" | "interpolated" | "fallback"
```

`shield_source` makes the interpolation auditable: reading the file shows at
a glance which frames the art forgot the plate in and which the pipeline
reconstructed.

The `body_dx` / `body_dy` fields are the **same** correction the runtime
applies today in `src/ui/gameplay_runtime.py` — they move from a runtime
measurement to a declared number.

### 2.4 The auditor — `tools/sprite_pipeline/audit.py`

Read-only by default. Deterministic: same assets in, same verdict out. No AI,
no network, no writes unless `--write-anchors` is passed.

Seven states, each with a severity:

| State | Detected by | Severity | Meaning |
|---|---|---|---|
| `COLAPSADO` | duplicate md5 inside a clip | FAIL | the animation silently became a still (this happened twice: BLOQUE 64.B / 73.3) |
| `CORTADO` | silhouette touches the canvas edge | FAIL | the sprite is clipped |
| `LADO_EQUIVOCADO` | feature detected on the wrong side | FAIL | the character was drawn turned around |
| `FIRMA_AMBIGUA` | detection overlaps an excluded colour | FAIL | the detector is measuring something else |
| `AUSENTE` | feature not found in the frame | FAIL | the art is missing the feature |
| `FUERA_DE_RANGO` | rx/ry outside `detect.ranges` | WARN | the measurement is not credible |
| `ESCALADO` | silhouette bbox **height** ±`scale_tolerance` from the clip median | WARN | the boss changes size between frames |

Exit code is `1` if any FAIL is present, `0` otherwise. `--json` emits a
machine-readable report for CI.

**On the scale metric.** An earlier draft measured scale by silhouette *area*.
That is wrong: area is dominated by the pose, not the scale. A frame with an
outstretched arm has far more opaque pixels than one with the arm at rest,
while the body is exactly the same size — that alone accounts for the 35%
"spread" measured in `javelin` and `purple_bullet`. The metric is therefore
the **bounding-box height** of the silhouette, which is a linear dimension
and far less pose-sensitive.

The metric still has two known polluters, and both are handled explicitly:

- **Baked effects** stretch the bbox. `laser/f03`–`f06` contain the beam,
  which extends the silhouette and inflates the height. The auditor excludes
  pixels matching `detect.exclude` before measuring.
- **Intentional pose collapse.** `death` is the boss falling apart: its
  height legitimately drops from 75 px to 37 px. Each clip therefore
  declares its own tolerance, and `death` declares a loose one:

```toml
[[clips]]
id     = "death"
dir    = "death"
frames = 10
fps    = 10
loop   = false
scale_tolerance = 0.60   # the boss collapses — that is the animation
```

Every other clip uses the default `0.15`.

Expected output on today's assets, before repair:

```
[clip] javelin
  frame_03  FAIL  shield_plate: LADO_EQUIVOCADO (probe col 27.9, expected > 48)
  frame_04  WARN  shield_plate: FUERA_DE_RANGO (rx outside 6.5..11.0)
  frame_07  WARN  shield_plate: FUERA_DE_RANGO (rx outside 6.5..11.0)
[clip] laser
  frame_04  FAIL  shield_plate: FIRMA_AMBIGUA (overlaps exclude (255,220,80))
  frame_07  WARN  shield_plate: FUERA_DE_RANGO (rx outside 6.5..11.0)
[clip] purple_bullet
  frame_06  FAIL  shield_plate: LADO_EQUIVOCADO (probe col 31.1, expected > 48)
  frame_08  FAIL  shield_plate: FIRMA_AMBIGUA (overlaps exclude (240,200,120))
summary: 7/60 frames failing — 3 distinct states
exit 1
```

The two probe columns (27.9 and 31.1) are **measured** values, as are the
excluded colours. The `FUERA_DE_RANGO` entries show the range rather than an
exact `rx`, because the exact figure is produced by the auditor at run time;
the measured fact for those three frames is that the plate centroid lands at
col 46.6, 47.5 and 49.4 — inside the healthy band but outside what the shape
rule will accept as a credible ellipse.

### 2.5 The repair pass — `tools/sprite_pipeline/repair.py`

Each state is repaired **at the layer where it is actually fixable**:

| State | Repaired in | How |
|---|---|---|
| `CORTADO` | build (PNG) | re-pad: composite the sprite offset onto a fresh transparent canvas (generalises `tools/fix_sprite_padding_bloque73.py`) |
| `LADO_EQUIVOCADO` | build (PNG) | mirror the frame horizontally, then re-measure |
| `FIRMA_AMBIGUA` | config (manifest) | add the colliding colour to `detect.exclude`; **the art is not touched** |
| `AUSENTE` | anchors | interpolate the missing value from the neighbouring frames where it *was* measured (Catmull-Rom) |
| `FUERA_DE_RANGO` | anchors | same interpolation |
| `ESCALADO` | **not auto-repaired** | reported for a human to look at — see below |
| `COLAPSADO` | — | not repairable: the art is gone. Hard FAIL. |

**Why `ESCALADO` is not auto-repaired.** An earlier draft resampled the frame
to the clip's median height. That is destructive for pixel art: a
non-integer resample breaks the pixel grid, and the resampled frame no
longer matches the art style of its neighbours. Worse, the underlying metric
is not reliable enough to justify touching the art automatically — the height
metric is still polluted by baked effects and by intentional pose changes.
`ESCALADO` stays a WARN that flags a clip for a human to inspect.

**Correction to an earlier draft of this spec:** `FIRMA_AMBIGUA` was
originally listed as a build-time repair that erases the baked effect from the
silhouette. That is a deeper, separate operation (state `HORNEADO`) and it is
**not** what fixes GOLIATH's four affected frames. The baked beam looks good
and stays; only the detector's exclusion list changes.

Repairs are **idempotent** and run with `--dry-run` by default; `--fix` is
required to write.

### 2.6 The compositor — `src/anim/`

```
src/anim/manifest.py        load + validate manifest.toml and anchors.toml
src/anim/clip.py            Clip: elapsed time -> frame index (loop / one-shot)
src/anim/parts.py           draw implementations: frames / ellipse / point / procedural
src/anim/tween.py           PHASE 2 — easing and value interpolation
src/anim/state_machine.py   PHASE 2 — declarative clip transitions
src/anim/atlas.py           PHASE 2 — sprite atlas with pivots
```

Phase 1 ships the first three. The other three are the engine (§9).

```python
set_ = BossAnimSet.load("goliath")     # reads manifest.toml + anchors.toml
clip = set_.clip("javelin")
frame = clip.frame_at(elapsed)         # 0..9, honours loop / one-shot
clip.draw(target, frame, x, y)         # composes parts in z order
```

The runtime keeps its existing draw semantics — `Boss.animation_state`,
`Boss.animation_frame` and `ANIMATION_FRAME_DURATION` become reads from the
clip instead of hardcoded constants, so the migration is behaviour-preserving.

### 2.7 The pipeline command

```
python tools/sprite_pipeline/run.py goliath
  1. validate   manifest vs assets (clips, frames, canvas)
  2. audit      measure and classify                    -> exit 1 on any FAIL
  3. repair     (--fix only) re-pad, rescale, mirror
  4. re-audit   must reach 0 FAIL
  5. anchors    write anchors.toml
  6. report     write docs/reports/sprite_audit_goliath.md
```

---

## 3. Migration of GOLIATH

### 3.1 Art

**Exactly 2 PNGs change:**

| File | Change |
|---|---|
| `Assets/sprites/bosses/goliath/javelin/frame_03.png` | mirrored (character drawn turned around) |
| `Assets/sprites/bosses/goliath/purple_bullet/frame_06.png` | mirrored (character drawn turned around) |

The remaining five failures are resolved by the manifest's `exclude` list and
by anchor interpolation — **no PNG is touched**.

Mirroring is chosen over "let the oval follow the art" because the user
specified the shield as *always* on the right arm; mirroring keeps the
shield and its hitbox on the same side in all 60 frames. The trade-off is
that the javelin appears in the opposite hand in those two frames.

### 3.2 Code

```
NEW      src/anim/manifest.py
NEW      src/anim/clip.py
NEW      src/anim/parts.py
NEW      tools/sprite_pipeline/audit.py
NEW      tools/sprite_pipeline/repair.py
NEW      tools/sprite_pipeline/run.py
NEW      tests/test_manifest_matches_assets.py
NEW      tests/test_anchors_are_fresh.py
NEW      tests/test_features_detected_everywhere.py
NEW      tests/test_manifest_side_consistency.py
NEW      tests/test_sprite_pipeline_audit.py
NEW      Assets/sprites/bosses/goliath/manifest.toml
NEW      Assets/sprites/bosses/goliath/anchors.toml   (generated)
MODIFIED src/ui/scenes.py           the 3 anchor functions read the baked table
MODIFIED src/ui/gameplay_runtime.py _draw_boss goes through BossAnimSet
MODIFIED src/entities/enemies/boss.py  fps and loop come from the manifest
```

`get_sprite_centroid_offset()`, `get_sprite_eye_anchor()` and
`get_sprite_shield_ellipse()` keep their signatures — they become table
lookups instead of pixel scans, so the call sites do not change. The three
`_*_cache` dicts are deleted. The brass-signature bug in
`get_sprite_arm_anchor()` is fixed by the manifest's `exclude` list, which
the detector now honours.

**Estimated size:** ~1,850 LOC plus 2 PNGs. Two to three focused sessions.

### 3.3 Performance

The runtime currently pays **3.9 ms** the first time it sees a frame
(pygame `get_at` pixel scan of 96×80). GOLIATH's measured frame time is
median 2.28 ms / p99 3.20 ms against an 8.33 ms budget at 120 FPS.

After the migration the scan disappears entirely: the anchors are read from
TOML. **The per-frame cost does not rise — it falls**, and the scan cost
becomes zero rather than 3.9 ms.

---

## 4. Testing

New guards, all in `tests/`:

| Test | Asserts |
|---|---|
| `test_manifest_matches_assets.py` | every clip's directory exists, frame count matches, every frame's canvas equals `[meta].canvas` |
| `test_anchors_are_fresh.py` | regenerating `anchors.toml` produces no diff — the file is not stale |
| `test_features_detected_everywhere.py` | every `required` feature is measured or interpolated in **every** frame of every clip |
| `test_manifest_side_consistency.py` | every detected feature sits on the side declared in `detect.side` |

Existing guards that stay as they are:
`test_all_ten_frames_of_each_animation_are_distinct` (the BLOQUE 73.3
regression), `test_no_sprite_touches_the_canvas_edge`,
`test_goliath_anchor_coincidence.py`, `test_goliath_animation_advances.py`.

The auditor itself is exercised by `tests/test_sprite_pipeline_audit.py`,
which feeds it synthetic frames for each of the seven states and asserts the
classification — so the auditor's own logic is covered, not just its use.

---

## 5. Delivery order

The work is split into four phases so that each one is independently
verifiable and lands with the suite green. This is also the decomposition the
implementation plan will follow.

**Phase 1 — the manifest (no runtime change yet).**
`manifest.toml` for GOLIATH, `src/anim/manifest.py` (loader + validator),
`tests/test_manifest_matches_assets.py`,
`tests/test_manifest_side_consistency.py`. The side-consistency test fails
at this point — that is the point: it proves the auditor will catch the
flipped frames.

**Phase 2 — the auditor.**
`tools/sprite_pipeline/audit.py`, the measurement pass that produces
`anchors.toml`, `tests/test_sprite_pipeline_audit.py` (the seven states,
against synthetic frames), `tests/test_anchors_are_fresh.py`,
`tests/test_features_detected_everywhere.py`. Still no runtime change; the
auditor runs standalone and reports the 7 failures.

**Phase 3 — the repair.**
`tools/sprite_pipeline/repair.py`, `tools/sprite_pipeline/run.py`, the
manifest's `exclude` list, and the two mirrored PNGs. After this phase
`run.py goliath` exits 0 and `anchors.toml` is regenerated clean.

**Phase 4 — the compositor and the runtime migration.**
`src/anim/clip.py`, `src/anim/parts.py`, then `src/ui/scenes.py`,
`src/ui/gameplay_runtime.py` and `src/entities/enemies/boss.py` move to the
baked anchors. This is the only phase that changes what the player sees, and
it is behaviour-preserving by construction.

---

## 6. Success criteria

1. `python tools/sprite_pipeline/run.py goliath` → **exit 0, 0 FAIL**. For
   GOLIATH specifically the bar is **0 FAIL and 0 WARN**: the set must be
   fully clean, not merely passing. (Exit code is driven by FAIL only, so a
   future set can ship with warnings while GOLIATH cannot.)
2. `python -m pytest tests/` → green (2,772 + the 5 new tests).
3. `git diff v1.7.2 HEAD -- src/entities src/ui/scenes.py` → only the intended
   runtime change.
4. The built `.exe` starts; GOLIATH renders the same or better; the shield
   tracks the arm across all 60 frames.
5. Runtime per-frame cost does not increase (it decreases: no pixel scans).
6. `master` remains untouched (`a40fdaf`, clean, its 8 unpushed commits
   intact) and `bloquec-67-goliath-port` remains published at `v1.7.2`.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Mirroring two frames makes the javelin swap hands, visible to the player | accepted explicitly by the user; the alternative (an oval that moves sides) was rejected because it moves the hitbox |
| The manifest drifts from the assets | `test_manifest_matches_assets.py` + `test_anchors_are_fresh.py` |
| The auditor reproduces the bugs it is meant to catch | the auditor's classification is unit-tested against synthetic frames for all seven states |
| `tomllib` needs Python ≥ 3.11 | the project already requires 3.11 (`.venv` is 3.11.16); the manifest loader degrades to a clear error otherwise |
| Scope creep towards "a real engine" | phase 2/3 are explicitly out of this spec; the non-goals list is binding |

---

## 8. Out of scope for this spec

- Migrating HYDRA, PHANTOM or NEMESIS to sprites (phase 2, and it needs the
  pipeline to exist first).
- The `tween` / `state_machine` / `atlas` modules.
- Any change to `master` or to the published `v1.7.2` release.

---

## 9. File map

```
src/anim/manifest.py                          NEW
src/anim/clip.py                              NEW
src/anim/parts.py                             NEW
tools/sprite_pipeline/audit.py                NEW
tools/sprite_pipeline/repair.py               NEW
tools/sprite_pipeline/run.py                  NEW
tests/test_manifest_matches_assets.py         NEW
tests/test_anchors_are_fresh.py               NEW
tests/test_features_detected_everywhere.py    NEW
tests/test_manifest_side_consistency.py      NEW
tests/test_sprite_pipeline_audit.py           NEW
Assets/sprites/bosses/goliath/manifest.toml   NEW
Assets/sprites/bosses/goliath/anchors.toml    NEW (generated)
src/ui/scenes.py                              MODIFIED
src/ui/gameplay_runtime.py                    MODIFIED
src/entities/enemies/boss.py                  MODIFIED
Assets/sprites/bosses/goliath/javelin/frame_03.png        MODIFIED (mirrored)
Assets/sprites/bosses/goliath/purple_bullet/frame_06.png  MODIFIED (mirrored)
```

---

## 10. The path to a 2D engine

This spec is step 1 of the goal *"un motor gráfico con pygame en 2D y que no
tengamos nada que envidiarle a los motores 2D de pixelart como Godot y
Unity."*

| Engine piece | Where it lives | When |
|---|---|---|
| Declarative manifest | `manifest.toml` | phase 1 (this spec) |
| Baked pivots / anchors | `anchors.toml` | phase 1 (this spec) |
| Clips and timeline | `src/anim/clip.py` | phase 1 (this spec) |
| Layered composition | `src/anim/parts.py` | phase 1 (this spec) |
| State machine + transitions | `src/anim/state_machine.py` | phase 2 |
| Tweens / easing | `src/anim/tween.py` | phase 2 |
| Sprite atlas with pivots | `src/anim/atlas.py` | phase 2 |
| Scene hierarchy | `src/core/scene_manager.py` | exists |

**Phase 2 — the minimum engine.** `Boss.set_animation_state()`, whose logic is
currently inline in `src/entities/enemies/boss.py`, becomes a declarative
state machine. The idle bob — `sin(t) * amp` with a per-state amplitude —
becomes a tween with easing. `Clip` grows from a constant-fps frame counter
into a real timeline with keyframes. The 60 loose PNGs become an atlas.

**Phase 3 — the full engine.** Sprite sheets with per-sprite pivots, a
compositor with bones, and a declarative effect system.

**The principle.** The engine does not try to compete with Godot on
features. It competes on **control**: the pipeline is ours, the art is ours,
and every decision is auditable in a text file. Godot gives you an editor and
a generic runtime; we end up with a runtime that knows *exactly* what
GOLIATH is, with the whole pipeline under version control and under test.
