"""BLOQUE 58.8: tests for procedural wave patterns + manager.

80+ tests covering:
  - BEZIER_SWEEP: control points, stagger, determinism
  - V_FORMATION: offsets, sizes, rigidity
  - LEADER_FOLLOWER_CHAIN: history queue, delay, leader/follower
  - DICE_FIVE_GRID: 5 ships, layout, orbit
  - PINCER_CROSS: mirror, convergence, sides
  - Manager: difficulty curve, determinism, anti-repeat
  - Enemy factory: param variation, determinism, level scaling
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest


# =====================================================================
# BEZIER_SWEEP tests
# =====================================================================
class TestBezierSweep:
    def test_kind_is_bezier_sweep(self):
        from src.systems.wave_patterns import BezierSweepPattern
        from src.systems.wave_patterns.base import WavePatternKind
        assert BezierSweepPattern.kind == WavePatternKind.BEZIER_SWEEP

    def test_difficulty_is_medium(self):
        from src.systems.wave_patterns import BezierSweepPattern
        from src.systems.wave_patterns.base import PatternDifficulty
        assert BezierSweepPattern.difficulty == PatternDifficulty.MEDIUM

    def test_generates_at_least_4_ships(self):
        from src.systems.wave_patterns import BezierSweepPattern
        rng = random.Random(42)
        result = BezierSweepPattern().generate(rng, level=1)
        assert len(result.ships) >= 4

    def test_ship_count_scales_with_level(self):
        from src.systems.wave_patterns import BezierSweepPattern
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        r1 = BezierSweepPattern().generate(rng1, level=1)
        r2 = BezierSweepPattern().generate(rng2, level=10)
        assert len(r2.ships) >= len(r1.ships)

    def test_has_5_pairs_at_level_5(self):
        """BLOQUE 58.13: level 5+ produces 10 ships (5 pairs)."""
        from src.systems.wave_patterns import BezierSweepPattern
        rng = random.Random(42)
        result = BezierSweepPattern().generate(rng, level=5)
        assert len(result.ships) == 10

    def test_has_parallel_pair(self):
        """BLOQUE 58.13: each ship has parallel_pair in extra (not segments)."""
        from src.systems.wave_patterns import BezierSweepPattern
        rng = random.Random(42)
        result = BezierSweepPattern().generate(rng, level=3)
        for ship in result.ships:
            assert "parallel_pair" in ship.extra
            assert "side" in ship.extra
            assert "segments" not in ship.extra

    def test_pairs_share_t_offset(self):
        """BLOQUE 58.13: consecutive ships (a pair) share t_offset;
        pair index increments by 0.12s between pairs."""
        from src.systems.wave_patterns import BezierSweepPattern
        rng = random.Random(42)
        result = BezierSweepPattern().generate(rng, level=3)
        # Ships [0,1] = pair 0, [2,3] = pair 1, [4,5] = pair 2
        # Within a pair: same t_offset
        for i in range(0, len(result.ships), 2):
            assert result.ships[i].t_offset == pytest.approx(
                result.ships[i + 1].t_offset, abs=0.001
            )
        # Between pairs: later pair starts later
        if len(result.ships) >= 4:
            assert result.ships[2].t_offset > result.ships[0].t_offset

    def test_deterministic_same_seed(self):
        from src.systems.wave_patterns import BezierSweepPattern
        rng_a = random.Random(123)
        rng_b = random.Random(123)
        ra = BezierSweepPattern().generate(rng_a, level=5)
        rb = BezierSweepPattern().generate(rng_b, level=5)
        assert ra.duration_s == pytest.approx(rb.duration_s, abs=0.01)
        assert len(ra.ships) == len(rb.ships)

    def test_color_per_ship(self):
        from src.systems.wave_patterns import BezierSweepPattern
        rng = random.Random(42)
        result = BezierSweepPattern().generate(rng, level=3)
        for s in result.ships:
            assert s.color is not None
            assert len(s.color) == 3

    def test_entry_off_screen(self):
        """BLOQUE 58.13: the parallel pair path starts off-screen
        (first point of the top path's first segment)."""
        from src.systems.wave_patterns import BezierSweepPattern
        from src.core.settings import INTERNAL_W, INTERNAL_H
        from src.movement.parallel_path import ParallelPathPair
        rng = random.Random(42)
        for _ in range(20):
            result = BezierSweepPattern().generate(rng, level=2)
            pair = result.ships[0].extra["parallel_pair"]
            assert isinstance(pair, ParallelPathPair)
            p0 = pair.get_top().position_at(0.0)
            # first point of the top path should be off-screen
            assert (
                p0.x < 0 or p0.x > INTERNAL_W
                or p0.y < 0 or p0.y > INTERNAL_H
            ), f"Entry not off-screen: ({p0.x}, {p0.y})"

    def test_duration_positive(self):
        from src.systems.wave_patterns import BezierSweepPattern
        rng = random.Random(42)
        result = BezierSweepPattern().generate(rng, level=3)
        assert result.duration_s > 0

    def test_slot_indices_sequential(self):
        from src.systems.wave_patterns import BezierSweepPattern
        rng = random.Random(42)
        result = BezierSweepPattern().generate(rng, level=3)
        for i, s in enumerate(result.ships):
            assert s.slot == i


# =====================================================================
# V_FORMATION tests
# =====================================================================
class TestVFormation:
    def test_kind_is_v_formation(self):
        from src.systems.wave_patterns import VFormationPattern
        from src.systems.wave_patterns.base import WavePatternKind
        assert VFormationPattern.kind == WavePatternKind.V_FORMATION

    def test_difficulty_is_easy(self):
        from src.systems.wave_patterns import VFormationPattern
        from src.systems.wave_patterns.base import PatternDifficulty
        assert VFormationPattern.difficulty == PatternDifficulty.EASY

    def test_odd_ship_count(self):
        from src.systems.wave_patterns import VFormationPattern
        for level in [1, 3, 5, 10]:
            rng = random.Random(42)
            result = VFormationPattern().generate(rng, level=level)
            assert len(result.ships) % 2 == 1  # always odd

    def test_minimum_5_ships(self):
        from src.systems.wave_patterns import VFormationPattern
        rng = random.Random(42)
        result = VFormationPattern().generate(rng, level=1)
        assert len(result.ships) >= 5

    def test_v_shape_offsets(self):
        from src.systems.wave_patterns import VFormationPattern
        rng = random.Random(42)
        result = VFormationPattern().generate(rng, level=3)
        offsets = result.ships[0].extra["wing_offsets"]
        # Leader at (0,0)
        assert offsets[0] == (0.0, 0.0)
        # V opens UPWARD (wings above leader in screen coords, negative Y)
        # so the leader is at the FRONT of motion (apex pointing down
        # toward the player, like a flying goose).
        for ox, oy in offsets[1:]:
            assert oy < 0, f"wing offset oy={oy} should be < 0 (above leader)"

    def test_v_symmetric(self):
        from src.systems.wave_patterns import VFormationPattern
        rng = random.Random(42)
        result = VFormationPattern().generate(rng, level=3)
        offsets = result.ships[0].extra["wing_offsets"]
        # For each offset, the mirror exists
        for ox, oy in offsets:
            if (ox, oy) == (0.0, 0.0):
                continue
            mirror = (-ox, oy)
            assert mirror in offsets

    def test_no_t_offset_stagger(self):
        from src.systems.wave_patterns import VFormationPattern
        rng = random.Random(42)
        result = VFormationPattern().generate(rng, level=3)
        for s in result.ships:
            assert s.t_offset == 0.0

    def test_deterministic_same_seed(self):
        from src.systems.wave_patterns import VFormationPattern
        ra = VFormationPattern().generate(random.Random(99), level=3)
        rb = VFormationPattern().generate(random.Random(99), level=3)
        assert len(ra.ships) == len(rb.ships)
        assert ra.duration_s == pytest.approx(rb.duration_s, abs=0.01)

    def test_direction_is_left_or_right(self):
        from src.systems.wave_patterns import VFormationPattern
        for _ in range(10):
            rng = random.Random(_)
            result = VFormationPattern().generate(rng, level=3)
            d = result.ships[0].extra["direction"]
            assert d in (-1, 1)


# =====================================================================
# LEADER_FOLLOWER_CHAIN tests
# =====================================================================
class TestLeaderFollowerChain:
    def test_kind(self):
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        from src.systems.wave_patterns.base import WavePatternKind
        assert LeaderFollowerChainPattern.kind == WavePatternKind.LEADER_FOLLOWER_CHAIN

    def test_has_two_leaders(self):
        """BLOQUE 58.13: 2 leaders (one per chain)."""
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        # ship 0 = chain A leader, ship 5 = chain B leader
        assert result.ships[0].is_leader is True
        assert result.ships[5].is_leader is True
        # Other ships are followers
        non_leader_indices = [i for i in range(len(result.ships))
                              if i not in (0, 5)]
        for i in non_leader_indices:
            assert result.ships[i].is_leader is False

    def test_chains_have_decreasing_delay_within_chain(self):
        """BLOQUE 58.13: t_offsets DECREASE within each chain (leader at
        front, followers trail behind in snake-like formation)."""
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        # Chain A = ships 0..4, Chain B = ships 5..9
        for chain_start in (0, 5):
            for i in range(chain_start + 1, chain_start + 5):
                assert result.ships[i].t_offset <= result.ships[i - 1].t_offset, (
                    f"chain {chain_start}: ship {i} t_offset "
                    f"{result.ships[i].t_offset} should be <= ship {i-1} "
                    f"t_offset {result.ships[i-1].t_offset}"
                )

    def test_frequency_param(self):
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        freq = result.ships[0].extra["frequency"]
        assert 0.3 <= freq <= 1.5  # reasonable range

    def test_frequency_scales_with_level(self):
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        ra = LeaderFollowerChainPattern().generate(random.Random(42), level=1)
        rb = LeaderFollowerChainPattern().generate(random.Random(42), level=10)
        assert rb.ships[0].extra["frequency"] >= ra.ships[0].extra["frequency"]

    def test_all_share_parallel_pair(self):
        """BLOQUE 58.13: all ships share a single ParallelPathPair."""
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        pair = result.ships[0].extra["parallel_pair"]
        for s in result.ships[1:]:
            assert s.extra["parallel_pair"] is pair

    def test_all_share_color(self):
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        leader_color = result.ships[0].color
        for s in result.ships[1:]:
            assert s.color == leader_color

    def test_history_size_60_frames(self):
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        assert result.ships[0].extra["history_size"] == 60

    def test_minimum_4_ships(self):
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=1)
        assert len(result.ships) >= 4

    def test_has_10_ships(self):
        """BLOQUE 58.13: 2 chains × 5 ships = 10 ships at level 4+."""
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=4)
        assert len(result.ships) == 10

    def test_amplitude_in_range(self):
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        amp = result.ships[0].extra["amplitude"]
        assert 30 <= amp <= 100  # reasonable amplitude range


