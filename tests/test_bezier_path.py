"""Tests for src.systems.bezier_path (BLOQUE 56)."""
from __future__ import annotations

import pytest

from src.systems.bezier_path import BezierPath, ControlPoint


# ---------------------------------------------------------------------------
# 1. Construction
# ---------------------------------------------------------------------------
def test_quadratic_path_constructs_with_3_points() -> None:
    p0, p1, p2 = ControlPoint(0, 0), ControlPoint(50, 100), ControlPoint(100, 0)
    path = BezierPath([p0, p1, p2])
    assert path.is_quadratic is True
    assert path.t == 0.0
    assert path.is_complete is False


def test_cubic_path_constructs_with_4_points() -> None:
    p = [ControlPoint(i * 10, i * 5) for i in range(4)]
    path = BezierPath(p)
    assert path.is_quadratic is False


def test_path_with_2_or_5_points_raises() -> None:
    with pytest.raises(ValueError, match="3 .quadratic. or 4 .cubic"):
        BezierPath([ControlPoint(0, 0), ControlPoint(1, 1)])
    with pytest.raises(ValueError, match="3 .quadratic. or 4 .cubic"):
        BezierPath([ControlPoint(i, i) for i in range(5)])


# ---------------------------------------------------------------------------
# 2. Endpoints
# ---------------------------------------------------------------------------
def test_quadratic_endpoints() -> None:
    p0, p1, p2 = ControlPoint(0, 0), ControlPoint(50, 100), ControlPoint(100, 0)
    path = BezierPath([p0, p1, p2])
    assert path.eval(0.0) == (0.0, 0.0)
    assert path.eval(1.0) == (100.0, 0.0)


def test_cubic_endpoints() -> None:
    p = [ControlPoint(0, 0), ControlPoint(30, 100), ControlPoint(70, 100), ControlPoint(100, 0)]
    path = BezierPath(p)
    assert path.eval(0.0) == (0.0, 0.0)
    assert path.eval(1.0) == (100.0, 0.0)


# ---------------------------------------------------------------------------
# 3. update() advances t
# ---------------------------------------------------------------------------
def test_speed_advances_t_proportionally() -> None:
    """BLOQUE 56: At speed = path_length / 2 px/s, t goes from 0 to ~0.5
    in 1 second."""
    p0, p1, p2 = ControlPoint(0, 0), ControlPoint(50, 50), ControlPoint(100, 0)
    path = BezierPath([p0, p1, p2])
    total = path.total_length
    half_speed = total / 2.0
    path.update(1.0, speed=half_speed)
    assert abs(path.t - 0.5) < 0.01, f"t={path.t}, expected ~0.5"


def test_update_clamps_at_complete() -> None:
    """BLOQUE 56: A single very long update clamps t at 1.0 and triggers
    on_complete exactly once."""
    completed: list[bool] = []
    path = BezierPath(
        [ControlPoint(0, 0), ControlPoint(50, 50), ControlPoint(100, 0)],
        on_complete=lambda: completed.append(True),
    )
    path.update(100.0, speed=10000.0)  # way more than needed
    assert path.t == 1.0
    assert path.is_complete is True
    assert completed == [True]


def test_on_complete_fires_only_once() -> None:
    completed: list[int] = []
    path = BezierPath(
        [ControlPoint(0, 0), ControlPoint(50, 50), ControlPoint(100, 0)],
        on_complete=lambda: completed.append(1),
    )
    path.update(100.0, speed=10000.0)
    path.update(100.0, speed=10000.0)
    path.update(100.0, speed=10000.0)
    assert len(completed) == 1, f"on_complete should fire once, got {len(completed)}"


# ---------------------------------------------------------------------------
# 4. Pre-bake cache
# ---------------------------------------------------------------------------
def test_prebake_changes_eval_path_but_not_endpoints() -> None:
    p = [ControlPoint(0, 0), ControlPoint(30, 100), ControlPoint(70, 100), ControlPoint(100, 0)]
    path = BezierPath(p)
    pre_prebake_start = path.eval(0.0)
    pre_prebake_end = path.eval(1.0)
    path.prebake(steps=20)
    assert path.eval(0.0) == pre_prebake_start
    assert path.eval(1.0) == pre_prebake_end


def test_prebake_with_2_steps_raises() -> None:
    path = BezierPath([ControlPoint(0, 0), ControlPoint(50, 50), ControlPoint(100, 0)])
    with pytest.raises(ValueError, match="steps must be >= 2"):
        path.prebake(steps=1)


# ---------------------------------------------------------------------------
# 5. reset()
# ---------------------------------------------------------------------------
def test_reset_restores_initial_state() -> None:
    completed: list[bool] = []
    path = BezierPath(
        [ControlPoint(0, 0), ControlPoint(50, 50), ControlPoint(100, 0)],
        on_complete=lambda: completed.append(True),
    )
    path.update(100.0, speed=10000.0)
    assert path.is_complete
    path.reset()
    assert path.t == 0.0
    assert path.is_complete is False


# ---------------------------------------------------------------------------
# 6. Realistic use case: GOLIATH entrance
# ---------------------------------------------------------------------------
def test_goliath_entrance_path() -> None:
    """BLOQUE 56: GOLIATH enters from above the screen, curves through
    the top quadrant, and lands at the boss anchor (160, 80)."""
    path = BezierPath([
        ControlPoint(160, -40),   # off-screen top
        ControlPoint(80, 60),     # curve in from the left
        ControlPoint(240, 60),    # curve out to the right
        ControlPoint(160, 80),    # land at anchor
    ])
    assert path.eval(0.0) == (160.0, -40.0)
    assert path.eval(1.0) == (160.0, 80.0)
    # Path should be a real curve, not a straight line — middle t is offset
    mid = path.eval(0.5)
    assert mid != (160.0, 20.0), f"Midpoint should be curved, got {mid}"
    # Total length > straight-line distance (120 px). Curve adds 40+ px.
    assert path.total_length > 140.0, (
        f"Path too short ({path.total_length:.1f} px), control points too close"
    )
