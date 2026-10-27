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

    "Malformed" covers a manifest with a SYNTAX error: `tomllib` raises
    `TOMLDecodeError`, which is a `ValueError` and NOT a `ManifestError`.
    The manifest is hand-edited, so a half-written file is a plausible
    state -- it must degrade, not break the game loop. This is the same
    contract as the UI's own loader (`src/ui/scenes.py::_load_manifest`):
    the two loaders must never disagree about what "unreadable" means.
    """
    key = (name, root)
    cached = _LOADED.get(key)
    if cached is not None:
        return cached
    try:
        anim_set = load_set(name, root)
    except (OSError, ValueError):
        # ValueError covers ManifestError (a subclass) AND
        # tomllib.TOMLDecodeError: a broken manifest degrades to None.
        return None
    _LOADED[key] = anim_set
    return anim_set


def clear_loaded_cache() -> None:
    """Drop the cached manifests.

    The runtime swaps the art at runtime (the tests do), so a manifest
    that changed on disk must be re-read. `src/ui/scenes.py` calls this
    from `clear_anchor_cache()`: the two caches hold the SAME file, so
    they have to be dropped together.
    """
    _LOADED.clear()


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
