"""BLOQUE 58.8: Procedural Wave Patterns.

5 patterns inspired by Star Fox 64:
  1. BEZIER_SWEEP        - random bezier P_0..P_3, ships sweep screen
  2. V_FORMATION         - rigid V, fixed offsets
  3. LEADER_FOLLOWER_CHAIN - leader + history queue followers
  4. DICE_FIVE_GRID      - 5 ships in dice-5 around dynamic point
  5. PINCER_CROSS        - two mirror bezier curves from sides

Plus ProceduralWaveManager that picks patterns per wave based on
roguelike floor + difficulty curve.
"""
from src.systems.wave_patterns.base import (
    WavePattern,
    WavePatternKind,
    SpawnedShip,
    PatternDifficulty,
)
from src.systems.wave_patterns.bezier_sweep import BezierSweepPattern
from src.systems.wave_patterns.v_formation import VFormationPattern
from src.systems.wave_patterns.leader_chain import LeaderFollowerChainPattern
from src.systems.wave_patterns.dice_grid import DiceFiveGridPattern
from src.systems.wave_patterns.pincer_cross import PincerCrossPattern
from src.systems.wave_patterns.manager import ProceduralWaveManager


def make_pattern(kind: WavePatternKind) -> WavePattern:
    """Factory: returns the right pattern impl for a given kind."""
    mapping = {
        WavePatternKind.BEZIER_SWEEP: BezierSweepPattern,
        WavePatternKind.V_FORMATION: VFormationPattern,
        WavePatternKind.LEADER_FOLLOWER_CHAIN: LeaderFollowerChainPattern,
        WavePatternKind.DICE_FIVE_GRID: DiceFiveGridPattern,
        WavePatternKind.PINCER_CROSS: PincerCrossPattern,
    }
    return mapping[kind]()


__all__ = [
    "WavePattern",
    "WavePatternKind",
    "SpawnedShip",
    "PatternDifficulty",
    "BezierSweepPattern",
    "VFormationPattern",
    "LeaderFollowerChainPattern",
    "DiceFiveGridPattern",
    "PincerCrossPattern",
    "ProceduralWaveManager",
    "make_pattern",
]
