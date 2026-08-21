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

    __slots__ = ("segments", "segment_durations", "_total_duration",
                 "_arc_lengths", "_arc_cumulative", "_total_arc_length")

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
        # BLOQUE 58.next: pre-compute arc lengths per segment for distance-based motion.
        self._build_arc_table()

    def _segment_arc_length(self, seg: Segment) -> float:
        """Total arc length of one segment."""
        if isinstance(seg, BezierPath):
            return seg.total_arc_length
        if isinstance(seg, WaypointPath):
            return seg.total_length
        raise TypeError(f"unknown segment type: {type(seg).__name__}")

    def _build_arc_table(self) -> None:
        """Pre-compute per-segment arc length and cumulative offsets.

        _arc_lengths[i]    = arc length of segment i
        _arc_cumulative[i] = arc length at the START of segment i
                            (cumulative sum, 0-indexed at start of seg 0)
        _total_arc_length  = sum of all segment arc lengths
        """
        n = len(self.segments)
        self._arc_lengths: list[float] = [self._segment_arc_length(s) for s in self.segments]
        cum: list[float] = [0.0] * (n + 1)
        for i in range(n):
            cum[i + 1] = cum[i] + self._arc_lengths[i]
        self._arc_cumulative: list[float] = cum
        self._total_arc_length: float = cum[-1]

    @property
    def total_arc_length(self) -> float:
        """Total arc length of the entire HybridPath (sum of segments)."""
        return self._total_arc_length

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

    def _segment_for_s(self, s: float) -> tuple[int, float]:
        """BLOQUE 58.next: return (segment_index, local_distance_in_segment)
        for the given global arc length s in [0, total_arc_length]."""
        if s <= 0.0:
            return 0, 0.0
        if s >= self._total_arc_length:
            last = len(self.segments) - 1
            return last, self._arc_lengths[last]
        for i in range(len(self.segments)):
            seg_start = self._arc_cumulative[i]
            seg_end = self._arc_cumulative[i + 1]
            if s <= seg_end:
                return i, s - seg_start
        last = len(self.segments) - 1
        return last, self._arc_lengths[last]

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

    # ------------------------------------------------------------------
    # BLOQUE 58.next: distance-based API (constant speed in screen space)
    # ------------------------------------------------------------------

    def position_at_distance(self, s: float) -> Point:
        """Return the point at global arc length s in [0, total_arc_length].

        Dispatched per segment:
          - BezierPath: uses its pre-computed arc table
          - WaypointPath: walks the polyline by distance (already supported)
        """
        if s <= 0.0:
            return self.position_at(0.0)
        if s >= self._total_arc_length:
            return self.position_at(1.0)
        idx, local_s = self._segment_for_s(s)
        seg = self.segments[idx]
        if isinstance(seg, BezierPath):
            return seg.position_at_distance(local_s)
        if isinstance(seg, WaypointPath):
            pt, _ = seg.position_at_distance(local_s)
            return pt
        raise TypeError(f"unknown segment type: {type(seg).__name__}")

    def tangent_at_distance(self, s: float) -> Point:
        """Return the unnormalized tangent at global arc length s.

        Bezier: raw derivative at the local t corresponding to s.
        Waypoint: unit vector along the current segment.
        """
        if s <= 0.0:
            return self.tangent_at(0.0)
        if s >= self._total_arc_length:
            return self.tangent_at(1.0)
        idx, local_s = self._segment_for_s(s)
        seg = self.segments[idx]
        if isinstance(seg, BezierPath):
            return seg.tangent_at_distance(local_s)
        if isinstance(seg, WaypointPath):
            _, tan = seg.position_at_distance(local_s)
            return tan
        raise TypeError(f"unknown segment type: {type(seg).__name__}")

    def is_complete_by_distance(self, s: float) -> bool:
        return s >= self._total_arc_length

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