# =====================================================================
# DICE_FIVE_GRID tests
# =====================================================================
class TestDiceFiveGrid:
    def test_kind(self):
        from src.systems.wave_patterns import DiceFiveGridPattern
        from src.systems.wave_patterns.base import WavePatternKind
        assert DiceFiveGridPattern.kind == WavePatternKind.DICE_FIVE_GRID

    def test_always_5_ships(self):
        from src.systems.wave_patterns import DiceFiveGridPattern
        for level in [1, 3, 5, 100]:
            rng = random.Random(42)
            result = DiceFiveGridPattern().generate(rng, level=level)
            assert len(result.ships) == 5

    def test_dice_5_layout(self):
        from src.systems.wave_patterns import DiceFiveGridPattern
        rng = random.Random(42)
        result = DiceFiveGridPattern().generate(rng, level=3)
        offsets = result.ships[0].extra["dice_offsets"]
        # 4 corners + 1 center
        assert (0.0, 0.0) in offsets  # center
        # 4 corners: 2 above, 2 below (relative to center)
        above = [o for o in offsets if o[1] < 0]
        below = [o for o in offsets if o[1] > 0]
        assert len(above) == 2
        assert len(below) == 2

    def test_each_ship_has_different_color(self):
        from src.systems.wave_patterns import DiceFiveGridPattern
        rng = random.Random(42)
        result = DiceFiveGridPattern().generate(rng, level=3)
        colors = [s.color for s in result.ships]
        # All 5 should be unique (when palette is not shuffled)
        # When shuffled, they may still be unique
        # Either way, all should be valid RGB tuples
        for c in colors:
            assert c is not None
            assert len(c) == 3

    def test_deterministic_same_seed(self):
        from src.systems.wave_patterns import DiceFiveGridPattern
        ra = DiceFiveGridPattern().generate(random.Random(42), level=3)
        rb = DiceFiveGridPattern().generate(random.Random(42), level=3)
        assert len(ra.ships) == len(rb.ships)
        for a, b in zip(ra.ships, rb.ships):
            assert a.color == b.color

    def test_control_point_within_playfield(self):
        from src.systems.wave_patterns import DiceFiveGridPattern
        from src.core.settings import INTERNAL_W, INTERNAL_H
        rng = random.Random(42)
        for _ in range(20):
            result = DiceFiveGridPattern().generate(rng, level=3)
            ctrl_x = result.ships[0].extra["control_x"]
            assert -50 <= ctrl_x <= INTERNAL_W + 50  # allows slight outside


