"""BLOQUE 58.6x: tests for the movement package (Bezier + Waypoint + Hybrid + Formation)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# -----------------------------------------------------------------------
# BezierPath
# -----------------------------------------------------------------------
def test_bezier_position_at_endpoints() -> None:
    """At t=0 must be p0; at t=1 must be p3."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(0, 0), Point(10, 50), Point(100, 50), Point(120, 0))
    p_start = b.position_at(0.0)
    p_end = b.position_at(1.0)
    assert p_start.x == 0 and p_start.y == 0
    assert p_end.x == 120 and p_end.y == 0


def test_bezier_position_at_midpoint_is_inside_control_polygon() -> None:
    """At t=0.5 the position must lie somewhere between the control points."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(0, 0), Point(0, 100), Point(200, 100), Point(200, 0))
    p_mid = b.position_at(0.5)
    # The midpoint of a symmetric curve is (100, 75) \u2014 75 is the average
    # of the Y of P0/P3 (0) and P1/P2 (100), weighted by the bezier math.
    assert 95 < p_mid.x < 105
    assert 70 < p_mid.y < 80


def test_bezier_tangent_direction() -> None:
    """At t=0 the tangent is along (P1-P0); at t=1 along (P3-P2)."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(0, 0), Point(10, 0), Point(20, 0), Point(30, 0))  # straight line
    t0 = b.tangent_at(0.0)
    t1 = b.tangent_at(1.0)
    assert t0.x == 10 and t0.y == 0
    assert t1.x == 10 and t1.y == 0


def test_bezier_clamps_out_of_range() -> None:
    """t < 0 returns p0; t > 1 returns p3."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(5, 5), Point(10, 10), Point(20, 20), Point(30, 30))
    assert b.position_at(-0.5) == Point(5, 5)
    assert b.position_at(2.0) == Point(30, 30)


def test_bezier_length_estimate_positive() -> None:
    """length_estimate should be > 0 for any non-degenerate curve."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(0, 0), Point(50, 100), Point(150, 100), Point(200, 0))
    L = b.length_estimate
    assert L > 0
    # Straight line of length 200 should give 200; bezier is longer
    straight = BezierPath(Point(0, 0), Point(0, 0), Point(200, 0), Point(200, 0))
    assert abs(straight.length_estimate - 200.0) < 1.0


# -----------------------------------------------------------------------
# BLOQUE 58.next: arc-length parameterization
# -----------------------------------------------------------------------
def test_bezier_total_arc_length_matches_length_estimate() -> None:
    """total_arc_length (64-sample table) should agree with length_estimate
    (16-sample polyline) to within a small tolerance."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(0, 0), Point(50, 100), Point(150, 100), Point(200, 0))
    assert abs(b.total_arc_length - b.length_estimate) < 1.0, (
        f"arc={b.total_arc_length}, estimate={b.length_estimate}"
    )


def test_bezier_position_at_distance_endpoints() -> None:
    """s=0 -> p0, s=total_arc_length -> p3."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(0, 0), Point(10, 50), Point(100, 50), Point(120, 0))
    a = b.position_at_distance(0.0)
    z = b.position_at_distance(b.total_arc_length)
    assert a.x == 0 and a.y == 0
    assert z.x == 120 and z.y == 0


def test_bezier_position_at_distance_constant_speed() -> None:
    """For a straight-line bezier, equal distance steps give equal
    position steps. (The point of arc-length: t and distance differ
    on curves, but agree on straight lines.)"""
    from src.movement import BezierPath, Point

    straight = BezierPath(Point(0, 0), Point(0, 0), Point(200, 0), Point(200, 0))
    L = straight.total_arc_length
    a = straight.position_at_distance(L * 0.25)
    b = straight.position_at_distance(L * 0.50)
    c = straight.position_at_distance(L * 0.75)
    # Each step should be 50 px
    assert a.x == pytest.approx(50, abs=0.5)
    assert b.x == pytest.approx(100, abs=0.5)
    assert c.x == pytest.approx(150, abs=0.5)


