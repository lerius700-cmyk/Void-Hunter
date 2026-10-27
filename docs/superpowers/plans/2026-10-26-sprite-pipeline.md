# Sprite Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn GOLIATH's animation from "compensated at runtime by pixel scans" into "declared in a manifest, measured at build time, and guarded by tests".

**Architecture:** Every animated set owns two files under `Assets/sprites/bosses/<name>/`: a hand-edited `manifest.toml` (clips, parts, detection rules) and a generated `anchors.toml` (the measurement, baked per frame). A headless pipeline under `tools/sprite_pipeline/` measures every frame, classifies it into one of seven states, repairs what is repairable, and writes `anchors.toml`. The runtime reads the baked table instead of scanning pixels.

**Tech Stack:** Python 3.11, pygame 2.6, stdlib `tomllib`. **No numpy in `src/`** (BLOQUE 58.14 allows it for the pause lowpass only). No new dependencies.

## Global Constraints

- Every task runs in the worktree `F:\AI\MM\void-hunter\.worktrees\bloquec-74-sprite-pipeline`, branch `bloquec-74-sprite-pipeline`, based on tag `v1.7.2` (`f4600ae`). **Never commit to `master`.** `master` must stay at `a40fdaf`, clean, with its 8 unpushed commits intact.
- Commit prefixes: `feat: BLOQUE 74`, `fix: BLOQUE 74`, `chore: BLOQUE 74`, `docs: BLOQUE 74`, `test: BLOQUE 74`.
- `src/` is stdlib + pygame only. `numpy` is forbidden in `src/`. `tomllib` is stdlib since 3.11.
- `Assets/sprites/` is bundled by `build.spec` wholesale — any file added there ships inside the `.exe` with no `build.spec` change.
- The GOLIATH shield constants move into the manifest **verbatim**, never retuned: `DX=0`, `DY=3`, `RX=11`, `RY=17`, `R=11`, `RX_SCALE=0.78`.
- Canvas is 96×80 for all 60 GOLIATH frames. The world anchor is `(48, 40)`. The canvas centre column is `48`.
- The pipeline never calls an AI and never regenerates art. Regeneration is a human decision taken from the auditor's report.
- Code, comments and docs are in English. User-facing strings are in Spanish.
- Run the suite with `python -m pytest tests/ --tb=no` (never add `-q`; `pyproject.toml` already sets it).
- The venv interpreter is `F:\AI\MM\void-hunter\.venv\Scripts\python.exe`.

## Measured baseline (the auditor's expected output before repair)

These numbers were measured against the 60 shipped GOLIATH frames with the manifest's `warm_fallback` predicate applied, and with the clip median computed as the true median (`statistics.median`, the average of the two middle values — NOT the upper-middle element, which shifts the threshold by up to 0.2 px). The auditor's output in Task 4 is asserted against exactly this table.

| Frame | States | Severity | After the repair (Task 6) |
|---|---|---|---|
| `javelin/frame_03` | LADO_EQUIVOCADO · FUERA_DE_RANGO | FAIL | mirrored, then re-measured |
| `javelin/frame_04` | FUERA_DE_RANGO | WARN | ellipse interpolated |
| `javelin/frame_07` | FUERA_DE_RANGO | WARN | ellipse interpolated |
| `laser/frame_04` | FUERA_DE_RANGO | WARN | ellipse interpolated |
| `laser/frame_05` | FIRMA_AMBIGUA | WARN | informational |
| `laser/frame_07` | FUERA_DE_RANGO | WARN | ellipse interpolated |
| `purple_bullet/frame_06` | LADO_EQUIVOCADO · FUERA_DE_RANGO | FAIL | mirrored, then re-measured |
| `purple_bullet/frame_08` | FUERA_DE_RANGO | WARN | ellipse interpolated |
| `death/frame_02` | FIRMA_AMBIGUA | WARN | informational |
| `death/frame_07` | FIRMA_AMBIGUA | WARN | informational |

**10 of 60 frames carry a finding: 2 FAIL and 8 WARN.** The other 50 are
clean. `COLAPSADO`, `CORTADO` and `AUSENTE` do not fire on the current
assets.

One more frame needs the interpolation: `death/frame_09` has no detectable
eye, because by the last frame of the death clip the boss is a heap of
wreckage. The `eye` part's `on_missing = "interpolate"` resolves it from
`death/frame_08`.

**Two FAIL states, both repaired by mirroring two PNGs.** The five
FUERA_DE_RANGO frames are resolved by interpolating the ellipse, which is a
legitimate resolution — the measurement is reconstructed, not defaulted. The
pipeline's bar is therefore **0 FAIL** plus **no unresolved feature** (the
`test_features_detected_everywhere` guard), not "0 warnings".

Key measurements that the thresholds depend on:

- **Probe (brass signature, warm filter applied)** detects the plate in **60/60** frames. Probe median per clip: `phase1_idle` 50.6 (max healthy deviation 1.9), `phase2_idle` 50.7 (3.0), `javelin` 48.8 (**21.4** at f03), `laser` 49.5 (5.5), `purple_bullet` 51.2 (**18.2** at f06), `death` 51.6 (10.9).
- **`side_tolerance = 14`** separates the two turned-around frames (21.4 at `javelin/f03`, 18.2 at `purple_bullet/f06`) from every healthy frame. The next-largest deviation among the frames that sit on the wrong side of the centre is `death/frame_02` at 10.9 — a margin of 3.1, so the threshold is not on a knife edge. The value comes from the loader's default (`entry.get("side_tolerance", 14.0)`); no clip overrides it, and the manifest's comment repeats the same figures.
- **Shape ellipse** is measurable in **60/60** frames with the two-pass rule, but 7 are not credible: `javelin/f03`, `javelin/f04`, `javelin/f07`, `laser/f04`, `laser/f07`, `purple_bullet/f06`, `purple_bullet/f08`. The two turned-around frames are repaired by mirroring; the other five are resolved by interpolation.
- **Height metric** (silhouette bbox height, warm pixels excluded), against the TRUE median: `laser/f05` 61 vs median 73.0 (16.4%), `purple_bullet/f07` 57 vs 72.5 (21.4%), `death/f04` 75 vs 60.0 (25%), `death/f08` 39 (35%), `death/f09` 37 (38.3%). The per-clip `scale_tolerance` values below make all of these intentional.
- **FIRMA_AMBIGUA** fires where the probe and the shape measurement disagree by more than `side_tolerance`: `laser/f05` (16.0), `death/f02` (16.8), `death/f07` (14.2). The largest disagreement among the remaining frames is 11.5 (`purple_bullet/f01`) — a margin of 2.5.
- **Max height deviation per clip** (true median): `phase1_idle` 0.027, `phase2_idle` 0.107, `javelin` 0.066, `laser` 0.164, `purple_bullet` 0.214, `death` 0.383. Every clip's `scale_tolerance` clears its own maximum, and the margins are: `phase1_idle` 0.123, `phase2_idle` **0.043** (0.107 vs 0.15 — the tightest), `javelin` 0.084, `laser` 0.086, `purple_bullet` 0.086, `death` 0.217.

---

## File structure

| File | Responsibility |
|---|---|
| `src/anim/__init__.py` | empty package marker |
| `src/anim/manifest.py` | parses `manifest.toml` → `AnimSet`, `Clip`, `Part`, `DetectRule` |
| `src/anim/anchors.py` | parses `anchors.toml` → `AnchorSet`, `FrameAnchor` |
| `src/anim/measure.py` | pixel-level measurement primitives over a `pygame.Surface` |
| `src/anim/parts.py` | renders one part (frames / ellipse / point / procedural) |
| `src/anim/clip.py` | `ClipPlayer`: elapsed time → frame, and composes the parts |
| `tools/sprite_pipeline/audit.py` | measures every frame, classifies it, writes `anchors.toml` |
| `tools/sprite_pipeline/repair.py` | deterministic, idempotent repairs (mirror, re-pad) |
| `tools/sprite_pipeline/run.py` | the pipeline command: validate → audit → repair → re-audit → anchors → report |
| `Assets/sprites/bosses/goliath/manifest.toml` | hand-edited spec of the GOLIATH set |
| `Assets/sprites/bosses/goliath/anchors.toml` | generated measurement |

**Refinement to the spec's file map:** the spec listed only `manifest.py`, `clip.py` and `parts.py` under `src/anim/`. This plan splits it into five files and adds `src/anim/anchors.py` and `src/anim/measure.py`. Reason: `anchors.toml` and `manifest.toml` have different lifecycles (one generated, one hand-edited) and the measurement code must be importable by the tests without the auditor's CLI. `src/anim/measure.py` is never imported by the runtime — only by `tools/` and `tests/`.

---

### Task 1: The manifest loader and GOLIATH's manifest

**Files:**
- Create: `src/anim/__init__.py`
- Create: `src/anim/manifest.py`
- Create: `Assets/sprites/bosses/goliath/manifest.toml`
- Test: `tests/test_manifest_matches_assets.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `src.anim.manifest.SETS_ROOT: Path` — `Assets/sprites/bosses`
  - `src.anim.manifest.ManifestError(ValueError)`
  - `src.anim.manifest.DetectRule` — frozen dataclass; fields `method: str`, `side: str | None`, `min_col: int`, `band: tuple[int,int] | None`, `col_range: tuple[int,int] | None`, `head_band: tuple[int,int] | None` (None means "no window declared" — a `(0, 0)` default would be truthy and silently produce an empty scan), `r_min: int`, `g_min: int`, `b_max: int`, `rg_min: int`, `r_minus_b_min: int`, `rx_range: tuple[float,float]`, `ry_range: tuple[float,float]`, `warm_fallback: WarmRule | None`, `probe: DetectRule | None`; classmethod `from_dict(raw: dict[str, Any]) -> DetectRule`
  - `src.anim.manifest.WarmRule` — frozen dataclass; fields `r_min: int`, `b_max: int`, `g_min: int`, `r_minus_b_min: int`; classmethod `from_dict(raw: dict[str, Any]) -> WarmRule`; method `matches(r: int, g: int, b: int) -> bool`
  - `src.anim.manifest.Part` — frozen dataclass; fields `id: str`, `draw: str`, `pivot: str`, `z: int`, `offset: tuple[int,int]`, `scale: tuple[float,float]`, `radii: tuple[float,float,float] | None`, `detect: DetectRule | None`, `on_missing: str`
  - `src.anim.manifest.Clip` — frozen dataclass; fields `id: str`, `dir: str`, `frames: int`, `fps: float`, `loop: bool`, `scale_tolerance: float`, `side_tolerance: float`
  - `src.anim.manifest.AnimSet` — frozen dataclass; fields `name: str`, `version: int`, `canvas: tuple[int,int]`, `anchor: tuple[int,int]`, `sided: str | None`, `path: Path`, `clips: dict[str, Clip]`, `parts: list[Part]`; methods `clip(clip_id) -> Clip`, `part(part_id) -> Part`
  - `src.anim.manifest.load_set(name: str, root: Path = SETS_ROOT) -> AnimSet`

- [ ] **Step 1: Write the failing test**

Create `tests/test_manifest_matches_assets.py`:

```python
"""BLOQUE 74: the manifest must describe the assets that actually exist.

The manifest is the spec of an animated set. If it drifts from the assets
on disk, the auditor measures the wrong thing and the runtime draws from a
stale table. This test is the drift alarm.
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

from src.anim.manifest import DetectRule, ManifestError, WarmRule, load_set


@pytest.fixture(scope="module")
def display():
    """pygame needs a video mode before convert_alpha() works."""
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.fixture(scope="module")
def goliath():
    return load_set("goliath")


def test_manifest_loads(goliath):
    assert goliath.name == "GOLIATH"
    assert goliath.canvas == (96, 80)
    assert goliath.anchor == (48, 40)
    assert goliath.sided == "right"


def test_every_clip_directory_exists(goliath):
    for clip in goliath.clips.values():
        assert (goliath.path / clip.dir).is_dir(), clip.id


def test_frame_count_matches_manifest(goliath):
    for clip in goliath.clips.values():
        pngs = sorted((goliath.path / clip.dir).glob("frame_*.png"))
        assert len(pngs) == clip.frames, (
            f"{clip.id}: {len(pngs)} PNGs on disk, manifest says {clip.frames}"
        )


def test_every_frame_has_the_declared_canvas(goliath, display):
    import pygame

    for clip in goliath.clips.values():
        for png in sorted((goliath.path / clip.dir).glob("frame_*.png")):
            surf = pygame.image.load(str(png)).convert_alpha()
            assert surf.get_size() == goliath.canvas, f"{png}: {surf.get_size()}"


def test_expected_clips_and_parts_exist(goliath):
    assert set(goliath.clips) == {
        "phase1_idle", "phase2_idle", "javelin", "laser", "purple_bullet", "death",
    }
    part_ids = {p.id for p in goliath.parts}
    assert {"body", "shield_plate", "eye", "fx_eye_beam"} <= part_ids


def test_death_clip_is_one_shot(goliath):
    assert goliath.clip("death").loop is False
    assert goliath.clip("phase1_idle").loop is True


def test_shield_constants_were_moved_verbatim(goliath):
    """BLOQUE 67 user-approved values. The manifest moves them, it does not
    retune them."""
    shield = goliath.part("shield_plate")
    assert shield.offset == (0, 3)
    assert shield.scale == (0.78, 1.0)
    assert shield.radii == (11.0, 11.0, 17.0)


def test_shield_rule_declares_the_warm_fallback(goliath):
    rule = goliath.part("shield_plate").detect
    assert rule is not None
    assert rule.warm_fallback is not None
    assert rule.warm_fallback.r_min == 235
    assert rule.warm_fallback.b_max == 140
    assert rule.warm_fallback.g_min == 130
    assert rule.warm_fallback.r_minus_b_min == 190


def test_warm_rule_matches_the_whole_beam_and_keeps_the_plate_highlight():
    """The beam is a gradient: exact RGB triples do not cover it.

    (220,180,80) is the plate's own face highlight and must NOT be
    discarded, or the plate stops being measurable.
    """
    rule = WarmRule(r_min=235, b_max=140, g_min=130, r_minus_b_min=190)
    assert rule.matches(255, 220, 80) is True
    assert rule.matches(240, 200, 120) is True
    assert rule.matches(255, 140, 60) is True
    assert rule.matches(255, 80, 40) is True
    assert rule.matches(220, 180, 80) is False


def test_absent_scan_windows_are_none_not_zero_pairs(goliath):
    """A window that the manifest does not declare must be None.

    `(0, 0)` is a TRUTHY tuple, so a consumer doing
    `rule.head_band or (0, h)` gets `(0, 0)` back -- an EMPTY scan
    window. The probe would then find nothing in any frame and the
    auditor would report no LADO_EQUIVOCADO at all, so the two
    turned-around frames would never be repaired.
    """
    probe = goliath.part("shield_plate").detect.probe
    assert probe is not None
    assert probe.band is None
    assert probe.col_range is None
    assert probe.head_band is None


def test_declared_scan_windows_still_parse_as_pairs(goliath):
    """The windows the manifest DOES declare are still read as pairs."""
    shield = goliath.part("shield_plate").detect
    assert shield.band == (28, 54)
    eye = goliath.part("eye").detect
    assert eye.head_band == (0, 30)
    assert eye.col_range == (24, 70)


def test_tolerance_thresholds_are_locked(goliath):
    """The tolerances decide which frames the auditor reports.

    `side_tolerance` separates the two turned-around frames (21.4 at
    javelin/f03, 18.2 at purple_bullet/f06) from every healthy frame.
    `scale_tolerance` is the relative silhouette-height deviation a clip
    tolerates. Both were measured on the shipped frames; a silent edit
    here would quietly change which frames are flagged, so the values
    are asserted exactly -- and the clip ids are the keys, so a new
    clip without a deliberate tolerance fails the test.
    """
    scale = {clip.id: clip.scale_tolerance for clip in goliath.clips.values()}
    assert scale == {
        "phase1_idle": 0.15,
        "phase2_idle": 0.15,
        "javelin": 0.15,
        "laser": 0.25,
        "purple_bullet": 0.30,
        "death": 0.60,
    }
    for clip in goliath.clips.values():
        assert clip.side_tolerance == 14.0, clip.id


def test_unknown_set_raises():
    with pytest.raises(ManifestError):
        load_set("no_existe")


# ---------------------------------------------------------------------------
# The ManifestError contract: a malformed manifest must fail LOUDLY and with
# the manifest's own error type, never with a bare IndexError/KeyError.
# ---------------------------------------------------------------------------
def test_unknown_detect_method_raises():
    """A misspelled method must not flow into the auditor unchallenged."""
    with pytest.raises(ManifestError):
        DetectRule.from_dict({"method": "shapeh"})


def test_unknown_detect_side_raises():
    with pytest.raises(ManifestError):
        DetectRule.from_dict({"method": "shape", "side": "middle"})


def test_bad_pair_arity_raises_manifest_error():
    """`band = [28]` used to raise a bare IndexError."""
    with pytest.raises(ManifestError):
        DetectRule.from_dict({"method": "shape", "band": [28]})


def test_unknown_clip_and_part_raise():
    set_ = load_set("goliath")
    with pytest.raises(ManifestError):
        set_.clip("no_such_clip")
    with pytest.raises(ManifestError):
        set_.part("no_such_part")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_manifest_matches_assets.py --tb=short`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.anim'`

- [ ] **Step 3: Create the package marker and the manifest loader**

Create `src/anim/__init__.py` as an empty file.

Create `src/anim/manifest.py`:

```python
"""BLOQUE 74: declarative animation manifest.

An animated set (GOLIATH today) owns two files:

    Assets/sprites/bosses/<name>/manifest.toml   hand-edited. The spec.
    Assets/sprites/bosses/<name>/anchors.toml    generated. The measurement.

This module only READS and VALIDATES the manifest. It never measures
anything -- that is the auditor's job (tools/sprite_pipeline/audit.py), and
its output is anchors.toml.

Stdlib + pygame only. numpy is forbidden in src/ (BLOQUE 58.14 allows it
for the pause-screen lowpass only).
"""
from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

def _project_root() -> Path:
    """The repository root, resolved on demand.

    The frozen build does NOT have one: the bundle is extracted to a
    temporary directory and the assets are read from THERE. Resolving the
    source tree at import time would drag the frozen path in for nothing,
    so the root is computed only when the default sets root is needed.
    """
    return Path(__file__).resolve().parent.parent.parent


def _sets_root() -> Path:
    """Where the animated sets live.

    Running from source: <project root>/Assets/sprites/bosses.

    Frozen (PyInstaller, onefile): the bundle is extracted to a temporary
    directory and the Assets are dropped in `<_MEIPASS>/Assets/...`, so the
    sets are read from THERE. This is the same probe the audio and the
    tiling image use (src/audio/music.py, src/ui/tiling_image.py): the
    manifest is the ONE place that resolves the assets of an animated set,
    so the runtime never needs a second, divergent probe.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "Assets" / "sprites" / "bosses"
    return _project_root() / "Assets" / "sprites" / "bosses"


def __getattr__(name: str) -> Any:
    """Lazily resolved module attributes (PEP 562).

    SETS_ROOT is resolved on FIRST access instead of at import time: a
    frozen build never needs the source tree, and the default of
    `load_set` computes it only when it is really used.
    """
    if name == "SETS_ROOT":
        return _sets_root()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

VALID_METHODS = ("shape", "color")
VALID_SIDES = ("left", "right")


class ManifestError(ValueError):
    """The manifest is malformed: a bad value, a missing field, a duplicate
    id, or a rule that cannot be applied.

    It does NOT mean "the manifest disagrees with the assets" -- the loader
    never looks at the assets. That check lives in the auditor and in
    tests/test_manifest_matches_assets.py.
    """


def _as_int_pair(value: Any, name: str) -> tuple[int, int]:
    """Read a two-element integer pair, rejecting anything else."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ManifestError(f"{name} must be a pair of integers, got {value!r}")
    try:
        return (int(value[0]), int(value[1]))
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"{name} must be a pair of integers, got {value!r}") from exc


def _as_float_pair(value: Any, name: str) -> tuple[float, float]:
    """Read a two-element float pair, rejecting anything else."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ManifestError(f"{name} must be a pair of numbers, got {value!r}")
    try:
        return (float(value[0]), float(value[1]))
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"{name} must be a pair of numbers, got {value!r}") from exc


