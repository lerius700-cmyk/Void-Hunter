# BLOQUE 75 Phase 1 — Enemy sprite sets into the pipeline: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The 8 enemy sprite sets under `Assets/sprites/enemies/` get a hand-written `manifest.toml` and a generated `anchors.toml`, the auditor measures them with **0 FAIL and 0 WARN**, and **not one PNG byte changes**.

**Architecture:** The manifest is the *declaration* (hand-edited) and `anchors.toml` is the *measurement* (generated). Phase 1 adds three optional manifest fields — `meta.cut_margin`, `clip.distinct`, `clip.canvas` — plus two that are parsed but not enforced yet (`clip.mode`, `clip.on_end`), and makes the auditor survive a set with no detected features. The runtime is **not** touched in this phase.

**Tech Stack:** Python 3.12, pygame 2.6 (headless), `tomllib` (stdlib), pytest. Stdlib + pygame only — no numpy, no new dependency.

**Spec:** `docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md`

---

## Global Constraints

These apply to **every** task. Copy them verbatim into the task brief when dispatching a subagent.

| # | Constraint | Value |
|---|---|---|
| R1 | **Not one PNG byte may change.** The enemy art is user-approved. The pipeline may only READ it. | `git diff --stat Assets/sprites/enemies/` must stay empty of `.png` |
| R2 | GOLIATH is the control group: its `manifest.toml`, its `anchors.toml` and its shield constants (`DX=0`, `DY=3`, `RX=11`, `RY=17`, `R=11`, `RX_SCALE=0.78`) must not change | `git diff --stat Assets/sprites/bosses/` must be empty |
| R4 | `src/` is stdlib + pygame only | no numpy, no new imports beyond the stdlib |
| R7 | Headless and deterministic: no wall clock, no network, no AI | `SDL_VIDEODRIVER=dummy` in every test that touches pygame |
| L1 | **No multi-line inline table** in any TOML the pipeline writes or reads | every `detect = {...}` stays on ONE line |
| L5 | Narrow `except`: never a bare `except:` | catch `(OSError, ValueError)` |
| L7 | **The tests never write into the repository.** A test that runs the pipeline does it on a `tmp_path` copy. | `git status --short` must be empty after the suite |
| C1 | The auditor must survive a set with **no** `shield_plate` and **no** `eye` part | `tests/test_audit_runs_on_a_featureless_set.py` |
| — | **Baseline:** `python -m pytest tests\ --tb=no` → **1 failed, 2 941 passed, 6 skipped**. The one failure is `test_paths_no_star_shapes` (pre-existing, documented in `CLAUDE.md`, out of scope). The CRLF failure is **already fixed upstream**: `f0a97f1` (merged in by `a70673c`) passes `newline="\n"` to `write_anchors` and pins it with two tests. | measured on `ddb135c` |
| — | Commit prefixes: `feat: BLOQUE 75`, `fix: BLOQUE 75`, `chore: BLOQUE 75`, `docs: BLOQUE 75`, `test: BLOQUE 75` | one commit per task |
| — | **Work ONLY in `F:\AI\MM\void-hunter\.worktrees\bloquec-75-migration-spec`.** The root repo and the other worktrees belong to other agents. | `git worktree list` before starting |

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/anim/manifest.py` | modify | the declaration loader: the three new fields, `part_or_none()` |
| `src/anim/measure.py` | modify | `is_cut_off(margins, min_margin)` + `effective_cut_margin(anim_set)` — the single source of the margin |
| `tools/sprite_pipeline/audit.py` | modify | the measurement: tolerate a featureless set, honour `distinct`, honour the set's margin, write LF |
| `tools/sprite_pipeline/repair.py` | modify | read the same effective margin the auditor uses |
| `tools/sprite_pipeline/sets.py` | create | set discovery: `resolve_set()`, `discover_sets()` |
| `tools/sprite_pipeline/gate.py` | create | the Phase 1 gate, one command |
| `Assets/sprites/enemies/<kind>/manifest.toml` × 8 | create | the declaration of each set |
| `Assets/sprites/enemies/<kind>/anchors.toml` × 8 | create, **generated** | the measurement of each set |
| `tests/test_audit_runs_on_a_featureless_set.py` | create | C1 + the false-provenance regression |
| `tests/test_anim_manifest_new_fields.py` | create | the new fields parse; GOLIATH is unchanged |
| `tests/test_effective_cut_margin.py` | create | one shared margin (P6) |
| `tests/test_distinct_rule.py` | create | `COLAPSADO` honours `distinct` |
| `tests/test_enemy_manifest_matches_assets.py` | create | the manifest ↔ assets guard (canvas included) |
| `tests/test_enemy_anchors_are_fresh.py` | create | the freshness guard (text comparison, never writes) |
| `tests/test_enemy_set_discovery.py` | create | the discovery rules D1-D6 |
| `tests/test_enemy_art_is_untouched.py` | create | A4 / R1 |
| `tests/test_enemy_hitbox_is_not_the_canvas.py` | create | F1 |
| `tests/test_enemy_clip_semantics.py` | create | `mode`/`on_end` vs the runtime |
| `tests/test_sprite_pipeline_gate.py` | create | the gate runs and passes |

---

## Task 1: The auditor survives a set with no detected features

The shipped auditor asks for `shield_plate` and `eye` **unconditionally**
(`audit.py:154`, `:175`, `:176`), and `manifest.py` raises `ManifestError` for an
unknown part — so it aborts before measuring a single frame of an enemy set.
It also labels an unresolved feature as `"measured"`, which `load_anchors`
(`anchors.py:100-111`) then reads as a real anchor at `(0, 0)`: the "eye laser
launched from the corner of the canvas" hazard the module's own docstring
warns about.

**Files:**
- Modify: `src/anim/manifest.py` (`AnimSet.part_or_none`)
- Modify: `tools/sprite_pipeline/audit.py` (3 lookups + the source defaults)
- Test: `tests/test_audit_runs_on_a_featureless_set.py`

**Interfaces:**
- Consumes: `load_set(name, root)` → `AnimSet`; `audit_set(anim_set)` → `(findings, measurements)`
- Produces: `AnimSet.part_or_none(part_id: str) -> Part | None` — the non-raising sibling of `part()`

- [ ] **Step 1: Write the failing test**

Create `tests/test_audit_runs_on_a_featureless_set.py`:

```python
"""BLOQUE 75: the auditor must survive a set with NO detected features.

The enemy sets declare a single `body` part: no shield plate, no eye.
The shipped auditor asked for both unconditionally, so it raised
ManifestError before it measured a single frame -- and it labelled an
unresolved feature as "measured", which `load_anchors` reads as a real
anchor at (0, 0).
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set
from sprite_pipeline.audit import audit_set


@pytest.fixture(scope="module")
def display():
    """pygame needs a video mode before convert_alpha() works."""
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _write_probe_set(tmp_path: Path) -> None:
    """A minimal set: one clip, one body-only part, two identical frames."""
    import pygame

    set_dir = tmp_path / "probe"
    (set_dir / "idle").mkdir(parents=True)
    for i in range(2):
        surf = pygame.Surface((8, 8), pygame.SRCALPHA, 32)
        surf.fill((255, 255, 255, 255))
        pygame.image.save(surf, str(set_dir / "idle" / f"frame_{i:02d}.png"))
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'version = 1\n'
        'canvas = [8, 8]\n'
        'anchor = [4, 4]\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'dir = "idle"\n'
        'frames = 2\n'
        'fps = 12.5\n'
        'loop = true\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n'
        'pivot = "fixed"\n'
        'z = 0\n',
        encoding="utf-8",
    )


def test_the_auditor_measures_a_set_without_features(tmp_path, display):
    _write_probe_set(tmp_path)
    anim_set = load_set("probe", root=tmp_path)
    findings, measurements = audit_set(anim_set)
    assert len(measurements) == 2


def test_an_unresolved_feature_is_not_labelled_measured(tmp_path, display):
    """A feature the set does not declare is UNRESOLVED, not measured.

    "measured" with a (0, 0) value is the eye-at-the-corner hazard: a
    consumer would launch the beam from the corner of the canvas.
    """
    _write_probe_set(tmp_path)
    anim_set = load_set("probe", root=tmp_path)
    _, measurements = audit_set(anim_set)
    for m in measurements:
        assert m.eye is None
        assert m.eye_source == "missing"
        assert m.shield is None
        assert m.shield_source == "missing"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_audit_runs_on_a_featureless_set.py -v`

Expected: **FAIL** with `ManifestError: unknown part 'shield_plate' in PROBE`

- [ ] **Step 3: Add `part_or_none`**

In `src/anim/manifest.py`, inside `class AnimSet`, right after `part()`:

```python
    def part_or_none(self, part_id: str) -> Part | None:
        """The part with this id, or None when the set declares no such part.

        The enemy sets declare a single `body` part: no shield plate, no
        eye. `part()` raises for them, which is right for a caller that
        REQUIRES a part and wrong for one that only wants to know whether
        the feature exists.
        """
        for part in self.parts:
            if part.id == part_id:
                return part
        return None
```

- [ ] **Step 4: Make the auditor tolerant**

In `tools/sprite_pipeline/audit.py`:

1. Line 154 (`_clip_probe_columns`) — replace

   ```python
       rule = anim_set.part("shield_plate").detect
   ```

   with

   ```python
       shield_part = anim_set.part_or_none("shield_plate")
       rule = shield_part.detect if shield_part is not None else None
   ```

2. Lines 175-176 (`audit_set`) — replace

   ```python
       shield_part = anim_set.part("shield_plate")
       eye_part = anim_set.part("eye")
   ```

   with

   ```python
       shield_part = anim_set.part_or_none("shield_plate")
       eye_part = anim_set.part_or_none("eye")
       rule = shield_part.detect if shield_part is not None else None
   ```

   (`rule` MUST be bound here: the silhouette measurement below reads it. The
   old `rule = shield_part.detect` line is deleted in step 3.)

3. Line 207 — delete the line `rule = shield_part.detect` (the rule is now
   resolved once, above, and it may be `None`).

4. The eye block (lines 256-267) — replace

   ```python
           eye = None
           eye_source = "measured"
           if eye_part.detect is not None:
               found = color_centroid(surf, eye_part.detect)
               if found is not None:
                   eye = (int(round(found[0])), int(round(found[1])))
               else:
                   # The boss is a wreck by the end of the death clip: the
                   # last frame has no eye left to find. The part's
                   # on_missing policy (interpolate) resolves it.
                   eye_source = "missing"
   ```

   with

   ```python
           eye = None
           eye_source = "missing"
           if eye_part is not None and eye_part.detect is not None:
               found = color_centroid(surf, eye_part.detect)
               if found is not None:
                   eye = (int(round(found[0])), int(round(found[1])))
                   eye_source = "measured"
               # else: the feature is absent from the art. The source
               # stays "missing" -- UNRESOLVED, never "measured" at (0, 0).
   ```

5. The shield block (lines 269-273) — replace

   ```python
           shield = None
           shield_source = "measured"
           if rule is not None:
   ```

   with

   ```python
           shield = None
           shield_source = "missing"
           if rule is not None:
   ```

6. The `else` branch of the ellipse measurement (line 328-329) — replace

   ```python
               else:
                   shield = ellipse
   ```

   with

   ```python
               else:
                   shield = ellipse
                   shield_source = "measured"
   ```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_audit_runs_on_a_featureless_set.py -v`

Expected: **2 passed**

- [ ] **Step 6: Prove GOLIATH is unharmed**

Run: `python tools\sprite_pipeline\verify_contract.py goliath`

Expected: `CONTRACT OK`, exit 0 — and `git diff --stat Assets/sprites/bosses/` empty.

- [ ] **Step 7: Commit**

```powershell
git add src/anim/manifest.py tools/sprite_pipeline/audit.py tests/test_audit_runs_on_a_featureless_set.py
git commit -m "fix: BLOQUE 75 - el auditor sobrevive a un set sin features detectadas"
```

---

## Task 2: The LF fix (already shipped upstream — verify, do not rewrite)

**This task was already implemented on the release line** and merged into this
branch by `a70673c`:

* `f0a97f1 fix: BLOQUE 75 - el generador de anchors escribe LF, como declara el repositorio`
  — `write_anchors` now passes `newline="\n"` to `path.write_text`, and TWO
  tests pin it (`test_the_generated_anchors_use_lf_line_endings` and
  `test_the_repository_declares_lf_for_the_toml`).

**Do NOT rewrite `write_anchors`.** The upstream version carries a longer
comment that explains the same thing. This task is a VERIFICATION, and the
only thing it may add is a missing test.

**Files:**
- Modify: `tests/test_sprite_pipeline_run.py` — only if a test is missing
- Test: `tests/test_sprite_pipeline_run.py`

**Interfaces:**
- Consumes: `write_anchors(anim_set, measurements, path)`
- Produces: nothing new; the guarantee already exists

- [ ] **Step 1: Run the LF tests**

Run: `python -m pytest tests/test_sprite_pipeline_run.py -v`

Expected: **all passed**, including `test_the_fix_run_changes_no_file`,
`test_the_generated_anchors_use_lf_line_endings` and
`test_the_repository_declares_lf_for_the_toml`.

- [ ] **Step 2: Confirm the writer really is LF-only**

Run:

```powershell
Select-String -Path tools\sprite_pipeline\audit.py -Pattern 'newline=' -Context 0,1
```

Expected: `write_anchors` passes `newline="\n"`.

- [ ] **Step 3: Confirm the byte-level guarantee is tested**

If `tests/test_sprite_pipeline_run.py` does NOT contain
`test_the_generated_anchors_use_lf_line_endings`, add it:

```python
def test_the_generated_anchors_use_lf_line_endings(goliath_copy: Path):
    """The committed anchors.toml is LF; a CRLF write changes its bytes.

    The text comparison of the freshness test passes either way (universal
    newlines), so only a byte-level check catches this.
    """
    from src.anim.manifest import load_set
    from sprite_pipeline.audit import audit_set, write_anchors

    anim_set = load_set("goliath")
    _, measurements = audit_set(anim_set)
    out = goliath_copy / "anchors_lf_probe.toml"
    write_anchors(anim_set, measurements, out)
    raw = out.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")
```

- [ ] **Step 4: Commit (only if a test was added)**

```powershell
git add tests/test_sprite_pipeline_run.py
git commit -m "test: BLOQUE 75 - los anchors se escriben en LF (byte a byte)"
```

If the test already existed, **do not commit anything** for this task: write
`Task 2: already satisfied upstream (f0a97f1)` in the ledger and move on.

---
## Task 3: The manifest grows the Phase 1 fields

Three fields are **used** in Phase 1 (`meta.cut_margin`, `clip.distinct`,
`clip.canvas`) and two are **parsed but not enforced** (`clip.mode`,
`clip.on_end`) — enforcing them now would reject GOLIATH's own manifest, which
declares neither.

**Files:**
- Modify: `src/anim/manifest.py` (`Clip`, `AnimSet`, `load_set`)
- Test: `tests/test_anim_manifest_new_fields.py`

**Interfaces:**
- Produces: `Clip.distinct: int | None`, `Clip.canvas: tuple[int, int] | None`, `Clip.mode: str`, `Clip.on_end: str`, `AnimSet.cut_margin: int | None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_anim_manifest_new_fields.py`:

```python
"""BLOQUE 75: the manifest grows the fields the enemy sets need.

