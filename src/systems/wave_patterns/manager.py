"""BLOQUE 58.8: ProceduralWaveManager.

Picks a WavePattern per wave based on:
  - floor number (1-indexed difficulty curve)
  - roguelike seed (for reproducibility)
  - player progression (anti-stuck)

BLOQUE 58.10: Difficulty curve fix.
  - All 5 patterns are available from floor 1 (BEFORE: floor 1 only had 2)
  - Difficulty is now controlled by IN-pattern parameters (ship count,
    curve amplitude, bezier sweep count), not by GATING which patterns
    can appear. The user wants to see all formations in v1.1, not
    "unlock them later".
  - Each floor has a weight vector; easier patterns are still more
    likely on early floors, but nothing is hidden.

Weight per floor (out of ~100 picks per 100 waves):
  Floor 1: 25% V_FORMATION, 20% DICE_FIVE_GRID, 20% LEADER_FOLLOWER_CHAIN,
           20% BEZIER_SWEEP, 15% PINCER_CROSS
  Floor 2: 20% V_FORMATION, 20% DICE_FIVE_GRID, 20% LEADER_FOLLOWER_CHAIN,
           20% BEZIER_SWEEP, 20% PINCER_CROSS
  Floor 3+: 17% each, equal rotation

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
from src.systems.wave_patterns.oscillating_butterfly import OscillatingButterflyPattern


# BLOQUE 58.10: Weighted pool per floor. Weights determine probability,
# not availability. All patterns are always eligible.
# BLOQUE 58.11: added OSCILLATING_BUTTERFLY to all floors.
_WEIGHTED_POOL: dict[int, list[tuple[WavePatternKind, int]]] = {
    1: [
        (WavePatternKind.V_FORMATION, 20),
        (WavePatternKind.DICE_FIVE_GRID, 18),
        (WavePatternKind.LEADER_FOLLOWER_CHAIN, 16),
        (WavePatternKind.BEZIER_SWEEP, 16),
        (WavePatternKind.PINCER_CROSS, 12),
        (WavePatternKind.OSCILLATING_BUTTERFLY, 18),
    ],
    2: [
        (WavePatternKind.V_FORMATION, 16),
        (WavePatternKind.DICE_FIVE_GRID, 16),
        (WavePatternKind.LEADER_FOLLOWER_CHAIN, 16),
        (WavePatternKind.BEZIER_SWEEP, 16),
        (WavePatternKind.PINCER_CROSS, 16),
        (WavePatternKind.OSCILLATING_BUTTERFLY, 20),
    ],
}
# Floor 3+ = roughly equal weight, with OSCILLATING_BUTTERFLY slightly preferred
_EQUAL_WEIGHT = [
    (WavePatternKind.V_FORMATION, 16),
    (WavePatternKind.DICE_FIVE_GRID, 16),
    (WavePatternKind.LEADER_FOLLOWER_CHAIN, 16),
    (WavePatternKind.BEZIER_SWEEP, 16),
    (WavePatternKind.PINCER_CROSS, 16),
    (WavePatternKind.OSCILLATING_BUTTERFLY, 20),
]


def _pool_for_floor(floor: int) -> list[tuple[WavePatternKind, int]]:
    """Return weighted pool for the given floor. All 5 patterns always
    available; weights control probability not eligibility.
    """
    if floor in _WEIGHTED_POOL:
        return list(_WEIGHTED_POOL[floor])
    return list(_EQUAL_WEIGHT)


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

        BLOQUE 58.10: Uses weighted random choice from full pool of 5
        patterns (BEFORE: hard pool that gated patterns by floor).
        """
        weighted_pool = _pool_for_floor(self._floor)
        # Filter out the previous kind (avoid immediate repeats)
        if self._last_kind is not None and len(weighted_pool) > 1:
            weighted_pool = [(k, w) for k, w in weighted_pool if k != self._last_kind]
        # Build flat list weighted by count, then random.choice
        flat: list[WavePatternKind] = []
        for kind, weight in weighted_pool:
            flat.extend([kind] * weight)
        kind = self._rng.choice(flat)
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
        if kind == WavePatternKind.OSCILLATING_BUTTERFLY:
            return OscillatingButterflyPattern()
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
        """For UI/debug: returns the pool of patterns the manager could pick next.
        BLOQUE 58.10: returns the deduped kinds (one entry per kind)."""
        seen: set[WavePatternKind] = set()
        out: list[str] = []
        for k, _ in _pool_for_floor(self._floor):
            if k not in seen:
                seen.add(k)
                out.append(k.value)
        return out
