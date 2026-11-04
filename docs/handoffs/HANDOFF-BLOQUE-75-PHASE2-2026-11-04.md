# HANDOFF — BLOQUE 75 Phase 2: the layered rendering engine

**Date:** 2026-11-04
**Branch:** `bloquec-75-phase2-layers` (from `bloquec-67-goliath-port` @ `e619527`)
**Status:** Phase 2 implemented and reviewed; the Phase 2 gate is the door

---

## 1. What this phase is

Phase 1 put the eight enemy sets into a manifest-driven sprite pipeline.
**Phase 2 turns the gameplay frame into a layer stack** and moves the enemy
bodies onto that pipeline's compositor — without moving a single pixel.

The shape of the work:

| | Before | After |
|---|---|---|
| The frame | one `draw` per scene, in source order | **30 named layers** with an explicit `z` |
| The enemy body | the runtime loaded a PNG, scaled it by 1.05 and blitted it | the **compositor** draws it, from the manifest |
| The pivot | a measured registration correction was applied to every enemy | the manifest **declares** `pivot = "fixed"` (centred) |
| The scale | hardcoded `1.05` in the runtime | the manifest **declares** `scale = [1.05, 1.05]` |
| The proof | none | **six golden frames**, pixel-exact, plus spies on the new path |

Two checkpoints, and both of them are about the pixels:

- **2A** (`4c2e5c5`) — the frame is composed with the `LayerStack`. The six
  golden frames did not move.
- **2B** (`19a5fad`) — the enemies are drawn through the compositor. The six
  golden frames did not move.

**The engine is `src/render/`** (generic, no game imports):
`layer.py` holds `Layer`, `LayerStack` and `DrawContext`. `SceneManager` was
**not** touched. The runtime's draw helpers were extracted verbatim into
`src/ui/gameplay_layers.py` — the extraction had to be *verbatim*, or the
golden frames would have caught it.

## 2. The rule the phase ran on

> A guarantee the check cannot see is not a guarantee, it is a hypothesis.

Every task ended with the implementer **proving that the new check can
fail** — by mutating the code and pasting the red run. That rule is what
found the defects that had survived review:

| Defect | How it survived | What killed it |
|---|---|---|
| The `fixed` pivot was unpinned | both tests called the **private** `_base()` | mutating the public `draw_part` left the whole suite green (3072 total / 3064 pass / 0 fail) |
| The golden frames were blind to the change | they compare pixels, not paths | a spy test that counts the pipeline calls: with the pipeline off, **3 spy tests go red while the 6 goldens still pass** |
| The flash path dropped the body | the golden frames never hit the fallback | A/B against the base commit: 192 differing pixels, a flat `(178,178,178)` silhouette |
| The enemy draw cost was 20× higher | no test looks at the cost | `timeit`: 6.36 µs → 114.43 µs per enemy per frame |
| The Phase 1 gate went red | — | the gate's own range diff found GOLIATH's **generated** anchors |

## 3. What the reviews changed