`distinct`, `cut_margin` and `clip.canvas` are USED in Phase 1. `mode` and
`on_end` are PARSED but not enforced yet: enforcing them now would reject
GOLIATH's own manifest, which declares neither.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import ManifestError, load_set


def _write(tmp_path: Path, body: str) -> None:
    set_dir = tmp_path / "probe"
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / "manifest.toml").write_text(body, encoding="utf-8")


def test_the_new_fields_are_parsed(tmp_path):
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        'anchor = [16, 16]\n'
        'cut_margin = 0\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 10\n'
        'fps = 12.5\n'
        'distinct = 3\n'
        'canvas = [16, 16]\n'
        'mode = "variants"\n'
        'on_end = "reset"\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    anim_set = load_set("probe", root=tmp_path)
    clip = anim_set.clip("idle")
    assert anim_set.cut_margin == 0
    assert clip.distinct == 3
    assert clip.canvas == (16, 16)
    assert clip.mode == "variants"
    assert clip.on_end == "reset"


def test_on_end_is_derived_from_loop_when_it_is_not_declared(tmp_path):
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        '\n'
        '[[clips]]\n'
        'id = "loops"\n'
        'frames = 2\n'
        'loop = true\n'
        '\n'
        '[[clips]]\n'
        'id = "holds"\n'
        'frames = 2\n'
        'loop = false\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    anim_set = load_set("probe", root=tmp_path)
    assert anim_set.clip("loops").on_end == "loop"
    assert anim_set.clip("holds").on_end == "hold"