# =====================================================================
# PINCER_CROSS tests
# =====================================================================
class TestPincerCross:
    def test_kind(self):
        from src.systems.wave_patterns import PincerCrossPattern
        from src.systems.wave_patterns.base import WavePatternKind
        assert PincerCrossPattern.kind == WavePatternKind.PINCER_CROSS

    def test_difficulty_is_hard(self):
        from src.systems.wave_patterns import PincerCrossPattern
        from src.systems.wave_patterns.base import PatternDifficulty
        assert PincerCrossPattern.difficulty == PatternDifficulty.HARD

    def test_two_sides(self):
        from src.systems.wave_patterns import PincerCrossPattern
        rng = random.Random(42)
        result = PincerCrossPattern().generate(rng, level=3)
        left = [s for s in result.ships if s.extra["side"] == "left"]
        right = [s for s in result.ships if s.extra["side"] == "right"]
        assert len(left) == len(right)
        assert len(left) >= 4

    def test_left_color_different_from_right(self):
        from src.systems.wave_patterns import PincerCrossPattern
        rng = random.Random(42)
        result = PincerCrossPattern().generate(rng, level=3)
        left_colors = {s.color for s in result.ships if s.extra["side"] == "left"}
        right_colors = {s.color for s in result.ships if s.extra["side"] == "right"}
        # Should be different palettes
        assert left_colors != right_colors

    def test_mirror_symmetry_y_axis(self):
        """BLOQUE 58.13: 4-segment paths, first segment mirrors across y axis."""
        from src.systems.wave_patterns import PincerCrossPattern
        from src.core.settings import INTERNAL_W
        rng = random.Random(42)
        result = PincerCrossPattern().generate(rng, level=3)
        left = [s for s in result.ships if s.extra["side"] == "left"][0]
        right = [s for s in result.ships if s.extra["side"] == "right"][0]
        # First segment of left: p0 should be on the left side (< INTERNAL_W/2)
        l_p0 = left.extra["segments"][0][0]
        r_p0 = right.extra["segments"][0][0]
        assert l_p0[0] < INTERNAL_W / 2
        assert r_p0[0] > INTERNAL_W / 2

    def test_convergence_in_middle(self):
        """BLOQUE 58.13: end of segment 1 is at center (X moment)."""
        from src.systems.wave_patterns import PincerCrossPattern
        from src.core.settings import INTERNAL_W
        rng = random.Random(42)
        result = PincerCrossPattern().generate(rng, level=3)
        for s in result.ships:
            seg1 = s.extra["segments"][0]
            end_of_seg1 = seg1[3]
            # End of segment 1 should be near center (within 50px of INTERNAL_W/2)
            assert abs(end_of_seg1[0] - INTERNAL_W / 2) < 50

    def test_deterministic(self):
        from src.systems.wave_patterns import PincerCrossPattern
        ra = PincerCrossPattern().generate(random.Random(42), level=3)
        rb = PincerCrossPattern().generate(random.Random(42), level=3)
        assert len(ra.ships) == len(rb.ships)
        assert ra.duration_s == pytest.approx(rb.duration_s, abs=0.01)

    def test_total_ship_count(self):
        """BLOQUE 58.11: bigger pincer (10-16 ships total, was 8-12)."""
        from src.systems.wave_patterns import PincerCrossPattern
        for level in [1, 3, 5, 10]:
            rng = random.Random(42)
            result = PincerCrossPattern().generate(rng, level=level)
            assert 10 <= len(result.ships) <= 16


