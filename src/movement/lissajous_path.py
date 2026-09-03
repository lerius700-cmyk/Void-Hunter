"""LissajousPath — parametric (sin/cos) curve (BLOQUE 58.next)."""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class LissajousPath:
    def __init__(self, a: int = 3, b: int = 2, delta: float = math.pi / 2,
                 scale_x: float = 120.0, scale_y: float = 80.0,
                 duration_s: float = 6.0) -> None:
        if a <= 0 or b <= 0:
            raise ValueError("a and b must be > 0")
        self._a = a
        self._b = b
        self._delta = delta
        self._scale_x = scale_x
        self._scale_y = scale_y
        self._duration_s = duration_s

    def _point(self, t: float) -> tuple[float, float]:
        return (
            self._scale_x * math.sin(self._a * t + self._delta),
            self._scale_y * math.sin(self._b * t),
        )

    def get_path(self) -> HybridPath:
        n = 12
        anchors = [self._point(2 * math.pi * i / n) for i in range(n)]
        segs: list[BezierPath] = []
        for i in range(n):
            p0 = anchors[i]
            p3 = anchors[(i + 1) % n]
            dx = p3[0] - p0[0]
            dy = p3[1] - p0[1]
            plen = math.hypot(dx, dy) or 1
            mid_t = 2 * math.pi * (i + 0.5) / n
            tx = self._scale_x * self._a * math.cos(self._a * mid_t + self._delta)
            ty = self._scale_y * self._b * math.cos(self._b * mid_t)
            tlen = math.hypot(tx, ty) or 1
            tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
            p1 = (p0[0] + tx, p0[1] + ty)
            p2 = (p3[0] - tx, p3[1] - ty)
            segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
        per_seg = self._duration_s / n
        return HybridPath(segs, [per_seg] * n)
