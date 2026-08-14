"""BLOQUE 58.6x: integration tests for Enemy + PathFollower.

Verify the Enemy.update() path actually drives position from the
PathFollower when one is attached, and that the formation slot offset
is applied correctly.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _build_test_enemy():
    """Create a minimal Enemy with sane defaults for testing."""
    from src.entities.enemies.enemy import Enemy
    e = Enemy()
    e.active = True
    e.x = 0.0
    e.y = 0.0
    e.vx = 0.0
    e.vy = 0.0
    e.on_spawn()
    return e


def test_enemy_with_straight_path_follows_it() -> None:
    """Enemy with a straight HybridPath.straighten follower should slide
    along (0,0) -> (100, 0) over 1.0 s at 100 px/s.
    """
    from src.movement import HybridPath, PathFollower, Point

    e = _build_test_enemy()
    path = HybridPath.straighten(Point(0, 0), Point(100, 0), speed_px_s=100.0)
    e.attach_path(PathFollower(path))
    e.update(0.5, player_x=160.0, player_y=400.0)
    # After 0.5s the path follower is at t=0.5 -> midpoint
    assert 49 <= e.x <= 51
    assert e.y == 0
    # Velocity should be (100, 0)
    assert e.vx == 100.0 and e.vy == 0.0


def test_enemy_with_bezier_path_curves() -> None:
    """Enemy with a bezier S-curve should have non-trivial position over time."""
    from src.movement import BezierPath, HybridPath, PathFollower, Point

    e = _build_test_enemy()
    # Small bezier (control points close to endpoints) so the length is
    # short and a 1.0s duration gives us a full sweep.
    bez = BezierPath(
        Point(0, 0),
        Point(50, 80),    # right-down pull
        Point(150, -80),  # right-up pull
        Point(200, 0),    # back to neutral
    )
    h = HybridPath([bez], segment_durations=[2.0])  # explicit 2s duration
    e.attach_path(PathFollower(h))
    e.update(1.0, player_x=160.0, player_y=400.0)
    # After 1.0s on a 2.0s path, t=0.5 (midpoint of S-curve).
    # The y is symmetric and equals 0 at t=0.5; the interesting thing is
    # the velocity vector (the curve pulls through y=0, so vy should be
    # non-zero).
    assert 80 < e.x < 120, f"x at t=0.5 should be near 100, got {e.x}"
    # Velocity should be non-zero (the curve is moving)
    assert e.vx != 0.0 or e.vy != 0.0, (
        f"velocity at t=0.5 should be non-zero, got ({e.vx}, {e.vy})"
    )
    # And it must NOT be a straight line: a straight line at t=0.5
    # would have vx ~ 200, vy = 0. The bezier at t=0.5 has a
    # different velocity vector (the tangent is along the curve).
    assert not (abs(e.vx - 100.0) < 1.0 and e.vy == 0.0), (
        f"velocity ({e.vx}, {e.vy}) matches a straight line, not a bezier"
    )


def test_enemy_formation_slot_offset_applied() -> None:
    """Enemy with path + slot offset should sit at path_pos + slot_offset."""
    from src.movement import HybridPath, PathFollower, Point

    e = _build_test_enemy()
    path = HybridPath.straighten(Point(0, 0), Point(100, 0), speed_px_s=100.0)
    e.attach_path(PathFollower(path), slot_dx=20.0, slot_dy=30.0)
    e.update(0.5, player_x=160.0, player_y=400.0)
    # path midpoint is (50, 0); with slot offset (20, 30) -> (70, 30)
    assert 69 <= e.x <= 71
    assert 29 <= e.y <= 31


def test_enemy_without_path_uses_straight_line() -> None:
    """Default behavior (no follower) is preserved: enemy moves via vx/vy."""
    from src.entities.enemies.enemy import Enemy, EnemyKind

    e = _build_test_enemy()
    e.kind = EnemyKind.SCOUT
    e.vx = 0.0
    e.vy = 100.0  # straight down
    initial_y = e.y
    e.update(0.5, player_x=160.0, player_y=400.0)
    # Should have moved down 50 px via vx/vy
    assert e.y == initial_y + 50.0
    assert e.path_follower is None


def test_enemy_path_complete_stays_at_end() -> None:
    """When the path is done, enemy should stop moving (vx=vy=0)."""
    from src.movement import HybridPath, PathFollower, Point

    e = _build_test_enemy()
    path = HybridPath.straighten(Point(0, 0), Point(100, 0), speed_px_s=100.0)
    e.attach_path(PathFollower(path))
    # Run long enough to complete
    for _ in range(30):
        e.update(0.1, player_x=160.0, player_y=400.0)
    # x should be at end (100), vx/vy should be 0
    assert e.x == 100.0
    assert e.vx == 0.0
    assert e.vy == 0.0


# -----------------------------------------------------------------------
# FormationPathSpec \u2014 the bridge between FlightFormation + HybridPath
# -----------------------------------------------------------------------
def test_formation_path_spec_generates_enemies() -> None:
    """FormationPathSpec should produce N enemies (one per slot), each
    with a follower + slot offset set up correctly.
    """
    from src.movement import FlightFormation, HybridPath, PathFollower, Point
    from src.movement.spec import FormationPathSpec  # defined below

    formation = FlightFormation.v(5, spacing=18.0)
    path = HybridPath.straighten(Point(160, 0), Point(160, 480), speed_px_s=120.0)
    spec = FormationPathSpec(
        formation=formation,
        path=path,
        enemy_kind=None,  # type: ignore[arg-type]
        spawn_interval_s=0.15,
    )
    enemies = spec.build()
    assert len(enemies) == 5
    for e, (dx, dy) in zip(enemies, formation.offsets):
        assert e.path_follower is not None
        assert e.path_slot_dx == dx
        assert e.path_slot_dy == dy
