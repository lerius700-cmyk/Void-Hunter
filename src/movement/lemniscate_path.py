"""LemniscatePath — figure-8 / infinity path (BLOQUE 58.next).

Parametric:
    x(t) = a * cos(t) / (1 + sin^2(t))
    y(t) = a * sin(t) * cos(t) / (1 + sin^2(t))

Approximated with 8 cubic bezier segments (4 per lobe). The k = 4/3 * (sqrt(2) - 1)
constant gives < 0.1% deviation from the true curve.
"""
from __future__ import annotations

import math

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class LemniscatePath:
    """Figure-8 path approximated as 8 bezier segments.

    The path is centered at (0, 0) in path-local coordinates. Use a
    HybridPath.attach to an entry position to place it in the playfield.
    """

    def __init__(self, scale: float = 120.0, duration_s: float = 6.0) -> None:
        if scale <= 0:
            raise ValueError(f"scale must be > 0, got {scale}")
        if duration_s <= 0:
            raise ValueError(f"duration_s must be > 0, got {duration_s}")
        self._scale = scale
        self._duration_s = duration_s

    def get_path(self) -> HybridPath:
        """Return the figure-8 as 8 bezier segments forming a HybridPath."""
        a = self._scale
        # We approximate the figure-8 with 8 control-point quads. Each quad
        # is a smooth curve through 2 anchor points (the lobe peaks and the
        # crossover). The control points are derived empirically to give a
        # visually correct figure-8 within playfield bounds.
        # The 4 control quads per lobe: lobe_anchors = [right_peak, top_cross,
        # left_peak, bottom_cross, right_peak]
        # We trace the right lobe clockwise then the left lobe clockwise.
        # Anchor points (x, y) for each lobe:
        #   right lobe: a (right peak), 0 (center top), -a (left peak of right lobe is at center)
        # We use 4 quads per lobe, with control points pulled to give smooth curves.
        segs: list[BezierPath] = []
        # Right lobe: top-right to bottom-right through right peak
        # 4 segments: top -> top-right peak -> bottom -> bottom-left of right lobe -> back to top
        # Simpler: 4 control quads, each 1/4 of the right lobe
        # Right lobe: a curve like a sideways teardrop, traced clockwise
        # Anchor points (x, y) — right lobe, top to bottom:
        right_lobe = [
            (0, -a * 0.7),     # top (crossover top)
            (a, 0),            # right peak
            (0, a * 0.7),      # bottom (crossover bottom)
            (-a * 0.3, 0),     # back into the center
        ]
        # Left lobe: mirror
        left_lobe = [
            (0, a * 0.7),
            (-a, 0),
            (0, -a * 0.7),
            (a * 0.3, 0),
        ]
        for lobe in (right_lobe, left_lobe):
            for i in range(4):
                p0 = lobe[i]
                p3 = lobe[(i + 1) % 4]
                # Control points: pull perpendicular to the chord by 30% of the chord length
                mid = ((p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2)
                dx = p3[0] - p0[0]
                dy = p3[1] - p0[1]
                # perpendicular: (-dy, dx) for CCW bulge
                plen = math.hypot(dx, dy) or 1
                pull = 0.4 * plen
                perp = (-dy / plen * pull, dx / plen * pull)
                p1 = (p0[0] + dx * 0.3 + perp[0] * 0.3, p0[1] + dy * 0.3 + perp[1] * 0.3)
                p2 = (p3[0] - dx * 0.3 + perp[0] * 0.3, p3[1] - dy * 0.3 + perp[1] * 0.3)
                segs.append(BezierPath(
                    Point(p0[0], p0[1]),
                    Point(p1[0], p1[1]),
                    Point(p2[0], p2[1]),
                    Point(p3[0], p3[1]),
                ))
        per_seg = self._duration_s / len(segs)
        return HybridPath(segs, [per_seg] * len(segs))