def test_goliath_is_unchanged():
    """The control group: no new field is declared, so nothing changes."""
    anim_set = load_set("goliath")
    assert anim_set.cut_margin is None
    for clip in anim_set.clips.values():
        assert clip.distinct is None
        assert clip.canvas is None
        assert clip.mode == "sequence"
    assert anim_set.clip("phase1_idle").on_end == "loop"
    assert anim_set.clip("death").on_end == "hold"


def test_a_malformed_cut_margin_raises_manifest_error(tmp_path):
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        'cut_margin = "nope"\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)


def test_a_bool_is_not_an_integer(tmp_path):
    """`True` would become 1, and for `distinct` that inverts the intent."""
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        'cut_margin = true\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)


def test_a_negative_margin_is_rejected(tmp_path):
    """A negative margin would make the cut-off test never fire."""
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        'cut_margin = -3\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)


def test_a_malformed_distinct_raises_manifest_error(tmp_path):
    """The loader fails LOUDLY, with the manifest's own error type."""
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        'distinct = "nope"\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_anim_manifest_new_fields.py -v`

Expected: **FAIL** — `AttributeError: 'Clip' object has no attribute 'distinct'`

- [ ] **Step 3: Extend the dataclasses**

In `src/anim/manifest.py`, append to `class Clip` (after `side_tolerance`):

```python
    # BLOQUE 75: the fields the enemy sets need. All of them are optional
    # and default to the behaviour that shipped with BLOQUE 74.
    #
    # `distinct` is how many DISTINCT source images the clip is built from:
    # the enemy art cycles 3-4 poses to fill ten slots, and without this
    # the auditor reads every one of them as a collapsed animation.
    # `canvas` overrides the set's canvas for ONE clip (the mine's death
    # art is 32x32 inside a 64x64 set).
    # `mode` and `on_end` are PARSED but NOT ENFORCED in Phase 1: GOLIATH's
    # manifest declares neither, and enforcing the rules now would reject
    # it. Phase 2 consumes them.
    distinct: int | None = None
    canvas: tuple[int, int] | None = None
    mode: str = "sequence"
    # The LOADER derives this from `loop`; the default is for direct builds.
    on_end: str = "loop"
```

Append to `class AnimSet` (after `parts`):

```python
    # BLOQUE 75: the margin this set's silhouettes must keep from the
    # canvas edge. None means "the pipeline default" (CORTADO_MARGIN in
    # src/anim/measure.py), which is where the number lives: the manifest
    # must not import measure.py (measure.py imports this module).
    cut_margin: int | None = None
```

- [ ] **Step 4: Parse them in `load_set`**

In `src/anim/manifest.py`, replace the `clips[clip_id] = Clip(...)` block with:

```python
        loop = bool(entry.get("loop", True))
        on_end = entry.get("on_end")
        if on_end is None:
            # Derived from `loop` so GOLIATH keeps its shipped behaviour:
            # a looping clip loops, a one-shot holds on its last frame.
            on_end = "loop" if loop else "hold"
        distinct_raw = entry.get("distinct")
        canvas_raw = entry.get("canvas")
        clips[clip_id] = Clip(
            id=clip_id,
            dir=str(entry.get("dir", clip_id)),
            frames=int(entry.get("frames", 0)),
            fps=float(entry.get("fps", 10)),
            loop=loop,
            scale_tolerance=float(entry.get("scale_tolerance", 0.15)),
            side_tolerance=float(entry.get("side_tolerance", 14.0)),
            distinct=_as_optional_int(distinct_raw, f"{clip_id}.distinct"),
            canvas=(
                None
                if canvas_raw is None
                else _as_int_pair(canvas_raw, f"{clip_id}.canvas")
            ),
            mode=str(entry.get("mode", "sequence")),
            on_end=str(on_end),
        )
```

And in the `return AnimSet(...)` call, add:

```python
        cut_margin=(
            None
            if (meta.get("cut_margin") is None)
            else int(meta["cut_margin"])
        ),
```

(an `int("nope")` raises `ValueError`, which `ManifestError` subclasses — but
to satisfy the test's `pytest.raises(ManifestError)` the conversion must raise
`ManifestError`, so wrap it:)

```python
        cut_margin=_as_optional_int(meta.get("cut_margin"), "meta.cut_margin"),
```

and add this helper next to `_as_int_pair`:

```python
def _as_optional_int(value: Any, name: str) -> int | None:
    """Read an optional integer, rejecting anything that is not one.

    A bool is NOT an integer here: `True` would become 1, and for
    `distinct` that silently inverts the author's intent (the clip
    declares how many source images it cycles).
    A negative value is rejected too: a negative margin makes the
    cut-off test never fire.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ManifestError(f"{name} must be an integer, got {value!r}")
    if value < 0:
        raise ManifestError(f"{name} must not be negative, got {value!r}")
    return value
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_anim_manifest_new_fields.py -v`

Expected: **7 passed** (4 parsing + 3 rejection cases)

- [ ] **Step 6: Run the whole manifest + pipeline test set**

Run: `python -m pytest tests/test_manifest_matches_assets.py tests/test_anim_manifest_degrades.py tests/test_anchors_are_fresh.py -v`

Expected: **all passed** (the GOLIATH control group is untouched)

- [ ] **Step 7: Commit**

```powershell
git add src/anim/manifest.py tests/test_anim_manifest_new_fields.py
git commit -m "feat: BLOQUE 75 - el manifest declara distinct, cut_margin, canvas, mode y on_end"
```

---

## Task 4: One shared cut margin, and `COLAPSADO` that honours `distinct`

**Files:**
- Modify: `src/anim/measure.py`
- Modify: `tools/sprite_pipeline/audit.py`
- Modify: `tools/sprite_pipeline/repair.py`
- Test: `tests/test_effective_cut_margin.py`
- Test: `tests/test_distinct_rule.py`

**Interfaces:**
- Consumes: `AnimSet.cut_margin`, `Clip.distinct`
- Produces: `measure.effective_cut_margin(anim_set) -> int`, `measure.is_cut_off(margins, min_margin) -> bool`

