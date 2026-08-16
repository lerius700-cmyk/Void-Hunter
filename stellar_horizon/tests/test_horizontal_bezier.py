# stellar_horizon/tests/test_horizontal_bezier.py
import pytest
from src.movement import BezierPath, WaypointPath, HybridPath, Point

from stellar_horizon.waves.bezier_horizontal import (
    path_s_right_to_left, path_top_dive, path_zigzag_exit_top, path_boss_entry,
)


def _is_off_screen(p: Point) -> bool:
    """Returns True if point is outside 480x270 play area (with small margin)."""
    return p.x < -8 or p.x > 488 or p.y < -8 or p.y > 278


def test_path_s_right_to_left_returns_bezier():
    p = path_s_right_to_left()
    assert isinstance(p, BezierPath)


def test_path_s_right_to_left_starts_off_screen_right():
    p = path_s_right_to_left()
    start = p.position_at(0.0)
    assert start.x > 480  # off-screen right


def test_path_s_right_to_left_ends_off_screen_left():
    p = path_s_right_to_left()
    end = p.position_at(1.0)
    assert end.x < 0  # off-screen left


def test_path_s_right_to_left_traverses_screen():
    p = path_s_right_to_left()
    mid = p.position_at(0.5)
    assert 0 <= mid.x <= 480
    assert 0 <= mid.y <= 270


def test_path_s_right_to_left_with_y_offset():
    p = path_s_right_to_left(y_offset=80.0)
    start = p.position_at(0.0)
    assert abs(start.y - 140) < 1.0  # 60 + 80


def test_path_top_dive_starts_off_screen_top():
    p = path_top_dive()
    start = p.position_at(0.0)
    assert start.y < 0  # off-screen top


def test_path_top_dive_right_ends_right():
    p = path_top_dive(side="right")
    end = p.position_at(1.0)
    assert end.x > 480  # off-screen right


def test_path_top_dive_left_ends_left():
    p = path_top_dive(side="left")
    end = p.position_at(1.0)
    assert end.x < 0  # off-screen left


def test_path_zigzag_exit_top_returns_hybrid():
    p = path_zigzag_exit_top()
    assert isinstance(p, HybridPath)


def test_path_zigzag_exit_top_starts_off_screen_right():
    p = path_zigzag_exit_top()
    start = p.position_at(0.0)
    assert start.x > 480  # enters from right


def test_path_zigzag_exit_top_ends_off_screen_top():
    p = path_zigzag_exit_top()
    end = p.position_at(1.0)
    assert end.y < 0  # exits top


def test_path_boss_entry_starts_off_screen_right():
    p = path_boss_entry()
    start = p.position_at(0.0)
    assert start.x > 480


def test_path_boss_entry_ends_at_arena():
    p = path_boss_entry()
    end = p.position_at(1.0)
    # Spec: boss arena is (350, 135)
    assert abs(end.x - 350) < 0.01
    assert abs(end.y - 135) < 0.01
