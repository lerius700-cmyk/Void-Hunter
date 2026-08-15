"""BLOQUE 58.8: ProceduralWaveManager.

Picks a WavePattern per wave based on:
  - floor number (1-indexed difficulty curve)
  - roguelike seed (for reproducibility)
  - player progression (anti-stuck)

Difficulty curve (from user brief):
  Floor 1-2 (easy):   V_FORMATION, DICE_FIVE_GRID
  Floor 3-4 (medium): LEADER_FOLLOWER_CHAIN, BEZIER_SWEEP
  Floor 5+   (hard):  PINCER_CROSS, mixed patterns

The manager logs each pick to logs/patterns.log so the user can
verify the pattern sequence matches their difficulty curve.
"""
from __future__ import annotations

import os
import random
from datetime import datetime
from typing import Optional

from src.systems.wave_patterns.base import (
    PatternDifficulty,
    WavePattern,
    WavePatternKind,
    WavePatternResult,
)
from src.systems.wave_patterns.bezier_sweep import BezierSweepPattern
from src.systems.wave_patterns.v_formation import VFormationPattern
from src.systems.wave_patterns.leader_chain import LeaderFollowerChainPattern
from src.systems.wave_patterns.dice_grid import DiceFiveGridPattern
from src.systems.wave_patterns.pincer_cross import PincerCrossPattern


# Floor -> allowed pattern pool (difficulty curve)
_DIFFICULTY_POOL: dict[int, list[WavePatternKind]] = {
    1: [WavePatternKind.V_FORMATION, WavePatternKind.DICE_FIVE_GRID],
    2: [WavePatternKind.V_FORMATION, WavePatternKind.DICE_FIVE_GRID,
        WavePatternKind.LEADER_FOLLOWER_CHAIN],
    3: [WavePatternKind.LEADER_FOLLOWER_CHAIN, WavePatternKind.BEZIER_SWEEP,
        WavePatternKind.DICE_FIVE_GRID],
    4: [WavePatternKind.LEADER_FOLLOWER_CHAIN, WavePatternKind.BEZIER_SWEEP,
        WavePatternKind.PINCER_CROSS],
}
# Floor 5+ = all patterns available
def _pool_for_floor(floor: int) -> list[WavePatternKind]:
    if floor in _DIFFICULTY_POOL:
        return list(_DIFFICULTY_POOL[floor])
    # 5+: all 5 patterns
    return list(WavePatternKind)


class ProceduralWaveManager:
    """Manages pattern selection for a roguelike run."""

    def __init__(
        self,
        seed: int,
        floor: int = 1,
        log_path: Optional[str] = None,
    ) -> None:
        self._seed = seed
        self._floor = floor
        self._rng = random.Random(seed)
        # History to avoid immediate repeats (anti-stuck)
        self._last_kind: Optional[WavePatternKind] = None
        # Log
        self._log_path = log_path
        if log_path is None:
            try:
                log_dir = os.path.join(os.getcwd(), "logs")
                os.makedirs(log_dir, exist_ok=True)
                self._log_path = os.path.join(log_dir, "patterns.log")
            except Exception:
                self._log_path = None

    def set_floor(self, floor: int) -> None:
        """Update the current floor (called on level transitions)."""
        self._floor = floor

    def get_floor(self) -> int:
        return self._floor

    def get_seed(self) -> int:
        return self._seed

    def pick_pattern(
        self,
        level: int = 1,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        """Pick and instantiate a pattern for the current wave.

        `level` is the in-floor wave index (1, 2, 3...). Affects ship count
        and curve amplitude.
        """
        pool = _pool_for_floor(self._floor)
        # Filter out the previous kind (avoid immediate repeats)
        if self._last_kind is not None and len(pool) > 1:
            pool = [k for k in pool if k != self._last_kind]
        kind = self._rng.choice(pool)
        self._last_kind = kind

        # Instantiate the pattern
        pattern = self._make_pattern(kind)
        result = pattern.generate(self._rng, level, enemy_kind)

        # Log
        self._log_pick(kind, result)
        return result

    @staticmethod
    def _make_pattern(kind: WavePatternKind) -> WavePattern:
        if kind == WavePatternKind.BEZIER_SWEEP:
            return BezierSweepPattern()
        if kind == WavePatternKind.V_FORMATION:
            return VFormationPattern()
        if kind == WavePatternKind.LEADER_FOLLOWER_CHAIN:
            return LeaderFollowerChainPattern()
        if kind == WavePatternKind.DICE_FIVE_GRID:
            return DiceFiveGridPattern()
        if kind == WavePatternKind.PINCER_CROSS:
            return PincerCrossPattern()
        raise ValueError(f"Unknown pattern kind: {kind}")

    def _log_pick(
        self,
        kind: WavePatternKind,
        result: WavePatternResult,
    ) -> None:
        if not self._log_path:
            return
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                ts = datetime.now().strftime("%H:%M:%S")
                f.write(
                    f"[{ts}] floor={self._floor} seed={self._seed} "
                    f"kind={kind.value} difficulty={result.difficulty.name} "
                    f"ships={len(result.ships)} duration={result.duration_s:.1f}s\n"
                )
        except Exception:
            pass

    def preview_next_pool(self) -> list[str]:
        """For UI/debug: returns the pool of patterns the manager could pick next."""
        return [k.value for k in _pool_for_floor(self._floor)]
