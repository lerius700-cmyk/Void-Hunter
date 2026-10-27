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

import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SETS_ROOT = ROOT / "Assets" / "sprites" / "bosses"


class ManifestError(ValueError):
    """The manifest is malformed, or it contradicts the assets on disk."""


@dataclass(frozen=True)
class DetectRule:
    """How to locate one feature inside a frame.

    `method` is "shape" (the feature is found by the outline of a solid
    block of pixels) or "color" (it is found by a colour signature).

    `probe` is an optional colour signature used ONLY to answer "which side
    is the feature on?". The shape rule cannot detect a turned-around
    character: it finds the ARM at the right of the band and measures a
    plausible-looking ellipse that is not the plate.
    """

    method: str
    side: str | None = None
    min_col: int = 0
    band: tuple[int, int] = (0, 0)
    col_range: tuple[int, int] = (0, 0)
    head_band: tuple[int, int] = (0, 0)
    r_min: int = 0
    g_min: int = 0
    b_max: int = 255
    rg_min: int = 0
    r_minus_b_min: int = 0
    rx_range: tuple[float, float] = (0.0, 0.0)
    ry_range: tuple[float, float] = (0.0, 0.0)
    exclude: tuple[tuple[int, int, int], ...] = ()
    probe: "DetectRule | None" = None

    @classmethod
    def from_dict(cls, raw: dict) -> "DetectRule":
        ranges = raw.get("ranges") or {}
        rx = tuple(ranges.get("rx", (0.0, 0.0)))
        ry = tuple(ranges.get("ry", (0.0, 0.0)))
        probe_raw = raw.get("probe")
        return cls(
            method=str(raw.get("method", "")),
            side=raw.get("side"),
            min_col=int(raw.get("min_col", 0)),
            band=tuple(raw.get("band", (0, 0))),
            col_range=tuple(raw.get("col_range", (0, 0))),
            head_band=tuple(raw.get("head_band", (0, 0))),
            r_min=int(raw.get("r_min", 0)),
            g_min=int(raw.get("g_min", 0)),
            b_max=int(raw.get("b_max", 255)),
            rg_min=int(raw.get("rg_min", 0)),
            r_minus_b_min=int(raw.get("r_minus_b_min", 0)),
            rx_range=(float(rx[0]), float(rx[1])),
            ry_range=(float(ry[0]), float(ry[1])),
            exclude=tuple(tuple(int(v) for v in c) for c in raw.get("exclude", ())),
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
    """

    id: str
    draw: str
    pivot: str
    z: int
    offset: tuple[int, int]
    scale: tuple[float, float]
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


def load_set(name: str, root: Path = SETS_ROOT) -> AnimSet:
    """Load and validate the manifest of the set called `name`."""
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
        if not clip_id:
            raise ManifestError(f"{name}: a clip has no id")
        if clip_id in clips:
            raise ManifestError(f"{name}: duplicate clip id {clip_id!r}")
        clips[clip_id] = Clip(
            id=clip_id,
            dir=entry.get("dir", clip_id),
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
        if not part_id:
            raise ManifestError(f"{name}: a part has no id")
        detect_raw = entry.get("detect")
        parts.append(
            Part(
                id=part_id,
                draw=str(entry.get("draw", "frames")),
                pivot=str(entry.get("pivot", "centroid")),
                z=int(entry.get("z", 0)),
                offset=tuple(entry.get("offset", (0, 0))),
                scale=tuple(entry.get("scale", (1.0, 1.0))),
                detect=DetectRule.from_dict(detect_raw) if detect_raw else None,
                on_missing=str(entry.get("on_missing", "fallback")),
            )
        )
    if not parts:
        raise ManifestError(f"{name}: the manifest declares no parts")

    return AnimSet(
        name=str(meta.get("name", name)),
        version=int(meta.get("version", 1)),
        canvas=tuple(meta.get("canvas", (0, 0))),
        anchor=tuple(meta.get("anchor", (0, 0))),
        sided=meta.get("sided"),
        path=path,
        clips=clips,
        parts=parts,
    )
