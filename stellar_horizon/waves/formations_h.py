"""Formation helpers for horizontal play.

These wrap Void-Hunter's `FlightFormation` by rotating the offsets so the
formation points in the direction enemies move (-X, i.e. right-to-left).
"""
from __future__ import annotations

from src.movement import FlightFormation


def _v_offsets_rotated(count: int, spacing: float) -> list[tuple[float, float]]:
    """VH's V (apex -Y) rotated 90° CW -> wings at +X (apex points -X)."""
    base = FlightFormation.v(count, spacing)
    return [(y, -x) for (x, y) in base.offsets]


def v_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]:
    """V formation with apex pointing -X (enemies moving right→left)."""
    if count == 1:
        return [(0.0, 0.0)]
    return _v_offsets_rotated(count, spacing)


def line_horizontal(count: int = 5, spacing: float = 22.0) -> list[tuple[float, float]]:
    """Horizontal line of N slots, perpendicular to the direction of motion."""
    if count == 1:
        return [(0.0, 0.0)]
    half = (count - 1) * spacing / 2.0
    return [(-half + i * spacing, 0.0) for i in range(count)]


def diamond_pointing_left(count: int = 5, spacing: float = 20.0) -> list[tuple[float, float]]:
    """Diamond formation with vertex pointing -X."""
    if count == 1:
        return [(0.0, 0.0)]
    offsets: list[tuple[float, float]] = [(0.0, 0.0)]
    layer = 1
    while len(offsets) < count:
        offsets.append((-spacing * layer, 0.0))            # front (toward -X)
        if len(offsets) >= count: break
        offsets.append((-spacing * 0.5, -spacing * layer))  # top-front
        if len(offsets) >= count: break
        offsets.append((-spacing * 0.5, +spacing * layer))  # bottom-front
        if len(offsets) >= count: break
        offsets.append((+spacing * layer, 0.0))             # back
        layer += 1
    return offsets[:count]


def wedge_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]:
    """Wedge (> shape) with tip pointing -X."""
    if count == 1:
        return [(0.0, 0.0)]
    # VH's WEDGE rotated 90° CW: (x, y) -> (y, -x)
    base = FlightFormation.wedge(count, spacing)
    return [(y, -x) for (x, y) in base.offsets]
