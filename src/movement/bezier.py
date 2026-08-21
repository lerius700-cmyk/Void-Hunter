"""BezierPath — cubic bezier curve for ship motion (BLOQUE 58.6x + 58.next).

A BezierPath is a 4-point cubic curve (P0, P1, P2, P3) parameterized by
t in [0, 1]. At t=0 the position is P0; at t=1 it's P3. P1 and P2 are
control points that pull the curve.

BLOQUE 58.next: arc-length parameterization. The `t` parameter is
*parameter space*, not *screen-space distance*. Two paths with the same
`length_estimate` can have very different `t -> distance` mappings
(e.g., a tight loop has the same length but very different speed at each
`t`). For constant speed in screen space, use the distance-based API:

  - `position_at_distance(s)` — point at arc length s
  - `tangent_at_distance(s)`  — unnormalized tangent at arc length s
  - `total_arc_length`        — pre-computed total arc length

A 64-sample arc-length table is built in `__init__` (~0.01% error vs.
the true integral). Binary search + linear interpolation gives O(log N)
lookups. PathFollower uses this for velocity that's truly constant in
pixels per second.

Used for smooth sweeps (entry curves, S-bends, arcs). Paired with
WaypointPath and HybridPath in src.movement.

Math:
  B(t) = (1-t)^3 * P0 + 3*(1-t)^2*t * P1 + 3*(1-t)*t^2 * P2 + t^3 * P3
  B'(t) = 3*(1-t)^2 * (P1-P0) + 6*(1-t)*t * (P2-P1) + 3*t^2 * (P3-P2)

Coordinate convention: 320x480 internal. Y increases downward (screen).

Constraints: no numpy/scipy (GDD \u00a70); pure stdlib math.
"""
from __future__ import annotations

import math
from typing import NamedTuple


class Point(NamedTuple):
    x: float
    y: float


