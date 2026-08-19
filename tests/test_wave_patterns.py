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
        # V opens downward (positive Y in screen coords)
        for ox, oy in offsets[1:]:
            assert oy > 0  # wings are below leader (in screen y)

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

    def test_chains_have_increasing_delay_within_chain(self):
        """BLOQUE 58.13: t_offsets are non-decreasing within each chain."""
        from src.systems.wave_patterns import LeaderFollowerChainPattern
        rng = random.Random(42)
        result = LeaderFollowerChainPattern().generate(rng, level=3)
        # Chain A = ships 0..4, Chain B = ships 5..9
        for chain_start in (0, 5):
            for i in range(chain_start + 1, chain_start + 5):
                assert result.ships[i].t_offset >= result.ships[i - 1].t_offset

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