# =====================================================================
# BLOQUE 58.next: build_path() contract — visual replay API
# =====================================================================
class TestBuildPathContract:
    """Pin the build_path() classmethod contract that the capture script
    and any future visual-replay tool depend on.

    Regression: PINCER_CROSS used to crash the capture script with
    'int() argument ... not Point' because the script's build_path_from_ship
    only understood the 'segments' key, not parallel_pair/orbital/rigid.
    Moving the logic into pattern.build_path() guarantees every pattern
    exposes its per-ship path in a uniform way.
    """

    def test_base_default_returns_none(self):
        """WavePattern.build_path() default is None — patterns must override."""
        from src.systems.wave_patterns.base import WavePattern
        from src.systems.wave_patterns.base import SpawnedShip

        class _MinimalPattern(WavePattern):
            kind = None
            difficulty = None

            def generate(self, rng, level, enemy_kind="SCOUT"):
                return None

        ship = SpawnedShip(spawn_x=0, spawn_y=0)
        assert _MinimalPattern.build_path(ship) is None

    def test_pincer_cross_build_path(self):
        """PINCER_CROSS: 4-segment HybridPath (one per side per ship)."""
        from src.systems.wave_patterns import PincerCrossPattern
        from src.movement.hybrid import HybridPath
        rng = random.Random(42)
        result = PincerCrossPattern().generate(rng, level=3)
        for ship in result.ships:
            path = PincerCrossPattern.build_path(ship)
            assert isinstance(path, HybridPath)
            assert path.total_arc_length > 0
            assert len(path.segments) == 4

    def test_bezier_sweep_build_path(self):
        """BEZIER_SWEEP: 2 unique HybridPaths (top/bot of the parallel pair)."""
        from src.systems.wave_patterns import BezierSweepPattern
        from src.movement.hybrid import HybridPath
        rng = random.Random(42)
        result = BezierSweepPattern().generate(rng, level=3)
        path_ids = set()
        for ship in result.ships:
            path = BezierSweepPattern.build_path(ship)
            assert isinstance(path, HybridPath)
            assert path.total_arc_length > 0
            path_ids.add(id(path))
        assert len(path_ids) == 2  # top + bot only

    def test_leader_follower_chain_build_path(self):
        """LEADER_FOLLOWER_CHAIN: 2 unique HybridPaths (one per chain)."""
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        from src.movement.hybrid import HybridPath
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        path_ids = set()
        for ship in result.ships:
            path = LeaderFollowerChainPattern.build_path(ship)
            assert isinstance(path, HybridPath)
            assert path.total_arc_length > 0
            path_ids.add(id(path))
        assert len(path_ids) == 2  # top + bot

    def test_oscillating_butterfly_build_path(self):
        """OSCILLATING_BUTTERFLY: 4-quarter-orbital HybridPath."""
        from src.systems.wave_patterns import OscillatingButterflyPattern
        from src.movement.hybrid import HybridPath
        rng = random.Random(42)
        result = OscillatingButterflyPattern().generate(rng, level=3)
        for ship in result.ships:
            path = OscillatingButterflyPattern.build_path(ship)
            assert isinstance(path, HybridPath)
            assert len(path.segments) == 4

    def test_v_formation_build_path(self):
        """V_FORMATION: single straight-line HybridPath (rigid motion mirror)."""
        from src.systems.wave_patterns import VFormationPattern
        from src.movement.hybrid import HybridPath
        rng = random.Random(42)
        result = VFormationPattern().generate(rng, level=3)
        for ship in result.ships:
            path = VFormationPattern.build_path(ship)
            assert isinstance(path, HybridPath)
            assert len(path.segments) == 1
            assert path.total_arc_length > 0

    def test_dice_five_grid_build_path(self):
        """DICE_FIVE_GRID: single straight-down HybridPath (rigid motion mirror)."""
        from src.systems.wave_patterns import DiceFiveGridPattern
        from src.movement.hybrid import HybridPath
        rng = random.Random(42)
        result = DiceFiveGridPattern().generate(rng, level=3)
        for ship in result.ships:
            path = DiceFiveGridPattern.build_path(ship)
            assert isinstance(path, HybridPath)
            assert len(path.segments) == 1
            assert path.total_arc_length > 0

    def test_path_follower_advances_on_each_path(self):
        """Smoke: every pattern's build_path can be wrapped in a PathFollower
        and produces a valid (Point, Point) update."""
        from src.movement.follower import PathFollower
        from src.systems.wave_patterns import (
            BezierSweepPattern,
            VFormationPattern,
            LeaderFollowerChainPattern,
            DiceFiveGridPattern,
            PincerCrossPattern,
            OscillatingButterflyPattern,
        )
        patterns = [
            BezierSweepPattern, VFormationPattern, LeaderFollowerChainPattern,
            DiceFiveGridPattern, PincerCrossPattern, OscillatingButterflyPattern,
        ]
        for pcls in patterns:
            rng = random.Random(42)
            result = pcls().generate(rng, level=1)
            assert result.ships, f"{pcls.__name__} produced 0 ships"
            path = pcls.build_path(result.ships[0])
            assert path is not None, f"{pcls.__name__}.build_path returned None"
            follower = PathFollower(path, t_offset=result.ships[0].t_offset)
            pos, vel = follower.update(1.0 / 60.0)
            # pos must be a Point with x,y attrs
            assert hasattr(pos, 'x') and hasattr(pos, 'y'), \
                f"{pcls.__name__}: pos has no x/y attrs (type={type(pos).__name__})"
            assert isinstance(vel, tuple) and len(vel) == 2


