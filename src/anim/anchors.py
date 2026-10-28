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