**Nine per-task reviews, one final pre-landing review, and three fix rounds.
Every finding was fixed with a red run first.** The implementers' code
produced **one** defect (the Phase 1 gate's range pathspec); everything else
was in the briefs, the specs and the plan — i.e. mine.

The ones worth carrying forward:

**A generated file is validated by freshness, not by "did it change?".**
The Phase 1 gate's G5 diffs the whole `Assets/sprites/bosses/` directory over
a commit range. Phase 2 legitimately changed GOLIATH's **generated**
`anchors.toml` (its header stopped naming a test file that only protected
GOLIATH), and the gate went red — with no escape: not regenerating it makes
`verify_contract` report it stale. The fix (`42d252e`) narrows G5's range
pathspec to exclude the generated measurement and keeps the manifest and the
PNGs inside the diff. GOLIATH's anchors' freshness is already checked by G5's
second half.

**A pixel-equality proof proves the pixels, not the path.** Checkpoint 2B's
promise was "the enemies go through the compositor" and its proof was "the
goldens did not move" — but a runtime that never calls the compositor draws
the same pixels. The checkpoint needed a **second** proof: a spy that
asserts the pipeline was called, with the right clip and frame.

**A guard that compares content cannot see a rewrite.** The `goliath_copy`
fixture existed to keep the tests from touching the shipped set. When the CLI
started resolving the set through `sets.py`, the fixture stopped isolating,
and the existing guard — which compares **md5** — could not see it, because a
rewrite with identical content leaves the md5 unchanged. The new guard
compares content **and mtime**, and its red run shows the md5 identical on
both sides while the mtime differs.

**The rule about briefs is now written down.** A brief is written once, before
dispatch, and **frozen**: corrections go to a new versioned file
(`task-N-brief-r1.md`) and to the corrections log in the plan. The Task 5
brief was rewritten in place after the implementer had already committed, and
a reviewer auditing "deviation vs the brief" from the files on disk could no
longer see any deviation — the record was falsified. The corrections log in
`docs/superpowers/plans/2026-11-03-bloque-75-phase2-layers.md` carries every
defect found in every brief, in the implementation and in the reviews.

## 3b. The final pre-landing review

The phase's last review was run over the whole range by a reviewer that had
not seen any of the work. Its verdict was **MERGE WITH FIXES**:

- the merge into `bloquec-67-goliath-port` is **clean — zero conflicts** — and
  the merged tree is **byte-identical** to the branch tip;
- the suite is green in the merged tree, **both gates are `GATE OK` there**, and
  the game boots and plays headless (including `--boss goliath`);
- the PyInstaller bundle ships **all 18** `.toml` (9 manifests + 9 anchors) and
  a `_MEIPASS` simulation loads all eight enemy sets — the highest-risk item
  of the phase, because a frozen build that cannot find a manifest makes the
  enemy fall back silently;
- **four of the five** headline guarantees were reproduced red by a named
  mutation. The fifth — *"the hot path does no per-frame filesystem
  resolution"* — was pinned only in its narrow form, and the reviewer produced
  a type-clean mutation that puts the filesystem back on the enemy path and
  leaves mypy clean and the whole suite green. The guard was broadened.


## 4. How to verify

From the Phase 2 worktree:

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-75-phase2-layers
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\ --tb=no
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m mypy src\anim\ src\render\
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\gate.py --phase 1
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\gate.py --phase 2
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\verify_contract.py goliath
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\capture\layerstack_frames.py --check
```

**The numbers to expect**, measured in a clean clone of the merged tree:
**3106 collected / 3098 passed / 0 failed / 7 skipped / 1 xfailed**. The
seventh skip is `tests/test_status_truth_anchors.py::test_the_build_artifact_is_there_when_this_machine_has_it`
— *"this machine has no build artifact"* — because the clone has no `dist/`.
In a worktree that HAS a `dist/` (the developer's machine) the same tree
reports **3099 passed / 6 skipped**. Same total, same tree, one fewer skip:
the skip count depends on the machine, not on the code.

`mypy src\` as a whole is **not** clean — **181** pre-existing errors, spread
over **7 packages** (`systems/wave_patterns` 41, `ui/scenes.py` 28,
`audio/synth_16bit.py` 15, `ui/gameplay_runtime.py` 6, `systems/parallax.py`
6, `audio/sfx_16bit_recipes.py` 4, `entities/enemies` 4, `ui/gallery_scene.py`
4, `ui/scrolling_galaxy.py` 3, `core/game.py` 2, `audio/music.py` 2,
`movement/*` 8, `fx/bomb_burst.py` 1). The count did not grow across the
phase (181 before, 181 after) — the authoritative gates are `src/anim/` and
`src/render/`, which are clean.

**R1, measured over the whole phase** (`773cf08..HEAD`): **zero** PNGs
modified or deleted. The six PNGs that appear in the range are **new** — the
golden frames under `tools/golden/layerstack/`, which are proof fixtures, not
art. All **1768** PNGs under `Assets/` have an identical tree digest.

## 5. The CI item — this is the next agent's job

The Phase 2 gate exists, but **the CI does not run it**: `.github/workflows/test.yml`
runs only `python -m pytest --tb=short`, and only on `master` and
`bloquec-67-goliath-port`.

That was deliberate: the release line does not have the Phase 2 code yet, so
wiring the Phase 2 gate into the CI now would make it red for a reason that
has nothing to do with the code.

**When the Phase 2 branch is merged into the release line, the gate must be
added to the CI workflow on THAT branch.** A gate that only exists in the
developer's machine is not a gate.

**And the job's timeout has to be raised with it.** The Phase 2 gate's
worst-case budget is **1380 s** (three git calls at 60 s + four 300 s budgets:
the golden pytest, the harness `--check`, mypy and the layer-order pytest).
The CI job is `timeout-minutes: 15` = **900 s**. The Phase 1 gate was
deliberately sized to fit inside it (840 s); nobody re-did that arithmetic for
Phase 2. **Raise the job to at least 25 minutes** when the gate goes in, or
the CI will kill the job with no diagnosis.

Both gates have to run in CI: `--phase 2` runs the six P2 checks only, not
the Phase 1 G-series.

## 6. What is deliberately still open

- **The mine's `death` clip is never played.** It has 10 frames and a 32×32
  canvas inside a 64×64 set; the runtime ignores `animation_state` for the
  mine. The pipeline reproduces the runtime faithfully, but the art stays
  unused. It wants a decision, not a fix.
- **`EnemyKind.CARRIER` has no set** under `Assets/sprites/enemies/`; it takes
  the procedural path, before and after — but it now pays a wasted
  `load_player_for_kind("carrier")` call per frame.
- **`Assets/sprites/enemy_<kind>.png` no longer exist**, so that branch of
  `_get_enemy_sprite` is dead code.
- **The Phase 1 gate's `PHASE_1_BASE = "773cf08"`** is a hard constant. It
  still measures the right range today, but it is the thing to move when a
  third phase starts.

## 7. The process rules this phase produced

1. **A brief is written once, before dispatch, and frozen.** Corrections go to
   a new versioned file and to the corrections log.
2. **The implementation outranks the brief.** When they disagree, the
   implementation is kept — but only if the implementer *reports* the
   deviation instead of improvising. Six implementers did exactly that, and
   every one of them found a real defect.
3. **Every new check must be shown able to fail**, by mutating the code and
   pasting the red run.
4. **Never two implementers committing in the same worktree** (the git index
   race). Reviews may run in parallel; implementers may not.
5. **Measure the baseline yourself.** A baseline reported by another agent —
   or by a brief — can be wrong. Three times in this phase, the number in the
   brief and the number on the machine disagreed, and the machine won.
