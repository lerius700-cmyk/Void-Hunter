"""BLOQUE 58.13: Tests for ParallelPathPair + OrbitalPath + 4 patterns."""
from __future__ import annotations

import pytest
from src.movement.parallel_path import ParallelPathPair
from src.movement.orbital_path import OrbitalPath


# ----------------------------------------------------------------------
# ParallelPathPair tests (5)
# ----------------------------------------------------------------------
def test_parallel_pair_top_bot_offset_at_midpoint():
    """top and bot paths have correct vertical offset at t=0.5 of seg 0."""
    base = [((10, 100), (50, 100), (100, 100), (200, 100))]
    ppp = ParallelPathPair(base, [2.0], gap_px=20)
    top = ppp.get_top().position_at(0.5)
    bot = ppp.get_bot().position_at(0.5)
    assert top.y == pytest.approx(100 - 10, abs=0.01)
    assert bot.y == pytest.approx(100 + 10, abs=0.01)
    assert top.x == pytest.approx(bot.x, abs=0.01)


def test_parallel_pair_same_segment_count_and_durations():
    """both paths have same segment count and durations."""
    base = [
        ((10, 100), (50, 100), (100, 100), (200, 100)),
        ((200, 100), (250, 100), (280, 150), (300, 200)),
    ]
    durations = [1.5, 2.0]
    ppp = ParallelPathPair(base, durations, gap_px=14)
    top = ppp.get_top()
    bot = ppp.get_bot()
    assert len(top.segments) == 2
    assert len(bot.segments) == 2
    assert top.segment_durations == durations
    assert bot.segment_durations == durations


def test_parallel_pair_gap_zero_equals_centerline():
    """gap_px=0 means top and bot are identical."""
    base = [((0, 50), (50, 50), (100, 50), (150, 50))]
    ppp = ParallelPathPair(base, [2.0], gap_px=0)
    top = ppp.get_top().position_at(0.3)
    bot = ppp.get_bot().position_at(0.3)
    assert top.x == pytest.approx(bot.x, abs=0.001)
    assert top.y == pytest.approx(bot.y, abs=0.001)


def test_parallel_pair_durations_match_base():
    """durations pass through unchanged for both paths."""
    durations = [1.0, 2.5, 1.5]
    base = [
        ((0, 0), (10, 0), (20, 0), (30, 0)),
        ((30, 0), (40, 0), (50, 0), (60, 0)),
        ((60, 0), (70, 0), (80, 0), (90, 0)),
    ]
    ppp = ParallelPathPair(base, durations, gap_px=10)
    assert ppp.get_top().segment_durations == durations
    assert ppp.get_bot().segment_durations == durations


def test_parallel_pair_offset_signs():
    """top is offset by -gap/2 (up), bot by +gap/2 (down)."""
    base = [((50, 100), (60, 100), (70, 100), (80, 100))]
    ppp = ParallelPathPair(base, [1.0], gap_px=14)
    top = ppp.get_top().position_at(0.5)
    bot = ppp.get_bot().position_at(0.5)
    assert top.y == pytest.approx(93.0, abs=0.01)
    assert bot.y == pytest.approx(107.0, abs=0.01)


# ----------------------------------------------------------------------
# OrbitalPath tests (4)
# ----------------------------------------------------------------------
def test_orbital_path_returns_4_segments():
    """4 segments (quarters of orbit)."""
    op = OrbitalPath(center=(160, 240), radius_x=100, radius_y=80, duration_s=6.0)
    path = op.get_path()
    assert len(path.segments) == 4


def test_orbital_path_segment_durations_sum_to_total():
    """durations add up to duration_s."""
    op = OrbitalPath(center=(160, 240), radius_x=100, radius_y=80, duration_s=4.8)
    path = op.get_path()
    assert sum(path.segment_durations) == pytest.approx(4.8, abs=0.001)


def test_orbital_path_center_is_inside_quad():
    """Midpoint of each segment is roughly on the orbital circle (within 20%)."""
    op = OrbitalPath(center=(100, 100), radius_x=80, radius_y=60, duration_s=4.0)
    path = op.get_path()
    for i in range(4):
        seg_dur = path.segment_durations[i]
        global_t = (sum(path.segment_durations[:i]) + seg_dur * 0.5) / path.total_duration_s
        pt = path.position_at(global_t)
        assert abs(pt.x - 100) <= 80 * 1.1 + 1
        assert abs(pt.y - 100) <= 60 * 1.1 + 1


