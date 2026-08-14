"""WaypointPath \u2014 a list of (x, y) waypoints the ship follows in order (BLOQUE 58.6x).

Each pair of consecutive waypoints is a straight line segment. The ship
moves at constant speed (px/s) along the path. When the last waypoint is
reached, the path is "complete" and the follower stops.

Used for sharp turns, multi-stop routes, and segments where the ship
needs to LINGER at a waypoint. Paired with BezierPath in HybridPath.
"""
from __future__ import annotations

import math
from typing import NamedTuple

from src.movement.bezier import Point


class WaypointPath:
    """A straight-line waypoint path with constant speed.

    Args:
        waypoints: list of (x, y) points, in order. Must have >= 1.
        speed_px_s: speed in pixels per second. Must be > 0.
        linger_s: optional per-waypoint pause (s). linger_s[i] is the
                  pause AFTER reaching waypoint i. Defaults to all 0.
    """

    __slots__ = ("waypoints", "speed_px_s", "linger_s", "_segment_lengths",
                 "_cumulative_lengths", "_total_length")

    def __init__(
        self,
        waypoints: list[Point | tuple[float, float]],
        speed_px_s: float = 120.0,
        linger_s: list[float] | None = None,
    ) -> None:
        if not waypoints:
            raise ValueError("waypoints cannot be empty")
        if speed_px_s <= 0.0:
            raise ValueError(f"speed_px_s must be > 0, got {speed_px_s}")
        # Normalize to Point
        self.waypoints: list[Point] = [
            p if isinstance(p, Point) else Point(p[0], p[1]) for p in waypoints
        ]
        self.speed_px_s = speed_px_s
        n = len(self.waypoints)
        self.linger_s: list[float] = (
            list(linger_s) if linger_s is not None else [0.0] * n
        )
        if len(self.linger_s) != n:
            raise ValueError(
                f"linger_s length ({len(self.linger_s)}) != waypoints length ({n})"
            )
        # Pre-compute segment lengths for fast position lookup
        self._segment_lengths: list[float] = []
        for i in range(n - 1):
            a = self.waypoints[i]
            b = self.waypoints[i + 1]
            self._segment_lengths.append(math.hypot(b.x - a.x, b.y - a.y))
        # Cumulative lengths: cumulative_lengths[i] = total distance traveled
        # at the START of segment i (i.e., at waypoint i).
        self._cumulative_lengths: list[float] = [0.0]
        acc = 0.0
        for L in self._segment_lengths:
            acc += L
            self._cumulative_lengths.append(acc)
        self._total_length: float = acc

    @property
    def total_length(self) -> float:
        return self._total_length

    @property
    def total_duration_s(self) -> float:
        """Total time to traverse the path, including all linger pauses."""
        move_t = self._total_length / self.speed_px_s
        linger_t = sum(self.linger_s)
        return move_t + linger_t

    def position_at_distance(self, distance: float) -> tuple[Point, Point]:
        """Walk along the path by `distance` (px) and return (point, tangent).

        The tangent is the unit vector along the current segment. If at a
        linger point, tangent is zero.
        """
        if distance <= 0.0:
            return self.waypoints[0], Point(0.0, 0.0)
        if distance >= self._total_length:
            return self.waypoints[-1], Point(0.0, 0.0)
        # Find the segment that contains `distance`
        for i in range(len(self._segment_lengths)):
            seg_start = self._cumulative_lengths[i]
            seg_end = self._cumulative_lengths[i + 1]
            if distance <= seg_end:
                seg_len = self._segment_lengths[i]
                if seg_len <= 0.0:
                    # Degenerate segment (two waypoints at same spot)
                    return self.waypoints[i], Point(0.0, 0.0)
                t = (distance - seg_start) / seg_len
                a = self.waypoints[i]
                b = self.waypoints[i + 1]
                pt = Point(
                    a.x + (b.x - a.x) * t,
                    a.y + (b.y - a.y) * t,
                )
                dx = (b.x - a.x) / seg_len
                dy = (b.y - a.y) / seg_len
                return pt, Point(dx, dy)
        # Shouldn't reach here
        return self.waypoints[-1], Point(0.0, 0.0)

    def is_complete(self, distance: float) -> bool:
        return distance >= self._total_length
