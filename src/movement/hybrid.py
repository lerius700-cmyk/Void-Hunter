"""HybridPath \u2014 concatenate BezierPath and WaypointPath segments (BLOQUE 58.6x).

The user requested a hybrid system: bezier for smooth sweeps, waypoints
for sharp turns. HybridPath lets us mix them in one continuous path.

Each segment has a duration_s. The total path duration is the sum of
all segment durations. Parameter t in [0, 1] maps to a position along
the entire path.
"""
from __future__ import annotations

import math
from typing import Union

from src.movement.bezier import BezierPath, Point
from src.movement.waypoint import WaypointPath


Segment = Union[BezierPath, WaypointPath]


class HybridPath:
    """Concatenated path of Bezier + Waypoint segments.

    The simplest way to build one is from_segments([seg1, seg2, ...]).
    Each segment's `duration_s` (or `total_duration_s` for waypoints)
    is its slice of the total path time.
    """

    __slots__ = ("segments", "segment_durations", "_total_duration")

    def __init__(
        self,
        segments: list[Segment],
        segment_durations: list[float] | None = None,
    ) -> None:
        if not segments:
            raise ValueError("segments cannot be empty")
        # Default: use each segment's intrinsic duration
        if segment_durations is None:
            segment_durations = [self._intrinsic_duration(s) for s in segments]
        if len(segment_durations) != len(segments):
            raise ValueError(
                f"segment_durations length ({len(segment_durations)}) != "
                f"segments length ({len(segments)})"
            )
        if any(d <= 0.0 for d in segment_durations):
            raise ValueError("all segment durations must be > 0")
        self.segments: list[Segment] = list(segments)
        self.segment_durations: list[float] = list(segment_durations)
        self._total_duration: float = sum(segment_durations)

    @staticmethod
    def _intrinsic_duration(seg: Segment) -> float:
        if isinstance(seg, BezierPath):
            # Default: 1 second per 80 px of curve (avg arcade ship speed)
            return max(0.5, seg.length_estimate / 80.0)
        if isinstance(seg, WaypointPath):
            return seg.total_duration_s
        raise TypeError(f"unknown segment type: {type(seg).__name__}")

    @classmethod
    def from_segments(cls, segments: list[Segment]) -> "HybridPath":
        return cls(segments, None)

    @property
    def total_duration_s(self) -> float:
        return self._total_duration

    def _segment_for_t(self, t: float) -> tuple[int, float, float]:
        """Return (segment_index, segment_t, distance_into_path).

        t is global [0, 1]. segment_t is local [0, 1] within that segment.
        """
        if t <= 0.0:
            return 0, 0.0, 0.0
        if t >= 1.0:
            return len(self.segments) - 1, 1.0, self._total_duration
        target = t * self._total_duration
        elapsed = 0.0
        for i, dur in enumerate(self.segment_durations):
            if elapsed + dur >= target:
                local = (target - elapsed) / dur
                return i, max(0.0, min(1.0, local)), elapsed
            elapsed += dur
        return len(self.segments) - 1, 1.0, elapsed

    def position_at(self, t: float) -> Point:
        idx, local_t, _ = self._segment_for_t(t)
        seg = self.segments[idx]
        if isinstance(seg, BezierPath):
            return seg.position_at(local_t)
        if isinstance(seg, WaypointPath):
            dist = local_t * seg.total_length
            pt, _ = seg.position_at_distance(dist)
            return pt
        raise TypeError(f"unknown segment type: {type(seg).__name__}")

    def tangent_at(self, t: float) -> Point:
        """Return the tangent at parameter t. Bezier: raw derivative.
        Waypoint: unit vector along current segment.

        For multi-segment paths, the tangent is in screen coordinates.
        """
        idx, local_t, _ = self._segment_for_t(t)
        seg = self.segments[idx]
        if isinstance(seg, BezierPath):
            return seg.tangent_at(local_t)
        if isinstance(seg, WaypointPath):
            dist = local_t * seg.total_length
            _, tan = seg.position_at_distance(dist)
            return tan
        raise TypeError(f"unknown segment type: {type(seg).__name__}")

    def is_complete(self, t: float) -> bool:
        return t >= 1.0

    @staticmethod
    def straighten(start: Point, end: Point, speed_px_s: float = 120.0) -> "HybridPath":
        """Build a single-segment straight-line path from start to end.

        Convenience for the common case. Useful for backward compat with
        the old "enemies move in straight line" behavior \u2014 wrapped as a
        HybridPath so the same follower code works.
        """
        distance = math.hypot(end.x - start.x, end.y - start.y)
        dur = distance / speed_px_s
        seg = WaypointPath([start, end], speed_px_s=speed_px_s)
        return HybridPath([seg], [dur])