- [ ] **Step 1: Write the failing test — the margin**

Create `tests/test_effective_cut_margin.py`:

```python
"""BLOQUE 75: one threshold, read by the auditor AND the repair.

The enemy art is authored tight to its canvas: 29 of the 33 live clips
touch the edge by design. GOLIATH's 2 px margin exists because the AI
generator drew the boss's limbs past the canvas. The margin is a property
of the ART, so each set declares its own -- and the auditor and the repair
must read the SAME value, or a frame the auditor flags could be one the
repair cannot reach.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set
from src.anim.measure import CORTADO_MARGIN, effective_cut_margin, is_cut_off
from sprite_pipeline.audit import audit_set


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def test_is_cut_off_takes_the_margin():
    assert is_cut_off((0, 3, 3, 3), 2) is True
    assert is_cut_off((0, 3, 3, 3), 0) is False
    assert is_cut_off((2, 2, 2, 2), 2) is False


def test_goliath_uses_the_pipeline_default():
    anim_set = load_set("goliath")
    assert effective_cut_margin(anim_set) == CORTADO_MARGIN


def test_a_set_declares_its_own_margin(tmp_path):
    set_dir = tmp_path / "probe"
    set_dir.mkdir(parents=True)
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [8, 8]\n'
        'anchor = [4, 4]\n'
        'cut_margin = 0\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 1\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
        encoding="utf-8",
    )
    anim_set = load_set("probe", root=tmp_path)
    assert effective_cut_margin(anim_set) == 0


def test_a_tight_silhouette_is_cut_off_only_when_the_margin_says_so(
    tmp_path, display
):
    """The same frame: CORTADO at margin 2, clean at margin 0."""
    import pygame

    set_dir = tmp_path / "probe"
    (set_dir / "idle").mkdir(parents=True)
    surf = pygame.Surface((8, 8), pygame.SRCALPHA, 32)
    surf.fill((255, 255, 255, 255))
    pygame.image.save(surf, str(set_dir / "idle" / "frame_00.png"))

    def _manifest(margin: int) -> str:
        return (
            '[meta]\n'
            'name = "PROBE"\n'
            'canvas = [8, 8]\n'
            'anchor = [4, 4]\n'
            f'cut_margin = {margin}\n'
            '\n'
            '[[clips]]\n'
            'id = "idle"\n'
            'frames = 1\n'
            '\n'
            '[[parts]]\n'
            'id = "body"\n'
            'draw = "frames"\n'
        )

    (set_dir / "manifest.toml").write_text(_manifest(2), encoding="utf-8")
    findings, _ = audit_set(load_set("probe", root=tmp_path))
    assert any(f.state == "CORTADO" for f in findings)

    (set_dir / "manifest.toml").write_text(_manifest(0), encoding="utf-8")
    findings, _ = audit_set(load_set("probe", root=tmp_path))
    assert not any(f.state == "CORTADO" for f in findings)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_effective_cut_margin.py -v`

Expected: **FAIL** — `TypeError: is_cut_off() takes 1 positional argument but 2 were given`

- [ ] **Step 3: Make the margin a parameter**

In `src/anim/measure.py`, replace `is_cut_off` with:

```python
def is_cut_off(
    margins: tuple[int, int, int, int], min_margin: int = CORTADO_MARGIN
) -> bool:
    """True when a silhouette comes closer than `min_margin` to an edge.

    The threshold is a PARAMETER, not a constant: the enemy art is
    authored tight to its canvas, and each set declares the margin it is
    held to. The default is the one GOLIATH uses. The auditor and the
    repair MUST pass the same value -- they both read it from
    `effective_cut_margin` -- or a frame the auditor flags could be one
    the repair cannot reach.
    """
    return min(margins) < min_margin
```

and add, right after it:

```python
def effective_cut_margin(anim_set: AnimSet) -> int:
    """The margin this set's silhouettes must keep from the canvas edge.

    A set that declares `meta.cut_margin` uses it; every other set uses
    the pipeline default (CORTADO_MARGIN). ONE source for the auditor and
    the repair: they can never disagree about what "cut off" means.
    """
    if anim_set.cut_margin is None:
        return CORTADO_MARGIN
    return anim_set.cut_margin
```

and extend the import at the top of the file:

```python
from src.anim.manifest import AnimSet, DetectRule, WarmRule
```

- [ ] **Step 4: Use it in the auditor and the repair**

In `tools/sprite_pipeline/audit.py`:

1. Add `effective_cut_margin` to the `from src.anim.measure import (...)` block.
2. Inside `audit_set`, right before the `for clip in anim_set.clips.values():`
   loop, add:

   ```python
       min_margin = effective_cut_margin(anim_set)
   ```

3. Replace the CORTADO test:

   ```python
               if margins is not None and is_cut_off(margins):
   ```

   with:

   ```python
               if margins is not None and is_cut_off(margins, min_margin):
   ```

In `tools/sprite_pipeline/repair.py`:

1. Extend the import:

   ```python
   from src.anim.measure import (
       CORTADO_MARGIN,
       effective_cut_margin,
       silhouette_margins,
   )
   ```

2. In `repair_set`, right after `actions: list[str] = []`, add:

   ```python
       min_margin = effective_cut_margin(anim_set)
   ```