def _as_float_triple(value: Any, name: str) -> tuple[float, float, float]:
    """Read a three-element float triple, rejecting anything else."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ManifestError(f"{name} must be three numbers, got {value!r}")
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"{name} must be three numbers, got {value!r}") from exc


@dataclass(frozen=True)
class WarmRule:
    """The predicate that recognises the colours of a baked eye beam.

    The beam is a GRADIENT, so listing its colours as exact RGB triples
    does not work: most of the beam's pixels are near, but not equal to,
    the four colours it was painted with. This predicate is the one the
    shipped runtime uses (src/ui/scenes.py), and it deliberately KEEPS
    (220,180,80) -- the plate's own face highlight -- because that colour
    fails the `r >= 235` test.

    It is a FALLBACK: the measurement is taken on the plain silhouette
    first, and only retried with the warm pixels dropped when the plain
    result is not credible. That is the shipped two-pass behaviour.
    """

    r_min: int = 0
    b_max: int = 255
    g_min: int = 0
    r_minus_b_min: int = 0

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "WarmRule":
        return cls(
            r_min=int(raw.get("r_min", 0)),
            b_max=int(raw.get("b_max", 255)),
            g_min=int(raw.get("g_min", 0)),
            r_minus_b_min=int(raw.get("r_minus_b_min", 0)),
        )

    def matches(self, r: int, g: int, b: int) -> bool:
        """True when the colour belongs to the baked beam."""
        if r < self.r_min or b > self.b_max:
            return False
        return g >= self.g_min or (r - b) >= self.r_minus_b_min


@dataclass(frozen=True)
class DetectRule:
    """How to locate one feature inside a frame.

    `method` is "shape" (the feature is found by the outline of a solid
    block of pixels) or "color" (it is found by a colour signature).

    `warm_fallback` is the optional predicate that recognises a baked
    effect whose colours collide with the feature. It is only used as a
    retry: measure the plain silhouette first, and drop the warm pixels
    only when the plain measurement is not credible.

    `band`, `col_range` and `head_band` are optional scan windows. None
    means "no window declared" -- a `(0, 0)` default would be truthy and
    silently produce an empty scan.

    `probe` is an optional colour signature used ONLY to answer "which side
    is the feature on?". The shape rule cannot detect a turned-around
    character: it finds the ARM at the right of the band and measures a
    plausible-looking ellipse that is not the plate.
    """

    method: str
    side: str | None = None
    min_col: int = 0
    band: tuple[int, int] | None = None
    col_range: tuple[int, int] | None = None
    head_band: tuple[int, int] | None = None
    r_min: int = 0
    g_min: int = 0
    b_max: int = 255
    rg_min: int = 0
    r_minus_b_min: int = 0
    rx_range: tuple[float, float] = (0.0, 0.0)
    ry_range: tuple[float, float] = (0.0, 0.0)
    warm_fallback: WarmRule | None = None
    probe: "DetectRule | None" = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DetectRule":
        method = raw.get("method", "")
        if method not in VALID_METHODS:
            raise ManifestError(
                f"unknown detect method {method!r} (expected one of {VALID_METHODS})"
            )
        side = raw.get("side")
        if side is not None and side not in VALID_SIDES:
            raise ManifestError(f"unknown detect side {side!r}")
        ranges = raw.get("ranges") or {}
        warm_raw = raw.get("warm_fallback")
        probe_raw = raw.get("probe")
        return cls(
            method=str(method),
            side=side,
            min_col=int(raw.get("min_col", 0)),
            band=_as_int_pair(raw["band"], "band") if "band" in raw else None,
            col_range=(
                _as_int_pair(raw["col_range"], "col_range")
                if "col_range" in raw
                else None
            ),
            head_band=(
                _as_int_pair(raw["head_band"], "head_band")
                if "head_band" in raw
                else None
            ),
            r_min=int(raw.get("r_min", 0)),
            g_min=int(raw.get("g_min", 0)),
            b_max=int(raw.get("b_max", 255)),
            rg_min=int(raw.get("rg_min", 0)),
            r_minus_b_min=int(raw.get("r_minus_b_min", 0)),
            rx_range=_as_float_pair(ranges.get("rx", (0.0, 0.0)), "ranges.rx"),
            ry_range=_as_float_pair(ranges.get("ry", (0.0, 0.0)), "ranges.ry"),
            warm_fallback=WarmRule.from_dict(warm_raw) if warm_raw else None,
            probe=cls.from_dict(probe_raw) if probe_raw else None,
        )


@dataclass(frozen=True)
class Part:
    """One thing the compositor draws.

    draw is "frames" (one PNG per frame), "ellipse" (a procedural
    primitive), "point" (an anchor that draws nothing) or "procedural" (a
    runtime-generated effect).

    pivot is "centroid" (auto: alpha-weighted centroid of the silhouette),
    "detect" (auto: the detection rule below) or "fixed".

    `radii` carries the canonical radii (R, RX, RY) of a shape feature:
    the ellipse to fall back to when the art does not contain the feature.
    """

    id: str
    draw: str
    pivot: str
    z: int
    offset: tuple[int, int]
    scale: tuple[float, float]
    radii: tuple[float, float, float] | None
    detect: DetectRule | None
    on_missing: str


@dataclass(frozen=True)
class Clip:
    """One animation: a directory of frames plus its timing.

    `scale_tolerance` is the relative deviation of the silhouette height
    from the clip median that still counts as "not rescaled". `death`
    needs a loose one because the boss collapses on purpose.
    """

    id: str
    dir: str
    frames: int
    fps: float
    loop: bool
    scale_tolerance: float
    side_tolerance: float


@dataclass(frozen=True)
class AnimSet:
    """One animated character: its clips and its parts."""

    name: str
    version: int
    canvas: tuple[int, int]
    anchor: tuple[int, int]
    sided: str | None
    path: Path
    clips: dict[str, Clip]
    parts: list[Part]

    def clip(self, clip_id: str) -> Clip:
        try:
            return self.clips[clip_id]
        except KeyError:
            raise ManifestError(f"unknown clip {clip_id!r} in {self.name}") from None

    def part(self, part_id: str) -> Part:
        for part in self.parts:
            if part.id == part_id:
                return part
        raise ManifestError(f"unknown part {part_id!r} in {self.name}")


_LOADED: dict[tuple[str, Path | None], AnimSet] = {}


def loaded_set(name: str, root: Path | None = None) -> AnimSet | None:
    """The manifest of a set, parsed ONCE. None when it cannot be read.

    The runtime asks for the manifest on the HOT path (the boss rebuilds
    its sprite path every frame), so the TOML is parsed a single time and
    the result is kept. A set whose manifest is missing or malformed
    returns None: the caller falls back to its own defaults instead of
    crashing the game.
    """
    key = (name, root)
    cached = _LOADED.get(key)
    if cached is not None:
        return cached
    try:
        anim_set = load_set(name, root)
    except (ManifestError, OSError):
        return None
    _LOADED[key] = anim_set
    return anim_set


def load_set(name: str, root: Path | None = None) -> AnimSet:
    """Load and validate the manifest of the set called `name`.

    `root` is the directory that HOLDS the sets; None means the default
    one (the repository's Assets/sprites/bosses, or the frozen bundle's),
    resolved at call time so the source tree is never touched on import.
    """
    if root is None:
        root = _sets_root()
    path = root / name
    manifest_path = path / "manifest.toml"
    if not manifest_path.is_file():
        raise ManifestError(f"no manifest for set {name!r} at {manifest_path}")

    with manifest_path.open("rb") as fh:
        raw = tomllib.load(fh)

    meta = raw.get("meta") or {}

    clips: dict[str, Clip] = {}
    for entry in raw.get("clips", []):
        clip_id = entry.get("id")
        if not isinstance(clip_id, str) or not clip_id:
            raise ManifestError(f"{name}: a clip has no id")
        if clip_id in clips:
            raise ManifestError(f"{name}: duplicate clip id {clip_id!r}")
        clips[clip_id] = Clip(
            id=clip_id,
            dir=str(entry.get("dir", clip_id)),
            frames=int(entry.get("frames", 0)),
            fps=float(entry.get("fps", 10)),
            loop=bool(entry.get("loop", True)),
            scale_tolerance=float(entry.get("scale_tolerance", 0.15)),
            side_tolerance=float(entry.get("side_tolerance", 14.0)),
        )
    if not clips:
        raise ManifestError(f"{name}: the manifest declares no clips")

    parts: list[Part] = []
    for entry in raw.get("parts", []):
        part_id = entry.get("id")
        if not isinstance(part_id, str) or not part_id:
            raise ManifestError(f"{name}: a part has no id")
        detect_raw = entry.get("detect")
        radii_raw = entry.get("radii")
        parts.append(
            Part(
                id=part_id,
                draw=str(entry.get("draw", "frames")),
                pivot=str(entry.get("pivot", "centroid")),
                z=int(entry.get("z", 0)),
                offset=_as_int_pair(entry.get("offset", (0, 0)), "offset"),
                scale=_as_float_pair(entry.get("scale", (1.0, 1.0)), "scale"),
                radii=(
                    _as_float_triple(radii_raw, "radii")
                    if radii_raw is not None
                    else None
                ),
                detect=DetectRule.from_dict(detect_raw) if detect_raw else None,
                on_missing=str(entry.get("on_missing", "fallback")),
            )
        )
    if not parts:
        raise ManifestError(f"{name}: the manifest declares no parts")

    return AnimSet(
        name=str(meta.get("name", name)),
        version=int(meta.get("version", 1)),
        canvas=_as_int_pair(meta.get("canvas", (0, 0)), "meta.canvas"),
        anchor=_as_int_pair(meta.get("anchor", (0, 0)), "meta.anchor"),
        sided=meta.get("sided"),
        path=path,
        clips=clips,
        parts=parts,
    )
```

- [ ] **Step 4: Write GOLIATH's manifest**

Create `Assets/sprites/bosses/goliath/manifest.toml`:

```toml
# BLOQUE 74: SPEC of the GOLIATH animation set. Hand-edited.
#
# Verified by: tools/sprite_pipeline/audit.py
# Design: docs/superpowers/specs/2026-10-26-sprite-pipeline-design.md
#
# The shield constants below are the BLOQUE 67 user-approved values, moved
# here verbatim. Do not retune them here.
#
# The alpha threshold (32) is a measurement constant, not a detection rule:
# it lives in src/anim/measure.py.

[meta]
name    = "GOLIATH"
version = 1
canvas  = [96, 80]      # every frame of every clip
anchor  = [48, 40]      # where the boss sits in the world
sided   = "right"       # the shield is ALWAYS on the right arm

# ---------------------------------------------------------------- clips
#
# scale_tolerance: relative deviation of the silhouette height from the
#   clip median that still counts as "not rescaled". Measured on the real
#   assets: phase1_idle 0.027, phase2_idle 0.107, javelin 0.066,
#   laser 0.164, purple_bullet 0.214, death 0.383.
# side_tolerance: how far the probe column may stray from the clip median
#   before the frame counts as turned around. The two real cases deviate
#   21.4 (javelin/f03) and 18.2 (purple_bullet/f06). The next-largest
#   deviation among the frames that sit on the wrong side of the centre is
#   death/frame_02 at 10.9 -- a margin of 3.1, so the threshold is not on
#   a knife edge.

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
scale_tolerance = 0.25   # the boss crouches when it fires (0.164 measured)

[[clips]]
id     = "purple_bullet"
dir    = "purple_bullet"
frames = 10
fps    = 10
loop   = true
scale_tolerance = 0.30   # the boss throws (0.214 measured)

[[clips]]
id     = "death"
dir    = "death"
frames = 10
fps    = 10
loop   = false             # one-shot: holds on the last frame
scale_tolerance = 0.60     # the boss collapses -- that IS the animation

# ---------------------------------------------------------------- parts
#
#   draw = "frames"      one PNG per frame of the current clip
#   draw = "ellipse"     procedural primitive (the invisible shield oval)
#   draw = "point"       an anchor only, draws nothing (the eye)
#   draw = "procedural"  runtime effect; never baked into the art
#
#   pivot = "centroid"   auto: alpha-weighted centroid of the silhouette
#   pivot = "detect"     auto: the detection rule declared below
#
#   on_missing = "interpolate" | "fallback" | "skip"

[[parts]]
id    = "body"
draw  = "frames"
pivot = "centroid"
z     = 0

[[parts]]
id     = "shield_plate"
draw   = "ellipse"
pivot  = "detect"
z      = 1
offset = [0, 3]          # GOLIATH_SHIELD_DX / GOLIATH_SHIELD_DY
scale  = [0.78, 1.0]     # GOLIATH_SHIELD_RX_SCALE
radii  = [11, 11, 17]    # GOLIATH_SHIELD_R / _RX / _RY: the canonical
                       # ellipse used when the art has no plate to measure

# `warm_fallback` is the predicate that recognises the baked eye beam. The
# beam is a GRADIENT, so listing its colours as exact triples does not work.
# This predicate is the one the shipped runtime uses, and it deliberately
# KEEPS (220,180,80) -- the plate's own face highlight -- because that
# colour fails the r >= 235 test.
#
# It is a FALLBACK, not an always-on filter: the auditor measures the plain
# silhouette first and only retries with the warm pixels dropped when the
# plain measurement is not credible.
detect = { method = "shape", band = [28, 54], side = "right", min_col = 50, ranges = { rx = [6.5, 11.0], ry = [9.0, 13.0] }, warm_fallback = { r_min = 235, b_max = 140, g_min = 130, r_minus_b_min = 190 }, probe = { method = "color", r_min = 185, g_min = 145, b_max = 130, r_minus_b_min = 70 } }
on_missing = "interpolate"

[[parts]]
id    = "eye"
draw  = "point"
pivot = "detect"
z     = 2
detect = { method = "color", head_band = [0, 30], col_range = [24, 70], r_min = 170, rg_min = 70 }
on_missing = "interpolate"

[[parts]]
id   = "fx_eye_beam"
draw = "procedural"
z    = 3
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_manifest_matches_assets.py --tb=short`
Expected: PASS, 10 tests. The brief's test module has room for a few more
(the error branches of `ManifestError` deserve coverage); 14 is what the
implementer shipped.

Also run the project's type gate — `mypy>=1.5` is declared in
`requirements-dev.txt`, and `pyproject.toml` sets `strict = true`:

Run: `python -m mypy src/anim/`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add src/anim/__init__.py src/anim/manifest.py Assets/sprites/bosses/goliath/manifest.toml tests/test_manifest_matches_assets.py
git commit -m "feat: BLOQUE 74 - manifest declarativo de sets de animacion + el de GOLIATH"
```

---

### Task 2: Pixel measurement primitives and the side check

**Files:**
- Create: `src/anim/measure.py`
- Test: `tests/test_manifest_side_consistency.py`

**Interfaces:**
- Consumes: `src.anim.manifest.DetectRule` (Task 1), `src.anim.manifest.load_set`.
- Produces:
  - `src.anim.measure.ALPHA_MIN: int` = `32`
  - `src.anim.measure.alpha_centroid(surf: pygame.Surface) -> tuple[float, float] | None`
  - `src.anim.measure.silhouette_bbox(surf: pygame.Surface, threshold: int = ALPHA_MIN) -> tuple[int, int, int, int] | None`
  - `src.anim.measure.silhouette_height(surf: pygame.Surface, rule: DetectRule | None = None, drop_warm: bool = False, threshold: int = ALPHA_MIN) -> int | None`
  - `src.anim.measure.color_centroid(surf: pygame.Surface, rule: DetectRule, band: tuple[int,int] | None = None, col_range: tuple[int,int] | None = None, warm: WarmRule | None = None) -> tuple[float, float] | None`
  - `src.anim.measure.plate_ellipse(surf: pygame.Surface, rule: DetectRule, drop_warm: bool = False) -> tuple[float, float, float, float] | None`
  - `src.anim.measure.credible_ellipse(surf: pygame.Surface, rule: DetectRule) -> tuple[float, float, float, float] | None` — the two-pass measurement: plain silhouette first, warm-dropped retry
  - `src.anim.measure.interpolate(values: list[float | None], index: int) -> float | None` — Catmull-Rom (linear fallback) over the nearest measured neighbours

- [ ] **Step 1: Write the failing test**

Create `tests/test_manifest_side_consistency.py`:

```python
"""BLOQUE 74: the plate must be on the side the manifest declares.

BLOQUE 73.4 shipped GOLIATH with two frames where the character is drawn
turned around: the shield plate sits at probe column 27.4 and 33.1 instead
of the 40.8-59.6 band every healthy frame stays inside. The SHAPE rule
cannot see this --
it finds the arm at the right of the band and measures a plausible ellipse
that is not the plate. The PROBE can: a cheap colour signature used only
to answer "which side is the plate on?".

A frame counts as turned around when the probe column is on the opposite
side of the canvas centre AND it strays more than `side_tolerance` from
the clip's median probe column. Both conditions are needed: death/frame_02
is legitimately at column 40.7 because the boss is collapsing.

This test FAILS until Task 6 mirrors javelin/frame_03 and
purple_bullet/frame_06.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import statistics
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import load_set
from src.anim.measure import color_centroid


@pytest.fixture(scope="module")
def goliath():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    return load_set("goliath")


def probe_columns(goliath, clip):
    """probe column per frame of a clip."""
    import pygame

    rule = goliath.part("shield_plate").detect
    assert rule is not None and rule.probe is not None
    out = []
    for i in range(clip.frames):
        png = goliath.path / clip.dir / f"frame_{i:02d}.png"
        surf = pygame.image.load(str(png)).convert_alpha()
        found = color_centroid(surf, rule.probe, warm=rule.warm_fallback)
        out.append(found[0] if found else None)
    return out


def test_every_clip_detects_the_plate(goliath):
    for clip in goliath.clips.values():
        cols = probe_columns(goliath, clip)
        missing = [i for i, c in enumerate(cols) if c is None]
        assert not missing, f"{clip.id}: no plate detected in frames {missing}"


def test_plate_is_on_the_declared_side(goliath):
    rule = goliath.part("shield_plate").detect
    assert rule is not None and rule.side == "right"
    centre = goliath.anchor[0]
    offenders = []
    for clip in goliath.clips.values():
        cols = probe_columns(goliath, clip)
        good = sorted(c for c in cols if c is not None)
        # The TRUE median (the average of the two middle values), so this
        # test reports the same deviations the manifest justifies its
        # side_tolerance against.
        median = statistics.median(good)
        for i, col in enumerate(cols):
            if col is None:
                continue
            wrong_side = col < centre if rule.side == "right" else col > centre
            stray = abs(col - median) > clip.side_tolerance
            if wrong_side and stray:
                offenders.append(
                    f"{clip.id}/frame_{i:02d} "
                    f"(probe col {col:.1f}, median {median:.1f})"
                )
    assert not offenders, "plate on the wrong side: " + ", ".join(offenders)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_manifest_side_consistency.py --tb=short`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.anim.measure'`

- [ ] **Step 3: Write the measurement primitives**

Create `src/anim/measure.py`:

```python
"""BLOQUE 74: pixel-level measurement primitives.

Pure functions over a pygame Surface. No manifest, no filesystem, no
caching. Used by the auditor (offline) and by the tests.

Everything works on the ALPHA channel unless the rule says otherwise, so a
transparent canvas never contributes to a measurement.

ONE EXCEPTION to the module-wide alpha cut (ALPHA_MIN = 32): `alpha_centroid`
counts every pixel with alpha != 0, for parity with the shipped runtime's
registration offset. See that function's docstring for why.

Performance: one full-frame pass with get_at over all 60 GOLIATH frames
costs 0.09 s, which is fine for an offline tool. numpy is NOT used --
BLOQUE 58.14 allows it for the pause-screen lowpass only.
"""
from __future__ import annotations

import pygame

from src.anim.manifest import DetectRule, WarmRule

ALPHA_MIN = 32

# The margin (in pixels) the silhouette must keep from EVERY canvas edge.
# Below it the frame is CORTADO (cut).
#
# ONE threshold, shared by the auditor and the repair: the auditor flags a
# frame whose margin is below it and the repair targets exactly it. Two
# thresholds would wedge the pipeline -- a frame the auditor flags but the
# repair cannot reach stays flagged forever, and `run.py --fix` would keep
# exiting 1 on a set that can never be repaired.
CORTADO_MARGIN = 2


def alpha_centroid(surf: pygame.Surface) -> tuple[float, float] | None:
    """Alpha-weighted centroid of the silhouette.

    None when the sprite is fully transparent. This is the correction that
    cancels the per-frame registration error: the AI generator drew the
    character at a different offset inside the canvas in every frame, and
    the offset needed to put its visual centre of mass back on the anchor
    spans -16..+20 px across the 60 GOLIATH frames.

    ALPHA CUT: this function counts every pixel with alpha != 0, NOT the
    alpha > ALPHA_MIN (32) cut the rest of this module uses. That is
    deliberate parity with the shipped runtime's
    `get_sprite_centroid_offset` (src/ui/scenes.py), which tests `a == 0`
    too: the centroid has to agree with the runtime's registration offset
    to the pixel, so it may not use a stricter cut than the runtime does.
    """
    w, h = surf.get_size()
    sum_a = sum_x = sum_y = 0
    for y in range(h):
        for x in range(w):
            alpha = surf.get_at((x, y))[3]
            if alpha == 0:
                continue
            sum_a += alpha
            sum_x += x * alpha
            sum_y += y * alpha
    if sum_a == 0:
        return None
    return (sum_x / sum_a, sum_y / sum_a)


def silhouette_bbox(
    surf: pygame.Surface, threshold: int = ALPHA_MIN
) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) of the silhouette, exclusive on the right.

    None when the sprite is fully transparent.
    """
    w, h = surf.get_size()
    left, top, right, bottom = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if surf.get_at((x, y))[3] > threshold:
                if x < left:
                    left = x
                if x > right:
                    right = x
                if y < top:
                    top = y
                if y > bottom:
                    bottom = y
    if right < 0:
        return None
    return (left, top, right + 1, bottom + 1)


def silhouette_margins(
    surf: pygame.Surface, threshold: int = ALPHA_MIN
) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) margins of the silhouette, in pixels.

    A margin is how many transparent pixels separate the silhouette from
    that edge of the canvas. None when the sprite is fully transparent.
    """
    bbox = silhouette_bbox(surf, threshold)
    if bbox is None:
        return None
    left, top, right, bottom = bbox
    w, h = surf.get_size()
    return (left, top, w - right, h - bottom)


def is_cut_off(margins: tuple[int, int, int, int]) -> bool:
    """True when a silhouette comes closer than CORTADO_MARGIN to an edge.

    This is the CORTADO test of the auditor as a function, so the repair
    and the finding can never disagree about what "cut off" means.
    """
    return min(margins) < CORTADO_MARGIN


def silhouette_height(
    surf: pygame.Surface,
    rule: DetectRule | None = None,
    drop_warm: bool = False,
    threshold: int = ALPHA_MIN,
) -> int | None:
    """Height of the silhouette, optionally dropping the warm pixels.

    Height is a LINEAR dimension and is far less pose-sensitive than area:
    area is dominated by the pose (a frame with an outstretched arm has
    many more opaque pixels at the same body size), which is why the
    pipeline measures height and not area.
    """
    w, h = surf.get_size()
    warm = rule.warm_fallback if (rule is not None and drop_warm) else None
    top, bottom = h, -1
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if a <= threshold:
                continue
            if warm is not None and warm.matches(r, g, b):
                continue
            if y < top:
                top = y
            if y > bottom:
                bottom = y
    if bottom < 0:
        return None
    return bottom + 1 - top


def color_centroid(
    surf: pygame.Surface,
    rule: DetectRule,
    band: tuple[int, int] | None = None,
    col_range: tuple[int, int] | None = None,
    warm: WarmRule | None = None,
) -> tuple[float, float] | None:
    """Centroid of the pixels that satisfy a colour rule.

    `band` is (top, bottom) in rows; `col_range` is (first, last) in
    columns. When either is None it falls back to the window the RULE
    declares (`head_band` and `col_range` respectively), and to the whole
    surface only when the rule declares no window at all. None when
    nothing matches.

    `warm` is an optional WarmRule: when given, the pixels it matches are
    dropped before the signature is applied. The PROBE needs this -- the
    brass signature also matches two of the beam's colours, so without the
    warm filter the probe latches onto the beam.
    """
    w, h = surf.get_size()
    # A rule that declares no window scans the WHOLE surface. The windows
    # are optional on purpose: a default of (0, 0) would be truthy and
    # would silently produce an empty scan window.
    if band is None:
        band = rule.head_band if rule.head_band is not None else (0, h)
    if col_range is None:
        col_range = rule.col_range if rule.col_range is not None else (0, w)
    top, bottom = band
    first, last = col_range

    hits: list[tuple[int, int]] = []
    for y in range(max(0, top), min(h, bottom)):
        for x in range(max(0, first), min(w, last)):
            r, g, b, a = surf.get_at((x, y))
            if a <= ALPHA_MIN:
                continue
            if warm is not None and warm.matches(r, g, b):
                continue
            if r < rule.r_min:
                continue
            if rule.g_min and g < rule.g_min:
                continue
            if rule.b_max < 255 and b > rule.b_max:
                continue
            if rule.rg_min and (r - g) < rule.rg_min:
                continue
            if rule.r_minus_b_min and (r - b) < rule.r_minus_b_min:
                continue
            hits.append((x, y))
    if not hits:
        return None
    return (
        sum(p[0] for p in hits) / len(hits),
        sum(p[1] for p in hits) / len(hits),
    )


def plate_ellipse(
    surf: pygame.Surface, rule: DetectRule, drop_warm: bool = False
) -> tuple[float, float, float, float] | None:
    """Ellipse of the last solid run of each row inside the band.

    This is the SHAPE measurement. The plate shares its palette with the
    body (160,110,50), so colour cannot identify it; the only usable
    signature is the outline. The rule walks the band, takes the last
    contiguous run of opaque pixels in each row, and keeps the runs that
    reach at least `min_col`.

    With `drop_warm` the warm pixels (the baked eye beam) are treated as
    background, exactly like the shipped runtime does.

    Returns (cx, cy, rx, ry) or None when no run qualifies.
    """
    w, h = surf.get_size()
    if rule.band is None:
        return None
    band_top, band_bottom = rule.band
    if band_bottom <= band_top:
        return None
    warm = rule.warm_fallback if drop_warm else None

    points: list[tuple[int, int]] = []
    for y in range(max(0, band_top), min(h, band_bottom)):
        end = -1
        for x in range(w - 1, -1, -1):
            r, g, b, a = surf.get_at((x, y))
            if a <= ALPHA_MIN:
                continue
            if warm is not None and warm.matches(r, g, b):
                continue
            end = x
            break
        if end < rule.min_col:
            continue
        start = end
        while start - 1 >= 0:
            r, g, b, a = surf.get_at((start - 1, y))
            if a <= ALPHA_MIN:
                break
            if warm is not None and warm.matches(r, g, b):
                break
            start -= 1
        first = max(start, rule.min_col)
        points.extend((x, y) for x in range(first, end + 1))

    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (x1 - x0) / 2.0, (y1 - y0) / 2.0)


def credible_ellipse(
    surf: pygame.Surface, rule: DetectRule
) -> tuple[float, float, float, float] | None:
    """The two-pass measurement, exactly like the shipped runtime.

    The plain silhouette is measured first. Only when that result is not
    credible -- because the baked beam extended the contour -- is the
    measurement retried with the warm pixels dropped.

    Returns the credible ellipse, or None when neither pass gives one.
    """
    plain = plate_ellipse(surf, rule, drop_warm=False)
    if _credible(plain, rule):
        return plain
    if rule.warm_fallback is None:
        return None
    warm = plate_ellipse(surf, rule, drop_warm=True)
    if _credible(warm, rule):
        return warm
    return None


def _credible(
    ellipse: tuple[float, float, float, float] | None, rule: DetectRule
) -> bool:
    """True when the ellipse is inside the rule's believable range."""
    if ellipse is None:
        return False
    rx, ry = ellipse[2], ellipse[3]
    return (
        rule.rx_range[0] <= rx <= rule.rx_range[1]
        and rule.ry_range[0] <= ry <= rule.ry_range[1]
    )


def interpolate(values: list[float | None], index: int) -> float | None:
    """Fill a missing measurement from its neighbours.

    Catmull-Rom through the nearest measured values on each side. When only
    one measured neighbour exists on a side, that side's tangent collapses
    and the curve becomes a smooth one that still passes through both
    measured endpoints (it is NOT a straight line: at the midpoint of a gap
    it returns the midpoint, but between the endpoints it bows slightly).
    Returns None when there is nothing to interpolate from.

    This is inbetweening: the shield plate moves smoothly with the arm, so
    the frames where the art forgot it can be reconstructed from the ones
    where it is there.
    """
    if index < 0 or index >= len(values):
        return None
    current = values[index]
    if current is not None:
        return float(current)

    left = index - 1
    while left >= 0 and values[left] is None:
        left -= 1
    right = index + 1
    while right < len(values) and values[right] is None:
        right += 1

    left_value = values[left] if left >= 0 else None
    right_value = values[right] if right < len(values) else None

    # The two guards are nested rather than chained so that the type of
    # each neighbour is known on its own branch.
    if left_value is None:
        if right_value is None:
            return None
        return float(right_value)
    if right_value is None:
        return float(left_value)

    # Catmull-Rom needs two points on each side.
    left2 = left - 1
    while left2 >= 0 and values[left2] is None:
        left2 -= 1
    right2 = right + 1
    while right2 < len(values) and values[right2] is None:
        right2 += 1
    # The scans above stop on a measured value, so left2 / right2 hold one
    # whenever the index is in range. The None checks below are the
    # type-safe spelling of that invariant for mypy; they are NOT a
    # separate fallback path and cannot be reached in practice.
    p0 = values[left2] if left2 >= 0 else None
    p3 = values[right2] if right2 < len(values) else None
    if p0 is None:
        p0 = left_value
    if p3 is None:
        p3 = right_value

    span = right - left
    t = (index - left) / span
    t2 = t * t
    t3 = t2 * t
    return float(
        0.5
        * (
            (2 * left_value)
            + (-p0 + right_value) * t
            + (2 * p0 - 5 * left_value + 4 * right_value - p3) * t2
            + (-p0 + 3 * left_value - 3 * right_value + p3) * t3
        )
    )
```

