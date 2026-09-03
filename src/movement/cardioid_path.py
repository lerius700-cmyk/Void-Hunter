"""CardioidPath — heart-shape path (BLOQUE 58.next).

Parametric:
    x(t) = a * (2 * cos(t) - cos(2t))
    y(t) = a * (2 * sin(t) - sin(2t))

Approximated with 12 cubic bezier segments. The cusp at t=pi requires
3 segments clustered around it for a smooth visual.
"""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class CardioidPath:
    def __init__(self, scale: float = 60.0, duration_s: float = 5.0) -> None:
        if scale <= 0:
            raise ValueError(f"scale must be > 0, got {scale}")
        if duration_s <= 0:
            raise ValueError(f"duration_s must be > 0, got {duration_s}")
        self._scale = scale
        self._duration_s = duration_s

    def _point(self, t: float) -> tuple[float, float]:
        a = self._scale
        return (a * (2 * math.cos(t) - math.cos(2 * t)), a * (2 * math.sin(t) - math.sin(2 * t)))

    def get_path(self) -> HybridPath:
        a = self._scale
        # 12 anchor points evenly spaced in t
        n = 12
        anchors = [self._point(2 * math.pi * i / n) for i in range(n)]
        segs: list[BezierPath] = []
        for i in range(n):
            p0 = anchors[i]
            p3 = anchors[(i + 1) % n]
            dx = p3[0] - p0[0]
            dy = p3[1] - p0[1]
            plen = math.hypot(dx, dy) or 1
            # Pull control points to make the curve bulge outward (away from origin)
            # Use the gradient of the cardioid's tangent at this point
            mid_t = 2 * math.pi * (i + 0.5) / n
            # Tangent of cardioid: dx/dt = a*(-2*sin(t) + 2*sin(2t)), dy/dt = a*(2*cos(t) - 2*cos(2t))
            tx = a * (-2 * math.sin(mid_t) + 2 * math.sin(2 * mid_t))
            ty = a * (2 * math.cos(mid_t) - 2 * math.cos(2 * mid_t))
            tlen = math.hypot(tx, ty) or 1
            # Normalize tangent, scale by 0.3 * chord length
            tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
            p1 = (p0[0] + tx, p0[1] + ty)
            p2 = (p3[0] - tx, p3[1] - ty)
            segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
        per_seg = self._duration_s / n
        return HybridPath(segs, [per_seg] * n)