3. Replace the re-pad call:

   ```python
               if repad_frame(path):
   ```

   with:

   ```python
               if repad_frame(path, min_margin=min_margin):
   ```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_effective_cut_margin.py -v`

Expected: **4 passed**

- [ ] **Step 6: Write the failing test — the `distinct` rule**

Create `tests/test_distinct_rule.py`:

```python
"""BLOQUE 75: COLAPSADO against a DECLARED number of distinct images.

The enemy art cycles 1-4 poses to fill ten slots at 12.5 FPS. The shipped
rule ("any duplicate md5 inside a clip") reads all of it as a collapsed
animation -- 29 of the 33 live clips. With `distinct` declared, the finding
is raised only when the art disagrees with the DECLARATION.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set
from sprite_pipeline.audit import audit_set


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _write_set(tmp_path: Path, distinct: int | None, frames: int) -> None:
    """`frames` frames, of which 3 are distinct images."""
    import pygame

    set_dir = tmp_path / "probe"
    (set_dir / "idle").mkdir(parents=True, exist_ok=True)
    colors = ((255, 255, 255, 255), (255, 0, 0, 255), (0, 0, 255, 255))
    for i in range(frames):
        surf = pygame.Surface((8, 8), pygame.SRCALPHA, 32)
        surf.fill(colors[i % 3])
        pygame.image.save(surf, str(set_dir / "idle" / f"frame_{i:02d}.png"))
    declared = "" if distinct is None else f"distinct = {distinct}\n"
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [8, 8]\n'
        'anchor = [4, 4]\n'
        'cut_margin = 0\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = %d\n' % frames
        + declared
        + '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
        encoding="utf-8",
    )


def _collapsed(tmp_path: Path) -> bool:
    findings, _ = audit_set(load_set("probe", root=tmp_path))
    return any(f.state == "COLAPSADO" for f in findings)


def test_a_matching_declaration_is_clean(tmp_path, display):
    _write_set(tmp_path, distinct=3, frames=9)
    assert _collapsed(tmp_path) is False


def test_a_stale_declaration_is_a_finding(tmp_path, display):
    """The manifest says 2, the art has 3: the manifest is stale."""
    _write_set(tmp_path, distinct=2, frames=9)
    assert _collapsed(tmp_path) is True


def test_without_a_declaration_any_duplicate_is_a_finding(tmp_path, display):
    """The shipped rule, unchanged: GOLIATH declares no `distinct`."""
    _write_set(tmp_path, distinct=None, frames=9)
    assert _collapsed(tmp_path) is True
```

- [ ] **Step 7: Run the test to verify it fails**

Run: `python -m pytest tests/test_distinct_rule.py -v`

Expected: **FAIL** — `test_a_matching_declaration_is_clean` fails (the clip
still reports COLAPSADO)

- [ ] **Step 8: Make the rule honour `distinct`**

In `tools/sprite_pipeline/audit.py`, replace the COLAPSADO block (lines 183-197)
with:

```python
        # --- COLAPSADO: duplicate frames inside a clip -----------------
        digests: dict[str, list[int]] = {}
        for i in range(clip.frames):
            path = _frame_path(anim_set, clip, i)
            digests.setdefault(_md5(path), []).append(i)
        if clip.distinct is None:
            # No declaration: ANY duplicate is a collapsed animation. This
            # is the shipped GOLIATH rule, unchanged.
            for digest, indices in digests.items():
                if len(indices) > 1:
                    findings.append(
                        Finding(
                            clip.id,
                            indices[0],
                            "COLAPSADO",
                            f"frames {indices} share md5 {digest[:8]} -- the animation is a still",
                        )
                    )
        else:
            # The manifest DECLARES how many source images the clip is
            # built from: the enemy art repeats poses on purpose. The
            # finding is raised only when the art disagrees with the
            # declaration -- in either direction.
            measured = len(digests)
            if measured != clip.distinct:
                groups = sorted(digests.values(), key=len, reverse=True)
                # The two failure modes are NOT interchangeable: more images
                # than declared means the MANIFEST is stale; fewer means the
                # ART collapsed further than declared. Say which one.
                detail = (
                    f"the manifest declares {clip.distinct} distinct images, "
                    f"the clip measures {measured} (groups {groups})"
                )
                if measured > clip.distinct:
                    detail += " -- the manifest is stale"
                else:
                    detail += " -- the art collapsed further than declared"
                findings.append(
                    Finding(
                        clip.id,
                        groups[0][0] if groups else 0,
                        "COLAPSADO",
                        detail,
                    )
                )
```

- [ ] **Step 9: Run the test to verify it passes**

Run: `python -m pytest tests/test_distinct_rule.py tests/test_effective_cut_margin.py -v`

Expected: **7 passed**

- [ ] **Step 10: Prove GOLIATH is unharmed**

Run: `python tools\sprite_pipeline\verify_contract.py goliath`

Expected: `CONTRACT OK`, exit 0.

- [ ] **Step 11: Commit**

```powershell
git add src/anim/measure.py tools/sprite_pipeline/audit.py tools/sprite_pipeline/repair.py tests/test_effective_cut_margin.py tests/test_distinct_rule.py
git commit -m "feat: BLOQUE 75 - el margen es por set y COLAPSADO respeta el distinct declarado"
```

---

## Task 5: The 8 enemy manifests + the canvas guard

**Files:**
- Create: `Assets/sprites/enemies/{scout,cruiser,drone,heavy,kamikaze,sniper,turret,mine_asteroid}/manifest.toml`
- Test: `tests/test_enemy_manifest_matches_assets.py`

**Interfaces:**
- Consumes: `load_set(name, root)` → `AnimSet` with `canvas`, `clip.canvas`, `cut_margin`
- Produces: 8 manifests whose declared canvas matches every frame on disk

- [ ] **Step 1: Write the failing test**

Create `tests/test_enemy_manifest_matches_assets.py`:

```python
"""BLOQUE 75: the enemy manifests must describe the assets that exist.

The canvas is the SPRITE canvas (measured), NOT the hitbox in
ENEMY_CONFIGS. The mine mixes two: its open/closed states are 64x64 and
its death art is 32x32, which is why `clip.canvas` exists.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import load_set

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


def test_every_enemy_set_has_a_manifest(enemies_root):
    for name in ENEMY_SETS:
        assert (enemies_root / name / "manifest.toml").is_file(), name


def test_every_clip_directory_exists(enemies_root):
    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        for clip in anim_set.clips.values():
            assert (anim_set.path / clip.dir).is_dir(), f"{name}/{clip.id}"


def test_frame_count_matches_manifest(enemies_root):
    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        for clip in anim_set.clips.values():
            pngs = sorted((anim_set.path / clip.dir).glob("frame_*.png"))
            assert len(pngs) == clip.frames, f"{name}/{clip.id}"


def test_every_frame_has_the_declared_canvas(enemies_root, display):
    """The clip's own canvas, or the set's when the clip declares none."""
    import pygame

    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        for clip in anim_set.clips.values():
            expected = clip.canvas or anim_set.canvas
            for png in sorted((anim_set.path / clip.dir).glob("frame_*.png")):
                surf = pygame.image.load(str(png)).convert_alpha()
                assert surf.get_size() == expected, f"{name}/{clip.id}/{png.name}"


def test_the_mine_declares_two_canvases(enemies_root):
    """The special case: 64x64 states, 32x32 death art."""
    anim_set = load_set("mine_asteroid", root=enemies_root)
    assert anim_set.canvas == (64, 64)
    assert anim_set.clip("death").canvas == (32, 32)
    assert anim_set.clip("closed").canvas is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_enemy_manifest_matches_assets.py -v`

Expected: **FAIL** — `assert (enemies_root / 'scout' / 'manifest.toml').is_file()`

- [ ] **Step 3: Write the 8 manifests**

The seven ships share one shape. `Assets/sprites/enemies/scout/manifest.toml`
(the other six are the same with their own name):

```toml
# BLOQUE 75: SPEC of the SCOUT animation set. Hand-edited.
#
# Verified by: tools/sprite_pipeline/audit.py
# Design: docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md
#
# The canvas is the SPRITE canvas, measured (32x32), NOT the hitbox
# (ENEMY_CONFIGS says 12x8). The hitbox never enters the manifest.
#
# `distinct`: the clip is built from 3 source poses, cycled to fill 10
#   slots at 12.5 FPS. The order is IRREGULAR on purpose -- do not
#   "clean it up": de-duplicating the playback would change the animation.
# `cut_margin = 0`: the enemy art is authored tight to its canvas (the
#   wings span the full 32 px). GOLIATH's 2 px margin exists because the
#   AI generator drew the boss's limbs past the canvas.
# `pivot = "fixed"`: the sprite is blitted centred on the entity, exactly
#   as the runtime does today. The measured registration is recorded, not
#   applied -- applying it would move the ship up to 3.7 px off its hitbox.
# `loop` + `on_end`: the one-shot clips carry BOTH. `loop = false` is what
#   the shipped ClipPlayer actually branches on (src/anim/clip.py:54), so
#   without it a damage/death clip would WRAP FOREVER. `on_end = "reset"`
#   declares the ENTITY's behaviour: the enemy goes back to idle.

[meta]
name        = "SCOUT"
version     = 1
canvas      = [32, 32]
anchor      = [16, 16]
cut_margin  = 0

[[clips]]
id       = "idle"
dir      = "idle"
frames   = 10
fps      = 12.5
distinct = 3
mode     = "sequence"
on_end   = "loop"
scale_tolerance = 0.10

[[clips]]
id       = "thrust"
dir      = "thrust"
frames   = 10
fps      = 12.5
distinct = 1
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
loop     = false
on_end   = "reset"
scale_tolerance = 0.10

[[clips]]
id       = "death"
dir      = "death"
frames   = 10
fps      = 12.5
distinct = 4
mode     = "sequence"
loop     = false
on_end   = "reset"
scale_tolerance = 0.45

