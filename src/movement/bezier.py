"""BezierPath — cubic bezier curve for ship motion (BLOQUE 58.6x).

A BezierPath is a 4-point cubic curve (P0, P1, P2, P3) parameterized by
t in [0, 1]. At t=0 the position is P0; at t=1 it's P3. P1 and P2 are
control points that pull the curve.

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

    __slots__ = ("p0", "p1", "p2", "p3")

    def __init__(self, p0: Point, p1: Point, p2: Point, p3: Point) -> None:
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3

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

    @property
    def length_estimate(self) -> float:
        """Approximate path length via 16-segment polyline.

        Good enough for timing calculations (a few % off is fine). For
        exact length, would need numerical integration.
        """
        prev = self.p0
        total = 0.0
        steps = 16
        for i in range(1, steps + 1):
            cur = self.position_at(i / steps)
            total += math.hypot(cur.x - prev.x, cur.y - prev.y)
            prev = cur
        return total