def test_orbital_path_rotation_offset():
    """rotation_deg=90 rotates the orbit (start point moves)."""
    op0 = OrbitalPath(center=(100, 100), radius_x=80, radius_y=80,
                      duration_s=4.0, rotation_deg=0)
    op90 = OrbitalPath(center=(100, 100), radius_x=80, radius_y=80,
                       duration_s=4.0, rotation_deg=90)
    p0 = op0.get_path().position_at(0.0)
    p90 = op90.get_path().position_at(0.0)
    assert p0.x == pytest.approx(180, abs=1.0)
    assert p0.y == pytest.approx(100, abs=1.0)
    assert p90.x == pytest.approx(100, abs=1.0)
    assert p90.y == pytest.approx(20, abs=1.0)


# ----------------------------------------------------------------------
# Runtime attach tests (2)
# ----------------------------------------------------------------------
def test_attach_parallel_pair_path_attaches_follower():
    """attach_parallel_pair_path sets path_follower on the enemy."""
    from src.entities.enemies.enemy import Enemy, EnemyKind, EnemyPool
    from src.systems.wave_patterns.runtime import attach_parallel_pair_path
    from src.movement.parallel_path import ParallelPathPair

    pool = EnemyPool(capacity=2)
    ppp = ParallelPathPair([((0, 100), (100, 100), (200, 100), (300, 100))], [1.0])
    e = pool.spawn(EnemyKind.SCOUT, 0, 100)
    assert e is not None
    assert e.path_follower is None
    attach_parallel_pair_path(e, ppp, "top", t_offset=0.0)
    assert e.path_follower is not None


def test_attach_orbital_path_attaches_follower():
    """attach_orbital_path sets path_follower on the enemy."""
    from src.entities.enemies.enemy import Enemy, EnemyKind, EnemyPool
    from src.systems.wave_patterns.runtime import attach_orbital_path
    from src.movement.orbital_path import OrbitalPath

    pool = EnemyPool(capacity=2)
    op = OrbitalPath(center=(160, 240), radius_x=80, radius_y=60, duration_s=4.0)
    e = pool.spawn(EnemyKind.SCOUT, 160, 240)
    assert e is not None
    assert e.path_follower is None
    attach_orbital_path(e, op, t_offset=0.0)
    assert e.path_follower is not None


# ----------------------------------------------------------------------
# BEZIER_SWEEP pair dance tests (3)
# ----------------------------------------------------------------------
def test_bezier_sweep_5_pairs_at_level5():
    """5 pairs (10 ships) at level 5+."""
    import random
    from src.systems.wave_patterns.bezier_sweep import BezierSweepPattern
    rng = random.Random(42)
    pattern = BezierSweepPattern()
    result = pattern.generate(rng, level=5)
    assert len(result.ships) == 10
    leader_count = sum(1 for s in result.ships if s.is_leader)
    assert leader_count == 5


def test_bezier_sweep_pairs_share_parallel_pair():
    """2 ships in a pair share the same parallel_pair but different sides."""
    import random
    from src.systems.wave_patterns.bezier_sweep import BezierSweepPattern
    rng = random.Random(42)
    pattern = BezierSweepPattern()
    result = pattern.generate(rng, level=2)
    for i in range(0, len(result.ships), 2):
        s1 = result.ships[i]
        s2 = result.ships[i + 1]
        assert s1.extra["parallel_pair"] is s2.extra["parallel_pair"]
        assert {s1.extra["side"], s2.extra["side"]} == {"top", "bot"}


def test_bezier_sweep_pair_color_variation():
    """Pair colors are close but distinct."""
    import random
    from src.systems.wave_patterns.bezier_sweep import BezierSweepPattern
    rng = random.Random(42)
    pattern = BezierSweepPattern()
    result = pattern.generate(rng, level=2)
    s1 = result.ships[0]
    s2 = result.ships[1]
    assert s1.color is not None
    assert s2.color is not None
    assert s1.color != s2.color