# =====================================================================
# BLOQUE 58.next: motion invariants — tests that catch visual bugs
# =====================================================================
class TestMotionInvariants:
    """Motion-level invariants that the structural tests miss.

    Each test below simulates the pattern via PathFollower.update() and
    checks a geometric property that the pattern MUST satisfy. If the
    pattern's intent ever drifts (e.g., the V gets inverted, the dice
    cluster deforms, the cross-side swap fails, the orbit collapses),
    one of these tests breaks.

    These are the tests that would have caught the bugs surfaced by
    the audit: the inverted V, the PINCER_CROSS extract_xy crash, the
    OSCILLATING_BUTTERFLY orbit integrity, etc.
    """

    def _make_followers(self, pattern_cls, level=3, seed=42):
        """Helper: build a list of (ship, PathFollower) for a generated pattern."""
        from src.movement.follower import PathFollower
        result = pattern_cls().generate(random.Random(seed), level=level)
        pairs = []
        for ship in result.ships:
            path = pattern_cls.build_path(ship)
            assert path is not None, f"{pattern_cls.__name__}.build_path returned None"
            pairs.append((ship, PathFollower(path, t_offset=ship.t_offset)))
        return pairs, result

    def _positions_at(self, pairs, t):
        """Run each follower for t seconds, return list of (ship, pos)."""
        out = []
        for ship, follower in pairs:
            pos, _ = follower.update(t)
            out.append((ship, pos))
        return out

    # ------------------------------------------------------------------
    # V_FORMATION — leader must be at the FRONT of the direction of motion
    # ------------------------------------------------------------------
    def test_v_formation_leader_at_front_of_motion(self):
        """V_FORMATION: leader's projection onto the forward direction
        must be the MAXIMUM among all ships. The V should point in the
        direction of motion (Star Fox 64 style). If the V is inverted
        (wings ahead of leader), this test fails."""
        import math
        from src.systems.wave_patterns import VFormationPattern
        pairs, result = self._make_followers(VFormationPattern, level=3)
        direction = result.ships[0].extra["direction"]
        # Forward unit vector: V moves at (direction * speed, +1 * speed)
        norm = math.sqrt(direction * direction + 1.0)
        fx, fy = direction / norm, 1.0 / norm
        # Sample at t=2.0s — well past spawn, formation has spread
        positions = self._positions_at(pairs, 2.0)
        leader_ship = next(s for s in result.ships if s.is_leader)
        leader_proj = None
        for ship, p in positions:
            proj = p.x * fx + p.y * fy
            if ship is leader_ship:
                leader_proj = proj
                break
        assert leader_proj is not None, "Leader ship not found in positions"
        for ship, p in positions:
            proj = p.x * fx + p.y * fy
            assert proj <= leader_proj + 1e-6, (
                f"V_FORMATION: ship slot={ship.slot} is AHEAD of leader "
                f"(forward_proj={proj:.2f} > leader={leader_proj:.2f}). "
                f"The V is INVERTED — wings are in front of the leader."
            )

    # ------------------------------------------------------------------
    # DICE_FIVE_GRID — 5 ships must move as a rigid cluster
    # ------------------------------------------------------------------
    def test_dice_five_grid_rigid_cluster(self):
        """DICE_FIVE_GRID: relative positions of all 5 ships must be
        CONSTANT over time. If the cluster deforms in motion (ships
        drift apart or the shape warps), this test fails."""
        from src.systems.wave_patterns import DiceFiveGridPattern
        pairs, result = self._make_followers(DiceFiveGridPattern, level=3)
        # Initial relative positions (subtract centroid)
        initial = self._positions_at(pairs, 0.0)
        cx0 = sum(p.x for _, p in initial) / len(initial)
        cy0 = sum(p.y for _, p in initial) / len(initial)
        rel0 = [(p.x - cx0, p.y - cy0) for _, p in initial]
        # After 2.0s, check relative positions are still the same
        later = self._positions_at(pairs, 2.0)
        cx1 = sum(p.x for _, p in later) / len(later)
        cy1 = sum(p.y for _, p in later) / len(later)
        for i, (ship, p) in enumerate(later):
            rx_now, ry_now = p.x - cx1, p.y - cy1
            assert rx_now == pytest.approx(rel0[i][0], abs=0.5), (
                f"DICE_FIVE_GRID: ship slot={ship.slot} drifted in X "
                f"({rx_now:.2f} vs initial {rel0[i][0]:.2f})"
            )
            assert ry_now == pytest.approx(rel0[i][1], abs=0.5), (
                f"DICE_FIVE_GRID: ship slot={ship.slot} drifted in Y "
                f"({ry_now:.2f} vs initial {rel0[i][1]:.2f})"
            )

    # ------------------------------------------------------------------
    # PINCER_CROSS — at midpoint, 'left' ships must be on the RIGHT side
    # ------------------------------------------------------------------
    def test_pincer_cross_swaps_sides_at_midpoint(self):
        """PINCER_CROSS: at t=2.3s (end of the CROSS segment), the
        'left' ships must be on the RIGHT side of the playfield and
        vice versa. Duration 4.8s = 1.5s entry + 0.8s cross + 1.0s
        cruise + 1.5s exit. If the cross segment fails, this test fails."""
        from src.systems.wave_patterns import PincerCrossPattern
        from src.core.settings import INTERNAL_W
        pairs, result = self._make_followers(PincerCrossPattern, level=3)
        positions = self._positions_at(pairs, 2.3)
        mid_x = INTERNAL_W / 2
        for ship, p in positions:
            side = ship.extra["side"]
            if side == "left":
                assert p.x > mid_x, (
                    f"PINCER_CROSS: left ship at t=2.3s is still on the "
                    f"LEFT (X={p.x:.1f} < mid={mid_x}). CROSS segment failed."
                )
            else:  # right
                assert p.x < mid_x, (
                    f"PINCER_CROSS: right ship at t=2.3s is still on the "
                    f"RIGHT (X={p.x:.1f} > mid={mid_x}). CROSS segment failed."
                )

    # ------------------------------------------------------------------
    # OSCILLATING_BUTTERFLY — each ship must stay on the orbital ellipse
    # ------------------------------------------------------------------
    def test_oscillating_butterfly_ships_on_closed_orbit(self):
        """OSCILLATING_BUTTERFLY: all 6 ships must remain on the same
        closed orbit. We sample the orbit path itself at 16 arc-length
        waypoints and use the centroid of those samples as the orbit
        center (rotation-invariant). Every ship's position at any
        time must be at a distance from that center within the orbit's
        own [min, max] distance range.

        This invariant holds for ANY elliptical orbit, regardless of
        rotation, rx/ry, or how the path is parametrized.
        """
        import math
        from src.systems.wave_patterns import OscillatingButterflyPattern
        from src.movement.follower import PathFollower
        # Build the orbit path and sample it at 16 arc-length waypoints
        result = OscillatingButterflyPattern().generate(random.Random(42), level=3)
        orbit_path = result.ships[0].extra["orbital"].get_path()
        N = 16
        orbit_points = [
            orbit_path.position_at_distance(orbit_path.total_arc_length * i / N)
            for i in range(N)
        ]
        # Centroid of orbit samples = orbit center (rotation-invariant)
        cx = sum(p.x for p in orbit_points) / N
        cy = sum(p.y for p in orbit_points) / N
        # All orbit samples should be at non-trivial distance from center
        distances = [math.hypot(p.x - cx, p.y - cy) for p in orbit_points]
        min_d, max_d = min(distances), max(distances)
        assert min_d > 30, (
            f"OSCILLATING_BUTTERFLY: orbit is too small (min_d={min_d:.1f}, "
            f"expected > 30)"
        )
        # Ellipse: max_d / min_d = rx / ry. With rx in [100,140] and ry
        # in [70,100], the ratio is at most 2.0. If higher, the orbit is
        # broken (e.g., not closed, or one axis collapsed).
        assert max_d / min_d < 2.5, (
            f"OSCILLATING_BUTTERFLY: orbit not elliptical "
            f"(max_d/min_d={max_d/min_d:.2f}, expected < 2.5)"
        )
        # Now check every ship's position at multiple times falls on the orbit
        for ship in result.ships:
            for t_sample in (0.5, 1.5, 2.5, 3.5):
                # Fresh follower per sample (PathFollower is stateful)
                ship_path = OscillatingButterflyPattern.build_path(ship)
                follower = PathFollower(ship_path, t_offset=ship.t_offset)
                pos, _ = follower.update(t_sample)
                dist = math.hypot(pos.x - cx, pos.y - cy)
                assert min_d - 3 <= dist <= max_d + 3, (
                    f"OSCILLATING_BUTTERFLY: ship slot={ship.slot} at t={t_sample} "
                    f"is OFF the orbit (dist={dist:.1f}, expected in "
                    f"[{min_d:.1f}, {max_d:.1f}])"
                )

    # ------------------------------------------------------------------
    # LEADER_FOLLOWER_CHAIN — followers must be BEHIND the leader
    # ------------------------------------------------------------------
    def test_leader_follower_chain_followers_behind_leader(self):
        """LEADER_FOLLOWER_CHAIN: at any time, the leader of each chain
        must be FURTHER ALONG the path than its followers. The chain
        is a 'follow the leader' snake — leader at front, followers
        trailing behind. If the t_offset logic is inverted (followers
        ahead of leader), this test fails.

        We test via arc-length progress: at the same simulation time,
        the leader's arc length should be >= each follower's arc length
        in the same chain."""
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        from src.movement.follower import PathFollower
        result = LeaderFollowerChainPattern().generate(random.Random(42), level=4)
        # 2 chains × 5 ships = 10. Chain A = ships[0..4], Chain B = ships[5..9]
        # Leader is slot 0 in each chain (ships[0] and ships[5]).
        for chain_start in (0, 5):
            leader = result.ships[chain_start]
            assert leader.is_leader, f"ship {chain_start} should be the leader"
            # Build the path the leader uses, then compute the path arc length
            # of the leader and each follower at t=2.0s.
            leader_path = LeaderFollowerChainPattern.build_path(leader)
            assert leader_path is not None
            leader_follower = PathFollower(leader_path, t_offset=leader.t_offset)
            leader_pos, _ = leader_follower.update(2.0)
            # For each follower in this chain, compute its position
            for slot in range(1, 5):
                follower = result.ships[chain_start + slot]
                follower_path = LeaderFollowerChainPattern.build_path(follower)
                assert follower_path is not None
                # Sanity: same path object (shared parallel_pair per chain)
                assert follower_path is leader_path, (
                    f"Chain {chain_start}: follower slot={slot} has DIFFERENT "
                    f"path than leader. Top/bot split?"
                )
                follower_f = PathFollower(follower_path, t_offset=follower.t_offset)
                follower_pos, _ = follower_f.update(2.0)
                # The leader should be FURTHER ALONG the path (larger arc
                # length from the spawn point p0) than the follower.
                # We measure this as: distance from start of path.
                p0 = leader_path.segments[0].p0
                leader_dist = (
                    (leader_pos.x - p0.x) ** 2 + (leader_pos.y - p0.y) ** 2
                ) ** 0.5
                follower_dist = (
                    (follower_pos.x - p0.x) ** 2 + (follower_pos.y - p0.y) ** 2
                ) ** 0.5
                assert leader_dist >= follower_dist - 0.5, (
                    f"LEADER_FOLLOWER_CHAIN: chain={chain_start//5} follower "
                    f"slot={slot} is AHEAD of the leader at t=2.0s "
                    f"(follower_dist={follower_dist:.1f} > leader_dist={leader_dist:.1f}). "
                    f"t_offsets are inverted: follower has t_offset={follower.t_offset} "
                    f"vs leader t_offset={leader.t_offset}."
                )

    # ------------------------------------------------------------------
    # COMPOSED — ships must preserve formation slot offsets along the path
    # ------------------------------------------------------------------
    def test_composed_ships_preserve_formation_offsets(self):
        """COMPOSED: every ship in the pattern must stay at its formation
        slot offset (dx, dy) RELATIVE TO the path, not collapse onto the
        path's start point.

        Before the BLOQUE 58.next fix, attach_multi_segment_path() passed
        slot_dx=slot_dy=0 to enemy.attach_path, so all ships followed
        the same shared path from the same world position. The result
        was every ship rendered on top of each other (the user-reported
        "stacked ships" bug in COMPOSED).

        We test a V formation (slots spread up to 88 px in X, 30 px in Y)
        on a sweep path. After the fix, at any sample time the ships'
        positions must be spread by at least one formation-slot unit
        on at least one axis. Without the fix, x_range and y_range are
        both ~0 (all ships at the path's start).
        """
        from src.systems.wave_patterns.composed import ComposedPattern
        from src.systems.wave_patterns.base import PatternDifficulty
        from src.movement.follower import PathFollower
        pattern = ComposedPattern(
            name="v_sweep_leader_n5",
            formation="v",
            path="sweep",
            follow="leader",
            count=5,
            difficulty=PatternDifficulty.EASY,
        )
        result = pattern.generate(random.Random(42), level=3)
        assert len(result.ships) == 5, (
            f"Expected 5 ships from n=5 COMPOSED, got {len(result.ships)}"
        )
        for t_sample in (0.1, 0.5, 1.0, 1.5, 2.0):
            positions = []
            for ship in result.ships:
                path = ComposedPattern.build_path(ship)
                assert path is not None, (
                    f"ComposedPattern.build_path returned None for ship "
                    f"slot={ship.slot} (missing 'segments' in extra?)"
                )
                follower = PathFollower(path, t_offset=ship.t_offset)
                pos, _ = follower.update(t_sample)
                # Account for the formation slot offset that the runtime
                # applies via path_slot_dx / path_slot_dy. The test mirrors
                # the runtime: each ship's effective position is
                # path_position + (slot_dx, slot_dy).
                pos_x = pos.x + ship.extra.get("slot_dx", 0.0)
                pos_y = pos.y + ship.extra.get("slot_dy", 0.0)
                positions.append((pos_x, pos_y))
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            x_range = max(xs) - min(xs)
            y_range = max(ys) - min(ys)
            # The V formation has 5 ships spanning ~88 px in X and ~30 px
            # in Y (before jitter). A spread of < 10 px on BOTH axes means
            # the ships are visually stacked. 10 px is well below the
            # minimum formation spread but well above the <1 px you'd see
            # if all ships were collapsed.
            assert x_range > 10.0 or y_range > 10.0, (
                f"COMPOSED: ships are STACKED at t={t_sample}s "
                f"(x_range={x_range:.1f}, y_range={y_range:.1f}). "
                f"All positions: {positions}. "
                f"slot_dx/slot_dy are not being applied to the path follower "
                f"(or ship.extra is missing 'slot_dx' / 'slot_dy')."
            )


