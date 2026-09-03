"""RoseK2Path + RoseK3Path — rose curves (BLOQUE 58.next)."""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


def _build_rose(k: int, scale: float, duration_s: float, n_anchors: int) -> HybridPath:
    anchors = []
    for i in range(n_anchors):
        theta = 2 * math.pi * i / n_anchors
        r = scale * math.cos(k * theta)
        anchors.append((r * math.cos(theta), r * math.sin(theta)))
    segs: list[BezierPath] = []
    n_segs = n_anchors  # one segment per anchor
    for i in range(n_segs):
        p0 = anchors[i]
        p3 = anchors[(i + 1) % n_segs]
        dx = p3[0] - p0[0]
        dy = p3[1] - p0[1]
        plen = math.hypot(dx, dy) or 1
        mid_theta = 2 * math.pi * (i + 0.5) / n_segs
        r = scale * math.cos(k * mid_theta)
        tx = r * math.cos(mid_theta) - k * scale * math.sin(k * mid_theta) * math.cos(mid_theta)
        ty = r * math.sin(mid_theta) - k * scale * math.sin(k * mid_theta) * math.sin(mid_theta)
        tlen = math.hypot(tx, ty) or 1
        tx, ty = tx / tlen * plen * 0.3, ty / tlen * plen * 0.3
        p1 = (p0[0] + tx, p0[1] + ty)
        p2 = (p3[0] - tx, p3[1] - ty)
        segs.append(BezierPath(Point(p0[0], p0[1]), Point(p1[0], p1[1]), Point(p2[0], p2[1]), Point(p3[0], p3[1])))
    per_seg = duration_s / n_segs
    return HybridPath(segs, [per_seg] * n_segs)


class RoseK2Path:
    def __init__(self, scale: float = 80.0, duration_s: float = 6.0) -> None:
        if scale <= 0:
            raise ValueError("scale must be > 0")
        self._scale = scale
        self._duration_s = duration_s

    def get_path(self) -> HybridPath:
        return _build_rose(2, self._scale, self._duration_s, n_anchors=8)


class RoseK3Path:
    def __init__(self, scale: float = 80.0, duration_s: float = 6.0) -> None:
        if scale <= 0:
            raise ValueError("scale must be > 0")
        self._scale = scale
        self._duration_s = duration_s

    def get_path(self) -> HybridPath:
        return _build_rose(3, self._scale, self._duration_s, n_anchors=12)