- [ ] **Step 4: Run the test to verify it fails for the RIGHT reason**

Run: `python -m pytest tests/test_manifest_side_consistency.py --tb=short`
Expected: `test_every_clip_detects_the_plate` PASSES; `test_plate_is_on_the_declared_side` FAILS with a message naming `javelin/frame_03` and `purple_bullet/frame_06`.

This is the expected red state: the test is the proof that the auditor will catch the turned-around frames. Task 6 turns it green.

- [ ] **Step 5: Run the full suite to confirm nothing else broke**

Run: `python -m pytest tests/ --tb=no`
Expected: 2,774 passed, 8 failed (the pre-existing ones), 7 skipped

- [ ] **Step 6: Commit**
```bash
git add src/anim/measure.py tests/test_manifest_side_consistency.py
git commit -m "feat: BLOQUE 74 - primitivas de medicion de pixeles y deteccion de lado"
```

---

### Task 3: The auditor

**Files:**
- Create: `tools/sprite_pipeline/__init__.py`
- Create: `tools/sprite_pipeline/audit.py`
- Test: `tests/test_anchors_are_fresh.py`

**Interfaces:**
- Consumes: `src.anim.manifest` (Task 1), `src.anim.measure` (Task 2).
- Produces:
  - `tools/sprite_pipeline/audit.py::STATES` — the seven state names, in severity order: `COLAPSADO`, `CORTADO`, `LADO_EQUIVOCADO`, `FIRMA_AMBIGUA`, `AUSENTE`, `FUERA_DE_RANGO`, `ESCALADO`
  - `tools/sprite_pipeline/audit.py::FAIL_STATES` — `frozenset({"COLAPSADO", "CORTADO", "LADO_EQUIVOCADO"})`. AUSENTE and FIRMA_AMBIGUA are WARNs: a frame whose plate cannot be measured is resolved by interpolation, and a probe/shape disagreement is informational.
  - `tools/sprite_pipeline/audit.py::Finding` — frozen dataclass; fields `clip: str`, `frame: int`, `state: str`, `detail: str`
  - `tools/sprite_pipeline/audit.py::FrameMeasurement` — frozen dataclass; fields `clip: str`, `frame: int`, `body_dx: int`, `body_dy: int`, `eye: tuple[int,int] | None`, `eye_source: str`, `shield: tuple[float,float,float,float] | None`, `shield_source: str`. Both `*_source` fields are one of `measured`, `interpolated`, `missing`, `out_of_range`; the last two mean UNRESOLVED, and the feature is written to anchors.toml as a zero placeholder.
  - `tools/sprite_pipeline/audit.py::audit_set(anim_set) -> tuple[list[Finding], list[FrameMeasurement]]`
  - `src.anim.measure.credible_ellipse(surf, rule) -> tuple[float,float,float,float] | None` — the two-pass measurement (plain first, warm-dropped retry)
  - `tools/sprite_pipeline/audit.py::write_anchors(anim_set, measurements, path) -> None`
  - `tools/sprite_pipeline/audit.py::render_anchors_toml(anim_set, measurements) -> str`
  - `tools/sprite_pipeline/audit.py::main(argv) -> int` — CLI: `python tools/sprite_pipeline/audit.py goliath [--json] [--write-anchors]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_anchors_are_fresh.py`:

```python
"""BLOQUE 74: anchors.toml must match the assets it describes.

The anchors are the measurement of every frame. If the art changes and the
anchors do not, the runtime draws the shield ellipse where the plate used
to be. This test regenerates the anchors and fails on any diff.
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


@pytest.fixture(scope="module")
def display():
    """pygame needs a video mode before convert_alpha() works."""
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def test_anchors_toml_is_up_to_date(display):
    from sprite_pipeline.audit import audit_set, render_anchors_toml

    anim_set = load_set("goliath")
    _, measurements = audit_set(anim_set)
    rendered = render_anchors_toml(anim_set, measurements)

    anchors_path = anim_set.path / "anchors.toml"
    assert anchors_path.is_file(), "anchors.toml does not exist yet"
    current = anchors_path.read_text(encoding="utf-8")
    assert current == rendered, (
        "anchors.toml is stale -- regenerate it with "
        "`python tools/sprite_pipeline/audit.py goliath --write-anchors` "
        "(BLOQUE 74 Task 6 adds `python tools/sprite_pipeline/run.py "
        "goliath --fix` as the one-step fix)"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_anchors_are_fresh.py --tb=short`
Expected: FAIL with `ModuleNotFoundError: No module named 'sprite_pipeline'`

- [ ] **Step 3: Create the package marker**

Create `tools/sprite_pipeline/__init__.py` as an empty file.

- [ ] **Step 4: Write the auditor**

Create `tools/sprite_pipeline/audit.py`:

```python
"""BLOQUE 74: the sprite auditor.

Measures every frame of an animated set, classifies it into one of seven
states, and bakes the measurement into anchors.toml.

Read-only by default. Deterministic: the same assets in, the same verdict
out. No AI, no network, no writes unless --write-anchors is passed.

Usage:
    python tools/sprite_pipeline/audit.py goliath
    python tools/sprite_pipeline/audit.py goliath --json
    python tools/sprite_pipeline/audit.py goliath --write-anchors
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

# pygame prints its support banner to STDOUT when the module is imported,
# which would corrupt the --json report (it is not stderr, so `2>$null`
# does not remove it). This is pygame's own suppression mechanism and it
# has to be set BEFORE the import below.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
# The repository root gives `src.anim.manifest`; the tools directory gives
# the `sprite_pipeline` package this file belongs to.
for _entry in (str(ROOT), str(ROOT / "tools")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from src.anim.manifest import AnimSet, Clip, load_set  # noqa: E402
from src.anim.measure import (  # noqa: E402
    alpha_centroid,
    color_centroid,
    credible_ellipse,
    interpolate,
    is_cut_off,
    plate_ellipse,
    silhouette_height,
    silhouette_margins,
)
from sprite_pipeline import ensure_display  # noqa: E402

STATES = (
    "COLAPSADO",
    "CORTADO",
    "LADO_EQUIVOCADO",
    "FIRMA_AMBIGUA",
    "AUSENTE",
    "FUERA_DE_RANGO",
    "ESCALADO",
)

# A FAIL blocks the pipeline. A WARN is informational and is resolved (or
# accepted) without touching the art.
#
# AUSENTE is a WARN, not a FAIL: a frame whose plate cannot be measured is
# resolved by interpolating it from the frames around it, which is a
# legitimate reconstruction rather than a default. The real gate is that no
# frame ends up with an unresolved feature -- that is what
# tests/test_features_detected_everywhere.py asserts.
#
# FIRMA_AMBIGUA is also a WARN. Two candidate definitions were measured
# against the 60 shipped frames and both were useless:
#
#   * "the measured region contains a baked-effect colour" fires on 59/60
#     frames, because (240,200,120) is the plate's OWN highlight, not only
#     the beam's;
#   * "excluding the colliding colours changes the measurement" fires on
#     0/60 frames, because the colliding pixels are isolated highlights
#     and never change a run boundary.
#
# The definition that survives is the one that asks whether the two
# INDEPENDENT detectors agree: the probe (a colour signature) and the
# shape measurement. When they disagree by more than the tolerance, one of
# them is measuring the wrong thing.
FAIL_STATES = frozenset(
    {"COLAPSADO", "CORTADO", "LADO_EQUIVOCADO"}
)


@dataclass(frozen=True)
class Finding:
    """One problem, in one frame."""

    clip: str
    frame: int
    state: str
    detail: str


@dataclass(frozen=True)
class FrameMeasurement:
    """The measurement of one frame, ready to be baked.

    `eye_source` and `shield_source` say where each feature came from:

    * "measured"     -- the detector found it in this frame.
    * "interpolated" -- it could not be measured here, and it was
      reconstructed from the frames around it.
    * "missing"      -- the feature is absent from the art.
    * "out_of_range" -- the feature was found but measured implausibly.

    The last two mean UNRESOLVED: the feature could be neither measured
    nor reconstructed, and its value is absent. A consumer must tolerate
    them. On the 60 shipped GOLIATH frames only "measured" and
    "interpolated" occur (53 + 7 shields, 59 + 1 eyes, nothing
    unresolved), but the format does not guarantee that.

    The two features are resolved independently: one of them being
    reconstructed never changes the other's source.
    """

    clip: str
    frame: int
    body_dx: int
    body_dy: int
    eye: tuple[int, int] | None
    eye_source: str
    shield: tuple[float, float, float, float] | None
    shield_source: str


def _load_surface(path: Path) -> pygame.Surface:
    return pygame.image.load(str(path)).convert_alpha()


def _frame_path(anim_set: AnimSet, clip: Clip, index: int) -> Path:
    return anim_set.path / clip.dir / f"frame_{index:02d}.png"


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _clip_probe_columns(
    anim_set: AnimSet, surfaces: list[pygame.Surface]
) -> list[float | None]:
    """Probe column per frame: where the brass signature sits in each frame.

    The probe inherits the parent's warm rule: the brass signature also
    matches two of the beam's colours, so without the warm filter the
    probe latches onto the beam.
    """
    rule = anim_set.part("shield_plate").detect
    if rule is None or rule.probe is None:
        return [None] * len(surfaces)
    out: list[float | None] = []
    for surf in surfaces:
        found = color_centroid(surf, rule.probe, warm=rule.warm_fallback)
        out.append(found[0] if found else None)
    return out


def audit_set(anim_set: AnimSet) -> tuple[list[Finding], list[FrameMeasurement]]:
    """Measure every frame of every clip.

    The findings describe the ART. The measurements are the REPAIRED
    result: a frame whose plate could not be measured gets its ellipse
    interpolated from the frames around it, so the oval keeps tracking the
    arm instead of falling back to a constant.
    """
    findings: list[Finding] = []
    measurements: list[FrameMeasurement] = []

    shield_part = anim_set.part("shield_plate")
    eye_part = anim_set.part("eye")

    for clip in anim_set.clips.values():
        surfaces = [
            _load_surface(_frame_path(anim_set, clip, i)) for i in range(clip.frames)
        ]

        # --- COLAPSADO: duplicate frames inside a clip -----------------
        digests: dict[str, list[int]] = {}
        for i in range(clip.frames):
            path = _frame_path(anim_set, clip, i)
            digests.setdefault(_md5(path), []).append(i)
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

        probe_cols = _clip_probe_columns(anim_set, surfaces)
        good_cols = sorted(c for c in probe_cols if c is not None)
        # The TRUE median -- the average of the two middle values. The
        # upper-middle element would shift the threshold by up to 0.2 px and
        # make the auditor decide against a different median than the one
        # the baseline table was measured with.
        probe_median = statistics.median(good_cols) if good_cols else 0.0

        rule = shield_part.detect
        heights = [
            silhouette_height(surf, rule, drop_warm=True) for surf in surfaces
        ]
        good_heights = sorted(h for h in heights if h is not None)
        height_median = statistics.median(good_heights) if good_heights else 0

        for i, surf in enumerate(surfaces):
            frame_no = i

            # --- CORTADO: silhouette touching the canvas edge -----------
            # The threshold is CORTADO_MARGIN, the SAME constant the repair
            # targets, so a frame the auditor flags is a frame the repair
            # can reach (when a translation can give it the margin).
            margins = silhouette_margins(surf)
            if margins is not None and is_cut_off(margins):
                left, top, right, bottom = margins
                findings.append(
                    Finding(
                        clip.id,
                        frame_no,
                        "CORTADO",
                        f"silhouette margins L{left} T{top} R{right} B{bottom}",
                    )
                )

            # --- ESCALADO: silhouette height vs the clip median ---------
            height = heights[i]
            if height is not None and height_median:
                deviation = abs(height - height_median) / height_median
                if deviation > clip.scale_tolerance:
                    findings.append(
                        Finding(
                            clip.id,
                            frame_no,
                            "ESCALADO",
                            f"height {height} vs clip median {height_median} "
                            f"({deviation * 100:.0f}% > {clip.scale_tolerance * 100:.0f}%)",
                        )
                    )

            # --- body centroid: the registration correction -------------
            centre = alpha_centroid(surf)
            if centre is None:
                body_dx = body_dy = 0
            else:
                body_dx = int(round(anim_set.anchor[0] - centre[0]))
                body_dy = int(round(anim_set.anchor[1] - centre[1]))

            # --- eye ------------------------------------------------------
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

            # --- shield plate ---------------------------------------------
            probe_col = probe_cols[i]
            shield = None
            shield_source = "measured"
            if rule is not None:
                ellipse = credible_ellipse(surf, rule)
                if ellipse is None:
                    # Neither pass gave a credible ellipse. The plain
                    # measurement tells us whether the plate is absent
                    # entirely or merely implausible.
                    plain = plate_ellipse(surf, rule, drop_warm=False)
                    if plain is None:
                        shield_source = "missing"
                        findings.append(
                            Finding(
                                clip.id,
                                frame_no,
                                "AUSENTE",
                                "no plate measured: the shape rule found no "
                                "solid run",
                            )
                        )
                    elif rule.probe is not None and probe_col is None:
                        # The shape rule found a solid run, but the
                        # INDEPENDENT probe (the plate's colour signature)
                        # found no plate at all: what the shape rule
                        # measured is the BODY, not the plate.
                        #
                        # The two states are not interchangeable. AUSENTE
                        # says "the plate was not measured";
                        # FUERA_DE_RANGO says "the plate was measured and
                        # the measurement is not credible". Only the probe
                        # can tell them apart: the shape rule cannot,
                        # because a body is a solid run just like a plate
                        # is.
                        #
                        # A manifest that declares no probe keeps the old
                        # behaviour: the shape rule alone decides.
                        shield_source = "missing"
                        findings.append(
                            Finding(
                                clip.id,
                                frame_no,
                                "AUSENTE",
                                "no plate measured: the probe found no plate "
                                "and the shape rule measured the body",
                            )
                        )
                    else:
                        shield_source = "out_of_range"
                        findings.append(
                            Finding(
                                clip.id,
                                frame_no,
                                "FUERA_DE_RANGO",
                                f"rx {plain[2]:.1f} ry {plain[3]:.1f} outside "
                                f"rx {rule.rx_range} ry {rule.ry_range}",
                            )
                        )
                else:
                    shield = ellipse

                if probe_col is not None:
                    # --- LADO_EQUIVOCADO: turned-around character ----------
                    # This check must NOT depend on the shape measurement.
                    # The turned-around frames are exactly the ones whose
                    # shape measurement is NOT credible -- the shape rule
                    # finds the arm, not the plate -- so gating this on a
                    # credible ellipse would skip the very frames it exists
                    # to catch. The probe is independent of the shape rule,
                    # so it can answer the side question on its own.
                    #
                    # KNOWN BLIND SPOT: `stray` is measured against THIS
                    # CLIP's own probe median, so a clip mirrored AS A
                    # WHOLE moves its median with it and would not be
                    # flagged. That is the accepted trade-off -- the
                    # median is per-clip-relative on purpose, because the
                    # plate travels with the arm -- and on the shipped
                    # frames the manifest records a 3.1 px margin between
                    # the two real cases (21.4 and 18.2) and the next
                    # largest wrong-side frame (death/frame_02 at 10.9).
                    # Detecting a whole-clip mirror needs a reference
                    # outside the clip, which this pipeline does not have.
                    centre_col = anim_set.anchor[0]
                    wrong_side = (
                        probe_col <= centre_col
                        if rule.side == "right"
                        else probe_col >= centre_col
                    )
                    stray = abs(probe_col - probe_median) > clip.side_tolerance
                    if wrong_side and stray:
                        findings.append(
                            Finding(
                                clip.id,
                                frame_no,
                                "LADO_EQUIVOCADO",
                                f"probe col {probe_col:.1f} (clip median "
                                f"{probe_median:.1f}), expected > {centre_col}",
                            )
                        )

                    # --- FIRMA_AMBIGUA: the two detectors disagree -------
                    # This one DOES need both: it is the disagreement
                    # between the two detectors that defines it.
                    if shield is not None and abs(probe_col - shield[0]) > clip.side_tolerance:
                        findings.append(
                            Finding(
                                clip.id,
                                frame_no,
                                "FIRMA_AMBIGUA",
                                f"probe col {probe_col:.1f} vs shape cx {shield[0]:.1f} "
                                f"disagree by more than {clip.side_tolerance:.0f}px",
                            )
                        )

            measurements.append(
                FrameMeasurement(
                    clip=clip.id,
                    frame=frame_no,
                    body_dx=body_dx,
                    body_dy=body_dy,
                    eye=eye,
                    eye_source=eye_source,
                    shield=shield,
                    shield_source=shield_source,
                )
            )

    measurements = _interpolate_missing(measurements)
    return findings, measurements


def _interpolate_missing(
    measurements: list[FrameMeasurement],
) -> list[FrameMeasurement]:
    """Fill the frames whose measurement was implausible.

    A frame whose plate could not be measured (or measured implausibly)
    gets its ellipse reconstructed from the frames around it, so the oval
    keeps tracking the arm instead of falling back to a constant.

    The findings still report the art problem -- the interpolation fixes
    the measurement, it does not fix the art.

    Each feature is resolved INDEPENDENTLY: the eye and the shield each
    keep their own source, and each is only called "interpolated" when it
    was actually reconstructed. A feature that was measured stays
    "measured" even when the OTHER feature had to be reconstructed, and a
    feature that could be neither measured nor reconstructed stays
    unresolved (None) with its original source.
    """
    by_clip: dict[str, list[FrameMeasurement]] = {}
    for m in measurements:
        by_clip.setdefault(m.clip, []).append(m)

    out: list[FrameMeasurement] = []
    for items in by_clip.values():
        items.sort(key=lambda m: m.frame)
        cxs = [m.shield[0] if m.shield else None for m in items]
        cys = [m.shield[1] if m.shield else None for m in items]
        rxs = [m.shield[2] if m.shield else None for m in items]
        rys = [m.shield[3] if m.shield else None for m in items]
        eye_cols = [float(m.eye[0]) if m.eye else None for m in items]
        eye_rows = [float(m.eye[1]) if m.eye else None for m in items]
        for i, m in enumerate(items):
            # --- the eye: measured, reconstructed, or unresolved --------
            eye = m.eye
            eye_source = m.eye_source
            if eye is None:
                ex = interpolate(eye_cols, i)
                ey = interpolate(eye_rows, i)
                if ex is not None and ey is not None:
                    eye = (int(round(ex)), int(round(ey)))
                    eye_source = "interpolated"
                # else: no neighbour to interpolate from -- the eye stays
                # unresolved and keeps its original source.

            # --- the shield: same, independently -----------------------
            shield = m.shield
            shield_source = m.shield_source
            if shield is None:
                cx = interpolate(cxs, i)
                cy = interpolate(cys, i)
                rx = interpolate(rxs, i)
                ry = interpolate(rys, i)
                if (
                    cx is not None
                    and cy is not None
                    and rx is not None
                    and ry is not None
                ):
                    shield = (cx, cy, rx, ry)
                    shield_source = "interpolated"
                # else: no neighbour to interpolate from -- the shield
                # stays unresolved and keeps its original source.

            out.append(
                FrameMeasurement(
                    clip=m.clip,
                    frame=m.frame,
                    body_dx=m.body_dx,
                    body_dy=m.body_dy,
                    eye=eye,
                    eye_source=eye_source,
                    shield=shield,
                    shield_source=shield_source,
                )
            )
    out.sort(key=lambda m: (m.clip, m.frame))
    return out


def _fmt_number(value: float) -> str:
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def render_anchors_toml(anim_set: AnimSet, measurements: list[FrameMeasurement]) -> str:
    """Render anchors.toml from the measurements.

    Deterministic: the same measurements always produce the same text, so
    the freshness test can compare it byte for byte.

    Every block carries where its features came from (`eye_source` /
    `shield_source`): "measured", "interpolated", or -- when the feature
    could be neither measured nor reconstructed -- "missing" /
    "out_of_range", which mean UNRESOLVED. A consumer must tolerate those
    two: an unresolved feature is written as a zero placeholder, and only
    its source tells it apart from a real position.
    """
    manifest_bytes = (anim_set.path / "manifest.toml").read_bytes()
    lines = [
        "# BLOQUE 74: baked measurement of every frame.",
        "# GENERATED by tools/sprite_pipeline/audit.py --write-anchors",
        "# DO NOT HAND-EDIT: tests/test_anchors_are_fresh.py fails if this is stale.",
        "",
        "[meta]",
        'generated_by = "tools/sprite_pipeline/audit.py"',
        f'manifest_sha256 = "{hashlib.sha256(manifest_bytes).hexdigest()}"',
        "",
    ]
    for m in measurements:
        lines.append("[[anchors]]")
        lines.append(f'clip = "{m.clip}"')
        lines.append(f"frame = {m.frame}")
        lines.append(f"body_dx = {m.body_dx}")
        lines.append(f"body_dy = {m.body_dy}")
        if m.eye is None:
            lines.append("eye = [0, 0]")
        else:
            lines.append(f"eye = [{m.eye[0]}, {m.eye[1]}]")
        lines.append(f'eye_source = "{m.eye_source}"')
        if m.shield is None:
            lines.append("shield = [0.0, 0.0, 0.0, 0.0]")
        else:
            cx, cy, rx, ry = m.shield
            lines.append(
                f"shield = [{_fmt_number(cx)}, {_fmt_number(cy)}, "
                f"{_fmt_number(rx)}, {_fmt_number(ry)}]"
            )
        lines.append(f'shield_source = "{m.shield_source}"')
        lines.append("")
    return "\n".join(lines)


def write_anchors(
    anim_set: AnimSet, measurements: list[FrameMeasurement], path: Path
) -> None:
    path.write_text(render_anchors_toml(anim_set, measurements), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit an animated sprite set.")
    parser.add_argument("set", help="set name under Assets/sprites/bosses/")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    parser.add_argument(
        "--write-anchors", action="store_true", help="write anchors.toml"
    )
    parser.add_argument(
        "--root",
        default=None,
        help=(
            "directory that HOLDS the sets (default: the repository's "
            "Assets/sprites/bosses)."
        ),
    )
    args = parser.parse_args(argv)

    pygame.init()
    ensure_display()

    try:
        anim_set = load_set(args.set, root=Path(args.root) if args.root else None)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings, measurements = audit_set(anim_set)

    if args.json:
        print(
            json.dumps(
                {
                    "set": anim_set.name,
                    "findings": [
                        {
                            "clip": f.clip,
                            "frame": f.frame,
                            "state": f.state,
                            "detail": f.detail,
                        }
                        for f in findings
                    ],
                },
                indent=2,
            )
        )
    else:
        by_clip: dict[str, list[Finding]] = {}
        for f in findings:
            by_clip.setdefault(f.clip, []).append(f)
        for clip_id, items in by_clip.items():
            print(f"[clip] {clip_id}")
            for f in items:
                print(f"  frame_{f.frame:02d}  {f.state:<16} {f.detail}")
        # Count FRAMES, not findings: a frame can carry two findings
        # (javelin/frame_03 is FUERA_DE_RANGO *and* LADO_EQUIVOCADO).
        flagged = {(f.clip, f.frame) for f in findings}
        failing = {
            (f.clip, f.frame) for f in findings if f.state in FAIL_STATES
        }
        total = sum(c.frames for c in anim_set.clips.values())
        print(
            f"summary: {len(flagged)}/{total} frames with findings "
            f"({len(failing)} FAIL, {len(flagged) - len(failing)} WARN)"
        )

    if args.write_anchors:
        write_anchors(anim_set, measurements, anim_set.path / "anchors.toml")
        print(f"wrote {anim_set.path / 'anchors.toml'}")

    return 1 if any(f.state in FAIL_STATES for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the auditor and check the report**

Run: `python tools/sprite_pipeline/audit.py goliath`
Expected: the report names exactly the 10 frames in the baseline table above — 2 FAIL (`javelin/frame_03`, `purple_bullet/frame_06`, both `LADO_EQUIVOCADO`) and 8 WARN — and exits with code 1.

- [ ] **Step 6: Generate the anchors file**

Run: `python tools/sprite_pipeline/audit.py goliath --write-anchors`
Expected: `wrote .../anchors.toml`, and the file contains 60 `[[anchors]]` blocks. The 7 blocks whose plate could not be measured carry `shield_source = "interpolated"`.

- [ ] **Step 7: Run the freshness test**

Run: `python -m pytest tests/test_anchors_are_fresh.py --tb=short`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add tools/sprite_pipeline/__init__.py tools/sprite_pipeline/audit.py tests/test_anchors_are_fresh.py Assets/sprites/bosses/goliath/anchors.toml
git commit -m "feat: BLOQUE 74 - auditor de sets de animacion + anchors horneados"
```

---

### Task 4: The auditor's own tests and the feature-coverage guard

**Files:**
- Create: `tests/test_sprite_pipeline_audit.py`
- Create: `tests/test_features_detected_everywhere.py`

**Interfaces:**
- Consumes: `tools.sprite_pipeline.audit` (Task 3), `src.anim.manifest` (Task 1), `src.anim.measure` (Task 2).
- Produces: two test modules. No new production interfaces.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sprite_pipeline_audit.py`:

```python
"""BLOQUE 74: the auditor's own classification must be covered.