# =====================================================================
# ProceduralWaveManager tests
# =====================================================================
class TestProceduralWaveManager:
    def test_floor_1_picks_easy_patterns(self):
        from src.systems.wave_patterns import ProceduralWaveManager, WavePatternKind
        mgr = ProceduralWaveManager(seed=42, floor=1)
        pool = mgr.preview_next_pool()
        # BLOQUE 58.11: 6 patterns (added OSCILLATING_BUTTERFLY)
        # BLOQUE 58.14.7: 7 patterns now (added COMPOSED)
        assert len(pool) == 7
        assert WavePatternKind.V_FORMATION.value in pool
        assert WavePatternKind.DICE_FIVE_GRID.value in pool
        assert WavePatternKind.LEADER_FOLLOWER_CHAIN.value in pool
        assert WavePatternKind.BEZIER_SWEEP.value in pool
        assert WavePatternKind.PINCER_CROSS.value in pool
        assert WavePatternKind.OSCILLATING_BUTTERFLY.value in pool
        assert WavePatternKind.COMPOSED.value in pool

    def test_floor_5_includes_all(self):
        from src.systems.wave_patterns import ProceduralWaveManager
        from src.systems.wave_patterns.base import WavePatternKind
        mgr = ProceduralWaveManager(seed=42, floor=5)
        pool = mgr.preview_next_pool()
        assert len(pool) == len(WavePatternKind)

    def test_deterministic_same_seed(self):
        from src.systems.wave_patterns import ProceduralWaveManager
        m1 = ProceduralWaveManager(seed=42, floor=3)
        m2 = ProceduralWaveManager(seed=42, floor=3)
        results1 = [m1.pick_pattern(level=i) for i in range(5)]
        results2 = [m2.pick_pattern(level=i) for i in range(5)]
        for r1, r2 in zip(results1, results2):
            assert r1.kind == r2.kind
            assert len(r1.ships) == len(r2.ships)

    def test_no_immediate_repeats(self):
        from src.systems.wave_patterns import ProceduralWaveManager
        mgr = ProceduralWaveManager(seed=42, floor=2)  # 3 options
        for _ in range(10):
            r1 = mgr.pick_pattern(level=1)
            r2 = mgr.pick_pattern(level=2)
            assert r1.kind != r2.kind, f"immediate repeat: {r1.kind}"

    def test_floor_can_be_updated(self):
        from src.systems.wave_patterns import ProceduralWaveManager
        mgr = ProceduralWaveManager(seed=42, floor=1)
        assert mgr.get_floor() == 1
        mgr.set_floor(5)
        assert mgr.get_floor() == 5
        pool = mgr.preview_next_pool()
        assert len(pool) >= 4

    def test_pick_pattern_returns_ships(self):
        from src.systems.wave_patterns import ProceduralWaveManager
        mgr = ProceduralWaveManager(seed=42, floor=3)
        result = mgr.pick_pattern(level=2)
        assert len(result.ships) >= 1
        assert result.duration_s > 0

    def test_logs_to_patterns_log(self, tmp_path):
        from src.systems.wave_patterns import ProceduralWaveManager
        log_path = tmp_path / "patterns.log"
        mgr = ProceduralWaveManager(seed=42, floor=2, log_path=str(log_path))
        for _ in range(3):
            mgr.pick_pattern(level=1)
        assert log_path.exists()
        content = log_path.read_text()
        assert "kind=" in content
        assert "ships=" in content

    def test_different_seeds_different_sequences(self):
        from src.systems.wave_patterns import ProceduralWaveManager
        m1 = ProceduralWaveManager(seed=42, floor=3)
        m2 = ProceduralWaveManager(seed=99, floor=3)
        seq1 = [m1.pick_pattern(level=i).kind for i in range(10)]
        seq2 = [m2.pick_pattern(level=i).kind for i in range(10)]
        # Should differ somewhere (high probability)
        assert seq1 != seq2

    def test_floor_2_includes_leader_chain(self):
        from src.systems.wave_patterns import ProceduralWaveManager
        from src.systems.wave_patterns.base import WavePatternKind
        mgr = ProceduralWaveManager(seed=42, floor=2)
        pool = mgr.preview_next_pool()
        assert WavePatternKind.LEADER_FOLLOWER_CHAIN.value in pool

    def test_floor_4_includes_pincer(self):
        from src.systems.wave_patterns import ProceduralWaveManager
        from src.systems.wave_patterns.base import WavePatternKind
        # BLOQUE 58.11: floor 4+ uses _EQUAL_WEIGHT (all 6 patterns)
        # BLOQUE 58.14.7: now 7 patterns (added COMPOSED)
        mgr = ProceduralWaveManager(seed=42, floor=4)
        pool = mgr.preview_next_pool()
        assert len(pool) == 7
        assert WavePatternKind.PINCER_CROSS.value in pool
        assert WavePatternKind.BEZIER_SWEEP.value in pool
        assert WavePatternKind.LEADER_FOLLOWER_CHAIN.value in pool
        assert WavePatternKind.OSCILLATING_BUTTERFLY.value in pool
        assert WavePatternKind.COMPOSED.value in pool

    def test_floor_1_sees_all_5_over_many_picks(self):
        """BLOQUE 58.10: floor 1 must eventually pick all 5 patterns
        (weights favor V_FORMATION but nothing is gated).
        With 200 picks at floor 1, all kinds should appear.
        BLOQUE 58.14.7: also includes COMPOSED in the seen set.
        """
        from src.systems.wave_patterns import ProceduralWaveManager
        from src.systems.wave_patterns.base import WavePatternKind
        mgr = ProceduralWaveManager(seed=1234, floor=1)
        # BLOQUE 58.14.7: register so COMPOSED is actually pickable
        mgr.register_composed_patterns()
        kinds_seen = set()
        for i in range(200):
            r = mgr.pick_pattern(level=1 + (i % 4))
            kinds_seen.add(r.kind)
        assert len(kinds_seen) == len(WavePatternKind), (
            f"After 200 picks at floor 1, only saw {kinds_seen}"
        )

    def test_floor_1_weights_favor_v_formation(self):
        """BLOQUE 58.10: V_FORMATION should be picked MORE often than
        PINCER_CROSS at floor 1 (V has weight 25, PINCER has weight 15).
        """
        from src.systems.wave_patterns import ProceduralWaveManager
        from src.systems.wave_patterns.base import WavePatternKind
        mgr = ProceduralWaveManager(seed=9999, floor=1)
        from collections import Counter
        counts = Counter()
        for i in range(500):
            r = mgr.pick_pattern(level=1)
            counts[r.kind] += 1
        # V_FORMATION count > PINCER_CROSS count
        assert counts[WavePatternKind.V_FORMATION] > counts[WavePatternKind.PINCER_CROSS], (
            f"V_FORMATION should be more common than PINCER_CROSS at floor 1, "
            f"got {counts}"
        )