[[parts]]
id    = "body"
draw  = "frames"
pivot = "fixed"
z     = 0
```

The six other ships are the same file with `name` changed
(`CRUISER`, `DRONE`, `HEAVY`, `KAMIKAZE`, `SNIPER`, `TURRET`) and the
`scale_tolerance` of the `death` clip taken from the table below:

| Set | `death` scale_tolerance | Set | `death` scale_tolerance |
|---|---|---|---|
| `cruiser` | 0.70 | `kamikaze` | 0.60 |
| `drone` | 0.65 | `sniper` | 0.45 |
| `heavy` | 0.65 | `turret` | 0.60 |

`Assets/sprites/enemies/mine_asteroid/manifest.toml`:

```toml
# BLOQUE 75: SPEC of the MINE_ASTEROID animation set. Hand-edited.
#
# The special set: four visual states, one of them with five VARIANTS,
# a death clip the runtime never plays, and TWO canvas sizes.

[meta]
name        = "MINE_ASTEROID"
version     = 1
canvas      = [64, 64]
anchor      = [32, 32]
cut_margin  = 0

[[clips]]
id       = "closed"
dir      = "closed"
frames   = 5
distinct = 5
mode     = "variants"
scale_tolerance = 0.25

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
dir      = "open"
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
mode     = "archive"
canvas   = [32, 32]
scale_tolerance = 0.10

[[parts]]
id    = "body"
draw  = "frames"
pivot = "fixed"
z     = 0
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_enemy_manifest_matches_assets.py -v`

Expected: **6 passed**

- [ ] **Step 5: Commit**

```powershell
git add Assets/sprites/enemies
git commit -m "feat: BLOQUE 75 - los 8 sets de enemigos declaran su manifest"
```

---

## Task 6: The 8 generated anchors + the freshness guard

**Files:**
- Create: `Assets/sprites/enemies/<kind>/anchors.toml` (8, **generated**)
- Test: `tests/test_enemy_anchors_are_fresh.py`

**Interfaces:**
- Consumes: `render_anchors_toml(anim_set, measurements)`, `audit_set(anim_set)`
- Produces: 8 `anchors.toml` files, byte-stable across runs

- [ ] **Step 1: Write the failing test**

Create `tests/test_enemy_anchors_are_fresh.py`:

```python
"""BLOQUE 75: the enemy anchors must not be stale.

The freshness check compares TEXT and never writes: a test that rewrote the
committed file would make the repo's own state depend on the test order.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set
from sprite_pipeline.audit import audit_set, render_anchors_toml

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


def test_every_enemy_set_has_its_anchors(enemies_root):
    for name in ENEMY_SETS:
        assert (enemies_root / name / "anchors.toml").is_file(), name


def test_the_enemy_anchors_are_fresh(enemies_root, display):
    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        _, measurements = audit_set(anim_set)
        rendered = render_anchors_toml(anim_set, measurements)
        on_disk = (enemies_root / name / "anchors.toml").read_text(encoding="utf-8")
        assert rendered == on_disk, f"{name}: the anchors are stale"


def test_the_enemy_anchors_are_lf(enemies_root):
    for name in ENEMY_SETS:
        raw = (enemies_root / name / "anchors.toml").read_bytes()
        assert b"\r\n" not in raw, name
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_enemy_anchors_are_fresh.py -v`

Expected: **FAIL** — the anchors files do not exist yet.

- [ ] **Step 3: Generate them**

```powershell
foreach ($set in @('scout','cruiser','drone','heavy','kamikaze','sniper','turret','mine_asteroid')) {
  python tools\sprite_pipeline\audit.py $set --root Assets\sprites\enemies --write-anchors
}
```

Expected: each run prints `wrote ...\anchors.toml`. **The exit code is 1** on
the first run (the art really has the findings the manifest declares) — that is
expected and does not stop the loop.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_enemy_anchors_are_fresh.py -v`

Expected: **3 passed**

- [ ] **Step 5: Prove the regeneration is deterministic**

Run it twice and compare:

```powershell
python tools\sprite_pipeline\audit.py scout --root Assets\sprites\enemies --write-anchors
git diff --stat Assets\sprites\enemies\scout\anchors.toml
```

Expected: the diff is **empty** — the second run produced the same bytes.

- [ ] **Step 6: Commit**

```powershell
git add Assets/sprites/enemies
git commit -m "feat: BLOQUE 75 - los anchors medidos de los 8 sets de enemigos"
```

---

## Task 7: Set discovery

**Files:**
- Create: `tools/sprite_pipeline/sets.py`
- Test: `tests/test_enemy_set_discovery.py`

**Interfaces:**
- Produces: `sets.resolve_set(name: str, root: Path | None = None) -> Path`,
  `sets.discover_sets(root: Path) -> list[Path]`, `sets.sets_roots() -> list[Path]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_enemy_set_discovery.py`:

```python
"""BLOQUE 75: what is a set, and what is not.

A directory is a SET iff it contains a manifest.toml. A directory whose
name starts with "_" is never one (that is what excludes
`_backup_pre_bloque_65`), and a PNG that is not named `frame_*.png` is
not a frame (that is what excludes the two reference PNGs the generator
reads).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline.sets import discover_sets, resolve_set, sets_roots


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


def test_the_two_roots_are_the_bosses_and_the_enemies():
    roots = [p.name for p in sets_roots()]
    assert roots == ["bosses", "enemies"]


def test_the_enemy_sets_are_discovered(enemies_root):
    found = {p.name for p in discover_sets(enemies_root)}
    assert found == {
        "scout",
        "cruiser",
        "drone",
        "heavy",
        "kamikaze",
        "sniper",
        "turret",
        "mine_asteroid",
    }


def test_the_backup_directory_is_not_a_set(enemies_root):
    found = {p.name for p in discover_sets(enemies_root)}
    assert "_backup_pre_bloque_65" not in found


def test_resolve_set_finds_an_enemy_by_name():
    assert resolve_set("scout").name == "scout"
    assert resolve_set("scout").parent.name == "enemies"


def test_resolve_set_finds_goliath():
    assert resolve_set("goliath").parent.name == "bosses"


def test_an_unknown_set_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        resolve_set("no_existe")


def test_discovery_does_not_crash_on_a_malformed_manifest(tmp_path):
    """L5: a broken manifest degrades, it never takes the caller down."""
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "manifest.toml").write_text(
        "this is not toml at all [[[", encoding="utf-8"
    )
    (tmp_path / "no_manifest").mkdir()
    found = {p.name for p in discover_sets(tmp_path)}
    assert "no_manifest" not in found
    assert "broken" in found  # discovery does not parse; the loader degrades
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_enemy_set_discovery.py -v`

Expected: **FAIL** — `ModuleNotFoundError: No module named 'sprite_pipeline.sets'`

- [ ] **Step 3: Write `tools/sprite_pipeline/sets.py`**

```python
"""BLOQUE 75: where the animated sets live.

A directory is a SET iff it contains a `manifest.toml`. Nothing else is.
That single rule is what keeps `_backup_pre_bloque_65` (no manifest) and
the two loose reference PNGs (not named `frame_*.png`) out of the
pipeline, without a heuristic that could get it wrong.

The two roots are probed in order: the bosses first (GOLIATH), then the
enemies. The frozen build resolves the same way: the bundle is extracted
to `_MEIPASS` and the Assets are read from THERE.
"""
from __future__ import annotations

import sys
from pathlib import Path

