"""PathFollower \u2014 advances a HybridPath over time and yields (x, y, vx, vy) (BLOQUE 58.6x).

A PathFollower is what an Enemy (or other entity) holds. Each frame the
follower is updated with dt seconds; it advances its internal t and
returns the current world position plus the current velocity vector.

The velocity is the tangent scaled by the segment's effective speed. This
lets the enemy face its motion direction (nose_angle = atan2(vy, vx)).
"""
from __future__ import annotations

from typing import Optional

from src.movement.bezier import Point
from src.movement.hybrid import HybridPath


class PathFollower:
    """Stateful follower that walks a HybridPath over time.

    Args:
        path: the HybridPath to follow
        t_offset: initial time offset in seconds (default 0). The follower
            starts at t = t_offset / path.total_duration_s. Use this for
            staggered entries (e.g., 5 ships entering a 6s path at 0s, 1s,
            2s, 3s, 4s).

    Usage:
        follower = PathFollower(some_hybrid_path)
        for dt in frame_deltas:
            x, y, vx, vy = follower.update(dt)
            entity.x, entity.y = x, y
    """

    __slots__ = ("path", "_t", "_complete", "_t_offset_s")

    def __init__(self, path: HybridPath, t_offset: float = 0.0) -> None:
        self.path: HybridPath = path
        self._t_offset_s: float = t_offset
        self._t: float = self._t_at_offset()
        self._complete: bool = False

    def _t_at_offset(self) -> float:
        if self.path.total_duration_s <= 0:
            return 0.0
        return min(1.0, max(0.0, self._t_offset_s / self.path.total_duration_s))

    @property
    def t(self) -> float:
        """Current parameter in [0, 1] along the path."""
        return self._t

    @property
    def is_complete(self) -> bool:
        return self._complete

    def reset(self) -> None:
        self._t = self._t_at_offset()
        self._complete = False

    def update(self, dt: float) -> tuple[Point, Point]:
        """Advance the follower by dt seconds.

        Returns:
            (position, velocity). Position is the current (x, y).
            Velocity is the tangent vector in screen coordinates \u2014 NOT
            normalized; its magnitude reflects local speed.
        """
        if self._complete or dt <= 0.0:
            # Stay at the last position; return zero velocity
            return self.path.position_at(self._t), Point(0.0, 0.0)
        new_t = self._t + dt / self.path.total_duration_s
        if new_t >= 1.0:
            self._t = 1.0
            self._complete = True
        else:
            self._t = new_t
        pos = self.path.position_at(self._t)
        tan = self.path.tangent_at(self._t)
        # Scale tangent by the effective speed of the current segment so
        # the velocity vector is in px/s and the entity can face it.
        speed = self._segment_speed()
        return pos, Point(tan.x * speed, tan.y * speed)

    def _segment_speed(self) -> float:
        """Effective speed in px/s for the current segment.

        For Bezier: derived from the segment's own duration vs length.
        For Waypoint: the path's own speed_px_s.
        """
        idx, _, _ = self.path._segment_for_t(self._t)
        seg = self.path.segments[idx]
        if hasattr(seg, "speed_px_s"):
            return float(seg.speed_px_s)
        # Bezier: length_estimate / duration_s
        seg_dur = self.path.segment_durations[idx]
        length = seg.length_estimate
        if seg_dur <= 0.0:
            return 0.0
        return length / seg_dur