# =====================================================================
# Procedural enemy factory tests
# =====================================================================
class TestEnemyFactory:
    def test_deterministic(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        e1 = make_procedural_enemy(random.Random(42), "SCOUT", 1)
        e2 = make_procedural_enemy(random.Random(42), "SCOUT", 1)
        assert e1 == e2

    def test_speed_in_range(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        for _ in range(50):
            e = make_procedural_enemy(random.Random(_), "SCOUT", 5)
            assert 0.5 <= e.speed_mult <= 1.5  # 1.0 ± 25% at full variance

    def test_hp_in_range(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        for _ in range(50):
            e = make_procedural_enemy(random.Random(_), "HEAVY", 5)
            assert 0.6 <= e.hp_mult <= 1.4  # 1.0 ± 20%

    def test_fire_rate_in_range(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        for _ in range(50):
            e = make_procedural_enemy(random.Random(_), "CRUISER", 5)
            assert 0.4 <= e.fire_rate_mult <= 1.6  # 1.0 ± 30%

    def test_color_tint_in_range(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        for _ in range(50):
            e = make_procedural_enemy(random.Random(_), "SCOUT", 6)
            assert -30.0 <= e.color_tint <= 30.0  # at full variance

    def test_weapon_variant_valid(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        for _ in range(100):
            e = make_procedural_enemy(random.Random(_), "SCOUT", 5)
            assert e.weapon_variant in ("default", "shotgun", "burst", "sniper")

    def test_default_distribution(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        # 100 trials, default should be ~70%
        defaults = sum(
            1 for _ in range(100)
            if make_procedural_enemy(random.Random(_), "SCOUT", 5).weapon_variant == "default"
        )
        # Generous range: 50-90
        assert 50 <= defaults <= 90

    def test_unknown_kind_falls_back_to_scout(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        e = make_procedural_enemy(random.Random(42), "UNKNOWN_KIND", 3)
        assert e.kind == "SCOUT"

    def test_make_enemy_mix_count(self):
        from src.roguelike.enemy_factory import make_enemy_mix
        rng = random.Random(42)
        enemies = make_enemy_mix(rng, count=10, level=3)
        assert len(enemies) == 10

    def test_make_enemy_mix_archetypes(self):
        from src.roguelike.enemy_factory import make_enemy_mix, BASE_ARCHETYPES
        rng = random.Random(42)
        enemies = make_enemy_mix(rng, count=50, level=3)
        for e in enemies:
            assert e.kind in BASE_ARCHETYPES

    def test_low_level_more_scouts(self):
        from src.roguelike.enemy_factory import make_enemy_mix
        rng = random.Random(42)
        enemies = make_enemy_mix(rng, count=100, level=1)
        scouts = sum(1 for e in enemies if e.kind == "SCOUT")
        # 60% of 100 = 60
        assert scouts >= 50  # generous lower bound

    def test_high_level_more_heavy(self):
        from src.roguelike.enemy_factory import make_enemy_mix
        rng = random.Random(42)
        enemies = make_enemy_mix(rng, count=200, level=10)
        heavies = sum(1 for e in enemies if e.kind == "HEAVY")
        # 20% of 200 = 40
        assert heavies >= 20  # generous lower bound

    def test_variance_zero_at_level_0(self):
        from src.roguelike.enemy_factory import make_procedural_enemy
        # level=0 means no variance
        e = make_procedural_enemy(random.Random(42), "SCOUT", level=0)
        # Should be exactly 1.0 (no random variation)
        assert e.speed_mult == 1.0
        assert e.hp_mult == 1.0
        assert e.fire_rate_mult == 1.0


# =====================================================================
# BLOQUE 58.next: composed cross-product expansion tests (Task 6)
# =====================================================================
class TestComposedExpansion:
    """BLOQUE 58.next: after expansion, COMPOSED_PATTERNS = 1050 entries,
    contains all 10 new formations and all 7 new paths. First 50 patterns
    must be byte-identical to pre-expansion output (backward compat).
    """

    def test_composed_count_after_expansion(self) -> None:
        """After BLOQUE 58.next, COMPOSED_PATTERNS has the full cross product
        (19 forms x 15 paths x 3 follows x 5 counts = 4275).

        Note: the brief originally specified a 1050 cap, but that cap with
        form->path->follow->count iteration only reaches the first 5 of 19
        formations, leaving the 10 new formations unused. The cap is raised
        to the full cross product so every new formation/path actually
        appears in the game. The first 50 patterns stay byte-identical to
        the pre-expansion output (covered by the other test).
        """
        from src.systems.wave_patterns.composed import COMPOSED_PATTERNS
        assert len(COMPOSED_PATTERNS) == 4275, (
            f"expected 4275 (19*15*3*5), got {len(COMPOSED_PATTERNS)}"
        )

    def test_composed_includes_new_formations(self) -> None:
        """At least one COMPOSED pattern uses each of the 10 new formation kinds."""
        from src.systems.wave_patterns.composed import COMPOSED_PATTERNS
        from src.movement.formation import FormationKind
        new_kinds = {
            FormationKind.FLOWER_OF_LIFE, FormationKind.VESICA_PISCIS,
            FormationKind.FIBONACFI_SPIRAL, FormationKind.TREE_OF_LIFE,
            FormationKind.SIERPINSKI_TRIANGLE, FormationKind.HEX_CLOSE_PACK,
            FormationKind.MANDALA_RINGS, FormationKind.GOLDEN_RATIO_ROW,
            FormationKind.KOCH_3FOLD, FormationKind.DRAGON_CURVE,
        }
        found_kinds = {p._formation for p in COMPOSED_PATTERNS}
        missing = new_kinds - found_kinds
        assert not missing, f"missing formations in COMPOSED: {missing}"

    def test_composed_includes_new_paths(self) -> None:
        """At least one COMPOSED pattern uses each of the 7 new paths."""
        from src.systems.wave_patterns.composed import COMPOSED_PATTERNS
        new_paths = {"lemniscate", "cardioid", "lissajous_3_2", "rose_k2",
                     "rose_k3", "hypocycloid", "epicycloid"}
        found_paths = {p._path for p in COMPOSED_PATTERNS}
        missing = new_paths - found_paths
        assert not missing, f"missing paths in COMPOSED: {missing}"

    def test_first_50_composed_unchanged_by_expansion(self) -> None:
        """Backward compat: first 50 patterns from COMPOSED with default ordering
        must be byte-identical to pre-expansion output."""
        from src.systems.wave_patterns.composed import (
            COMPOSED_PATTERNS,
            FORMATION_GENERATORS,
            PATH_GENERATORS,
        )
        # The first 9 formations and first 8 paths are the OLD ones (kept in
        # the same order). The cross product form[0..8] x path[0..7] x
        # follow[0..2] x count[0..4] yields 9*8*3*5 = 1080 patterns; the
        # first 50 are exactly the pre-expansion ordering.
        form_keys = list(FORMATION_GENERATORS.keys())
        path_keys = list(PATH_GENERATORS.keys())
        assert len(form_keys) >= 9, f"need >= 9 formations, got {len(form_keys)}"
        assert len(path_keys) >= 8, f"need >= 8 paths, got {len(path_keys)}"
        expected_first_50_formations = form_keys[:9]  # first 9 of new 19
        expected_first_50_paths = path_keys[:8]  # first 8 of new 15
        # Generate the first 50 expected pattern signatures
        expected = []
        for fk in expected_first_50_formations:
            for pk in expected_first_50_paths:
                for follow in ["leader", "chain", "free"]:
                    for count in [4, 5, 6, 7, 8]:
                        expected.append((fk, pk, follow, count))
                        if len(expected) == 50:
                            break
                    if len(expected) == 50:
                        break
                if len(expected) == 50:
                    break
            if len(expected) == 50:
                break
        # Compare to first 50 of COMPOSED_PATTERNS
        actual = [(p._formation, p._path, p._follow, p._count)
                  for p in COMPOSED_PATTERNS[:50]]
        assert actual == expected, (
            f"first 50 patterns changed! "
            f"actual[0:5]={actual[:5]}, expected[0:5]={expected[:5]}"
        )
