"""HypocycloidPath — Spirograph-style curve (BLOQUE 58.next)."""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class HypocycloidPath:
    def __init__(self, R: float = 60.0, r: float = 20.0, duration_s: float = 8.0) -> None:
        if R <= 0 or r <= 0:
            raise ValueError("R and r must be > 0")
        if r > R:
            raise ValueError("r must be <= R")
        self._R = R
        self._r = r
        self._duration_s = duration_s

    def _point(self, t: float) -> tuple[float, float]:
        R, r = self._R, self._r
        return (
            (R - r) * math.cos(t) + r * math.cos((R - r) * t / r),
            (R - r) * math.sin(t) - r * math.sin((R - r) * t / r),
        )

    def get_path(self) -> HybridPath:
        # Number of cusps = R / r
        n_cusps = max(1, int(round(self._R / self._r)))
        n_anchors = 6 * n_cusps  # 6 segments per cusp
        anchors = [self._point(2 * math.pi * i / n_anchors) for i in range(n_anchors)]
        segs: list[BezierPath] = []
        for i in range(n_anchors):
            p0 = anchors[i]
            p3 = anchors[(i + 1) % n_anchors]
            dx = p3[0] - p0[0]
            dy = p3[1] - p0[1]
            plen = math.hypot(dx, dy) or 1
            mid_t = 2 * math.pi * (i + 0.5) / n_anchors
            R, r = self._R, self._r
            tx = -(R - r) * math.sin(mid_t) - (R - r) * math.sin((R - r) * mid_t / r)
            ty = (R - r) * math.cos(mid_t) - (R - r) * math.cos((R - r) * mid_t / r)
            tlen = math.hypot(tx, ty) or 1
            tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
            p1 = (p0[0] + tx, p0[1] + ty)
            p2 = (p3[0] - tx, p3[1] - ty)
            segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
        per_seg = self._duration_s / n_anchors
        return HybridPath(segs, [per_seg] * n_anchors)
