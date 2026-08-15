"""BLOQUE 58.10 integration tests.

Floor-1 fix: all 5 patterns must be selectable from floor 1 (BEFORE: only
V_FORMATION and DICE_FIVE_GRID). Plus the visual leader highlight must
be tracked on the pattern runtime.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import random
import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.systems.wave_patterns import (
    BezierSweepPattern,
    DiceFiveGridPattern,
    LeaderFollowerChainPattern,
    PincerCrossPattern,
    ProceduralWaveManager,
    VFormationPattern,
)
from src.systems.wave_patterns.base import WavePatternKind


# =====================================================================
# Floor 1 fix: all 5 patterns available
# =====================================================================
class TestFloor1AllPatterns:
    def test_floor_1_pool_has_all_5(self):
        mgr = ProceduralWaveManager(seed=42, floor=1)
        pool = mgr.preview_next_pool()
        # BLOQUE 58.11: 6 patterns now (added OSCILLATING_BUTTERFLY)
        assert len(pool) == 6, f"floor 1 should have all 6 patterns, got {pool}"

    def test_floor_1_eventually_picks_each_kind(self):
        """BLOQUE 58.10: across many picks, all 5 kinds appear at floor 1."""
        mgr = ProceduralWaveManager(seed=1234, floor=1)
        seen = set()
        for i in range(200):
            r = mgr.pick_pattern(level=1 + (i % 4))
            seen.add(r.kind)
        assert seen == set(WavePatternKind), f"Missing: {set(WavePatternKind) - seen}"

    def test_floor_1_bezier_sweep_selectable(self):
        mgr = ProceduralWaveManager(seed=7, floor=1)
        # Force a specific RNG state to land on BEZIER_SWEEP
        for _ in range(200):
            r = mgr.pick_pattern(level=1)
            if r.kind == WavePatternKind.BEZIER_SWEEP:
                return
        raise AssertionError("BEZIER_SWEEP never selected at floor 1 in 200 picks")

    def test_floor_1_leader_chain_selectable(self):
        mgr = ProceduralWaveManager(seed=7, floor=1)
        for _ in range(200):
            r = mgr.pick_pattern(level=1)
            if r.kind == WavePatternKind.LEADER_FOLLOWER_CHAIN:
                return
        raise AssertionError("LEADER_FOLLOWER_CHAIN never selected at floor 1 in 200 picks")

    def test_floor_1_pincer_cross_selectable(self):
        mgr = ProceduralWaveManager(seed=7, floor=1)
        for _ in range(200):
            r = mgr.pick_pattern(level=1)
            if r.kind == WavePatternKind.PINCER_CROSS:
                return
        raise AssertionError("PINCER_CROSS never selected at floor 1 in 200 picks")


# =====================================================================
# Leader marking: each pattern must mark is_leader on at least 1 ship
# =====================================================================
class TestLeaderMarking:
    def test_v_formation_marks_slot_0(self):
        rng = random.Random(42)
        r = VFormationPattern().generate(rng, level=1)
        assert r.ships[0].is_leader is True
        for s in r.ships[1:]:
            assert s.is_leader is False

    def test_leader_chain_marks_slot_0(self):
        rng = random.Random(42)
        r = LeaderFollowerChainPattern().generate(rng, level=1)
        assert r.ships[0].is_leader is True
        for s in r.ships[1:]:
            assert s.is_leader is False

    def test_bezier_sweep_marks_slot_0(self):
        rng = random.Random(42)
        r = BezierSweepPattern().generate(rng, level=1)
        assert r.ships[0].is_leader is True
        for s in r.ships[1:]:
            assert s.is_leader is False

    def test_dice_marks_center(self):
        rng = random.Random(42)
        r = DiceFiveGridPattern().generate(rng, level=1)
        leaders = [s for s in r.ships if s.is_leader]
        assert len(leaders) == 1
        # The leader is the center of the dice (0, 0 offset)
        leader = leaders[0]
        # Center ship spawn_x should be the start_x (no offset)
        # and spawn_y should be start_y
        assert leader.slot == 2  # 3rd offset in DICE_OFFSETS is the center

    def test_pincer_marks_one_per_side(self):
        rng = random.Random(42)
        r = PincerCrossPattern().generate(rng, level=1)
        leaders = [s for s in r.ships if s.is_leader]
        # 1 left + 1 right = 2 leaders
        assert len(leaders) == 2


# =====================================================================
# Runtime leader tracking
# =====================================================================
class TestRuntimeLeaderTracking:
    def test_spawn_pattern_wave_tracks_leaders(self):
        """BLOQUE 58.10: spawn_pattern_wave must populate leader_enemy_ids."""
        from src.systems.wave_patterns.runtime import spawn_pattern_wave
        from src.entities.enemies.enemy import EnemyPool

        rng = random.Random(42)
        pool = EnemyPool(capacity=64)
        mgr = ProceduralWaveManager(seed=42, floor=1)

        # Try a few patterns until we get one that spawns successfully
        for _ in range(10):
            r = mgr.pick_pattern(level=2)
            try:
                runtime = spawn_pattern_wave(pool, r)
                break
            except Exception:
                continue
        else:
            raise AssertionError("Could not spawn any pattern")

        # All 5 pattern kinds should have at least 1 leader
        assert len(runtime.leader_enemy_ids) >= 1, (
            f"Pattern {r.kind} did not mark any leaders"
        )

    def test_draw_leader_glows_runs_without_error(self):
        """BLOQUE 58.10: the draw function must not crash even with no runtime."""
        from src.systems.wave_patterns.runtime import draw_leader_glows
        from src.entities.enemies.enemy import EnemyPool, Enemy

        pool = EnemyPool(capacity=8)
        # No runtime -> should be a no-op
        surface = pygame.Surface((320, 480))
        draw_leader_glows(surface, None, [], 0.0)

        # Runtime with no leaders -> also no-op
        from src.systems.wave_patterns.runtime import PatternRuntime
        from src.systems.wave_patterns.base import WavePatternResult
        fake = WavePatternResult(ships=[], kind=WavePatternKind.V_FORMATION,
                                 difficulty=0, duration_s=1.0, seed_used=0)
        runtime = PatternRuntime(kind=WavePatternKind.V_FORMATION,
                                 ships_spawned=[], result=fake)
        draw_leader_glows(surface, runtime, [], 0.0)


# =====================================================================
# --patterns mode + chain (Wolfen + GOLIATH) integration
# =====================================================================
class TestPatternsModeChainIntegration:
    """BLOQUE 58.10: --patterns mode must still advance the chain so
    the sub-boss (Wolfen) and boss (GOLIATH) triggers fire.

    Before this fix, _spawn_procedural_patterns bypassed chain.tick(),
    so chain.elapsed_s stayed at 0 and the Wolfen/GOLIATH never appeared.
    """

    def test_chain_advances_in_patterns_mode(self):
        """BLOQUE 58.10: --patterns mode ticks the chain."""
        from src.ui.gameplay_runtime import GameplayRuntime
        from src.entities.enemies.enemy import EnemyKind

        rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
        rt.on_enter()
        rt.enable_procedural_patterns(seed=1, floor=1, spawn_interval=2.0)
        # Tick the runtime for 5 seconds
        for _ in range(300):
            rt.update(1.0 / 60.0)
        # Chain must have advanced
        assert rt._level1_chain.elapsed_s > 4.0, (
            f"chain.elapsed_s should advance in --patterns mode, got {rt._level1_chain.elapsed_s}"
        )

    def test_patterns_pause_when_sub_boss_pending(self):
        """BLOQUE 58.10: when chain.sub_boss_pending, patterns stop spawning."""
        from src.ui.gameplay_runtime import GameplayRuntime

        rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
        rt.on_enter()
        rt.enable_procedural_patterns(seed=1, floor=1, spawn_interval=1.0)
        # Manually mark sub_boss_pending
        rt._level1_chain._sub_boss_pending = True
        rt._level1_chain.current_wave_idx = 2
        # Force a tick; no new pattern should spawn
        for _ in range(180):
            rt.update(1.0 / 60.0)
        # No new pattern after sub_boss_pending
        assert rt._active_pattern_runtime is None, (
            "Pattern spawned while sub_boss_pending=True"
        )
