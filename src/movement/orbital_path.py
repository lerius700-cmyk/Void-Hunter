"""BLOQUE 58.13: OrbitalPath — 4-segment orbital path (figure-of-breathing).

Used by OSCILLATING_BUTTERFLY for "butterfly" choreography. Ships orbit
a center point using 4 cubic bezier segments, each a quarter of the
orbit. The bezier approximation is good enough at the playfield scale
(320x480) — exact circular motion would need arc-length parameterization.

Bezier quarter-circle approximation:
  For a unit circle quadrant from (1, 0) to (0, 1), the magic constant
  k = 4/3 * (sqrt(2) - 1) ≈ 0.5523 gives a very close approximation.
  The control points are:
    start: (1, 0)
    cp1:   (1, k)
    cp2:   (k, 1)
    end:   (0, 1)
  This produces a curve that deviates from the true circle by < 0.02%.
"""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


# Magic constant for bezier quarter-circle approximation
_K = (4.0 / 3.0) * (math.sqrt(2.0) - 1.0)  # ≈ 0.5523


class OrbitalPath:
    """4-segment orbital path around a center point.

    Args:
        center: (cx, cy) — orbital center
        radius_x: horizontal radius of orbit
        radius_y: vertical radius of orbit
        duration_s: total time for one full orbit (default 6.0)
        rotation_deg: starting angle in degrees (default 0)
    """

    __slots__ = ("_path", "_total_duration_s")

    def __init__(
        self,
        center: tuple[float, float],
        radius_x: float,
        radius_y: float,
        duration_s: float = 6.0,
        rotation_deg: float = 0,
    ) -> None:
        if radius_x <= 0 or radius_y <= 0:
            raise ValueError("radius_x and radius_y must be > 0")
        if duration_s <= 0:
            raise ValueError("duration_s must be > 0")

        cx, cy = center
        segments = self._build_quarters(cx, cy, radius_x, radius_y, rotation_deg)
        seg_dur = duration_s / 4.0
        self._path = HybridPath(segments, [seg_dur] * 4)
        self._total_duration_s = duration_s

    @staticmethod
    def _build_quarters(
        cx: float, cy: float,
        rx: float, ry: float,
        rotation_deg: float,
    ) -> list[BezierPath]:
        """Build 4 quarter-orbit bezier segments.

        Without rotation, the orbit starts at (cx + rx, cy) (right side)
        and goes counterclockwise: right -> top -> left -> bottom -> right.
        With rotation, we offset the start angle.
        """
        rot_rad = math.radians(rotation_deg)
        kx = _K * rx
        ky = _K * ry

        def pt(angle_deg: float) -> Point:
            """Point on the orbit at the given angle (degrees, 0 = right, CCW).

            In screen coordinates (Y down), the first quarter (0 -> 90 deg)
            goes from (cx+rx, cy) [right] to (cx, cy-ry) [top], so we use
            `cy - ry*sin(a)` instead of `cy + ry*sin(a)`.
            """
            a = math.radians(angle_deg) + rot_rad
            return Point(cx + rx * math.cos(a), cy - ry * math.sin(a))

        def cp_for_quarter(start_angle: float, end_angle: float) -> tuple[Point, Point]:
            """Control points for the quarter from start_angle to end_angle.

            For a CCW quarter in screen coordinates: cp1 is the start
            tangent (screen-CCW = math-CW, i.e. direction (-sin a, -cos a)),
            cp2 is the reverse-tangent at end.
            """
            a_start = math.radians(start_angle) + rot_rad
            a_end = math.radians(end_angle) + rot_rad
            cp1 = Point(
                cx + rx * math.cos(a_start) - kx * math.sin(a_start),
                cy - ry * math.sin(a_start) - ky * math.cos(a_start),
            )
            cp2 = Point(
                cx + rx * math.cos(a_end) + kx * math.sin(a_end),
                cy - ry * math.sin(a_end) + ky * math.cos(a_end),
            )
            return cp1, cp2

        quarters = [
            (0, 90),    # right -> top
            (90, 180),  # top -> left
            (180, 270), # left -> bottom
            (270, 360), # bottom -> right
        ]
        segments: list[BezierPath] = []
        for start_a, end_a in quarters:
            p0 = pt(start_a)
            p3 = pt(end_a)
            cp1, cp2 = cp_for_quarter(start_a, end_a)
            segments.append(BezierPath(p0, cp1, cp2, p3))
        return segments

    def get_path(self) -> HybridPath:
        """Return the 4-segment HybridPath that traces the orbit."""
        return self._path

    @property
    def total_duration_s(self) -> float:
        return self._total_duration_s
