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
    """Read anchors.toml."""
    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    entries: dict[tuple[str, int], FrameAnchor] = {}
    for entry in raw.get("anchors", []):
        key = (str(entry["clip"]), int(entry["frame"]))
        eye = entry.get("eye", (0, 0))
        shield = entry.get("shield", (0.0, 0.0, 0.0, 0.0))
        eye_source = str(entry.get("eye_source", "measured"))
        shield_source = str(entry.get("shield_source", "measured"))
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
