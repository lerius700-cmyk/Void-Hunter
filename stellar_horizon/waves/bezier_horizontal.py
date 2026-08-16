"""Horizontal bezier paths for STELLAR HORIZON.

Each path enters from off-screen and exits off-screen, so the enemy visibly
travels across the play area. All paths are tuned for a 480x270 viewport.
"""
from __future__ import annotations

from src.movement import BezierPath, HybridPath, Point, WaypointPath


def path_s_right_to_left(y_offset: float = 0.0) -> BezierPath:
    """S-curve from off-screen right to off-screen left.

    Args:
        y_offset: shifts the curve vertically. Default 0 puts baseline at y=60.
    """
    return BezierPath(
        p0=Point(490, 60 + y_offset),
        p1=Point(380, 60 + y_offset),
        p2=Point(100, 200 - y_offset),
        p3=Point(-20, 200 - y_offset),
    )


def path_top_dive(side: str = "right") -> BezierPath:
    """Arcs down from off-screen top, exits off-screen right (or left).

    Args:
        side: "right" exits at x=490; "left" exits at x=-10.
    """
    end_x = 490 if side == "right" else -10
    return BezierPath(
        p0=Point(200, -20),
        p1=Point(200, 50),
        p2=Point(380 if side == "right" else 100, 150),
        p3=Point(end_x, 240),
    )


def path_zigzag_exit_top() -> HybridPath:
    """Bezier segment + waypoint zigzag, exits off-screen top."""
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 100),
            p1=Point(300, 100),
            p2=Point(200, 180),
            p3=Point(300, 220),
        ),
        WaypointPath(
            [Point(300, 220), Point(380, 150), Point(250, 80), Point(200, -20)],
            speed_px_s=140.0,
        ),
    ])


def path_boss_entry() -> BezierPath:
    """Dramatic S-curve from off-screen right to boss arena (350, 135)."""
    return BezierPath(
        p0=Point(540, 60),
        p1=Point(450, 100),
        p2=Point(380, 200),
        p3=Point(350, 135),
    )