def test_bezier_tangent_at_distance() -> None:
    """At s=0 tangent is along (P1-P0); at s=total along (P3-P2)."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(0, 0), Point(10, 0), Point(20, 0), Point(30, 0))
    t0 = b.tangent_at_distance(0.0)
    tz = b.tangent_at_distance(b.total_arc_length)
    assert t0.x == 10 and t0.y == 0
    assert tz.x == 10 and tz.y == 0


def test_bezier_position_at_distance_clamps() -> None:
    """s < 0 returns p0; s > total returns p3."""
    from src.movement import BezierPath, Point

    b = BezierPath(Point(5, 5), Point(10, 10), Point(20, 20), Point(30, 30))
    assert b.position_at_distance(-10.0) == Point(5, 5)
    assert b.position_at_distance(99999.0) == Point(30, 30)


# -----------------------------------------------------------------------
# WaypointPath
# -----------------------------------------------------------------------
def test_waypoint_simple_line() -> None:
    """Two waypoints: position at half-distance is the midpoint."""
    from src.movement import Point, WaypointPath

    wp = WaypointPath([Point(0, 0), Point(100, 0)], speed_px_s=100.0)
    pt, tan = wp.position_at_distance(50.0)
    assert pt.x == 50 and pt.y == 0
    assert tan.x == 1.0 and tan.y == 0.0  # unit vector along +x
    # Total length 100 at 100 px/s -> 1.0 s
    assert wp.total_duration_s == 1.0


def test_waypoint_three_points_with_linger() -> None:
    """Three waypoints with a linger in the middle; total duration sums linger + move."""
    from src.movement import Point, WaypointPath

    wp = WaypointPath(
        [Point(0, 0), Point(50, 0), Point(50, 100)],
        speed_px_s=100.0,
        linger_s=[0.0, 0.5, 0.0],  # 0.5s pause at the middle waypoint
    )
    # Move: 50 + 100 = 150 px at 100 px/s = 1.5 s
    # Linger: 0.5 s
    # Total: 2.0 s
    assert wp.total_duration_s == 2.0


def test_waypoint_empty_raises() -> None:
    from src.movement import WaypointPath

    try:
        WaypointPath([], speed_px_s=100.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty waypoints")


def test_waypoint_zero_speed_raises() -> None:
    from src.movement import Point, WaypointPath

    try:
        WaypointPath([Point(0, 0), Point(10, 10)], speed_px_s=0.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError for speed=0")


# -----------------------------------------------------------------------
# HybridPath
# -----------------------------------------------------------------------
def test_hybrid_two_segments_advance_over_time() -> None:
    """HybridPath with bezier + waypoint; position should move through both."""
    from src.movement import BezierPath, HybridPath, Point, WaypointPath

    bez = BezierPath(Point(0, 0), Point(50, 0), Point(50, 50), Point(100, 50))
    wp = WaypointPath([Point(100, 50), Point(100, 200)], speed_px_s=100.0)
    h = HybridPath([bez, wp])
    assert h.total_duration_s > 0
    # At t=0 should be at bezier start
    p0 = h.position_at(0.0)
    assert p0.x == 0 and p0.y == 0
    # At t=1 should be at the end of the waypoint
    p1 = h.position_at(1.0)
    assert p1.x == 100 and p1.y == 200


def test_hybrid_straighten_convenience() -> None:
    """HybridPath.straighten produces a single-segment waypoint path."""
    from src.movement import HybridPath, Point

    h = HybridPath.straighten(Point(0, 0), Point(100, 0), speed_px_s=50.0)
    assert h.total_duration_s == 2.0  # 100 px / 50 px/s


def test_hybrid_tangent_zero_at_endpoints_of_segment() -> None:
    """Inside a segment, tangent magnitude can be non-zero."""
    from src.movement import BezierPath, HybridPath, Point

    bez = BezierPath(Point(0, 0), Point(0, 100), Point(0, 100), Point(0, 200))
    h = HybridPath([bez])
    tan = h.tangent_at(0.5)
    # All going down (+y), so vx should be 0 (or very close), vy > 0
    assert abs(tan.x) < 0.01
    assert tan.y > 0


# -----------------------------------------------------------------------
# PathFollower
# -----------------------------------------------------------------------
def test_follower_advances_to_completion() -> None:
    """Follower with dt accumulation should hit t=1.0 after total_duration_s."""
    from src.movement import HybridPath, PathFollower, Point

    h = HybridPath.straighten(Point(0, 0), Point(100, 0), speed_px_s=100.0)
    f = PathFollower(h)
    assert f.t == 0.0
    assert not f.is_complete
    f.update(0.5)  # half-way
    assert 0.4 < f.t < 0.6
    f.update(0.5)  # rest of the way
    assert f.t == 1.0
    assert f.is_complete


def test_follower_position_matches_path() -> None:
    """Follower.update() position should equal path.position_at(t)."""
    from src.movement import HybridPath, PathFollower, Point

    h = HybridPath.straighten(Point(10, 20), Point(110, 20), speed_px_s=100.0)
    f = PathFollower(h)
    pos, vel = f.update(0.5)  # t=0.5 -> midpoint (60, 20)
    assert pos.x == 60
    assert pos.y == 20


# -----------------------------------------------------------------------
# BLOQUE 58.next: HybridPath + PathFollower distance-based behavior
# -----------------------------------------------------------------------
def test_hybrid_path_total_arc_length() -> None:
    """HybridPath.total_arc_length = sum of per-segment arc lengths."""
    from src.movement import HybridPath, WaypointPath, Point
    from src.movement.bezier import BezierPath

    # 2 segments: a straight 100px and a 200px bezier
    seg1 = WaypointPath([Point(0, 0), Point(100, 0)], speed_px_s=100.0)
    seg2 = BezierPath(Point(100, 0), Point(100, 100), Point(300, 100), Point(300, 0))
    h = HybridPath([seg1, seg2])
    expected = 100.0 + seg2.total_arc_length
    assert h.total_arc_length == pytest.approx(expected, abs=0.5)


def test_hybrid_path_position_at_distance() -> None:
    """s=0 -> first segment start, s=total -> last segment end."""
    from src.movement import HybridPath, WaypointPath, Point

    h = HybridPath([
        WaypointPath([Point(0, 0), Point(50, 0)], speed_px_s=100.0),
        WaypointPath([Point(50, 0), Point(100, 0)], speed_px_s=100.0),
    ])
    start = h.position_at_distance(0.0)
    end = h.position_at_distance(h.total_arc_length)
    assert start.x == 0 and start.y == 0
    assert end.x == 100 and end.y == 0


def test_follower_constant_speed_in_pixels() -> None:
    """BLOQUE 58.next: the follower's velocity is in px/s, constant in
    screen space. For a straight path, two equal dt's should produce
    equal pixel deltas (regardless of segment internals)."""
    from src.movement import HybridPath, PathFollower, Point

    h = HybridPath.straighten(Point(0, 0), Point(200, 0), speed_px_s=100.0)
    f = PathFollower(h)
    # 0.5s at 100 px/s = 50 px
    pos_a, _ = f.update(0.5)
    pos_b, _ = f.update(0.5)
    assert pos_b.x - pos_a.x == pytest.approx(50, abs=0.5)


def test_follower_s_property_reflects_arc_position() -> None:
    """BLOQUE 58.next: follower.s gives the current arc length (px)."""
    from src.movement import HybridPath, PathFollower, Point

    h = HybridPath.straighten(Point(0, 0), Point(100, 0), speed_px_s=100.0)
    f = PathFollower(h)
    assert f.s == pytest.approx(0.0, abs=0.1)
    f.update(0.3)  # 0.3s * 100 px/s = 30 px
    assert f.s == pytest.approx(30.0, abs=0.5)
    f.update(0.7)  # rest of the way
    assert f.s == pytest.approx(100.0, abs=0.5)
    assert f.is_complete


def test_follower_t_offset_uses_arc_length() -> None:
    """BLOQUE 58.next: t_offset (seconds) converts to arc length via the
    first segment's speed. Two followers with different t_offsets start
    at different positions along the same path."""
    from src.movement import HybridPath, PathFollower, Point

    h = HybridPath.straighten(Point(0, 0), Point(100, 0), speed_px_s=100.0)
    f0 = PathFollower(h, t_offset=0.0)
    f1 = PathFollower(h, t_offset=0.5)  # 0.5s ahead = 50 px
    assert f0.s == pytest.approx(0.0, abs=0.1)
    assert f1.s == pytest.approx(50.0, abs=0.5)
    # Velocity of f0 should be in +x at 100 px/s (use a small dt so the
    # follower's "complete + dt<=0 returns zero vel" branch doesn't fire).
    _, vel0 = f0.update(0.001)
    assert vel0.x == pytest.approx(100, abs=1.0)
    assert vel0.y == pytest.approx(0, abs=1.0)


def test_follower_reset() -> None:
    from src.movement import HybridPath, PathFollower, Point

    h = HybridPath.straighten(Point(0, 0), Point(100, 0), speed_px_s=100.0)
    f = PathFollower(h)
    f.update(2.0)  # over-shoot
    assert f.is_complete
    f.reset()
    assert not f.is_complete
    assert f.t == 0.0


# -----------------------------------------------------------------------
# FlightFormation
# -----------------------------------------------------------------------
def test_formation_v_count_matches() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.v(5)
    assert f.count == 5
    # Leader is at (0, 0)
    assert (0.0, 0.0) in f.offsets


def test_formation_line_symmetric() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.line(5, spacing=20.0)
    # Slots at -40, -20, 0, 20, 40 on the x axis
    xs = sorted(p[0] for p in f.offsets)
    assert xs == [-40.0, -20.0, 0.0, 20.0, 40.0]
    assert all(p[1] == 0.0 for p in f.offsets)


def test_formation_diamond_5_slots() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.diamond(5)
    # 5 slots: center + 4 cardinal points
    assert f.count == 5
    assert (0.0, 0.0) in f.offsets


def test_formation_square_5_slots() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.square(5)
    assert f.count == 5
    # Center + 4 corners
    assert (0.0, 0.0) in f.offsets


def test_formation_wedge_count_matches() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.wedge(5)
    assert f.count == 5


def test_formation_circle_count_matches() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.circle(8, radius=20.0)
    assert f.count == 8
    # All slots should be at the given radius
    for x, y in f.offsets:
        assert math.hypot(x, y) == pytest_approx(20.0)


def test_formation_triangle_count_matches() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.triangle(6)
    assert f.count == 6


def test_formation_half_v_count_matches() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.half_v(5)
    assert f.count == 5


def test_formation_custom() -> None:
    from src.movement import FlightFormation

    f = FlightFormation.custom([(0, 0), (10, 0), (20, 0), (5, 10)])
    assert f.count == 4


def test_formation_make_dispatch() -> None:
    """FlightFormation.make dispatches to the right preset."""
    from src.movement import FlightFormation, FormationKind

    f = FlightFormation.make(FormationKind.LINE, count=3, spacing=10.0)
    assert f.kind == FormationKind.LINE
    assert f.count == 3


def test_flower_of_life_default_count() -> None:
    """FLOWER_OF_LIFE with count=7 returns 7 slots: 1 center + 6 hex."""
    from src.movement import FlightFormation, FormationKind

    form = FlightFormation.flower_of_life()
    assert form.kind == FormationKind.FLOWER_OF_LIFE
    assert form.count == 7
    assert (0.0, 0.0) in form.offsets  # center


def test_flower_of_life_offsets_match_geometry() -> None:
    """The 6 outer slots are at radius=18, angles 0/60/120/180/240/300 deg."""
    from src.movement import FlightFormation

    form = FlightFormation.flower_of_life()
    outer = [(dx, dy) for dx, dy in form.offsets if (dx, dy) != (0.0, 0.0)]
    assert len(outer) == 6
    expected_angles = [0, 60, 120, 180, 240, 300]
    for dx, dy, angle_deg in zip([dx for dx, _ in outer], [dy for _, dy in outer], expected_angles):
        r = math.hypot(dx, dy)
        assert math.isclose(r, 18.0, abs_tol=0.1), f"radius {r} != 18 at angle {angle_deg}"
        expected_angle = math.radians(angle_deg)
        actual_angle = math.atan2(dy, dx)
        # angles modulo 2pi
        assert math.isclose(
            (actual_angle - expected_angle) % (2 * math.pi), 0, abs_tol=0.01
        ), f"angle {math.degrees(actual_angle)} != {angle_deg}"


# --- BLOQUE 58.next: 9 sacred-geometry / fractal formations ---
PHI = (1 + math.sqrt(5)) / 2  # golden ratio, for fibonacfi_spiral + golden_ratio_row


def test_vesica_piscis_two_ships() -> None:
    from src.movement import FlightFormation, FormationKind

    form = FlightFormation.vesica_piscis()
    assert form.kind == FormationKind.VESICA_PISCIS
    assert form.count == 2
    assert math.isclose(form.offsets[0][0], -9.0, abs_tol=0.1)
    assert math.isclose(form.offsets[1][0], 9.0, abs_tol=0.1)


def test_fibonacfi_spiral_golden_ratio() -> None:
    """Verify r-values follow r = r0 * phi^(i/2) within 1%."""
    from src.movement import FlightFormation

    form = FlightFormation.fibonacfi_spiral()
    r0 = 8.0
    for i, (dx, dy) in enumerate(form.offsets):
        r_actual = math.hypot(dx, dy)
        r_expected = r0 * (PHI ** (i / 2))
        assert math.isclose(r_actual, r_expected, rel_tol=0.01), f"slot {i}: r {r_actual} != {r_expected}"


def test_tree_of_life_10_ships() -> None:
    from src.movement import FlightFormation, FormationKind

    form = FlightFormation.tree_of_life()
    assert form.kind == FormationKind.TREE_OF_LIFE
    assert form.count == 10
    # 3 left col (-22, y), 3 mid col (0, y), 3 right col (+22, y), 1 bottom (0, +44)
    xs = sorted(dx for dx, _ in form.offsets)
    assert xs.count(-22) == 3
    assert xs.count(0) == 4
    assert xs.count(22) == 3


def test_sierpinski_triangle_depth_2() -> None:
    from src.movement import FlightFormation

    form = FlightFormation.sierpinski_triangle()
    assert form.count == 7
    # top vertex at (0, -24), centroid at (0, 0)
    assert (0.0, -24.0) in form.offsets
    assert (0.0, 0.0) in form.offsets


def test_hex_close_pack_seven_ships() -> None:
    from src.movement import FlightFormation

    form = FlightFormation.hex_close_pack()
    assert form.count == 7
    # 6 outer at radius 14
    outer = [(dx, dy) for dx, dy in form.offsets if (dx, dy) != (0.0, 0.0)]
    for dx, dy in outer:
        assert math.isclose(math.hypot(dx, dy), 14.0, abs_tol=0.1)


def test_mandala_rings_concentric() -> None:
    from src.movement import FlightFormation

    form = FlightFormation.mandala_rings()
    assert form.count == 12
    # 6 inner at r=12, 6 outer at r=24
    inner = [(dx, dy) for dx, dy in form.offsets if math.isclose(math.hypot(dx, dy), 12.0, abs_tol=0.1)]
    outer = [(dx, dy) for dx, dy in form.offsets if math.isclose(math.hypot(dx, dy), 24.0, abs_tol=0.1)]
    assert len(inner) == 6
    assert len(outer) == 6


def test_golden_ratio_row_phi_offsets() -> None:
    from src.movement import FlightFormation

    form = FlightFormation.golden_ratio_row(spacing=10.0)
    assert form.count == 5
    expected_xs = [0.0, 1 * PHI * 10, 2 * PHI * 10, 3 * PHI * 10, 4 * PHI * 10]
    actual_xs = [dx for dx, _ in form.offsets]
    for exp, act in zip(expected_xs, actual_xs):
        assert math.isclose(act, exp, rel_tol=0.01), f"x {act} != {exp}"


def test_koch_3fold_seven_ships() -> None:
    """Koch 3-fold: 7 anchor points on a 3-fold zigzag, NO central peak (not a star)."""
    from src.movement import FlightFormation

    form = FlightFormation.koch_3fold()
    assert form.count == 7
    # No slot should be at (0, 0) — that would be a central star point
    assert (0.0, 0.0) not in form.offsets


def test_dragon_curve_recursive_layout() -> None:
    """First 8 anchors of the Heighway dragon curve."""
    from src.movement import FlightFormation

    form = FlightFormation.dragon_curve()
    assert form.count == 8
    assert (0.0, 0.0) in form.offsets  # origin
    assert (0.0, -16.0) in form.offsets  # first up


# --- BLOQUE 58.next fix round 1: make() dispatch smoke tests ---
# These guard against the bug class where make() passes `spacing=18` (or
# the default `radius=24`) as a parameter that the formation builder
# doesn't accept, or accepts under a different name. Each test calls
# FlightFormation.make(...) (the public dispatch) and asserts the spec
# default radius is honored, not the generic spacing/radius argument.
def test_flower_of_life_make_dispatch() -> None:
    """make(FLOWER_OF_LIFE) routes through radius=18 (not spacing=18)."""
    from src.movement import FlightFormation, FormationKind

    f = FlightFormation.make(FormationKind.FLOWER_OF_LIFE, count=7)
    assert f.kind == FormationKind.FLOWER_OF_LIFE
    assert f.count == 7
    # 6 outer slots at radius 18
    outer = [(dx, dy) for dx, dy in f.offsets if (dx, dy) != (0.0, 0.0)]
    assert len(outer) == 6
    for dx, dy in outer:
        assert math.isclose(math.hypot(dx, dy), 18.0, abs_tol=0.1)


def test_vesica_piscis_make_dispatch() -> None:
    """make(VESICA_PISCIS) routes through spacing=18 (default)."""
    from src.movement import FlightFormation, FormationKind

    f = FlightFormation.make(FormationKind.VESICA_PISCIS, count=2)
    assert f.kind == FormationKind.VESICA_PISCIS
    assert f.count == 2
    assert math.isclose(f.offsets[0][0], -9.0, abs_tol=0.1)
    assert math.isclose(f.offsets[1][0], 9.0, abs_tol=0.1)


def test_fibonacfi_spiral_make_dispatch() -> None:
    """make(FIBONACFI_SPIRAL) routes through r0=8.0 (not spacing=18)."""
    from src.movement import FlightFormation, FormationKind

    f = FlightFormation.make(FormationKind.FIBONACFI_SPIRAL, count=7)
    assert f.kind == FormationKind.FIBONACFI_SPIRAL
    assert f.count == 7
    # First slot is at r0=8.0 (spec default), not 18.0 (would be the bug).
    r_first = math.hypot(f.offsets[0][0], f.offsets[0][1])
    assert math.isclose(r_first, 8.0, abs_tol=0.1), (
        f"first slot r={r_first} should be 8.0 (spec default r0), not 18.0"
    )


def test_hex_close_pack_make_dispatch() -> None:
    """make(HEX_CLOSE_PACK) routes through radius=14 (not spacing=18)."""
    from src.movement import FlightFormation, FormationKind

    f = FlightFormation.make(FormationKind.HEX_CLOSE_PACK, count=7)
    assert f.kind == FormationKind.HEX_CLOSE_PACK
    assert f.count == 7
    # 6 outer at radius 14, not 18 (would be the bug).
    outer = [(dx, dy) for dx, dy in f.offsets if (dx, dy) != (0.0, 0.0)]
    assert len(outer) == 6
    for dx, dy in outer:
        assert math.isclose(math.hypot(dx, dy), 14.0, abs_tol=0.1), (
            f"outer slot r={math.hypot(dx, dy)} should be 14.0, not 18.0"
        )


def test_sierpinski_triangle_make_dispatch() -> None:
    """make(SIERPINSKI_TRIANGLE) routes through radius=24 (not spacing=18)."""
    from src.movement import FlightFormation, FormationKind

    f = FlightFormation.make(FormationKind.SIERPINSKI_TRIANGLE, count=7)
    assert f.kind == FormationKind.SIERPINSKI_TRIANGLE
    assert f.count == 7
    # Top vertex at (0, -24) — r=24 (spec default), not 18 (would be the bug).
    assert (0.0, -24.0) in f.offsets, (
        f"top vertex (0, -24) missing; offsets={f.offsets}"
    )


def test_mandala_rings_make_dispatch() -> None:
    """make(MANDALA_RINGS) routes through inner_r=12, outer_r=24 (not radius=24)."""
    from src.movement import FlightFormation, FormationKind

    f = FlightFormation.make(FormationKind.MANDALA_RINGS, count=12)
    assert f.kind == FormationKind.MANDALA_RINGS
    assert f.count == 12
    # 6 inner at r=12, 6 outer at r=24
    inner = [(dx, dy) for dx, dy in f.offsets
             if math.isclose(math.hypot(dx, dy), 12.0, abs_tol=0.1)]
    outer = [(dx, dy) for dx, dy in f.offsets
             if math.isclose(math.hypot(dx, dy), 24.0, abs_tol=0.1)]
    assert len(inner) == 6
    assert len(outer) == 6


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def pytest_approx(value: float, rel: float = 1e-6) -> object:
    """Tiny local approx helper to avoid pytest import at top of test module."""
    class _Approx:
        def __init__(self, v: float, r: float) -> None:
            self.v = v
            self.r = r
        def __eq__(self, other: object) -> bool:
            return abs(float(other) - self.v) <= self.r * max(abs(self.v), 1.0)
    return _Approx(value, rel)
