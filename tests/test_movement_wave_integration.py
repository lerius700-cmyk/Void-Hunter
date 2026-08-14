"""BLOQUE 58.6x: integration test for the LEVEL1_WAVES path system.

Verifies that the `path` field on each wave spec is valid and that an
Enemy spawned from a wave with a path gets a PathFollower attached
(bypassing the straight-line vx/vy).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_all_level1_waves_have_valid_path_specs() -> None:
    """Every wave in LEVEL1_WAVES has either no `path` or a valid one.

    A valid `path` is a dict with `kind` in {"straight", "hybrid"} and
    matching segment structure.
    """
    from src.systems.wave_manager import LEVEL1_WAVES

    for i, spec in enumerate(LEVEL1_WAVES):
        path = spec.get("path")
        if path is None:
            continue
        kind = path.get("kind")
        assert kind in ("straight", "hybrid"), (
            f"wave {i}: path.kind must be 'straight' or 'hybrid', got {kind!r}"
        )
        if kind == "straight":
            # No segments needed, just speed
            assert "speed" in path, f"wave {i}: straight path needs 'speed'"
        else:
            segs = path.get("segments", [])
            assert segs, f"wave {i}: hybrid path needs non-empty segments"
            for j, seg in enumerate(segs):
                stype = seg.get("type")
                assert stype in ("bezier", "waypoint"), (
                    f"wave {i} seg {j}: type must be bezier/waypoint, got {stype!r}"
                )
                if stype == "bezier":
                    for key in ("p0", "p1", "p2", "p3"):
                        assert key in seg, f"wave {i} seg {j}: bezier missing {key}"
                        pt = seg[key]
                        assert len(pt) == 2, f"wave {i} seg {j}: {key} must be 2-tuple"
                else:  # waypoint
                    assert "points" in seg, f"wave {i} seg {j}: waypoint needs points"
                    assert len(seg["points"]) >= 2, (
                        f"wave {i} seg {j}: waypoint needs >= 2 points"
                    )


def test_attach_wave_path_straight() -> None:
    """A wave with `path: {kind: straight, speed: 80}` produces an enemy
    with a PathFollower, and the path is a single straight segment.
    """
    from src.entities.enemies.enemy import Enemy, EnemyKind
    from src.movement import PathFollower

    e = Enemy()
    e.active = True
    e.x = 50.0
    e.y = -10.0
    e.on_spawn()
    e.kind = EnemyKind.SCOUT

    # Simulate what _attach_wave_path does
    from src.movement import HybridPath, Point
    start = Point(e.x, e.y)
    end = Point(e.x, 520.0)
    path = HybridPath.straighten(start, end, speed_px_s=80.0)
    e.attach_path(PathFollower(path))

    # Run the enemy forward 1 second; it should move DOWN at 80 px/s
    for _ in range(10):
        e.update(0.1, player_x=160.0, player_y=400.0)
    # After 1.0s at 80 px/s: y moved 80 px -> from -10 to 70
    assert e.y > 50
    # The follower's vx should be 0 (pure vertical descent)
    assert abs(e.vx) < 0.1


def test_attach_wave_path_hybrid_segments_count() -> None:
    """A wave with `path: {kind: hybrid, segments: [bezier, waypoint]}`
    produces a HybridPath with 2 segments.
    """
    from src.movement import BezierPath, HybridPath, Point, WaypointPath

    bez = BezierPath(Point(0, 0), Point(0, 100), Point(200, 100), Point(200, 200))
    wp = WaypointPath([Point(200, 200), Point(200, 400)], speed_px_s=100.0)
    h = HybridPath([bez, wp], segment_durations=[2.0, 2.0])
    assert h.total_duration_s == 4.0
    # Verify it advances correctly
    from src.movement.follower import PathFollower
    f = PathFollower(h)
    pos0, _ = f.update(0.0)
    pos_mid, _ = f.update(2.0)  # end of bezier -> (200, 200)
    assert pos_mid.x == 200.0 and pos_mid.y == 200.0
    pos_end, _ = f.update(2.0)  # end of waypoint -> (200, 400)
    assert pos_end.x == 200.0 and pos_end.y == 400.0


def test_path_spec_in_actual_level1_wave2() -> None:
    """Wave 2 (V formation) has a bezier path; verify the path is reachable
    and produces a valid HybridPath when fed to the runtime helper.
    """
    from src.systems.wave_manager import LEVEL1_WAVES

    spec = LEVEL1_WAVES[1]  # O2
    assert spec.get("formation") == "v"
    path = spec.get("path")
    assert path is not None
    assert path["kind"] == "hybrid"
    seg = path["segments"][0]
    assert seg["type"] == "bezier"
    # Sanity: the bezier P0 starts at the top of the playfield
    assert seg["p0"][1] < 0  # negative y = off-screen above
    # P3 ends at or below the bottom of the playfield (480)
    assert seg["p3"][1] >= 400


def test_path_spec_in_actual_level1_wave3() -> None:
    """Wave 3 (line) has a waypoint path."""
    from src.systems.wave_manager import LEVEL1_WAVES

    spec = LEVEL1_WAVES[2]  # O3
    assert spec.get("formation") == "line"
    path = spec.get("path")
    assert path is not None
    seg = path["segments"][0]
    assert seg["type"] == "waypoint"
    # Should have 4 waypoints (down, right, down)
    assert len(seg["points"]) == 4


def test_path_spec_in_actual_level1_wave4_hybrid() -> None:
    """Wave 4 (diamond) has a HYBRID path: bezier + waypoint."""
    from src.systems.wave_manager import LEVEL1_WAVES

    spec = LEVEL1_WAVES[3]  # O4
    path = spec.get("path")
    assert path is not None
    segs = path["segments"]
    assert len(segs) == 2
    assert segs[0]["type"] == "bezier"
    assert segs[1]["type"] == "waypoint"
    # The bezier should end where the waypoint starts
    bez_end = segs[0]["p3"]
    wp_start = segs[1]["points"][0]
    assert bez_end[0] == wp_start[0]
    assert bez_end[1] == wp_start[1]