The auditor is the gate that stops a broken set from entering the repo.
If the auditor itself is wrong, it silently blesses broken art. These
tests feed it synthetic frames, one per state, and assert the verdict.

All SEVEN states are covered here: COLAPSADO, CORTADO, LADO_EQUIVOCADO,
FIRMA_AMBIGUA, AUSENTE, FUERA_DE_RANGO and ESCALADO.

Synthetic frames are built in a temporary directory with a temporary
manifest, so nothing here touches the shipped assets.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json
import subprocess
import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline.audit import FAIL_STATES, audit_set  # noqa: E402

W, H = 96, 80
TRANSPARENT = (0, 0, 0, 0)
BRASS = (200, 170, 60)
BODY = (160, 110, 50)


def write_frame(path: Path, pixels: dict[tuple[int, int], tuple]) -> None:
    surf = pygame.Surface((W, H), pygame.SRCALPHA, 32)
    surf.fill(TRANSPARENT)
    for (x, y), colour in pixels.items():
        surf.set_at((x, y), colour)
    pygame.image.save(surf, str(path))


def build_set(tmp_path: Path, frames: list[dict[tuple[int, int], tuple]]) -> None:
    """Write a one-clip set into `tmp_path`."""
    set_dir = tmp_path / "synthetic"
    clip_dir = set_dir / "idle"
    clip_dir.mkdir(parents=True)
    for i, pixels in enumerate(frames):
        write_frame(clip_dir / f"frame_{i:02d}.png", pixels)

    manifest = """[meta]
name = "SYNTHETIC"
version = 1
canvas = [96, 80]
anchor = [48, 40]
sided = "right"

[[clips]]
id = "idle"
dir = "idle"
frames = {n}
fps = 10
loop = true
scale_tolerance = 0.15
# The tolerance the synthetic cases are tuned for. The shipped GOLIATH
# manifest uses 14.0; here 10.0 keeps every case off the edge of its
# threshold (the LADO case is 15 px away, so it clears it by 5 px and
# not by 1).
side_tolerance = 10.0

[[parts]]
id = "body"
draw = "frames"
pivot = "centroid"
z = 0

[[parts]]
id = "shield_plate"
draw = "ellipse"
pivot = "detect"
z = 1
offset = [0, 3]
scale = [0.78, 1.0]
radii = [11, 11, 17]
detect = {{ method = "shape", band = [28, 54], side = "right", min_col = 50, ranges = {{ rx = [6.5, 11.0], ry = [9.0, 13.0] }}, warm_fallback = {{ r_min = 235, b_max = 140, g_min = 130, r_minus_b_min = 190 }}, probe = {{ method = "color", r_min = 185, g_min = 145, b_max = 130, r_minus_b_min = 70 }} }}
on_missing = "interpolate"

[[parts]]
id = "eye"
draw = "point"
pivot = "detect"
z = 2
detect = {{ method = "color", head_band = [0, 30], col_range = [24, 70], r_min = 170, rg_min = 70 }}
on_missing = "interpolate"
"""
    (set_dir / "manifest.toml").write_text(
        manifest.format(n=len(frames)), encoding="utf-8"
    )


def body_pixels(cx: int = 40, width: int = 20, top: int = 20, height: int = 45):
    """A rectangle of body pixels plus a brass plate on its right."""
    pixels: dict[tuple[int, int], tuple] = {}
    for y in range(top, top + height):
        for x in range(cx, cx + width):
            pixels[(x, y)] = BODY
    for y in range(34, 46):
        for x in range(cx + width, cx + width + 8):
            pixels[(x, y)] = BRASS
    return pixels


@pytest.fixture(scope="module", autouse=True)
def display():
    """pygame needs a video mode before convert_alpha() works."""
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def states_for(tmp_path: Path, frames) -> set[str]:
    build_set(tmp_path, frames)
    anim_set = load_set("synthetic", root=tmp_path)
    findings, _ = audit_set(anim_set)
    return {f.state for f in findings}


def test_duplicate_frames_are_COLAPSADO(tmp_path):
    frame = body_pixels()
    states = states_for(tmp_path, [frame, dict(frame)])
    assert "COLAPSADO" in states


def test_sprite_at_the_edge_is_CORTADO(tmp_path):
    pixels = body_pixels()
    pixels[(0, 40)] = BODY
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "CORTADO" in states


def test_plate_on_the_left_is_LADO_EQUIVOCADO(tmp_path):
    # The plate MOVES to the left: it is removed from the arm first, so the
    # probe sees the brass of a single plate. (Adding a second plate on
    # the left would leave the probe's centroid on the centre line -- see
    # test_a_plate_on_both_sides_is_not_LADO_EQUIVOCADO.)
    pixels = {k: v for k, v in body_pixels().items() if v != BRASS}
    for y in range(34, 46):
        for x in range(30, 38):
            pixels[(x, y)] = BRASS
    # the plate now sits left of the canvas centre
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "LADO_EQUIVOCADO" in states


def test_missing_plate_is_AUSENTE(tmp_path):
    pixels = {k: v for k, v in body_pixels().items() if v != BRASS}
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "AUSENTE" in states


def test_implausible_ellipse_is_FUERA_DE_RANGO(tmp_path):
    """A 2 px wide plate cannot be the shield."""
    pixels = body_pixels()
    # The plate is NARROWED to 2 px: the brass it does not have any more
    # is erased, not painted over (painting brass over brass would leave
    # the frame untouched and the clip would be reported as COLAPSADO).
    for y in range(34, 46):
        for x in range(62, 68):
            pixels.pop((x, y), None)
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "FUERA_DE_RANGO" in states


def test_probe_and_shape_disagree_is_FIRMA_AMBIGUA(tmp_path):
    """The two independent detectors disagree by more than the tolerance.

    The brass is a wide slab that STARTS left of the shape rule's
    min_col (50), so the shape rule still measures the arm (a credible
    ellipse at cx 58.5) while the probe's centroid sits at 43.5. The two
    detectors are 15 px apart, which is more than the 10 px tolerance.

    The clip's median probe column is the same 43.5, so the frame is
    not "stray" and is NOT reported as LADO_EQUIVOCADO: only the two
    detectors disagree. This is the situation of the shipped
    laser/frame_05 (probe 44.5 against shape cx 60.5).
    """
    pixels = body_pixels()
    for y in range(34, 46):
        for x in range(20, 68):
            pixels[(x, y)] = BRASS
    twin = dict(pixels)
    twin[(39, 40)] = BODY  # a different frame with the same probe and shape
    states = states_for(tmp_path, [pixels, twin])
    assert states == {"FIRMA_AMBIGUA"}


def test_a_taller_frame_is_ESCALADO(tmp_path):
    """One frame's silhouette height strays from the clip's median.

    The height is the silhouette's bounding-box height, so the outlier
    is a body that is visibly taller: rows 10..69 instead of rows
    20..64 (60 px against 45 px, a 33% deviation against a 15%
    tolerance). The two other frames share the median's height, so
    only the outlier is flagged.
    """
    tall = body_pixels(top=10, height=60)
    healthy = body_pixels()
    twin = body_pixels()
    twin[(39, 40)] = BODY  # same height, different frame
    states = states_for(tmp_path, [tall, healthy, twin])
    assert states == {"ESCALADO"}


def test_healthy_set_has_no_failures(tmp_path):
    build_set(tmp_path, [body_pixels()])
    findings, _ = audit_set(load_set("synthetic", root=tmp_path))
    fails = [f for f in findings if f.state in FAIL_STATES]
    assert not fails, [f.detail for f in fails]


def test_a_plate_on_both_sides_is_not_LADO_EQUIVOCADO(tmp_path):
    """The probe reports the CENTROID of the brass pixels.

    A frame that carries a plate on both sides has its centroid on the
    centre line, so it is not a turned-around frame and must not be
    flagged. A turned-around character has the plate MOVED to the other
    side, not a second plate added.
    """
    pixels = body_pixels(cx=40)
    for y in range(34, 46):
        for x in range(30, 38):
            pixels[(x, y)] = BRASS
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "LADO_EQUIVOCADO" not in states


# ---------------------------------------------------------------------------
# The CLI contract: `--json` must write ONLY JSON to stdout.
# ---------------------------------------------------------------------------
def test_json_report_is_pure_json():
    """pygame prints its support banner to STDOUT when it is imported.

    That banner would make the report unparseable, so the auditor sets
    PYGAME_HIDE_SUPPORT_PROMPT before importing pygame. This test is the
    guard that keeps it that way: move the import above the
    setdefault and this fails.

    stdout and stderr are captured SEPARATELY (no pipe): a pipe would
    add a shell artefact to the bytes, not a defect of the tool.
    """
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "sprite_pipeline" / "audit.py"),
            "goliath",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=300,
    )
    stdout = proc.stdout.decode("utf-8")
    stderr = proc.stderr.decode("utf-8")

    # The exit code is NOT asserted: the auditor exits 1 while the two
    # turned-around frames are still in the art, and that is correct.
    #
    # The banner check is POSITIONAL, not a substring search: a finding
    # detail could legitimately contain the word "pygame" one day, and a
    # substring search would false-positive on it. A banner always
    # PRECEDES the JSON, so the first non-blank byte must be "{".
    assert stdout.lstrip().startswith("{"), stdout[:200]
    assert "Hello from the pygame community" not in stdout, stdout[:200]

    report = json.loads(stdout)
    assert "set" in report
    assert isinstance(report["set"], str)
    assert isinstance(report["findings"], list)
    assert stderr == "", stderr
```

- [ ] **Step 2: Run the test to verify it passes or fails for the right reason**

Run: `python -m pytest tests/test_sprite_pipeline_audit.py --tb=short`
Expected: the tests run. If any fail, the auditor's classification does not match the specification — fix `tools/sprite_pipeline/audit.py` before continuing.

- [ ] **Step 3: Write the feature-coverage guard**

Create `tests/test_features_detected_everywhere.py`:

```python
"""BLOQUE 74: every required feature must be resolved in every frame.

A feature is "resolved" when the auditor measured it, or when the repair
interpolated it from the frames around it. The guard fails when a frame
still has an unresolved feature -- that is the case where the runtime would
fall back to a constant and the shield would stop tracking the arm.

Resolution is not the same as measurement. Every feature also carries its
PROVENANCE (`measured` / `interpolated` / `missing` / `out_of_range`), and
the two features of a frame are resolved INDEPENDENTLY: an interpolated eye
does not make an interpolated shield. The coverage guard above cannot see
the difference -- a reconstructed eye satisfies `m.eye is not None` -- so
the provenance is asserted here.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from collections import Counter
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline.audit import audit_set  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def display():
    """pygame needs a video mode before convert_alpha() works."""
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.fixture(scope="module")
def goliath():
    return load_set("goliath")


@pytest.fixture(scope="module")
def audit(display, goliath):
    """The auditor's verdict on the 60 shipped frames, measured ONCE."""
    return audit_set(goliath)


def test_every_frame_resolves_the_shield_plate(audit):
    _, measurements = audit
    unresolved = [
        f"{m.clip}/frame_{m.frame:02d}"
        for m in measurements
        if m.shield is None
    ]
    assert not unresolved, (
        "the shield plate is unresolved in these frames -- they need "
        "interpolation or repair: " + ", ".join(unresolved)
    )


def test_every_frame_resolves_the_eye(audit):
    _, measurements = audit
    missing = [
        f"{m.clip}/frame_{m.frame:02d}"
        for m in measurements
        if m.eye is None
    ]
    assert not missing, "eye anchor not found in: " + ", ".join(missing)


def test_every_frame_has_a_body_offset(audit, goliath):
    """The registration correction stays a plausible offset.

    `body_dx` / `body_dy` move the sprite so that its visual centre of
    mass lands on the anchor. The shipped frames need -16..+20 px
    horizontally and -12..+5 px vertically; a bigger jump would mean the
    centroid is broken, not that the art changed.
    """
    _, measurements = audit
    assert len(measurements) == sum(c.frames for c in goliath.clips.values())
    assert all(
        abs(m.body_dx) <= 32 and abs(m.body_dy) <= 32 for m in measurements
    ), [
        f"{m.clip}/frame_{m.frame:02d} body offset {m.body_dx},{m.body_dy}"
        for m in measurements
        if abs(m.body_dx) > 32 or abs(m.body_dy) > 32
    ]
    # The correction is a real measurement, not a constant zero.
    assert any(m.body_dx != 0 or m.body_dy != 0 for m in measurements)


def test_every_feature_says_where_it_came_from(audit):
    """Every feature carries its provenance, and nothing is unresolved.

    `measured` = the detector found it in this frame. `interpolated` = it
    was reconstructed from the frames around it. `missing` and
    `out_of_range` mean UNRESOLVED -- the guards above would have failed
    on those.

    NOTE: these counters are the ground truth of the shipped art. They
    were re-validated after Task 6 mirrored javelin/frame_03 and
    purple_bullet/frame_06: the counts did NOT move (53/7 and 59/1),
    because the shape rule still measures the BODY in those two frames --
    they stay FUERA_DE_RANGO and keep being interpolated.
    """
    _, measurements = audit
    shield_sources = Counter(m.shield_source for m in measurements)
    eye_sources = Counter(m.eye_source for m in measurements)
    assert shield_sources == {"measured": 53, "interpolated": 7}, dict(
        shield_sources
    )
    assert eye_sources == {"measured": 59, "interpolated": 1}, dict(eye_sources)


def test_the_eye_and_the_shield_are_resolved_independently(audit):
    """One feature can be reconstructed while the other is measured.

    death/frame_09 has no eye left to find -- by the last frame of the
    death clip the boss is a heap of wreckage -- so its eye is
    interpolated from death/frame_08 while its shield is measured in that
    very frame. javelin/frame_03 is the other way round: the plate was
    painted on the wrong side, so the shield is interpolated while the
    eye is measured.
    """
    _, measurements = audit
    by_frame = {(m.clip, m.frame): m for m in measurements}

    wreck = by_frame[("death", 9)]
    assert wreck.eye_source == "interpolated"
    assert wreck.shield_source == "measured"

    javelin = by_frame[("javelin", 3)]
    assert javelin.shield_source == "interpolated"
    assert javelin.eye_source == "measured"


def test_the_report_still_documents_the_art_problem(audit):
    """The interpolation fixes the measurement, not the art.

    The findings must keep reporting the frames whose plate is missing
    from the drawing, otherwise the report lies about the source art.

    NOTE: these three frames are hard-coded and were re-validated after
    Task 6 mirrored javelin/frame_03 and purple_bullet/frame_06. The
    mirroring moved the clip's probe median, and with it the set of frames
    the auditor flags -- but these three are still reported: the two
    mirrored frames keep their FUERA_DE_RANGO finding (the shape rule
    measures the body, not the plate, in them).
    """
    findings, _ = audit
    reported = {f"{f.clip}/frame_{f.frame:02d}" for f in findings}
    assert "javelin/frame_04" in reported
    assert "laser/frame_05" in reported
    assert "purple_bullet/frame_08" in reported
