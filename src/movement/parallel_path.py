"""BLOQUE 58.13: ParallelPathPair — two parallel HybridPath instances.

Used by Star Fox 64 style "pair dance" — 2 ships fly side-by-side on
parallel beziers, gap_px apart. The offset is VERTICAL (constant),
which is visually indistinguishable from true perpendicular offset
at the playfield scale (320x480) and 10x simpler to compute.

Static offset rationale:
  - True perpendicular offset requires computing the curve tangent at
    each t and rotating 90 degrees. Expensive and unnecessary noise.
  - Our beziers travel mostly horizontally, so a vertical offset is
    effectively perpendicular.

The base_segments are a list of 4-tuples (p0, p1, p2, p3) of
(x, y) tuples. Each segment's control points are offset by ±gap_px/2
in y, then wrapped in a BezierPath and assembled into a HybridPath.
"""
from __future__ import annotations

from src.movement.bezier import BezierPath, Point
from src.movement.hybrid import HybridPath


class ParallelPathPair:
    """Two parallel HybridPath instances, vertical offset.

    Args:
        base_segments: list of (p0, p1, p2, p3) — centerline bezier control points
        base_durations: list of float seconds — one per segment
        gap_px: vertical offset between the two paths (default 14)
    """

    __slots__ = ("_top", "_bot")

    def __init__(
        self,
        base_segments: list[tuple[tuple[float, float], tuple[float, float],
                                   tuple[float, float], tuple[float, float]]],
        base_durations: list[float],
        gap_px: float = 14,
    ) -> None:
        if len(base_segments) != len(base_durations):
            raise ValueError(
                f"base_segments ({len(base_segments)}) != "
                f"base_durations ({len(base_durations)})"
            )
        if not base_segments:
            raise ValueError("base_segments cannot be empty")
        if gap_px < 0:
            raise ValueError("gap_px must be >= 0")

        top_segs = self._offset_segments(base_segments, -gap_px / 2.0)
        bot_segs = self._offset_segments(base_segments, +gap_px / 2.0)
        self._top = HybridPath(top_segs, list(base_durations))
        self._bot = HybridPath(bot_segs, list(base_durations))

    @staticmethod
    def _offset_segments(
        segments: list[tuple[tuple[float, float], tuple[float, float],
                              tuple[float, float], tuple[float, float]]],
        dy: float,
    ) -> list[BezierPath]:
        """Build BezierPath instances with all control points offset by dy."""
        out: list[BezierPath] = []
        for seg in segments:
            p0, p1, p2, p3 = seg
            out.append(BezierPath(
                p0=Point(p0[0], p0[1] + dy),
                p1=Point(p1[0], p1[1] + dy),
                p2=Point(p2[0], p2[1] + dy),
                p3=Point(p3[0], p3[1] + dy),
            ))
        return out

    def get_top(self) -> HybridPath:
        """Return the upper path (offset -gap/2, smaller y in screen coords)."""
        return self._top

    def get_bot(self) -> HybridPath:
        """Return the lower path (offset +gap/2, larger y in screen coords)."""
        return self._bot