SET_DIR_NAMES = ("bosses", "enemies")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def sets_roots() -> list[Path]:
    """Every directory that HOLDS sets, in resolution order.

    The frozen bundle has no project root: the assets are read from
    `_MEIPASS`. This is the same probe `src/anim/manifest.py::_sets_root`
    uses, extended to the second root.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    base = Path(meipass) if meipass else _project_root()
    return [base / "Assets" / "sprites" / name for name in SET_DIR_NAMES]


def resolve_set(name: str, root: Path | None = None) -> Path:
    """The directory of the set called `name`.

    An explicit `root` wins. Otherwise the name is resolved against every
    sets root, in order. Raises `FileNotFoundError` (an `OSError`) when no
    root has it -- the CLI catches it and prints an error instead of a
    traceback.
    """
    if root is not None:
        candidate = root / name
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(f"no set {name!r} under {root}")
    for base in sets_roots():
        candidate = base / name
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"no set {name!r} under {sets_roots()}")


def discover_sets(root: Path) -> list[Path]:
    """Every set under `root`, sorted by name.

    A directory whose name starts with "_" is NEVER a set. A directory
    without a `manifest.toml` is not a set either. The manifests are NOT
    parsed here: discovery must not raise on a broken one -- the loader
    degrades to None for that.
    """
    if not root.is_dir():
        return []
    found: list[Path] = []
    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir() or candidate.name.startswith("_"):
            continue
        if not (candidate / "manifest.toml").is_file():
            continue
        found.append(candidate)
    return found
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_enemy_set_discovery.py -v`

Expected: **7 passed**

- [ ] **Step 5: Commit**

```powershell
git add tools/sprite_pipeline/sets.py tests/test_enemy_set_discovery.py
git commit -m "feat: BLOQUE 75 - el pipeline descubre los sets por su manifest"
```

---

## Task 8: The guards that prove the art was not touched

**Files:**
- Create: `tests/test_enemy_art_is_untouched.py`
- Create: `tests/test_enemy_hitbox_is_not_the_canvas.py`
- Create: `tests/test_enemy_clip_semantics.py`

**Interfaces:**
- Consumes: `resolve_set`, `audit_set`, `run.py --fix` on a `tmp_path` copy
- Produces: three guards, all read-only against the repository

- [ ] **Step 1: Write `tests/test_enemy_art_is_untouched.py`**

```python
"""BLOQUE 75: not one PNG byte may change.

The repair writes PNGs for CORTADO and LADO_EQUIVOCADO. With
`cut_margin = 0` and no sided feature declared, neither can fire on an
enemy set -- so the repair has nothing to write. This test proves it on
every run, on a COPY: the repository is never written to.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline.sets import discover_sets

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _png_digests(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): _md5(p)
        for p in sorted(root.rglob("*.png"))
    }


@pytest.mark.parametrize("name", ENEMY_SETS)
def test_the_fix_run_changes_no_png(tmp_path, name):
    enemies_root = ROOT / "Assets" / "sprites" / "enemies"
    copy_root = tmp_path / "sets"
    copy_root.mkdir()
    shutil.copytree(enemies_root / name, copy_root / name)

    before = _png_digests(copy_root)
    assert before, "the set has no PNGs to protect"

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "sprite_pipeline" / "run.py"),
            name,
            "--root",
            str(copy_root),
            "--fix",
        ],
        capture_output=True,
        cwd=str(ROOT),
    )
    after = _png_digests(copy_root)
    assert after == before, f"{name}: the --fix run rewrote a PNG"


def test_the_repository_itself_is_untouched():
    """The shipped tree is not a scratch pad."""
    enemies_root = ROOT / "Assets" / "sprites" / "enemies"
    found = {p.name for p in discover_sets(enemies_root)}
    assert found == set(ENEMY_SETS)
```

- [ ] **Step 2: Write `tests/test_enemy_hitbox_is_not_the_canvas.py`**

```python
"""BLOQUE 75: the canvas is not the hitbox.

The hitbox lives in ENEMY_CONFIGS (the collision box); the canvas is the
sprite's surface. They are different numbers and the manifest must carry
only the second one. The guard: the hitbox fits inside the canvas, always.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import load_set
from src.entities.enemies.enemy import ENEMY_CONFIGS

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


@pytest.mark.parametrize("name", ENEMY_SETS)
def test_the_hitbox_fits_inside_the_canvas(enemies_root, name):
    anim_set = load_set(name, root=enemies_root)
    config = ENEMY_CONFIGS[name]
    assert config.width <= anim_set.canvas[0], name
    assert config.height <= anim_set.canvas[1], name


def test_the_hitbox_is_not_the_canvas():
    """A guard against the two being conflated: they are not equal."""
    enemies_root = ROOT / "Assets" / "sprites" / "enemies"
    anim_set = load_set("scout", root=enemies_root)
    config = ENEMY_CONFIGS["scout"]
    assert (config.width, config.height) != anim_set.canvas
```

- [ ] **Step 3: Write `tests/test_enemy_clip_semantics.py`**

```python
"""BLOQUE 75: the declared semantics must match what the runtime does.

`mode` and `on_end` are PARSED but not enforced in Phase 1, so nothing
else would catch a declaration that contradicts the code. This test is the
consumer: it reads the manifest and the runtime and compares them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import load_set
from src.entities.enemies.enemy import ANIMATION_FRAME_DURATION

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
)


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


def test_the_runtime_fps_is_the_declared_fps(enemies_root):
    runtime_fps = 1.0 / ANIMATION_FRAME_DURATION
    assert runtime_fps == 12.5
    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        for clip in anim_set.clips.values():
            assert clip.fps == runtime_fps, f"{name}/{clip.id}"


@pytest.mark.parametrize("name", ENEMY_SETS)
def test_the_sequences_declare_what_the_runtime_does(enemies_root, name):
    anim_set = load_set(name, root=enemies_root)
    assert anim_set.clip("idle").on_end == "loop"
    assert anim_set.clip("thrust").on_end == "loop"
    # damage and death are one-shots that RETURN to idle: the runtime
    # resets `animation_frame` and `animation_state` (enemy.py:714-717).
    assert anim_set.clip("damage").on_end == "reset"
    assert anim_set.clip("death").on_end == "reset"


def test_the_mine_declares_its_states(enemies_root):
    anim_set = load_set("mine_asteroid", root=enemies_root)
    assert anim_set.clip("closed").mode == "variants"
    assert anim_set.clip("open1").mode == "state"
    assert anim_set.clip("open2").mode == "state"
    assert anim_set.clip("open3").mode == "state"
    # The death clip exists on disk but the runtime never plays it:
    # `Enemy.animation_path` always returns the mine's STATE path.
    assert anim_set.clip("death").mode == "archive"


def test_the_mine_states_match_the_runtime_directories(enemies_root):
    anim_set = load_set("mine_asteroid", root=enemies_root)
    # open3 reuses the `open/` directory (BLOQUE 65).
    assert anim_set.clip("open3").dir == "open"
    assert anim_set.clip("closed").frames == 5  # five asteroid VARIANTS