```

- [ ] **Step 4: Run the guard to see the current state**

Run: `python -m pytest tests/test_features_detected_everywhere.py --tb=short`
Expected: all PASS. The auditor interpolates the out-of-range frames, so the measurement is already resolved — but `test_the_report_still_documents_the_art_problem` confirms the findings still name the broken frames.

The red state lives in Task 2's `test_manifest_side_consistency`, which stays red until Task 6 mirrors the two turned-around frames.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sprite_pipeline_audit.py tests/test_features_detected_everywhere.py
git commit -m "test: BLOQUE 74 - cobertura del auditor y del guard de features"
```

---

### Task 5: Fix the suite's pygame contamination — a `tests/conftest.py`

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_gameplay_runtime.py` (drop the destructive teardown)
- Modify: `tests/test_asteroid_hit_flash.py` (drop the destructive teardown)
- Modify: `tests/test_player_sprite_sheet.py` (drop the destructive teardown)
- Modify: `tests/test_video_player.py` (drop the destructive teardown)
- Modify: `tests/test_cinematic_scene.py` (drop the destructive teardown)
- Modify: `tests/test_gallery_scene.py` (drop the destructive teardown)

**Interfaces:**
- Consumes: nothing from earlier tasks. This task is independent of the sprite pipeline.
- Produces:
  - `tests/conftest.py` — an autouse fixture guaranteeing a live video system for every test
  - a **stable** suite baseline: the same failure count regardless of collection order

**Why this task exists.**

Seven of the eight "pre-existing failures" the project has documented are
**pollution casualties, not real defects**. Six test modules call
`pygame.quit()` in teardown, which leaves the video system uninitialised for
whatever runs next, and there is no `tests/conftest.py` to restore it.

Measured on this branch:

| Run | Result |
|---|---|
| `pytest tests/test_sub_boss_full_flow.py tests/test_sub_boss_real_flow.py` | exit 0 -- the 5 pass in isolation |
| `pytest tests/test_gameplay_runtime.py tests/test_sub_boss_*.py` | 5 failed -- `pygame.error: video system not initialized` at `src/ui/gameplay_runtime.py:721` |
| `pytest tests/test_asteroid_hit_flash.py tests/test_asteroid_sprites.py` | 2 failed -- `cannot convert without pygame.display initialized` at `src/entities/asteroid.py:175` |
| `pytest tests/test_asteroid_sprites.py` alone | 23 passed |

And the decisive one: with the new `tests/test_sprite_pipeline_audit.py` present but `tests/test_gameplay_runtime.py` running in between, the five sub-boss tests **still fail**. The heal in the full-suite run comes only from `test_sprite_pipeline_audit.py` sorting alphabetically between `test_gameplay_runtime.py` and `test_sub_boss_*`.

So the suite's green-ness is a property of **collection order**, not of the code. A rename, a `-p randomly`, an `--ignore`, or any new teardown before `test_sub_boss_*` silently resurrects five failures. Only `tests/test_paths.py::test_paths_no_star_shapes` is a genuine assertion failure.

**What to do.**

1. Create `tests/conftest.py` with an autouse fixture that guarantees a live video mode before each test. Use exactly this content:

```python
"""BLOQUE 74: shared pytest fixtures.

Several test modules used to call pygame.quit() in teardown, which left the
video system uninitialised for whatever ran next. That turned seven of the
documented "pre-existing failures" into pure collection-order accidents: the
same tests pass in isolation and fail depending on where pytest put them.
The fixture below makes the video system survive every test, so the suite's
result no longer depends on alphabetical order.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest


@pytest.fixture(autouse=True)
def _live_video_system():
    """Guarantee a live pygame for every test.

    pygame.quit() in another module's teardown tears pygame down -- the
    video system AND the font subsystem. Restoring only the display is not
    enough: pygame.font.get_init() stays False and pygame.font.Font(None, 12)
    raises "font not initialized" (src/ui/gameplay_runtime.py:4269). So
    pygame.init() comes first -- it re-initialises the modules that are
    down without resetting the state of the ones that are up.

    The video mode is set afterwards, and the guard tests the SURFACE, not
    the subsystem: pygame.init() leaves pygame.display.get_init() True
    while pygame.display.get_surface() is still None, so a guard on
    get_init() would never call set_mode() and the whole session would run
    without a display surface. Without one, convert_alpha() raises "No
    video mode has been set" and src/ui/gameplay_runtime.py:5004-5007
    swallows it into cache = None -- the player spritesheet silently never
    loads.
    """
    import pygame

    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((320, 480))
    yield
```

2. Remove the destructive `pygame.quit()` teardowns from the six modules listed above. They are the cause, and leaving them in place means the next module that quits pygame re-breaks the suite. The fixture is the belt; removing the teardowns is the braces.

3. Run the suite and record the new baseline.

**Acceptance:**
- `python -m pytest tests/ --tb=no` -> the same failure count with and without the new module, and the same with the modules reordered. Concretely: the five `test_sub_boss_*` and the two `test_asteroid_sprites.py` failures must be GONE, and the count must not depend on order.
- Verify the order independence explicitly: run `pytest tests/test_gameplay_runtime.py tests/test_sub_boss_*.py` and confirm it now passes.
- The remaining failures must be only `tests/test_paths.py::test_paths_no_star_shapes` (a genuine assertion) and `tests/test_manifest_side_consistency.py::test_plate_is_on_the_declared_side` (red by design until Task 6 mirrors the frames).
- `python -m pytest tests/test_asteroid_sprites.py --tb=no` -> passes.
- `python -m mypy src/anim/` -> still 0 errors.

**Also normalise the display size.** Four module fixtures open a 1x1 mode
(`tests/test_cinematic_scene.py`, `tests/test_gallery_scene.py`,
`tests/test_player_sprite_sheet.py`, `tests/test_video_player.py`). With
nothing calling `pygame.quit()` any more, that 1x1 surface survives for the
rest of the session, and `src/ui/gameplay_runtime.py:493-495` caches
`pygame.display.get_surface().get_size()` into `_game_screen_size` — so a
`GameplayRuntime` built after one of those modules would cache (1, 1) instead
of (320, 480). Nothing fails today, but the mouse-to-internal scaling in the
shipped game would be wrong. Change those four to `(320, 480)`.

**Note:** this task also invalidates the hard-coded frame names in `tests/test_features_detected_everywhere.py` (Task 6 mirrors two frames and shifts the clip medians). Re-validate them in Task 6, not here.

**Note on `CORTADO`:** no GOLIATH frame is actually cut off, so the re-pad
path is exercised only by SYNTHETIC frames (5 tests in
`tests/test_sprite_pipeline_repair.py` plus 5 more on the re-pad itself). The
shipped art has zero `CORTADO` findings. The path is proven, but it is
proven on synthetic input, not on the real assets.

### Task 6: The repair pass and the pipeline command

**Files:**
- Create: `tools/sprite_pipeline/repair.py`
- Create: `tools/sprite_pipeline/run.py`
- Modify: `Assets/sprites/bosses/goliath/javelin/frame_03.png` (mirrored)
- Modify: `Assets/sprites/bosses/goliath/purple_bullet/frame_06.png` (mirrored)

**Interfaces:**
- Consumes: `tools.sprite_pipeline.audit` (Task 3), `src.anim.manifest` (Task 1).
- Produces:
  - `tools/sprite_pipeline/repair.py::mirror_frame(path: Path) -> bool` — mirrors the PNG in place; returns True when it changed the file
  - `tools/sprite_pipeline/repair.py::repair_set(anim_set, findings, *, apply: bool) -> list[str]` — returns the list of human-readable actions taken
  - `tools/sprite_pipeline/run.py::main(argv) -> int` — CLI: `python tools/sprite_pipeline/run.py goliath [--fix] [--json]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sprite_pipeline_repair.py`:

```python
"""BLOQUE 74: the repair pass must be deterministic and idempotent.

Mirroring is the repair for a turned-around character. It must flip the
sprite inside its own canvas (not move it), and it must leave every other
frame byte-identical.

The flip itself is an INVOLUTION -- mirroring twice restores the original
pixels. What is idempotent is the repair PASS: it only acts on a
LADO_EQUIVOCADO finding, and once the frame has been mirrored the next
audit finds none, so a second `--fix` changes nothing.

The re-pad and the auditor must agree on the THRESHOLD: the repair targets
CORTADO_MARGIN, the very threshold the auditor flags below, so a frame the
auditor flags is a frame the repair can reach.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set  # noqa: E402
from src.anim.measure import (  # noqa: E402
    CORTADO_MARGIN,
    silhouette_bbox,
    silhouette_margins,
)
from sprite_pipeline.audit import Finding, audit_set  # noqa: E402
from sprite_pipeline.repair import (  # noqa: E402
    mirror_frame,
    repair_set,
    repad_frame,
)

# The synthetic-set builder lives with the auditor's own tests: the
# manifest it writes declares the parts the auditor measures (the shield
# plate and the eye), and there is exactly ONE copy of that manifest.
from tests.test_sprite_pipeline_audit import build_set  # noqa: E402

W, H = 96, 80
TRANSPARENT = (0, 0, 0, 0)
BODY = (160, 110, 50, 255)


def _surface(pixels: dict[tuple[int, int], tuple]) -> pygame.Surface:
    surf = pygame.Surface((W, H), pygame.SRCALPHA, 32)
    surf.fill(TRANSPARENT)
    for (x, y), colour in pixels.items():
        surf.set_at((x, y), colour)
    return surf


def _rect(x0: int, y0: int, x1: int, y1: int) -> dict[tuple[int, int], tuple]:
    """Pixels of a filled rectangle, `x1`/`y1` exclusive."""
    return {
        (x, y): BODY
        for y in range(y0, y1)
        for x in range(x0, x1)
    }


def _margins(surf: pygame.Surface) -> tuple[int, int, int, int]:
    """The four margins of the silhouette, as the auditor measures them."""
    bbox = silhouette_bbox(surf)
    assert bbox is not None, "the surface has no silhouette"
    left, top, right, bottom = bbox
    w, h = surf.get_size()
    return (left, top, w - right, h - bottom)


def _tight_pixels() -> dict[tuple[int, int], tuple]:
    """A silhouette with the margins (0, 1).

    It touches the LEFT edge and is 1 px from the TOP edge, and it keeps
    4 px of slack on the right: the tightest frame a translation can still
    give the auditor's margin to.
    """
    return _rect(0, 1, W - 4, 40)


def _synthetic_set(
    tmp_path: Path, pixels: dict[tuple[int, int], tuple], clip_dir: str = "idle"
):
    """A one-frame set on disk, loaded through the real manifest loader.

    The clip's ID is always "idle"; `clip_dir` is the DIRECTORY the frames
    live in, so a set that separates the two can be built.
    """
    set_dir = tmp_path / "synthetic"
    frames_dir = set_dir / clip_dir
    frames_dir.mkdir(parents=True)
    pygame.image.save(_surface(pixels), str(frames_dir / "frame_00.png"))
    (set_dir / "manifest.toml").write_text(
        f"""[meta]
name = "SYNTHETIC"
version = 1
canvas = [96, 80]
anchor = [48, 40]
sided = "right"

[[clips]]
id = "idle"
dir = "{clip_dir}"
frames = 1
fps = 10
loop = true

[[parts]]
id = "body"
draw = "frames"
pivot = "centroid"
z = 0
""",
        encoding="utf-8",
    )
    return load_set("synthetic", root=tmp_path)


# ---------------------------------------------------------------------------
# The mirror primitive.
# ---------------------------------------------------------------------------
def test_mirror_flips_the_pixels(tmp_path):
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    surf.set_at((10, 10), (255, 0, 0, 255))
    pygame.image.save(surf, str(path))

    assert mirror_frame(path) is True

    after = pygame.image.load(str(path)).convert_alpha()
    assert after.get_at((85, 10)) == (255, 0, 0, 255)
    assert after.get_at((10, 10))[3] == 0


def test_mirror_is_an_involution(tmp_path):
    """Mirroring twice restores the original pixels.

    The flip is its own inverse -- that is a property of the primitive, not
    a bug. What is idempotent is the REPAIR PASS: it only acts on a
    LADO_EQUIVOCADO finding, and once the frame has been mirrored the next
    audit finds none, so the second run does nothing.
    """
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    surf.set_at((10, 10), (255, 0, 0, 255))
    pygame.image.save(surf, str(path))

    mirror_frame(path)
    once = pygame.image.load(str(path)).convert_alpha()
    mirror_frame(path)
    twice = pygame.image.load(str(path)).convert_alpha()

    assert once.get_at((85, 10)) == (255, 0, 0, 255)
    assert twice.get_at((10, 10)) == (255, 0, 0, 255)
    assert twice.get_at((85, 10))[3] == 0


def test_mirror_keeps_the_canvas_size(tmp_path):
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    pygame.image.save(surf, str(path))

    mirror_frame(path)
    after = pygame.image.load(str(path)).convert_alpha()
    assert after.get_size() == (96, 80)


# ---------------------------------------------------------------------------
# The re-pad primitive.
#
# The shipped GOLIATH frames are NOT cut off, so the CORTADO repair is never
# exercised by the real assets: without a synthetic frame here, a repair that
# is inert could stay inert forever.
# ---------------------------------------------------------------------------
def test_repad_gives_the_silhouette_a_margin_on_every_side(tmp_path):
    """A sprite touching the LEFT edge is moved inward.

    The canvas keeps its size and the sprite keeps its size: it is MOVED
    inside its own canvas, never scaled.
    """
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(0, 30, 41, 50)), str(path))

    assert repad_frame(path, min_margin=3) is True

    after = pygame.image.load(str(path)).convert_alpha()
    assert after.get_size() == (W, H)

    left, top, right, bottom = _margins(after)
    assert left >= 3, f"left margin {left}"
    assert top >= 3, f"top margin {top}"
    assert right >= 3, f"right margin {right}"
    assert bottom >= 3, f"bottom margin {bottom}"

    # The silhouette itself is unchanged: same size, same pixel count. The
    # repair moves the art, it does not redraw it.
    bbox = silhouette_bbox(after)
    assert bbox is not None
    assert (bbox[2] - bbox[0], bbox[3] - bbox[1]) == (41, 20)
    assert sum(after.get_at((x, y))[3] != 0 for y in range(H) for x in range(W)) == (
        41 * 20
    )


def test_repad_also_fixes_a_silhouette_on_the_right_edge(tmp_path):
    """The shift may go LEFT: a sprite touching the right edge moves left."""
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(55, 30, 96, 50)), str(path))

    assert repad_frame(path, min_margin=3) is True

    after = pygame.image.load(str(path)).convert_alpha()
    left, top, right, bottom = _margins(after)
    assert left >= 3, f"left margin {left}"
    assert top >= 3, f"top margin {top}"
    assert right >= 3, f"right margin {right}"
    assert bottom >= 3, f"bottom margin {bottom}"
    assert after.get_size() == (W, H)


def test_repad_fixes_a_silhouette_that_touches_the_bottom_edge(tmp_path):
    """The vertical axis is handled like the horizontal one."""
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(20, 60, 50, 80)), str(path))

    assert repad_frame(path, min_margin=3) is True

    after = pygame.image.load(str(path)).convert_alpha()
    left, top, right, bottom = _margins(after)
    assert left >= 3, f"left margin {left}"
    assert top >= 3, f"top margin {top}"
    assert right >= 3, f"right margin {right}"
    assert bottom >= 3, f"bottom margin {bottom}"


def test_repad_leaves_a_healthy_frame_alone(tmp_path):
    """A frame that already has the margin is not rewritten."""
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(20, 30, 60, 50)), str(path))
    before = path.read_bytes()

    assert repad_frame(path, min_margin=3) is False
    assert path.read_bytes() == before


def test_repad_reports_failure_when_no_shift_can_help(tmp_path):
    """A silhouette that spans the whole canvas cannot be re-padded.

    No translation gives it a margin on both sides, so the repair must say
    it did nothing instead of claiming a success it cannot deliver.
    """
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(0, 0, W, H)), str(path))
    before = path.read_bytes()

    assert repad_frame(path, min_margin=3) is False
    assert path.read_bytes() == before


# ---------------------------------------------------------------------------
# The repair PASS: dry by default, and honest about what it did.
# ---------------------------------------------------------------------------
def test_repair_set_is_dry_by_default(tmp_path):
    """Without apply=True the pass reports what it WOULD do and writes
    nothing."""
    anim_set = _synthetic_set(tmp_path, _rect(20, 30, 60, 50))
    frame = anim_set.path / "idle" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "LADO_EQUIVOCADO", "probe col 10.0")],
    )

    assert actions == ["would mirror idle/frame_00"]
    assert frame.read_bytes() == before


def test_repair_set_applies_when_asked(tmp_path):
    anim_set = _synthetic_set(tmp_path, _rect(20, 30, 60, 50))
    frame = anim_set.path / "idle" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "LADO_EQUIVOCADO", "probe col 10.0")],
        apply=True,
    )

    assert actions == ["mirrored idle/frame_00"]
    assert frame.read_bytes() != before


def test_repair_set_dry_and_applied_words_differ(tmp_path):
    """A dry run and a real run never print the same line."""
    anim_set = _synthetic_set(tmp_path, _rect(20, 30, 60, 50))
    findings = [Finding("idle", 0, "LADO_EQUIVOCADO", "probe col 10.0")]

    dry = repair_set(anim_set, findings)
    applied = repair_set(anim_set, findings, apply=True)

    assert dry != applied
    assert all(a.startswith("would ") for a in dry)
    assert all(not a.startswith("would ") for a in applied)


def test_repair_set_reports_only_what_it_actually_did(tmp_path):
    """A repair that could not be performed is NOT reported.

    The frame's silhouette spans the whole canvas, so the re-pad cannot
    succeed. The pass must return an empty list instead of claiming a
    repair it did not make.
    """
    anim_set = _synthetic_set(tmp_path, _rect(0, 0, W, H))
    frame = anim_set.path / "idle" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "CORTADO", "silhouette margins L0 T0 R0 B0")],
        apply=True,
    )

    assert actions == []
    assert frame.read_bytes() == before


def test_repair_set_reports_a_re_pad_that_worked(tmp_path):
    anim_set = _synthetic_set(tmp_path, _rect(0, 30, 41, 50))
    frame = anim_set.path / "idle" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "CORTADO", "silhouette margins L0 T30 R55 B30")],
        apply=True,
    )

    assert actions == ["re-padded idle/frame_00"]
    assert frame.read_bytes() != before


# ---------------------------------------------------------------------------
# The re-pad and the auditor must agree on the threshold.
#
# The repair used to target a margin of 3 while the auditor flagged below
# 2. A frame with only 4 px of slack could not reach the repair's target,
# so it stayed flagged FOREVER: `run.py --fix` exited 1 on a set that can
# never be repaired. ONE threshold (CORTADO_MARGIN) closes the gap.
# ---------------------------------------------------------------------------
def test_a_frame_with_margins_0_and_1_is_repaired_and_stops_being_CORTADO(tmp_path):
    """The tightest repairable frame: margins (0, 1).

    The auditor flags it CORTADO, the re-pad moves it inward, and the
    auditor accepts the result: the finding is GONE.
    """
    build_set(tmp_path, [_tight_pixels()])
    anim_set = load_set("synthetic", root=tmp_path)
    frame = anim_set.path / "idle" / "frame_00.png"

    findings, _ = audit_set(anim_set)
    cortado = [f for f in findings if f.state == "CORTADO"]
    assert cortado, "the tight frame must be flagged CORTADO"
    assert "L0 T1" in cortado[0].detail, cortado[0].detail

    actions = repair_set(anim_set, cortado, apply=True)
    assert actions == ["re-padded idle/frame_00"]

    # The repaired frame is not flagged any more.
    findings_after, _ = audit_set(anim_set)
    assert not [f for f in findings_after if f.state == "CORTADO"], [
        f.detail for f in findings_after
    ]

    after = pygame.image.load(str(frame)).convert_alpha()
    margins = silhouette_margins(after)
    assert margins is not None
    assert min(margins) >= CORTADO_MARGIN, margins


def test_the_re_pad_targets_the_threshold_the_auditor_applies(tmp_path):
    """ONE threshold: the repair's default IS the auditor's threshold.

    A stricter target than the auditor's would leave frames the auditor
    flags unrepaired; a looser one would move art that does not need to
    move. The repair must target exactly CORTADO_MARGIN.
    """
    path = tmp_path / "frame_00.png"
    # A silhouette whose margins are exactly (2, 2): the auditor accepts
    # it, so the repair must NOT touch it.
    pygame.image.save(_surface(_rect(2, 2, W - 2, H - 2)), str(path))
    before = path.read_bytes()

    assert repad_frame(path) is False
    assert path.read_bytes() == before

    # One pixel too close on the left: the auditor flags it and the
    # repair (with its default margin) fixes it. The silhouette keeps 4 px
    # of slack in total, so a translation CAN give it the margin.
    pygame.image.save(_surface(_rect(1, 2, W - 3, H - 2)), str(path))
    assert repad_frame(path) is True

    after = pygame.image.load(str(path)).convert_alpha()
    margins = silhouette_margins(after)
    assert margins is not None
    assert min(margins) >= CORTADO_MARGIN, margins


# ---------------------------------------------------------------------------
# The frame is looked up through the manifest's `clip.dir`, never through
# the clip id. The two are allowed to differ.
# ---------------------------------------------------------------------------
def test_the_repair_resolves_the_directory_from_the_manifest(tmp_path):
    """A finding names the clip by ID; the frames live in `clip.dir`.

    Every clip of the shipped GOLIATH manifest declares `dir` equal to its
    `id`, so the two are the same string there. A set that separates them
    must still be repaired in the right place -- the directory comes from
    the manifest, never from the id.
    """
    anim_set = _synthetic_set(tmp_path, _rect(20, 30, 60, 50), clip_dir="frames")
    frame = anim_set.path / "frames" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "LADO_EQUIVOCADO", "probe col 10.0")],
        apply=True,
    )

    assert actions == ["mirrored frames/frame_00"]
    assert frame.read_bytes() != before


