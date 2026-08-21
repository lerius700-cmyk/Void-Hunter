"""PathFollower — advances a HybridPath over time and yields (x, y, vx, vy).

A PathFollower is what an Enemy (or other entity) holds. Each frame the
follower is updated with dt seconds; it advances its internal arc length
s and returns the current world position plus the current velocity
vector.

BLOQUE 58.next: arc-length based motion. The follower no longer walks
parameter `t` in path parameter space; it walks arc length `s` in
screen-space pixels. Combined with the per-segment speed, the resulting
velocity is in pixels per second and is **constant in screen space** (no
faster-in-straights / slower-in-curves).

  - t_offset (in seconds) is still honored: it gets converted to a
    starting arc length via the *first segment's* speed.
  - `t` property is kept (computed as s / total_arc_length) for any
    external code that reads it.

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
            starts at arc length s = t_offset * first_segment_speed. Use
            this for staggered entries (e.g., 5 ships entering a 6s path
            at 0s, 1s, 2s, 3s, 4s).

    Usage:
        follower = PathFollower(some_hybrid_path)
        for dt in frame_deltas:
            x, y, vx, vy = follower.update(dt)
            entity.x, entity.y = x, y
    """

    __slots__ = ("path", "_s", "_complete", "_t_offset_s")

    def __init__(self, path: HybridPath, t_offset: float = 0.0) -> None:
        self.path: HybridPath = path
        self._t_offset_s: float = t_offset
        self._s: float = self._s_at_offset()
        self._complete: bool = False

    def _s_at_offset(self) -> float:
        """Convert t_offset (seconds) to a starting arc length.

        Uses the *first segment's* speed so the staggered entry matches
        the timing the caller asked for.
        """
        if not self.path.segments:
            return 0.0
        seg0 = self.path.segments[0]
        if hasattr(seg0, "speed_px_s"):
            speed = float(seg0.speed_px_s)
        else:
            # Bezier: length / duration
            seg_dur = self.path.segment_durations[0] if self.path.segment_durations else 0.0
            if seg_dur <= 0.0:
                return 0.0
            length = getattr(seg0, "total_arc_length", seg0.length_estimate)
            speed = length / seg_dur
        s = self._t_offset_s * speed
        return min(self.path.total_arc_length, max(0.0, s))

    @property
    def t(self) -> float:
        """Current parameter in [0, 1] along the path (backward compat).

        Computed from the current arc length: t = s / total_arc_length.
        """
        total = self.path.total_arc_length
        if total <= 0.0:
            return 0.0
        return min(1.0, max(0.0, self._s / total))

    @property
    def s(self) -> float:
        """Current arc length (in pixels) along the path."""
        return self._s

    @property
    def is_complete(self) -> bool:
        return self._complete

    def reset(self) -> None:
        self._s = self._s_at_offset()
        self._complete = False

    def update(self, dt: float) -> tuple[Point, Point]:
        """Advance the follower by dt seconds.

        BLOQUE 58.next: the internal state is arc length `s`, not `t`.
        Velocity is in pixels per second, constant in screen space.

        Returns:
            (position, velocity). Position is the current (x, y).
            Velocity is the tangent vector in screen coordinates — NOT
            normalized; its magnitude reflects local speed.
        """
        if self._complete or dt <= 0.0:
            # Stay at the last position; return zero velocity
            return self.path.position_at_distance(self._s), Point(0.0, 0.0)
        speed = self._segment_speed()
        new_s = self._s + speed * dt
        if new_s >= self.path.total_arc_length:
            self._s = self.path.total_arc_length
            self._complete = True
        else:
            self._s = new_s
        pos = self.path.position_at_distance(self._s)
        tan = self.path.tangent_at_distance(self._s)
        return pos, Point(tan.x * speed, tan.y * speed)

    def _segment_speed(self) -> float:
        """Effective speed in px/s for the current segment.

        For Bezier: derived from the segment's own duration vs length.
        For Waypoint: the path's own speed_px_s.
        """
        if not self.path.segments:
            return 0.0
        idx, _ = self.path._segment_for_s(self._s)
        seg = self.path.segments[idx]
        if hasattr(seg, "speed_px_s"):
            return float(seg.speed_px_s)
        # Bezier: length / duration
        seg_dur = self.path.segment_durations[idx]
        length = getattr(seg, "total_arc_length", seg.length_estimate)
        if seg_dur <= 0.0:
            return 0.0
        return length / seg_dur