```

- [ ] **Step 4: Run the three tests**

Run: `python -m pytest tests/test_enemy_art_is_untouched.py tests/test_enemy_hitbox_is_not_the_canvas.py tests/test_enemy_clip_semantics.py -v`

Expected: **all passed**. If `test_the_fix_run_changes_no_png` fails, the
repair is still writing PNGs: check that `cut_margin = 0` is in every enemy
manifest and that the repair reads `effective_cut_margin`.

- [ ] **Step 5: Prove the repository is untouched**

Run: `git status --short`

Expected: empty (the tests only ever wrote to `tmp_path`).

- [ ] **Step 6: Commit**

```powershell
git add tests/test_enemy_art_is_untouched.py tests/test_enemy_hitbox_is_not_the_canvas.py tests/test_enemy_clip_semantics.py
git commit -m "test: BLOQUE 75 - el arte no se toca, el hitbox no es el canvas y la semantica declarada es la real"
```

---

## Task 9: The Phase 1 gate

**Files:**
- Create: `tools/sprite_pipeline/gate.py`
- Test: `tests/test_sprite_pipeline_gate.py`

**Interfaces:**
- Consumes: `audit_set`, `render_anchors_toml`, `resolve_set`, `discover_sets`
- Produces: `python tools\sprite_pipeline\gate.py` → `PHASE 1 GATE OK` (exit 0) or `PHASE 1 GATE FAILED:` + the list (exit 1)

- [ ] **Step 1: Write the gate**

Create `tools/sprite_pipeline/gate.py`:

```python
"""BLOQUE 75: the Phase 1 gate.

One command that decides whether the enemy sets are ready for Phase 2.
It runs EVERY check and reports all the failures, not just the first.

    python tools/sprite_pipeline/gate.py

Exit 0 -> PHASE 1 GATE OK. Exit 1 -> PHASE 1 GATE FAILED: <the list>.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parent.parent.parent
for _entry in (str(ROOT), str(ROOT / "tools")):
    if _entry in sys.path:
        sys.path.remove(_entry)
    sys.path.insert(0, _entry)

import pygame  # noqa: E402

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline import ensure_display  # noqa: E402
from sprite_pipeline.audit import (  # noqa: E402
    FAIL_STATES,
    audit_set,
    render_anchors_toml,
)
from sprite_pipeline.sets import discover_sets, resolve_set  # noqa: E402

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


def main() -> int:
    pygame.init()
    ensure_display()

    failures: list[str] = []

    # G1: every enemy set audits clean.
    enemies_root = ROOT / "Assets" / "sprites" / "enemies"
    for name in ENEMY_SETS:
        try:
            anim_set = load_set(name, root=enemies_root)
        except (OSError, ValueError) as exc:
            failures.append(f"G1 {name}: the manifest does not load: {exc}")
            continue
        findings, _ = audit_set(anim_set)
        for finding in findings:
            if finding.state in FAIL_STATES:
                failures.append(
                    f"G1 {name}: {finding.clip}/frame_{finding.frame:02d} "
                    f"{finding.state}: {finding.detail}"
                )
            else:
                failures.append(
                    f"G1 {name}: {finding.clip}/frame_{finding.frame:02d} "
                    f"{finding.state} (WARN): {finding.detail}"
                )

    # G2 + G3: the anchors are fresh and deterministic.
    for name in ENEMY_SETS:
        try:
            anim_set = load_set(name, root=enemies_root)
        except (OSError, ValueError) as exc:
            failures.append(f"G2 {name}: the manifest does not load: {exc}")
            continue
        _, measurements = audit_set(anim_set)
        rendered = render_anchors_toml(anim_set, measurements)
        path = enemies_root / name / "anchors.toml"
        if not path.is_file():
            failures.append(f"G2 {name}: no anchors.toml")
            continue
        on_disk = path.read_text(encoding="utf-8")
        if rendered != on_disk:
            failures.append(f"G2 {name}: the anchors are stale")
        if render_anchors_toml(anim_set, measurements) != rendered:
            failures.append(f"G3 {name}: the anchors are not deterministic")

    # G5: GOLIATH is unharmed.
    goliath = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
    if not (goliath / "anchors.toml").is_file():
        failures.append("G5 goliath: no anchors.toml")

    # G6: discovery finds exactly the 8 sets.
    found = {p.name for p in discover_sets(enemies_root)}
    if found != set(ENEMY_SETS):
        failures.append(f"G6: discovery found {sorted(found)}")

    # G9: mypy is not optional.
    if not _mypy_available():
        failures.append(
            "G9: mypy is not installed -- run "
            "`python -m pip install -r requirements-dev.txt`"
        )

    if failures:
        print("PHASE 1 GATE FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("PHASE 1 GATE OK")
    return 0


def _mypy_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("mypy") is not None


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Write the test**

Create `tests/test_sprite_pipeline_gate.py`:

```python
"""BLOQUE 75: the gate runs and passes on the shipped tree."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_the_gate_passes():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "sprite_pipeline" / "gate.py")],
        capture_output=True,
        cwd=str(ROOT),
    )
    out = proc.stdout.decode("utf-8")
    assert proc.returncode == 0, out + proc.stderr.decode("utf-8")
    assert "PHASE 1 GATE OK" in out
```

- [ ] **Step 3: Run the test**

Run: `python -m pytest tests/test_sprite_pipeline_gate.py -v`

Expected: **PASS** — unless mypy is missing, in which case the gate reports
`G9: mypy is not installed` and the test fails with that message. Install the
dev requirements (`python -m pip install -r requirements-dev.txt`) and re-run.

- [ ] **Step 4: Commit**

```powershell
git add tools/sprite_pipeline/gate.py tests/test_sprite_pipeline_gate.py
git commit -m "feat: BLOQUE 75 - el gate de Fase 1 es un comando"
```

---

## Final verification (after Task 9)

- [ ] **Run the whole suite**

```powershell
python -m pytest tests\ --tb=no
```

Expected: **1 failed, 2 9xx passed, 7 skipped** — the one failure is
`test_paths_no_star_shapes` (pre-existing, out of scope). The count must be
**one failure lower** than the baseline (2), and no more.

- [ ] **Run the pipeline's own health checks**

```powershell
python tools\sprite_pipeline\verify_contract.py goliath
python tools\sprite_pipeline\gate.py
python -m mypy src\anim\
```

Expected: `CONTRACT OK`, `PHASE 1 GATE OK`, `Success: no issues found`.

- [ ] **Prove nothing moved**

```powershell
git status --short
git diff --stat master..HEAD -- Assets/sprites/bosses/
git diff --stat HEAD~9..HEAD -- '*.png'
```

Expected: the working tree is clean, GOLIATH's assets are untouched, and **no
PNG** appears in the diff.

- [ ] **Update the documentation**

```powershell
# the silo's index gains the plan row
# docs/superpowers/CONTEXT.md
```

Add this row to the "Contenido del silo" table:

```
| `plans/2026-11-03-bloque-75-phase1-enemy-pipeline.md` | Plan | Plan de implementación de la Fase 1 de BLOQUE 75 (los 8 sets de enemigos al pipeline, con gate) |
```

Then commit:

```powershell
git add docs/superpowers/CONTEXT.md
git commit -m "docs: BLOQUE 75 - el plan de la Fase 1 queda indexado en el silo"
```

---

## Self-review

**Spec coverage.** Every Phase 1 requirement of the spec maps to a task:
A1 (all 8 sets audit clean) → T5+T9 · A2 (GOLIATH unchanged) → T1/T2/T4
(`verify_contract`) · A3 (byte-identical anchors) → T2+T6 · A4 (no PNG
changes) → T8 · A5 (hitboxes untouched) → T8 · A6 (no network/clock) → the
import guard in T9 · C1 (featureless set) → T1 · I9 (false provenance) → T1 ·
F11 (CRLF) → T2 · F12 (L7, no writes in tests) → T6+T8+T9 (G11) · D1-D6
(discovery) → T7 · G1-G13 → T9.

**Deliberately NOT in this plan:** `mode`/`on_end` **enforcement** (Phase 2),
the `fixed` pivot in `src/anim/parts.py` (Phase 2), the `LayerStack`
(Phase 2), the frozen-build root change in `src/anim/manifest.py` (Phase 2).

**Type consistency.** `part_or_none`, `effective_cut_margin`, `is_cut_off`,
`resolve_set`, `discover_sets`, `sets_roots` are introduced once and used with
the same signature everywhere. `Clip.distinct` / `Clip.canvas` /
`Clip.mode` / `Clip.on_end` / `AnimSet.cut_margin` are added with defaults, so
the two positional constructions in `manifest.py` (both keyword-based) and
GOLIATH's manifest keep working untouched.