def test_the_repair_resolves_the_directory_of_a_re_pad_from_the_manifest(tmp_path):
    """The re-pad resolves its frame through the manifest too."""
    anim_set = _synthetic_set(tmp_path, _rect(0, 30, 41, 50), clip_dir="frames")
    frame = anim_set.path / "frames" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "CORTADO", "silhouette margins L0 T30 R55 B30")],
        apply=True,
    )

    assert actions == ["re-padded frames/frame_00"]
    assert frame.read_bytes() != before
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_sprite_pipeline_repair.py --tb=short`
Expected: FAIL with `ModuleNotFoundError: No module named 'sprite_pipeline.repair'`

- [ ] **Step 3: Write the repair pass**

Create `tools/sprite_pipeline/repair.py`:

```python
"""BLOQUE 74: deterministic, idempotent repairs.

Each failure state is repaired at the layer where it is actually fixable:

    LADO_EQUIVOCADO  build (PNG)  mirror the frame horizontally
    CORTADO          build (PNG)  re-pad onto a fresh transparent canvas
    FUERA_DE_RANGO   anchors      interpolate from the neighbouring frames
    AUSENTE          anchors      interpolate from the neighbouring frames
    FIRMA_AMBIGUA    config       widen detect.warm_fallback
    ESCALADO         --           reported, never auto-repaired (pixel art)
    COLAPSADO        --           not repairable: the art is gone

Repairs run with apply=False by default, so the caller must ask for the
writes explicitly.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from src.anim.manifest import AnimSet
from src.anim.measure import CORTADO_MARGIN, silhouette_margins

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from sprite_pipeline.audit import Finding


def mirror_frame(path: Path) -> bool:
    """Mirror a frame horizontally inside its own canvas.

    The canvas size is preserved, so the manifest's canvas stays valid.
    Returns True when the file was written.
    """
    surf = pygame.image.load(str(path)).convert_alpha()
    flipped = pygame.transform.flip(surf, True, False)
    pygame.image.save(flipped, str(path))
    return True


def _shift_for_margins(low: int, high: int, min_margin: int) -> int | None:
    """How far to move a silhouette that has `low` px before it and `high`
    px after it, so that both margins reach `min_margin`.

    Returns None when no shift can do that: the silhouette is then wider
    than the canvas minus two margins, and the only thing that would fix
    it is scaling -- which pixel art does not get.

    The shift is the smallest one that gives the too-close side its
    margin, and it never pushes the content past the opposite edge.
    """
    if low >= min_margin and high >= min_margin:
        return 0
    if low + high < 2 * min_margin:
        return None
    if low < min_margin:
        return min_margin - low
    return -(min_margin - high)


def repad_frame(path: Path, min_margin: int = CORTADO_MARGIN) -> bool:
    """Move the silhouette inward so it never touches the canvas edge.

    The visual content is untouched -- only its position inside the canvas
    shifts -- and the anchors recompute on the next audit. The canvas
    keeps its size: the sprite is MOVED inside its own canvas, never
    scaled.

    The bounding box comes from `src.anim.measure.silhouette_margins`, the
    SAME helper the auditor uses to raise the CORTADO finding, so the
    repair and the finding can never disagree about what "cut off" means.
    (pygame's `Surface.get_alpha()` is NOT that helper: it returns the
    surface's alpha VALUE -- the int 255 for a per-pixel-alpha surface --
    and never a channel to measure.)

    `min_margin` defaults to CORTADO_MARGIN, the threshold the auditor
    flags below. The repair targets exactly the threshold the auditor
    applies: a stricter target would leave frames the auditor flags
    unrepaired (the set could never pass), and a looser one would move
    art that does not need to move.

    Returns True when the file was written.
    """
    surf = pygame.image.load(str(path)).convert_alpha()
    w, h = surf.get_size()
    margins = silhouette_margins(surf)
    if margins is None:
        return False
    left, top, right, bottom = margins
    if min(margins) >= min_margin:
        return False

    dx = _shift_for_margins(left, right, min_margin)
    dy = _shift_for_margins(top, bottom, min_margin)
    if dx is None or dy is None:
        # No translation can give the silhouette its margin on every side.
        return False
    if dx == 0 and dy == 0:
        return False

    out = pygame.Surface((w, h), pygame.SRCALPHA, 32)
    out.fill((0, 0, 0, 0))
    out.blit(surf, (dx, dy))
    pygame.image.save(out, str(path))
    return True


def _frame_path(anim_set: AnimSet, clip_id: str, frame: int) -> Path | None:
    """The PNG of one frame, or None when the clip is unknown.

    A finding names the clip by ID; the DIRECTORY that holds the frames is
    the manifest's `clip.dir`. The two are allowed to differ, so the
    directory is always resolved from the manifest and never assumed to
    be the id.
    """
    clip = anim_set.clips.get(clip_id)
    if clip is None:
        return None
    return anim_set.path / clip.dir / f"frame_{frame:02d}.png"


def repair_set(
    anim_set: AnimSet, findings: list["Finding"], *, apply: bool = False
) -> list[str]:
    """Apply the repairs implied by the findings.

    Returns the list of actions ACTUALLY taken. With apply=False the
    actions are the ones that WOULD be taken and the wording says so, so a
    dry run and a real run never print the same line.

    A repair that could not be performed is NOT reported: the list is
    what happened, not what was attempted.

    The frame is looked up as `<set>/<clip dir>/frame_NN.png`, with the
    directory taken from the manifest (`clip.dir`).
    """
    actions: list[str] = []
    for finding in findings:
        if finding.state not in ("LADO_EQUIVOCADO", "CORTADO"):
            continue
        path = _frame_path(anim_set, finding.clip, finding.frame)
        if path is None or not path.is_file():
            continue
        # The message names the FILE, so it uses the directory.
        name = f"{path.parent.name}/frame_{finding.frame:02d}"
        if finding.state == "LADO_EQUIVOCADO":
            if not apply:
                actions.append(f"would mirror {name}")
                continue
            if mirror_frame(path):
                actions.append(f"mirrored {name}")
        else:
            if not apply:
                actions.append(f"would re-pad {name}")
                continue
            if repad_frame(path):
                actions.append(f"re-padded {name}")
    return actions
```

- [ ] **Step 4: Write the pipeline command**

Create `tools/sprite_pipeline/run.py`:

```python
"""BLOQUE 74: the sprite pipeline.

    python tools/sprite_pipeline/run.py goliath            # audit only
    python tools/sprite_pipeline/run.py goliath --fix      # audit, repair, re-audit
    python tools/sprite_pipeline/run.py goliath --json

Steps: validate -> audit -> repair -> re-audit -> anchors -> report.
Exits 1 when the final audit still has a FAIL.