class BezierPath:
    """Cubic bezier curve for ship motion.

    Example (a smooth right-to-left arc that curves down):
        p = BezierPath(
            p0=Point(300, 50),    # start (top right)
            p1=Point(300, 200),   # control 1: pull down
            p2=Point(20, 200),    # control 2: pull down
            p3=Point(20, 380),    # end (bottom left)
        )
    """

    __slots__ = ("p0", "p1", "p2", "p3", "_arc_t", "_arc_s", "_arc_total")

    def __init__(self, p0: Point, p1: Point, p2: Point, p3: Point) -> None:
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        # BLOQUE 58.next: pre-compute arc-length table for distance-based motion.
        self._build_arc_table()

    def position_at(self, t: float) -> Point:
        """Return the point on the curve at parameter t in [0, 1]."""
        if t <= 0.0:
            return self.p0
        if t >= 1.0:
            return self.p3
        u = 1.0 - t
        u2 = u * u
        t2 = t * t
        x = (
            u2 * u * self.p0.x
            + 3.0 * u2 * t * self.p1.x
            + 3.0 * u * t2 * self.p2.x
            + t2 * t * self.p3.x
        )
        y = (
            u2 * u * self.p0.y
            + 3.0 * u2 * t * self.p1.y
            + 3.0 * u * t2 * self.p2.y
            + t2 * t * self.p3.y
        )
        return Point(x, y)

    def tangent_at(self, t: float) -> Point:
        """Return the tangent (direction) of the curve at parameter t.

        The tangent is NOT normalized \u2014 its magnitude reflects the curve's
        local "speed" in parameter space. Multiply by speed_px_s to get a
        velocity vector.
        """
        if t <= 0.0:
            dx = self.p1.x - self.p0.x
            dy = self.p1.y - self.p0.y
        elif t >= 1.0:
            dx = self.p3.x - self.p2.x
            dy = self.p3.y - self.p2.y
        else:
            u = 1.0 - t
            dx = (
                3.0 * u * u * (self.p1.x - self.p0.x)
                + 6.0 * u * t * (self.p2.x - self.p1.x)
                + 3.0 * t * t * (self.p3.x - self.p2.x)
            )
            dy = (
                3.0 * u * u * (self.p1.y - self.p0.y)
                + 6.0 * u * t * (self.p2.y - self.p1.y)
                + 3.0 * t * t * (self.p3.y - self.p2.y)
            )
        return Point(dx, dy)

    # ------------------------------------------------------------------
    # Arc-length parameterization (BLOQUE 58.next)
    # ------------------------------------------------------------------
    # Pre-compute a (t, distance) table in __init__ so position_at_distance
    # is O(log N) binary search + linear interp between two bezier samples.
    # Default 64 samples; very accurate (sub-pixel error on cubic bezier).

    _ARC_TABLE_SAMPLES = 64

    def _build_arc_table(self) -> None:
        """Pre-compute the arc-length lookup table.

        self._arc_t[i] = t value at sample i
        self._arc_s[i] = cumulative distance at sample i
        self._arc_total = total arc length
        """
        n = self._ARC_TABLE_SAMPLES
        ts = [0.0] * (n + 1)
        ss = [0.0] * (n + 1)
        prev = self.position_at(0.0)
        ts[0] = 0.0
        ss[0] = 0.0
        for i in range(1, n + 1):
            t = i / n
            cur = self.position_at(t)
            ss[i] = ss[i - 1] + math.hypot(cur.x - prev.x, cur.y - prev.y)
            ts[i] = t
            prev = cur
        self._arc_t: list[float] = ts
        self._arc_s: list[float] = ss
        self._arc_total: float = ss[-1]

    def _t_to_arc(self, t: float) -> float:
        """Convert t in [0, 1] to arc length s in [0, total].

        Linear interpolation between adjacent table entries. O(log N) with
        a binary search.
        """
        ts = self._arc_t
        ss = self._arc_s
        # Binary search for the largest i with ts[i] <= t
        lo, hi = 0, len(ts) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if ts[mid] <= t:
                lo = mid
            else:
                hi = mid
        # Linear interp between (ts[lo], ss[lo]) and (ts[hi], ss[hi])
        t_span = ts[hi] - ts[lo]
        if t_span <= 0.0:
            return ss[lo]
        alpha = (t - ts[lo]) / t_span
        return ss[lo] + alpha * (ss[hi] - ss[lo])

    def _arc_to_t(self, s: float) -> float:
        """Convert arc length s in [0, total] to t in [0, 1]. O(log N)."""
        if s <= 0.0:
            return 0.0
        if s >= self._arc_total:
            return 1.0
        ts = self._arc_t
        ss = self._arc_s
        lo, hi = 0, len(ss) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if ss[mid] <= s:
                lo = mid
            else:
                hi = mid
        s_span = ss[hi] - ss[lo]
        if s_span <= 0.0:
            return ts[lo]
        alpha = (s - ss[lo]) / s_span
        return ts[lo] + alpha * (ts[hi] - ts[lo])

    @property
    def total_arc_length(self) -> float:
        """Total arc length (in pixels) using the pre-computed table.

        For a 64-sample polyline approximation of a cubic bezier, this is
        within ~0.01% of the true arc length.
        """
        return self._arc_total

    def position_at_distance(self, s: float) -> Point:
        """Return the point on the curve at arc length s in [0, total_arc_length].

        This is the key API for distance-based motion: pass a *distance*
        and get back a point. Combined with `tangent_at_distance`, the
        resulting velocity is in pixels per second (constant speed in
        screen space, not in parameter space).
        """
        t = self._arc_to_t(s)
        return self.position_at(t)

    def tangent_at_distance(self, s: float) -> Point:
        """Return the tangent (unnormalized) at arc length s."""
        t = self._arc_to_t(s)
        return self.tangent_at(t)

    @property
    def length_estimate(self) -> float:
        """Approximate path length via 16-segment polyline.

        Kept for backward compat. Prefer `total_arc_length` (64 samples,
        ~0.01% error) for new code.
        """
        prev = self.p0
        total = 0.0
        steps = 16
        for i in range(1, steps + 1):
            cur = self.position_at(i / steps)
            total += math.hypot(cur.x - prev.x, cur.y - prev.y)
            prev = cur
        return total