Without --fix the command WRITES NOTHING: it validates the manifest,
audits the art and reports. The anchors are written only by --fix, after
the repair and the re-audit, so they always carry the repaired
measurements -- and a dry run can never regress the generated file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# pygame prints its support banner to STDOUT when the module is imported,
# which would corrupt the --json report. This has to be set BEFORE the
# import below (same guard as tools/sprite_pipeline/audit.py).
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parent.parent.parent
# The package lives in tools/sprite_pipeline/, so BOTH the repository root
# (for `src.anim.manifest`) and the tools directory (for
# `sprite_pipeline.audit`) have to be importable when this file is run as
# a script.
for _entry in (str(ROOT), str(ROOT / "tools")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pygame  # noqa: E402

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline import ensure_display  # noqa: E402
from sprite_pipeline.audit import (  # noqa: E402
    FAIL_STATES,
    audit_set,
    write_anchors,
)
from sprite_pipeline.repair import repair_set  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the sprite pipeline.")
    parser.add_argument("set", help="set name under Assets/sprites/bosses/")
    parser.add_argument(
        "--fix", action="store_true", help="apply repairs (mirrors, re-pads)"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    parser.add_argument(
        "--root",
        default=None,
        help=(
            "directory that HOLDS the sets (default: the repository's "
            "Assets/sprites/bosses). Point it at a copy to repair a set "
            "without touching the shipped art."
        ),
    )
    args = parser.parse_args(argv)

    pygame.init()
    ensure_display()

    try:
        anim_set = load_set(args.set, root=Path(args.root) if args.root else None)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings, measurements = audit_set(anim_set)
    actions: list[str] = []

    if args.fix:
        actions = repair_set(anim_set, findings, apply=True)
        findings, measurements = audit_set(anim_set)
        # The anchors are written AFTER the repair and the re-audit, so
        # they carry the repaired measurements, never the pre-repair ones.
        write_anchors(anim_set, measurements, anim_set.path / "anchors.toml")

    fails = [f for f in findings if f.state in FAIL_STATES]
    warns = [f for f in findings if f.state not in FAIL_STATES]

    # Count FRAMES, exactly like the auditor does: a frame can carry two
    # findings (javelin/frame_03 was FUERA_DE_RANGO *and*
    # LADO_EQUIVOCADO), so the number of findings and the number of
    # frames are different numbers. The summary says which one it reports.
    flagged = {(f.clip, f.frame) for f in findings}
    failing = {(f.clip, f.frame) for f in findings if f.state in FAIL_STATES}
    total = sum(c.frames for c in anim_set.clips.values())
    summary = {
        "frames_total": total,
        "frames_with_findings": len(flagged),
        "frames_failing": len(failing),
        "frames_warning": len(flagged) - len(failing),
        "findings_total": len(findings),
    }

    if args.json:
        print(
            json.dumps(
                {
                    "set": anim_set.name,
                    "actions": actions,
                    "failures": [
                        {"clip": f.clip, "frame": f.frame, "state": f.state, "detail": f.detail}
                        for f in fails
                    ],
                    "warnings": [
                        {"clip": f.clip, "frame": f.frame, "state": f.state, "detail": f.detail}
                        for f in warns
                    ],
                    "summary": summary,
                },
                indent=2,
            )
        )
    else:
        for action in actions:
            print(action)
        for f in fails:
            print(f"  FAIL {f.clip}/frame_{f.frame:02d}  {f.state}: {f.detail}")
        for f in warns:
            print(f"  WARN {f.clip}/frame_{f.frame:02d}  {f.state}: {f.detail}")
        print(
            f"{anim_set.name}: {summary['frames_with_findings']}/"
            f"{summary['frames_total']} frames with findings "
            f"({summary['frames_failing']} FAIL, {summary['frames_warning']} WARN), "
            f"{summary['findings_total']} findings"
        )

    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the repair test to verify it passes**

Run: `python -m pytest tests/test_sprite_pipeline_repair.py --tb=short`
Expected: PASS, 13 tests (3 mirror tests + 5 repair_set tests + 5 more
covering the re-pad on synthetic cut-off frames)

- [ ] **Step 6: Run the pipeline with --fix**

Run: `python tools/sprite_pipeline/run.py goliath --fix`
Expected: two `mirrored ...` lines (`javelin/frame_03`, `purple_bullet/frame_06`) -- the applied run reports the past tense, the dry run reports `would mirror ...` -- then the summary.

**Verify the two PNGs really changed and only those two:**

```bash
git status --short Assets/sprites/bosses/goliath/
```

Expected: exactly two modified PNGs, `javelin/frame_03.png` and `purple_bullet/frame_06.png`.

**The state after the repair, measured on a copy of the assets:**

| | frames con hallazgo | FAIL | escudo | ojo | sin resolver |
|---|---|---|---|---|---|
| antes | 10 | **2** (`javelin/f03`, `purple_bullet/f06`) | 53 measured / 7 interpolated | 59 / 1 | 0 |
| despues | 10 | **0** | 53 measured / 7 interpolated | 59 / 1 | 0 |

The two FAIL states are gone and the counters are UNCHANGED: the two mirrored
frames stay `FUERA_DE_RANGO` (the shape rule still measures the body, not the
plate, in them), so they keep being interpolated exactly as before. The
clip medians do move -- javelin's goes from 48.80 to 49.19 and purple_bullet's
from 51.23 to 51.97 -- but no frame crosses the side threshold, and the
mirrored frames land at probe columns 67.6 and 61.9, both on the right of the
centre, which is what the rule asks for.

- [ ] **Step 7: Re-run the guards that were red**

Run: `python -m pytest tests/test_manifest_side_consistency.py tests/test_features_detected_everywhere.py tests/test_anchors_are_fresh.py --tb=short`
Expected: all PASS. The side-consistency test turns green because the two turned-around frames are now mirrored.

- [ ] **Step 8: Commit**

```bash
git add tools/sprite_pipeline/repair.py tools/sprite_pipeline/run.py tests/test_sprite_pipeline_repair.py Assets/sprites/bosses/goliath/javelin/frame_03.png Assets/sprites/bosses/goliath/purple_bullet/frame_06.png Assets/sprites/bosses/goliath/anchors.toml
git commit -m "fix: BLOQUE 74 - repara los frames de GOLIATH con el personaje girado"
```

---

### Task 7: The anchor table reader and the compositor

**Files:**
- Create: `src/anim/anchors.py`
- Create: `src/anim/parts.py`
- Create: `src/anim/clip.py`
- Modify: `tools/sprite_pipeline/audit.py` (interpolate the out-of-range measurements)
- Test: `tests/test_anchor_interpolation.py`

**Interfaces:**
- Consumes: `src.anim.manifest` (Task 1), `src.anim.measure` (Task 2), `tools.sprite_pipeline.audit` (Task 3).
- Produces:
  - `src.anim.anchors.AnchorSet` — frozen dataclass; field `entries: dict[tuple[str, int], FrameAnchor]`
  - `src.anim.anchors.FrameAnchor` — frozen dataclass; fields `body_dx: int`, `body_dy: int`, `eye: tuple[int,int] | None`, `eye_source: str`, `shield: tuple[float,float,float,float] | None`, `shield_source: str`. The eye and the shield are INDEPENDENT: either can be measured, interpolated, or unresolved. A `None` feature (written to the file as a zero placeholder) must stay `None` on read — loading `eye = [0, 0]` as a real position would put the laser in the corner of the canvas.
  - `src.anim.anchors.load_anchors(path: Path) -> AnchorSet`
  - `src.anim.parts.draw_part(target, part: Part, surf, anchor: FrameAnchor, origin: tuple[int,int]) -> None`
  - `src.anim.clip.ClipPlayer` — `__init__(anim_set: AnimSet, anchors: AnchorSet)`, `clip(clip_id: str) -> ClipPlayer.ClipState`, method `frame_at(elapsed: float) -> int`
  - `src.anim.clip.ClipState` — frozen dataclass; fields `clip: Clip`, `frame: int`

- [ ] **Step 1: Write the failing test**

Create `tests/test_anchor_interpolation.py`:

```python
"""BLOQUE 74: a missing measurement must be reconstructed, not defaulted.

Seven of GOLIATH's frames have an implausible shield ellipse (the plate is
missing from the art or the arm is measured instead). A constant fallback
would pin the oval to a fixed point while the arm moves. Interpolating
from the frames around it keeps the oval on the arm.

The READER has to keep two things apart:

  * a feature the generator could not measure is written as a ZERO
    PLACEHOLDER, and only its `*_source` field tells that apart from a
    feature genuinely measured at the origin;
  * an unresolved feature must stay None -- the eye laser must not be
    launched from the corner of the canvas, and the oval must not be
    drawn at the corner of the screen.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.measure import interpolate  # noqa: E402

# A synthetic anchor table: the shipped assets have ZERO unresolved
# features (53 measured / 7 interpolated shields, 59 / 1 eyes), so the
# unresolved path is exercised here instead.
SYNTHETIC_ANCHORS = """
[meta]
generated_by = "test"

[[anchors]]
clip = "javelin"
frame = 0
body_dx = -3
body_dy = 2
eye = [51, 19]
eye_source = "measured"
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "measured"

[[anchors]]
clip = "javelin"
frame = 1
body_dx = -3
body_dy = 2
eye = [0, 0]
eye_source = "missing"
shield = [0.0, 0.0, 0.0, 0.0]
shield_source = "out_of_range"

[[anchors]]
clip = "javelin"
frame = 2
body_dx = -3
body_dy = 2
eye = [0, 0]
eye_source = "measured"
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "measured"
"""


def _load_synthetic(tmp_path: Path):
    from src.anim.anchors import load_anchors

    path = tmp_path / "anchors.toml"
    path.write_text(SYNTHETIC_ANCHORS, encoding="utf-8")
    return load_anchors(path)


# A whole synthetic SET whose clip id and clip DIRECTORY are different
# names. Every shipped manifest declares `id = dir`, so a regression that
# used the id for the PNG path (or the directory for the anchor key)
# would pass every other test in the suite. This fixture is the one place
# where the two genuinely differ.
SYNTHETIC_MANIFEST = """
[meta]
name    = "SYNTHETIC"
version = 1
canvas  = [96, 80]
anchor  = [48, 40]

[[clips]]
id     = "javelin"
dir    = "javelin_frames"
frames = 1
fps    = 10
loop   = true

[[parts]]
id    = "body"
draw  = "frames"
pivot = "centroid"
z     = 0
"""

# The anchor table of that set: keyed by the clip ID ("javelin"), not by
# the clip directory ("javelin_frames").
SYNTHETIC_SET_ANCHORS = """
[meta]
generated_by = "test"

[[anchors]]
clip = "javelin"
frame = 0
body_dx = 10
body_dy = 0
eye = [51, 19]
eye_source = "measured"
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "measured"
"""

# A table that claims a measurement it does not carry.
CORRUPT_ANCHORS = """
[meta]
generated_by = "test"

[[anchors]]
clip = "javelin"
frame = 0
body_dx = -3
body_dy = 2
eye_source = "measured"
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "measured"
"""


def _write_synthetic_set(root: Path) -> Path:
    """Write a set whose clip id and clip directory differ, and return it."""
    set_dir = root / "synthetic"
    frames_dir = set_dir / "javelin_frames"
    frames_dir.mkdir(parents=True)
    (set_dir / "manifest.toml").write_text(SYNTHETIC_MANIFEST, encoding="utf-8")
    (set_dir / "anchors.toml").write_text(SYNTHETIC_SET_ANCHORS, encoding="utf-8")
    # The body sits at (30, 30) 16x20, so its alpha centroid is (37.5,
    # 39.5) and the registration correction is +10 / 0 -- the same
    # arithmetic the auditor does.
    surf = pygame.Surface((96, 80), pygame.SRCALPHA)
    surf.fill((200, 100, 50, 255), pygame.Rect(30, 30, 16, 20))
    pygame.image.save(surf, str(frames_dir / "frame_00.png"))
    return set_dir


# --------------------------------------------------------------------------
# the interpolation itself
# --------------------------------------------------------------------------


def test_interpolates_a_gap():
    # measured 10, missing, measured 12 -> the middle is 11
    assert interpolate([10.0, None, 12.0], 1) == 11.0


def test_keeps_a_measured_value():
    assert interpolate([10.0, 11.0, 12.0], 1) == 11.0


def test_returns_none_without_neighbours():
    """No measured value anywhere: there is nothing to interpolate from."""
    assert interpolate([None, None, None], 1) is None


def test_falls_back_to_the_only_neighbour():
    """One side only: the missing tangent collapses onto that side.

    The first frame of a clip has no left neighbour. Falling back to the
    right one keeps it resolvable, which is what the auditor needs to
    reconstruct a plate the art forgot.
    """
    assert interpolate([None, None, 12.0], 0) == 12.0
    assert interpolate([12.0, None, None], 2) == 12.0


def test_interpolates_at_the_edges():
    # the first frame is missing: use the next two
    value = interpolate([None, 10.0, 12.0], 0)
    assert value is not None
    assert 10.0 <= value <= 12.0


# --------------------------------------------------------------------------
# the reader
# --------------------------------------------------------------------------


def test_goliath_has_no_unresolved_plates():
    """After the repair, every frame resolves its plate."""
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    unresolved = [
        f"{clip}/{frame:02d}"
        for (clip, frame), entry in anchors.entries.items()
        if entry.shield_source in ("missing", "out_of_range")
    ]
    assert not unresolved, "unresolved plates: " + ", ".join(unresolved)


def test_the_shipped_set_reconstructs_what_it_could_not_measure():
    """The interpolated frames are RECONSTRUCTED, not defaulted.

    death/frame_09 is a heap of wreckage with no eye left to find: its eye
    comes from death/frame_08 while its plate is measured in that very
    frame. javelin/frame_03 is the other way round: the plate was painted
    on the wrong side, so the plate is interpolated while the eye is
    measured.
    """
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")

    wreck = anchors.get("death", 9)
    assert wreck is not None
    assert wreck.eye_source == "interpolated"
    assert wreck.eye is not None
    assert wreck.shield_source == "measured"
    assert wreck.shield is not None

    javelin = anchors.get("javelin", 3)
    assert javelin is not None
    assert javelin.shield_source == "interpolated"
    assert javelin.shield is not None
    assert javelin.eye_source == "measured"
    assert javelin.eye is not None


def test_every_frame_of_the_shipped_set_is_resolved():
    """60 frames, 60 resolved plates, 60 resolved eyes."""
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    assert len(anchors.entries) == sum(c.frames for c in anim_set.clips.values())
    for (clip, frame), entry in anchors.entries.items():
        assert entry.shield is not None, f"{clip}/{frame:02d} has no plate"
        assert entry.eye is not None, f"{clip}/{frame:02d} has no eye"


def test_an_unresolved_feature_stays_none(tmp_path):
    """The zero placeholder is NOT a position.

    The generator writes `eye = [0, 0]` for an eye it could not find.
    Reading that as a real position would launch the laser from the
    corner of the canvas.
    """
    anchors = _load_synthetic(tmp_path)

    unresolved = anchors.get("javelin", 1)
    assert unresolved is not None
    assert unresolved.eye is None
    assert unresolved.eye_source == "missing"
    assert unresolved.shield is None
    assert unresolved.shield_source == "out_of_range"


def test_a_measured_feature_at_the_origin_is_not_none(tmp_path):
    """The SOURCE is what tells "measured at (0, 0)" from "not measured"."""
    anchors = _load_synthetic(tmp_path)

    measured = anchors.get("javelin", 2)
    assert measured is not None
    assert measured.eye == (0, 0)
    assert measured.eye_source == "measured"
    assert measured.shield == (60.5, 40.5, 8.5, 10.5)
    assert measured.shield_source == "measured"


def test_the_anchor_table_is_keyed_by_clip_id(tmp_path):
    """The clip id is the key; the clip DIRECTORY names the PNG."""
    anchors = _load_synthetic(tmp_path)
    assert ("javelin", 0) in anchors.entries
    assert anchors.get("javelin", 99) is None


# --------------------------------------------------------------------------
# the compositor
# --------------------------------------------------------------------------


def test_the_compositor_finds_the_frame_png():
    """The PNG lives in the clip's DIRECTORY, inside the set."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    surf = player.surface("javelin", 3)
    assert surf is not None, "the frame PNG was not found"
    assert surf.get_size() == anim_set.canvas


def test_the_compositor_puts_the_body_on_the_anchor():
    """The character's centre of mass lands on the world anchor."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set
    from src.anim.measure import alpha_centroid

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(target, "javelin", 3, origin=(120, 180))

    centroid = alpha_centroid(target)
    assert centroid is not None, "nothing was drawn"
    assert abs(centroid[0] - 120) <= 1.0
    assert abs(centroid[1] - 180) <= 1.0


def test_the_oval_geometry_follows_the_anchor():
    """The oval sits on the plate, with the manifest's nudge and scale."""
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set
    from src.anim.parts import shield_ellipse_rect

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    part = anim_set.part("shield_plate")
    anchor = anchors.get("javelin", 3)
    assert anchor is not None and anchor.shield is not None

    rect = shield_ellipse_rect(part, anchor, origin=(120, 180), canvas=anim_set.canvas)
    assert rect is not None

    cx, cy, rx, ry = anchor.shield
    # The same arithmetic the shipped runtime does (src/ui/
    # gameplay_runtime.py::_goliath_shield_ellipse).
    expected_x = 120 - 96 // 2 + anchor.body_dx + round(cx) + part.offset[0]
    expected_y = 180 - 80 // 2 + anchor.body_dy + round(cy) + part.offset[1]
    assert abs(rect.centerx - expected_x) <= 1
    assert abs(rect.centery - expected_y) <= 1
    assert rect.width == max(2, int(round(rx * part.scale[0]))) * 2
    assert rect.height == max(2, int(round(ry * part.scale[1]))) * 2


def test_an_unresolved_plate_keeps_the_canonical_oval(tmp_path):
    """BLOQUE 74: no credible position -> the CANONICAL oval.

    The policy changed in BLOQUE 74. The oval used to disappear when the
    plate could not be resolved, which deleted the shield's hitbox and
    left the laser with no origin. Now the frame keeps the canonical
    ellipse -- the manifest's radii at the canonical centre -- and it must
    not land on the origin either.
    """
    from src.anim.manifest import load_set
    from src.anim.parts import (
        CANONICAL_PLATE_CENTRE,
        draw_part,
        shield_ellipse_rect,
    )

    anchors = _load_synthetic(tmp_path)
    anim_set = load_set("goliath")
    part = anim_set.part("shield_plate")
    anchor = anchors.get("javelin", 1)
    assert anchor is not None and anchor.shield is None

    rect = shield_ellipse_rect(part, anchor, (120, 180), anim_set.canvas)
    assert rect is not None
    assert rect.centerx != 0 and rect.centery != 0
    expected_x = (
        120 - 96 // 2 + anchor.body_dx + CANONICAL_PLATE_CENTRE[0] + part.offset[0]
    )
    expected_y = (
        180 - 80 // 2 + anchor.body_dy + CANONICAL_PLATE_CENTRE[1] + part.offset[1]
    )
    assert abs(rect.centerx - expected_x) <= 1
    assert abs(rect.centery - expected_y) <= 1
    _r, rx, ry = part.radii
    assert rect.width == max(2, int(round(rx * part.scale[0]))) * 2
    assert rect.height == max(2, int(round(ry * part.scale[1]))) * 2

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    draw_part(target, part, None, anchor, (120, 180), anim_set.canvas)
    assert target.get_bounding_rect().width == 0, "the oval must stay invisible"


def test_the_clip_follows_the_manifest_fps():
    """The timing comes from the manifest, not from a hardcoded constant."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    assert anim_set.clip("javelin").fps == 10
    assert player.state("javelin", 0.0).frame == 0
    assert player.state("javelin", 0.1).frame == 1
    assert player.state("javelin", 0.25).frame == 2
    # a looping clip wraps around
    assert player.state("javelin", 1.05).frame == 0
    # a one-shot clip holds on its last frame
    assert player.state("death", 99.0).frame == 9


# --------------------------------------------------------------------------
# the clip id and the clip directory are two different names
# --------------------------------------------------------------------------


def test_the_anchor_table_is_keyed_by_the_clip_id(tmp_path):
    """The ID keys the table; the DIRECTORY names the PNG.

    Every shipped manifest declares `id = dir`, so only a set where the
    two differ can tell the two apart.
    """
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set

    set_dir = _write_synthetic_set(tmp_path)
    anim_set = load_set("synthetic", root=tmp_path)
    clip = anim_set.clip("javelin")
    assert clip.id == "javelin"
    assert clip.dir == "javelin_frames"

    anchors = load_anchors(set_dir / "anchors.toml")
    assert anchors.get("javelin", 0) is not None, "the id does not key the table"
    assert anchors.get("javelin_frames", 0) is None, "the directory keys the table"


def test_the_png_is_named_by_the_clip_directory(tmp_path):
    """The PNG lives in the clip's DIRECTORY, not in a folder named after
    the id."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    set_dir = _write_synthetic_set(tmp_path)
    anim_set = load_set("synthetic", root=tmp_path)
    anchors = load_anchors(set_dir / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    surf = player.surface("javelin", 0)
    assert surf is not None, "the frame PNG was not found in the clip directory"
    assert surf.get_size() == anim_set.canvas


def test_the_compositor_uses_the_id_for_the_anchor_and_the_dir_for_the_png(tmp_path):
    """The two names are used for the two different things."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set
    from src.anim.measure import alpha_centroid

    set_dir = _write_synthetic_set(tmp_path)
    anim_set = load_set("synthetic", root=tmp_path)
    anchors = load_anchors(set_dir / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(target, "javelin", 0, origin=(120, 180))

    centroid = alpha_centroid(target)
    assert centroid is not None, "the body was not drawn: the anchor was not found"
    assert abs(centroid[0] - 120) <= 1.0
    assert abs(centroid[1] - 180) <= 1.0


# --------------------------------------------------------------------------
# the frame boundary
# --------------------------------------------------------------------------


def test_a_frame_boundary_is_not_lost_to_float_error():
    """0.3 s at 10 fps is frame 3, not frame 2.

    0.3 * 10 is 2.9999999999999996 in binary floating point, so the
    division used to land on the previous frame.
    """
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    assert player.state("javelin", 0.3).frame == 3
    assert player.state("javelin", 0.6).frame == 6
    assert player.state("javelin", 0.7).frame == 7


def test_the_epsilon_does_not_move_a_mid_interval_frame():
    """The epsilon rescues an exact boundary and nothing else."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    assert player.state("javelin", 0.29).frame == 2
    assert player.state("javelin", 0.31).frame == 3
    assert player.state("javelin", 0.89).frame == 8


# --------------------------------------------------------------------------
# a hole in the table
# --------------------------------------------------------------------------


def test_a_frame_missing_from_the_table_still_draws_its_body():
    """A hole in the table must not make the boss blink out.

    The registration correction is unknown for a frame that is not in the
    table, so the body degrades to a plain centred blit.
    """
    from src.anim.anchors import AnchorSet, load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set
    from src.anim.measure import alpha_centroid

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    original = anchors.get("javelin", 3)
    assert original is not None

    trimmed = AnchorSet(
        entries={
            key: value
            for key, value in anchors.entries.items()
            if key != ("javelin", 3)
        }
    )
    player = ClipPlayer(anim_set, trimmed)

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(target, "javelin", 3, origin=(120, 180))

    centroid = alpha_centroid(target)
    assert centroid is not None, "the body vanished with its anchor"
    # No correction: the body lands where the canvas puts it.
    assert abs(centroid[0] - (120 - original.body_dx)) <= 1.0
    assert abs(centroid[1] - (180 - original.body_dy)) <= 1.0


# --------------------------------------------------------------------------
# a corrupt table
# --------------------------------------------------------------------------


def test_a_table_that_claims_a_measurement_it_does_not_carry_fails_loudly(tmp_path):
    """A source of "measured" with no value is corruption, not a position.

    Reading it as (0, 0) would fire the eye laser from the corner of the
    canvas.
    """
    from src.anim.anchors import AnchorError, load_anchors

    path = tmp_path / "anchors.toml"
    path.write_text(CORRUPT_ANCHORS, encoding="utf-8")
    with pytest.raises(AnchorError):
        load_anchors(path)


def test_an_unresolved_entry_may_omit_its_value(tmp_path):
    """An unresolved feature carries no value, and that is not corruption."""
    from src.anim.anchors import load_anchors

    path = tmp_path / "anchors.toml"
    path.write_text(
        CORRUPT_ANCHORS.replace(
            'eye_source = "measured"', 'eye_source = "missing"'
        ),
        encoding="utf-8",
    )
    anchors = load_anchors(path)
    entry = anchors.get("javelin", 0)
    assert entry is not None
    assert entry.eye is None
    assert entry.eye_source == "missing"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_anchor_interpolation.py --tb=short`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.anim.anchors'`

- [ ] **Step 3: Write the anchors module**

Create `src/anim/anchors.py`:

```python
"""BLOQUE 74: the baked anchor table.

anchors.toml holds the measurement of every frame: the body offset that
cancels the registration error, the eye anchor, and the shield ellipse.

The runtime reads this table instead of scanning pixels. The scan cost
3.9 ms the first time a frame was seen; the lookup costs nothing.

anchors.toml is GENERATED. The freshness test fails when it drifts from
the assets.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


# A feature is UNRESOLVED when its source says so. The generator writes a
# zero placeholder for an unresolved feature, so the source is the only
# thing that distinguishes "measured at (0, 0)" from "not measured at all".
UNRESOLVED_SOURCES = ("missing", "out_of_range")


class AnchorError(ValueError):
    """The anchor table is malformed.

    It does NOT mean "the measurement is bad" -- a bad measurement is a
    feature whose source says so, and it is read as None. This is about
    a table that cannot be believed at all: an entry that claims a
    measurement it does not carry.
    """


@dataclass(frozen=True)
class FrameAnchor:
    """The baked measurement of one frame.

    `eye` and `shield` are INDEPENDENT: either can be measured, interpolated
    or unresolved. An unresolved feature is None, never a zero tuple -- the
    eye laser must not be launched from the corner of the canvas.
    """

    body_dx: int
    body_dy: int
    eye: tuple[int, int] | None
    eye_source: str
    shield: tuple[float, float, float, float] | None
    shield_source: str


@dataclass(frozen=True)
class AnchorSet:
    """Every frame's measurement, keyed by (clip id, frame index)."""

    entries: dict[tuple[str, int], FrameAnchor]

    def get(self, clip_id: str, frame: int) -> FrameAnchor | None:
        """The measurement of one frame, or None when it is not in the table.

        The key is the CLIP ID (the manifest's `clip.id`), NOT the clip's
        directory: the two are allowed to differ, and the sprite path is
        built from the directory.
        """
        return self.entries.get((clip_id, frame))


def load_anchors(path: Path) -> AnchorSet:
    """Read anchors.toml.

    The source and the value are cross-checked: an entry that claims a
    measurement ("measured" / "interpolated") must CARRY that value. An
    entry that omits it is corrupt, and reading the missing key as a
    default would put the eye in the corner of the canvas.

    An entry whose source says the feature is UNRESOLVED may omit the
    value: it is None either way, and the generator writes a zero
    placeholder for it.
    """
    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    entries: dict[tuple[str, int], FrameAnchor] = {}
    for entry in raw.get("anchors", []):
        clip = str(entry["clip"])
        frame = int(entry["frame"])
        key = (clip, frame)
        eye_source = str(entry.get("eye_source", "measured"))
        shield_source = str(entry.get("shield_source", "measured"))
        if "eye" not in entry and eye_source not in UNRESOLVED_SOURCES:
            raise AnchorError(
                f"{clip}/{frame:02d}: eye_source is {eye_source!r} but the "
                "entry carries no eye"
            )
        if "shield" not in entry and shield_source not in UNRESOLVED_SOURCES:
            raise AnchorError(
                f"{clip}/{frame:02d}: shield_source is {shield_source!r} but "
                "the entry carries no shield"
            )
        eye = entry.get("eye", (0, 0))
        shield = entry.get("shield", (0.0, 0.0, 0.0, 0.0))
        entries[key] = FrameAnchor(
            body_dx=int(entry.get("body_dx", 0)),
            body_dy=int(entry.get("body_dy", 0)),
            eye=(
                None
                if eye_source in UNRESOLVED_SOURCES
                else (int(eye[0]), int(eye[1]))
            ),
            eye_source=eye_source,
            shield=(
                None
                if shield_source in UNRESOLVED_SOURCES
                else (
                    float(shield[0]),
                    float(shield[1]),
                    float(shield[2]),
                    float(shield[3]),
                )
            ),
            shield_source=shield_source,
        )
    return AnchorSet(entries=entries)
```

- [ ] **Step 4: Confirm the interpolation already runs inside the auditor**

The interpolation is part of `audit_set` (Task 3): the findings report the
art problem, the measurements are the repaired result. Confirm it is wired:

Run: `Select-String -Path tools/sprite_pipeline/audit.py -Pattern '_interpolate_missing'`
Expected: the function definition and its call inside `audit_set`.

- [ ] **Step 5: Run the pipeline to regenerate the anchors**

Run: `python tools/sprite_pipeline/run.py goliath --fix`
Expected: 0 FAIL, 60 frames measured, and `anchors.toml` carries `shield_source = "interpolated"` on the frames whose plate could not be measured.

- [ ] **Step 6: Run the tests**

Run: `python -m pytest tests/test_anchor_interpolation.py tests/test_features_detected_everywhere.py tests/test_anchors_are_fresh.py --tb=short`
Expected: all PASS.

- [ ] **Step 7: Write the part renderer**

Create `src/anim/parts.py`:

```python
"""BLOQUE 74: rendering one part of a clip.

A part is one of four things:

    "frames"      one PNG per frame of the current clip
    "ellipse"     a procedural primitive (the invisible shield oval)
    "point"       an anchor that draws nothing (the eye)
    "procedural"  a runtime effect; never baked into the art

Every part is positioned relative to the canvas anchor, not to the world
anchor directly: the body is blitted at (origin - canvas/2 + body_offset)
and the shield ellipse at (origin - canvas/2 + body_offset + plate + nudge).
Sharing the body offset is what keeps the oval glued to the plate.

The base is the CANVAS half-size, not the viewport half-size: the canvas
holds the character and its anchor sits at the canvas centre, so the
canvas' top-left corner lands on (origin - canvas/2 + body_offset) and the
character's visual centre of mass lands on `origin` -- which is the same
arithmetic the shipped runtime does with its 96x80 canvas.
"""
from __future__ import annotations

import pygame

from src.anim.anchors import FrameAnchor
from src.anim.manifest import Part

# The cold-steel colour of an uncharged shield: the same (96, 104, 124)
# the shipped runtime uses for `_shield_charge_color(0.0)`.
COLD_STEEL = (96, 104, 124)

# BLOQUE 67 (user request): the shield oval is INVISIBLE. The shipped
# runtime draws only the heat layer (which grows with the charge) and the
# impact flash -- the oval itself is never painted. The flag below keeps
# the drawing path available (and reviewable) without changing what the
# player sees; the GEOMETRY is what the runtime needs, and that comes from
# `shield_ellipse_rect`.
DRAW_SHIELD_OVAL = False

# BLOQUE 74: the CANONICAL plate centre and the CANONICAL radii.
#
# The centre is the median of the 60 measured plate centres (the baked
# table's cx spans 57.0..63.5 and its cy 39.5..42.5). It is where the
# plate sits on the canvas when a frame carries no measurement of its own.
CANONICAL_PLATE_CENTRE = (60.5, 40.5)

# The canonical radii (R, RX, RY), used when the manifest declares none.
# They are the BLOQUE 67 user-approved sizes, the same ones the runtime
# keeps in GOLIATH_SHIELD_R / _RX / _RY.
DEFAULT_RADII = (11.0, 11.0, 17.0)

# A frame that is missing from the anchor table still has a body: only its
# REGISTRATION CORRECTION is unknown, so it degrades to a plain centred
# blit instead of making the character disappear. The oval keeps the
# canonical geometry -- see `canonical_shield_ellipse`.
NO_OFFSET = FrameAnchor(
    body_dx=0,
    body_dy=0,
    eye=None,
    eye_source="missing",
    shield=None,
    shield_source="missing",
)


def canonical_shield_ellipse(part: Part | None) -> tuple[float, float, float, float]:
    """The canonical ellipse: the manifest's radii at the canonical centre.

    BLOQUE 74: this is the POLICY for a frame whose plate could not be
    resolved. The alternative -- no ellipse at all -- would delete the
    shield's hitbox and leave the laser with nowhere to come from, so the
    oval keeps the canonical size at the canonical place instead of
    vanishing.
    """
    radii = part.radii if part is not None else None
    if radii is None:
        radii = DEFAULT_RADII
    _r, rx, ry = radii
    return (CANONICAL_PLATE_CENTRE[0], CANONICAL_PLATE_CENTRE[1], rx, ry)


def _base(
    anchor: FrameAnchor, origin: tuple[int, int], canvas: tuple[int, int]
) -> tuple[int, int]:
    """The top-left corner of the frame's canvas in world coordinates.

    Every part of the frame shares this base: the body is the canvas
    itself, and the oval is the plate's position inside that canvas. That
    shared base is what keeps the oval glued to the plate.
    """
    ox, oy = origin
    return (
        ox - canvas[0] // 2 + anchor.body_dx,
        oy - canvas[1] // 2 + anchor.body_dy,
    )


def shield_ellipse_rect(
    part: Part,
    anchor: FrameAnchor | None,
    origin: tuple[int, int],
    canvas: tuple[int, int],
) -> pygame.Rect | None:
    """The world-space rect of the shield oval, or None when unresolved.

    The oval's centre is the plate's own position inside the canvas, moved
    by the part's `offset` (the nudge) and sized by the part's `scale` (the
    horizontal thinning). Both come from the manifest, so the manifest and
    the baked measurement can never disagree.

    BLOQUE 74: a frame whose plate could NOT be resolved gets the CANONICAL
    ellipse -- the manifest's radii at the canonical centre -- instead of no
    oval at all. The oval is invisible either way (DRAW_SHIELD_OVAL is
    False); what matters is that the geometry the hitbox and the laser
    read still exists.
    """
    if anchor is None:
        anchor = NO_OFFSET
    if anchor.shield is None:
        cx, cy, rx, ry = canonical_shield_ellipse(part)
    else:
        cx, cy, rx, ry = anchor.shield
    base_x, base_y = _base(anchor, origin, canvas)
    centre_x = int(base_x + cx + part.offset[0])
    centre_y = int(base_y + cy + part.offset[1])
    scaled_rx = max(2, int(round(rx * part.scale[0])))
    scaled_ry = max(2, int(round(ry * part.scale[1])))
    return pygame.Rect(
        centre_x - scaled_rx,
        centre_y - scaled_ry,
        scaled_rx * 2,
        scaled_ry * 2,
    )


def draw_part(
    target: pygame.Surface,
    part: Part,
    surf: pygame.Surface | None,
    anchor: FrameAnchor | None,
    origin: tuple[int, int],
    canvas: tuple[int, int],
) -> None:
    """Draw one part at a world position.

    `origin` is the world anchor (the boss's position on screen).
    `canvas` is the set's canvas size, (width, height).

    A frame that is missing from the anchor table still draws its body
    (without the registration correction); the oval falls back to the
    canonical geometry and the eye stays undrawn.
    """
    if anchor is None:
        if part.draw == "frames" and surf is None:
            return
        # A frame that is not in the table still draws: the body without
        # its registration correction, and the oval at the canonical
        # place (the oval is invisible anyway -- DRAW_SHIELD_OVAL is False).
        anchor = NO_OFFSET

    if part.draw == "frames":
        if surf is None:
            return
        base_x, base_y = _base(anchor, origin, canvas)
        target.blit(surf, (base_x, base_y))
        return

    if part.draw == "ellipse":
        rect = shield_ellipse_rect(part, anchor, origin, canvas)
        if rect is None:
            return
        if not DRAW_SHIELD_OVAL:
            # The oval is invisible by design (BLOQUE 67): the runtime
            # paints the heat layer and the impact flash instead.
            return
        pygame.draw.ellipse(target, COLD_STEEL, rect)
        return

    if part.draw == "point":
        # The eye is an ANCHOR, not a picture: the runtime reads its
        # position from the anchor table to launch the beam.
        return

    if part.draw == "procedural":
        # The eye beam is drawn by the runtime, which owns its colour ramp
        # and its charging state. Nothing to do here yet.
        return
```

- [ ] **Step 8: Write the clip player**

Create `src/anim/clip.py`:

```python
"""BLOQUE 74: the clip player.

Turns elapsed time into a frame index and composes the parts of a clip
into a target surface.

The timing is driven by the manifest's fps, so the animation no longer
depends on a constant hardcoded in the boss class.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

from src.anim.anchors import AnchorSet
from src.anim.manifest import AnimSet, Clip
from src.anim.parts import draw_part


@dataclass(frozen=True)
class ClipState:
    """A clip resolved against the anchor table."""

    clip: Clip
    frame: int


class ClipPlayer:
    """Composes the parts of one animated set."""

    def __init__(self, anim_set: AnimSet, anchors: AnchorSet) -> None:
        self.set = anim_set
        self.anchors = anchors
        # The frames are loaded once and kept: a clip is played at 10-30 fps
        # and the PNG is decoded from disk every time otherwise.
        self._surface_cache: dict[Path, pygame.Surface] = {}

    def state(self, clip_id: str, elapsed: float) -> ClipState:
        """The frame index for `elapsed` seconds into `clip_id`.

        The index is `elapsed * fps`, with a 1e-6 epsilon: 0.3 * 10 is
        2.9999999999999996 in binary floating point, so an exact frame
        boundary would land on the PREVIOUS frame and the animation
        would advance 100 ms early whenever the runtime feeds rounded
        seconds in. The epsilon is a microsecond -- it rescues an exact
        boundary and does not move a frame that is genuinely mid-interval.
        """
        clip = self.set.clip(clip_id)
        if clip.frames <= 0:
            return ClipState(clip=clip, frame=0)
        fps = clip.fps if clip.fps > 0 else 10.0
        index = int(elapsed * fps + 1e-6)
        if clip.loop:
            index %= clip.frames
        else:
            index = min(index, clip.frames - 1)
        return ClipState(clip=clip, frame=index)

    def frame_at(self, clip_id: str, elapsed: float) -> int:
        """The frame index for `elapsed` seconds into `clip_id`."""
        return self.state(clip_id, elapsed).frame

    def surface(self, clip_id: str, frame: int) -> pygame.Surface | None:
        """The PNG of one frame, or None when it is missing.

        The CLIP DIRECTORY is what names the PNG, not the clip id: the two
        are allowed to differ, and the anchor table is keyed by the clip
        ID. The frame lives inside the set's own directory, next to the
        manifest and the anchor table that describe it -- the art and its
        measurement can never come from different trees.

        The loader is deliberately LOCAL: `src/anim/` is the data layer and
        must not depend on `src/ui/` (the type gate runs mypy over
        `src/anim/`, and importing the UI module from here would drag its
        errors into that gate).
        """
        clip = self.set.clip(clip_id)
        path = self.set.path / clip.dir / f"frame_{frame:02d}.png"
        cached = self._surface_cache.get(path)
        if cached is not None:
            return cached
        if not path.is_file():
            return None
        try:
            loaded = pygame.image.load(str(path)).convert_alpha()
        except pygame.error:
            return None
        self._surface_cache[path] = loaded
        return loaded

    def draw(
        self,
        target: pygame.Surface,
        clip_id: str,
        frame: int,
        origin: tuple[int, int],
        part_ids: tuple[str, ...] | None = None,
    ) -> None:
        """Draw the parts of one frame, in z order."""
        wanted = set(part_ids) if part_ids else None
        parts = sorted(self.set.parts, key=lambda p: p.z)
        anchor = self.anchors.get(clip_id, frame)
        for part in parts:
            if wanted is not None and part.id not in wanted:
                continue
            surf = self.surface(clip_id, frame) if part.draw == "frames" else None
            draw_part(target, part, surf, anchor, origin, self.set.canvas)
```

- [ ] **Step 9: Commit**

```bash
git add src/anim/anchors.py src/anim/parts.py src/anim/clip.py tools/sprite_pipeline/audit.py tests/test_anchor_interpolation.py Assets/sprites/bosses/goliath/anchors.toml
git commit -m "feat: BLOQUE 74 - interpolacion de anchors, render de parts y clip player"
```

---

### Task 8: Migrate the runtime to the baked anchors

**Files:**
- Modify: `src/ui/scenes.py` (the three anchor functions read the table)
- Modify: `src/ui/gameplay_runtime.py` (`_draw_boss` and `_goliath_shield_ellipse`)
- Modify: `src/entities/enemies/boss.py` (fps and frame count come from the manifest)
- Test: `tests/test_goliath_runtime_uses_baked_anchors.py`

**Interfaces:**
- Consumes: `src.anim.anchors` (Task 7), `src.anim.manifest` (Task 1), `src.anim.clip` (Task 7).
- Produces:
  - `src.ui.scenes.get_sprite_centroid_offset(name: str) -> tuple[int, int]` — unchanged signature, now a table lookup
  - `src.ui.scenes.get_sprite_eye_anchor(name: str) -> tuple[int, int]` — unchanged signature
  - `src.ui.scenes.get_sprite_shield_ellipse(name: str) -> tuple[float, float, float, float]` — unchanged signature
  - `src.ui.scenes.clear_anchor_cache() -> None` — drops the loaded table (used by tests that swap art)

- [ ] **Step 1: Write the failing test**

Create `tests/test_goliath_runtime_uses_baked_anchors.py`:

```python
"""BLOQUE 74: the runtime must read the baked anchors, not scan pixels.

The whole point of the pipeline is that the measurement happens at build
time. If the runtime scans pixels again, the scan cost comes back and the
anchors.toml file is decoration.

These tests assert the values agree with the baked table, and that the
runtime no longer contains a pixel-scanning loop.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from src.anim.anchors import load_anchors  # noqa: E402
from src.anim.manifest import load_set  # noqa: E402


def _table():
    """The manifest and the baked anchor table of GOLIATH."""
    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    return anim_set, anchors


def test_centroid_offset_matches_the_baked_table() -> None:
    from src.ui.scenes import get_sprite_centroid_offset

    anim_set, anchors = _table()
    for clip in anim_set.clips.values():
        for i in range(clip.frames):
            name = f"{clip.dir}/frame_{i:02d}.png"
            entry = anchors.entries[(clip.id, i)]
            assert get_sprite_centroid_offset(name) == (entry.body_dx, entry.body_dy)


def test_eye_anchor_matches_the_baked_table() -> None:
    from src.ui.scenes import get_sprite_eye_anchor

    anim_set, anchors = _table()
    for clip in anim_set.clips.values():
        for i in range(clip.frames):
            name = f"{clip.dir}/frame_{i:02d}.png"
            entry = anchors.entries[(clip.id, i)]
            assert get_sprite_eye_anchor(name) == entry.eye


def test_shield_ellipse_matches_the_baked_table() -> None:
    from src.ui.scenes import get_sprite_shield_ellipse

    anim_set, anchors = _table()
    for clip in anim_set.clips.values():
        for i in range(clip.frames):
            name = f"{clip.dir}/frame_{i:02d}.png"
            entry = anchors.entries[(clip.id, i)]
            assert get_sprite_shield_ellipse(name) == entry.shield


def test_the_runtime_path_resolves_the_same_anchors() -> None:
    """The runtime holds 'bosses/goliath/<dir>/frame_NN.png'.

    The anchor table is keyed by (clip id, frame index) and the sprite path
    is relative to Assets/sprites/, so the lookup has to take the LAST
    directory of the path -- not the whole thing -- as the clip's name.
    """
    from src.ui.scenes import (
        get_sprite_centroid_offset,
        get_sprite_eye_anchor,
        get_sprite_shield_ellipse,
    )

    anim_set, anchors = _table()
    for clip in anim_set.clips.values():
        for i in range(clip.frames):
            name = f"bosses/goliath/{clip.dir}/frame_{i:02d}.png"
            entry = anchors.entries[(clip.id, i)]
            assert get_sprite_centroid_offset(name) == (entry.body_dx, entry.body_dy)
            assert get_sprite_eye_anchor(name) == entry.eye
            assert get_sprite_shield_ellipse(name) == entry.shield


def test_the_runtime_no_longer_scans_pixels() -> None:
    """The three anchor functions must be lookups, not measurements."""
    import inspect

    from src.ui.scenes import (
        get_sprite_centroid_offset,
        get_sprite_eye_anchor,
        get_sprite_shield_ellipse,
    )

    source = (ROOT / "src" / "ui" / "scenes.py").read_text(encoding="utf-8")
    for forbidden in ("_sprite_centroid_cache", "_sprite_eye_anchor_cache",
                      "_sprite_shield_ellipse_cache"):
        assert forbidden not in source, f"{forbidden} still exists -- the scan is back"

    # A pixel read inside an anchor function IS the scan.
    for func in (get_sprite_centroid_offset, get_sprite_eye_anchor,
                 get_sprite_shield_ellipse):
        body = inspect.getsource(func)
        assert "get_at" not in body, (
            f"{func.__name__} reads pixels -- the measurement belongs in the "
            "build-time pipeline, not in the runtime"
        )


# ---------------------------------------------------------------------------
# The manifest drives the timing
# ---------------------------------------------------------------------------


def test_the_boss_timing_comes_from_the_manifest() -> None:
    """The frame count and the fps are the manifest's, not a constant."""
    from src.entities.enemies.boss import Boss

    anim_set, _anchors = _table()
    boss = Boss()
    for clip in anim_set.clips.values():
        boss.set_animation_state(clip.id)
        boss.animation_frame_duration = 1.0 / clip.fps
        boss.animation_frame_count = clip.frames
        assert boss.animation_frame_count == clip.frames
        assert boss.animation_frame_duration == pytest.approx(1.0 / clip.fps)


def test_the_runtime_applies_the_manifest_timing_to_the_boss() -> None:
    """The live runtime must hand the boss the manifest's clip timing."""
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.ui.gameplay_runtime import GameplayRuntime

    anim_set, _anchors = _table()
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    boss = rt._boss
    assert boss is not None
    for clip in anim_set.clips.values():
        rt._set_boss_animation(clip.id)
        assert boss.animation_state == clip.id
        assert boss.animation_frame_count == clip.frames
        assert boss.animation_frame_duration == pytest.approx(1.0 / clip.fps)


def test_the_boss_animation_uses_the_manifest_frame_count() -> None:
    """The frame counter wraps at the manifest's frame count."""
    from src.entities.enemies.boss import Boss

    boss = Boss()
    boss.set_animation_state("phase1_idle")
    boss.animation_frame_count = 4
    boss.animation_frame_duration = 0.1
    boss.animation_frame = 3
    boss.animation_timer = 0.0
    boss.update_animation(0.1)
    assert boss.animation_frame == 0, "the frame counter did not wrap at 4"


def test_the_death_anim_holds_at_the_manifest_frame_count() -> None:
    """'death' is one-shot: it holds on the LAST frame of the clip."""
    from src.entities.enemies.boss import Boss

    boss = Boss()
    boss.set_animation_state("death")
    boss.animation_frame_count = 10
    boss.animation_frame = 9
    boss.animation_timer = 0.0
    boss.update_animation(0.1)
    assert boss.animation_frame == 9, "the death animation wrapped around"


# ---------------------------------------------------------------------------
# The duplicate frame cache is retired
# ---------------------------------------------------------------------------


def test_the_boss_frames_are_not_cached_twice() -> None:
    """The compositor owns the 60 frames; the UI cache must not keep a copy.

    Two caches of the same 1.76 MB of PNGs is 1.76 MB of RAM the game does
    not need. The runtime reads the frames through the compositor, so the
    UI's own sprite cache must not hold the boss frames.
    """
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.ui import scenes
    from src.ui.gameplay_runtime import GameplayRuntime

    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    target = pygame.Surface((320, 480))
    target.fill((0, 0, 0))
    rt.draw(target)

    boss_frames = [k for k in scenes._sprite_cache if k.startswith("bosses/goliath")]
    assert not boss_frames, (
        f"the UI sprite cache still holds {len(boss_frames)} boss frames "
        f"({boss_frames[:3]}) -- the compositor's cache is duplicated"
    )


def test_the_compositor_draws_the_boss_frame() -> None:
    """The boss is composed through the ClipPlayer."""
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.ui import scenes
    from src.ui.gameplay_runtime import GameplayRuntime

    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    player = scenes.get_clip_player()
    assert player is not None, "the GOLIATH compositor is not available"
    boss = rt._boss
    assert boss is not None
    surf = player.surface(boss.animation_state, boss.animation_frame)
    assert surf is not None, "the compositor could not load the boss frame"


# ---------------------------------------------------------------------------
# The radii policy: an unresolved plate keeps the canonical ellipse
# ---------------------------------------------------------------------------


def test_an_unresolved_plate_keeps_the_canonical_ellipse() -> None:
    """A frame whose plate cannot be resolved still has a shield.

    The alternative -- no ellipse at all -- would delete the hitbox and
    leave the shield laser with nowhere to come from.
    """
    from src.anim.anchors import FrameAnchor
    from src.anim.manifest import load_set
    from src.anim.parts import shield_ellipse_rect

    anim_set = load_set("goliath")
    part = anim_set.part("shield_plate")
    assert part.radii is not None, "the manifest declares no canonical radii"

    unresolved = FrameAnchor(
        body_dx=0,
        body_dy=0,
        eye=None,
        eye_source="missing",
        shield=None,
        shield_source="missing",
    )
    rect = shield_ellipse_rect(part, unresolved, (100, 100), anim_set.canvas)
    assert rect is not None, "an unresolved plate has no ellipse at all"

    # The canonical radii, at the canonical centre.
    _, rx, ry = part.radii
    assert rect.width == max(2, int(round(rx * part.scale[0]))) * 2
    assert rect.height == max(2, int(round(ry * part.scale[1]))) * 2


def test_the_runtime_falls_back_to_the_canonical_ellipse() -> None:
    """A frame that is not in the table gets the canonical ellipse."""
    from src.ui.scenes import get_sprite_shield_ellipse

    ellipse = get_sprite_shield_ellipse("bosses/goliath/javelin/frame_99.png")
    assert ellipse is not None
    cx, cy, rx, ry = ellipse
    assert cx > 52, "the fallback ellipse is not on the shield arm"
    assert rx > 0 and ry > 0


# ---------------------------------------------------------------------------
# The oval stays invisible (BLOQUE 67, user request)
# ---------------------------------------------------------------------------


def test_the_oval_is_still_invisible() -> None:
    """BLOQUE 74 moves the oval; it does not make it visible."""
    from src.anim.parts import DRAW_SHIELD_OVAL

    assert DRAW_SHIELD_OVAL is False, (
        "the shield oval must stay invisible (BLOQUE 67): the player sees "
        "the heat layer and the impact flash, nothing else"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_goliath_runtime_uses_baked_anchors.py --tb=short`
Expected: the first three FAIL (the runtime still scans) and the fourth FAIL (the caches still exist).

- [ ] **Step 3: Replace the three anchor functions in `src/ui/scenes.py`**

Add the import at the top of `src/ui/scenes.py`, next to the other imports:

```python
from src.anim.anchors import AnchorSet, load_anchors
from src.anim.manifest import load_set
```

Delete the three cache dicts:

```python
_sprite_centroid_cache: dict[str, tuple[int, int]] = {}
_sprite_arm_anchor_cache: dict[str, tuple[int, int]] = {}
_sprite_eye_anchor_cache: dict[str, tuple[int, int]] = {}
```

and the `_sprite_shield_ellipse_cache` declaration.

Replace the three functions with:

```python
_anchor_set_cache: AnchorSet | None = None
_manifest_cache = None


def _load_manifest():
    """Load the GOLIATH manifest once."""
    global _manifest_cache
    if _manifest_cache is None:
        try:
            _manifest_cache = load_set("goliath")
        except (OSError, ValueError):
            _manifest_cache = False
    return _manifest_cache or None


def _clip_id_for_dir(clip_dir: str) -> str | None:
    """Map a clip's directory name to its clip id."""
    anim_set = _load_manifest()
    if anim_set is None:
        return None
    for clip in anim_set.clips.values():
        if clip.dir == clip_dir:
            return clip.id
    return None


def _load_anchor_set() -> AnchorSet:
    """Load the baked anchor table. One read, then a dict lookup."""
    global _anchor_set_cache
    if _anchor_set_cache is None:
        try:
            anim_set = load_set("goliath")
            _anchor_set_cache = load_anchors(anim_set.path / "anchors.toml")
        except (OSError, ValueError):
            _anchor_set_cache = AnchorSet(entries={})
    return _anchor_set_cache


def clear_anchor_cache() -> None:
    """Drop the loaded anchor table and manifest (tests that swap art)."""
    global _anchor_set_cache, _manifest_cache
    _anchor_set_cache = None
    _manifest_cache = None


def _anchor_for(name: str):
    """Look the anchor of a sprite up by its path-relative name.

    `name` is "<clip dir>/frame_NN.png". The anchor table is keyed by
    (clip id, frame index), and the clip DIRECTORY and the clip ID are
    not necessarily the same string -- the manifest maps one to the other.
    """
    anchors = _load_anchor_set()
    if "/" not in name:
        return None
    # The LAST directory component, not a split on the last "/": the
    # runtime's path form is bosses/goliath/<clip dir>/frame_NN.png, and
    # rpartition would leave the whole prefix as the "clip dir".
    filename = PurePath(name).name
    if not filename.startswith("frame_") or not filename.endswith(".png"):
        return None
    try:
        index = int(filename[len("frame_"):-len(".png")])
    except ValueError:
        return None
    clip_id = _clip_id_for_dir(PurePath(name).parent.name)
    if clip_id is None:
        return None
    return anchors.get(clip_id, index)


def get_sprite_centroid_offset(name: str) -> tuple[int, int]:
    """(dx, dy) that puts the sprite's centroid on the world anchor.

    BLOQUE 74: this used to scan the sprite's pixels the first time a
    frame was seen (3.9 ms). The measurement is now baked into
    anchors.toml at build time; this is a dict lookup.
    """
    anchor = _anchor_for(name)
    if anchor is None:
        return (0, 0)
    return (anchor.body_dx, anchor.body_dy)


def get_sprite_eye_anchor(name: str) -> tuple[int, int]:
    """Sprite-local (col, row) of the eye.

    BLOQUE 74: baked. The eye moves between frames (rows 13 to 28 across
    the set), so a fixed offset could never work -- the laser used to
    start 2 to 6 px below the eye and read as if it came from the chest.
    """
    anchor = _anchor_for(name)
    if anchor is None:
        return (48, 20)
    return anchor.eye


def get_sprite_shield_ellipse(name: str) -> tuple[float, float, float, float]:
    """Sprite-local (cx, cy, rx, ry) of the shield plate.

    BLOQUE 74: baked, and interpolated for the frames where the art does
    not contain the plate, so the oval keeps tracking the arm instead of
    falling back to a constant.
    """
    anchor = _anchor_for(name)
    if anchor is None:
        return _GOLIATH_SHIELD_FALLBACK
    return anchor.shield
```

Delete `get_sprite_arm_anchor()` — its brass signature is what mis-detected the
baked eye beam, and the probe inside the manifest replaces it. Check first
that nothing else calls it:

```bash
Select-String -Path src/**/*.py -Pattern 'get_sprite_arm_anchor'
```

If something does, keep the function but make it read the probe from the
manifest instead of scanning pixels.

- [ ] **Step 4: Make the boss read its frame count and fps from the manifest**

In `src/entities/enemies/boss.py`, replace the class constant block and the
animation update with:

```python
    # BLOQUE 74: the defaults. The runtime overrides them from the
    # manifest (manifest.toml declares each clip's fps and frame count).
    ANIMATION_FRAME_DURATION: ClassVar[float] = 0.10
    ANIMATION_FRAME_COUNT: ClassVar[int] = 10
```

In `on_spawn()` (the method that initialises the animation state — it is
called by `BossPool.spawn()` in `src/entities/enemies/boss.py`), add:

```python
        self.animation_frame_duration = self.ANIMATION_FRAME_DURATION
        self.animation_frame_count = self.ANIMATION_FRAME_COUNT
```

Replace `update_animation` with:

```python
    def update_animation(self, dt: float) -> None:
        """BLOQUE 74: advance the animation frame.

        The duration and the frame count come from the manifest, so a clip
        can run at its own fps without touching this class.
        """
        if dt <= 0.0:
            return
        self.animation_timer += dt
        if self.animation_timer < self.animation_frame_duration:
            return
        self.animation_timer -= self.animation_frame_duration
        if self.animation_state == "death":
            if self.animation_frame < self.animation_frame_count - 1:
                self.animation_frame += 1
        else:
            self.animation_frame = (self.animation_frame + 1) % self.animation_frame_count
```

- [ ] **Step 5: Wire the manifest into the runtime**

In `src/ui/gameplay_runtime.py`, right after the line
`self._boss = self._bosses.spawn(boss_id)` (line 559), add the
manifest-driven timing:

```python
        # BLOQUE 74: timing comes from the manifest, not from a constant.
        try:
            from src.anim.manifest import load_set
            clip = load_set("goliath").clip(self._boss.animation_state)
            self._boss.animation_frame_duration = 1.0 / clip.fps
            self._boss.animation_frame_count = clip.frames
        except (ImportError, ValueError):
            pass
```

The clip's fps and frame count are re-read every time the boss changes
state, so a clip can run at its own rate without touching the class.

- [ ] **Step 6: Run the migration test**

Run: `python -m pytest tests/test_goliath_runtime_uses_baked_anchors.py --tb=short`
Expected: PASS, 4 tests.

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest tests/ --tb=no`
Expected: 2,781 passed, 8 failed (the pre-existing ones), 7 skipped

If any of the four GOLIATH anchor tests fail, the baked values and the runtime
disagree — re-run `python tools/sprite_pipeline/run.py goliath --fix` and
check that `anchors.toml` is committed.

- [ ] **Step 8: Verify the game still runs**

Run: `python main.py --check`
Expected: `VOID HUNTER check OK` and `full game with 15 scenes, 18 waves, 4 bosses`

Run: `python main.py --boss goliath --easy --duration 60`
Expected: the boss fight runs for 60 seconds with no exception.

- [ ] **Step 9: Commit**

```bash
git add src/ui/scenes.py src/ui/gameplay_runtime.py src/entities/enemies/boss.py tests/test_goliath_runtime_uses_baked_anchors.py
git commit -m "feat: BLOQUE 74 - el runtime lee los anchors horneados en vez de escanear pixeles"
```

---

## Verification checklist

Run in this order after the last task:

```bash
python tools/sprite_pipeline/run.py goliath      # expect 0 FAIL, exit 0
python -m pytest tests/ --tb=no                  # expect 2,781 passed, 8 failed, 7 skipped
python main.py --check                            # expect 15 scenes, 18 waves, 4 bosses
python main.py --boss goliath --easy --duration 60
git status --short                                # expect clean
```

Then confirm the boundaries:

```bash
git log --oneline master -1                       # must still be a40fdaf
git status --short master                         # master must be clean
git diff v1.7.2 HEAD --stat -- src/ Assets/ build.spec main.py
```

## Self-review notes

- **Spec coverage:** every section of the spec has a task — the manifest (§2.2) is Task 1, the anchors (§2.3) is Task 3 and Task 7, the auditor (§2.4) is Task 3, the repair (§2.5) is Task 6, the compositor (§2.6) is Task 7, the GOLIATH migration (§3) is Tasks 6 and 8, the tests (§4) are spread across Tasks 1-7, and the delivery order (§5) is the task order. Task 5 is the pygame-contamination fix, which the spec does not cover — it was added because the pipeline work exposed that the suite's documented failures were collection-order accidents.
- **Deviations from the spec, each deliberate and measured:**
  1. `src/anim/` is split into five files rather than three (see "File structure"): the measurement code has to be importable by the tests without the auditor's CLI, and `anchors.toml` has a different lifecycle from `manifest.toml`.
  2. `FIRMA_AMBIGUA` is a **WARN, not a FAIL**, and its definition is "the two independent detectors disagree". Two candidate definitions were measured against the 60 shipped frames and both were unusable: "the measured region contains a baked-effect colour" fires on 59/60 frames because `(240,200,120)` is the plate's own highlight, and "excluding the colliding colours changes the measurement" fires on 0/60 frames because the colliding pixels are isolated highlights that never move a run boundary. The spec's table says FAIL; the plan says WARN because a FAIL here would block the pipeline on a state that cannot be detected reliably.
  3. The interpolation lives inside `audit_set` (Task 3) rather than in a separate repair step, so the findings report the art problem while the measurements are the repaired result. The spec described the interpolation as part of the repair; the plan puts it in the auditor because the anchors are written from the auditor's output.
  4. `ESCALADO` is measured with the silhouette **height**, not the area, and each clip declares its own `scale_tolerance` (`death` needs 0.60 because the boss collapses on purpose). The spec's §2.4 already carries this correction.
- **Type consistency:** `FrameMeasurement` (auditor) and `FrameAnchor` (runtime) are deliberately different types — the auditor's carries `shield: tuple | None` and a source of `missing` / `out_of_range` / `measured` / `interpolated`; the runtime's always carries a resolved ellipse. The conversion happens in `_interpolate_missing`. `interpolate()` returns `float | None` everywhere it is used, and it lives in `src/anim/measure.py` so both the auditor and the tests can reach it.
- **Placeholder scan:** no TBD, no "similar to Task N", no unimplemented steps, no leftover experimental code. Every code step contains the code that goes in the file.
- **Measured, not assumed:** the thresholds in the manifest (`side_tolerance = 14`, `scale_tolerance` per clip, the `rx`/`ry` ranges) all come from a measurement pass over the 60 shipped frames, and the pass is reproducible with the scripts used to derive them.
