"""BLOQUE 58.8: PINCER_CROSS wave pattern.

Two groups of ships enter from opposite sides (left and right) and
follow mirror bezier curves that converge near the center. Ships meet
in the middle then continue outward.

Visual: a pincer attack — the player has to choose which side to
prioritize. The two groups are mirror images of each other.
"""
from __future__ import annotations

import random

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.systems.wave_patterns.base import (
    PatternDifficulty,
    SpawnedShip,
    WavePattern,
    WavePatternKind,
    WavePatternResult,
)


class PincerCrossPattern(WavePattern):
    """Two mirror bezier curves from left and right edges."""
    kind = WavePatternKind.PINCER_CROSS
    difficulty = PatternDifficulty.HARD

    def generate(
        self,
        rng: random.Random,
        level: int,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        # 4-6 ships per side (8-12 total)
        per_side = min(6, 4 + level // 4)

        # Convergence point: somewhere in the middle 60% of the playfield
        converge_x = INTERNAL_W * rng.uniform(0.3, 0.7)
        converge_y = INTERNAL_H * rng.uniform(0.3, 0.6)

        # Left group: enter from far left, sweep right, then continue past
        # converge to far right
        # Mirror: enter from far right, sweep left, then continue past to far left
        # Control points: each side has 2 control points (P1, P2) that
        # shape the curve. We make them symmetric across the y axis.

        # Spread: how far apart the control points are (curve amplitude)
        spread = 80.0 + rng.uniform(0, 40)

        # Left side curve
        l_p0 = (-20, rng.uniform(40, INTERNAL_H * 0.4))
        l_p3 = (INTERNAL_W + 20, rng.uniform(INTERNAL_H * 0.6, INTERNAL_H - 40))
        l_p1 = (converge_x - spread, converge_y - spread * 0.5)
        l_p2 = (converge_x - spread * 0.3, converge_y + spread * 0.3)

        # Right side curve (mirror of left)
        r_p0 = (INTERNAL_W + 20, l_p0[1])
        r_p3 = (-20, l_p3[1])
        r_p1 = (converge_x + spread, l_p1[1])
        r_p2 = (converge_x + spread * 0.3, l_p2[1])

        # Color: each side has its own color (red left, cyan right)
        left_color = (255, 100, 100)   # red-ish
        right_color = (100, 220, 255)  # cyan-ish

        ships: list[SpawnedShip] = []
        # Left group
        for slot in range(per_side):
            # Stagger so they don't all enter at the same time
            t_offset = slot * 0.04
            x, y = self._bezier_point(0.0, l_p0, l_p1, l_p2, l_p3)
            ships.append(SpawnedShip(
                spawn_x=x, spawn_y=y,
                t_offset=t_offset, slot=slot, color=left_color,
                is_leader=(slot == 0),  # BLOQUE 58.10: front of pincer
                extra={
                    "p0": l_p0, "p1": l_p1, "p2": l_p2, "p3": l_p3,
                    "side": "left", "side_idx": slot,
                    "duration_s": 6.0 + rng.uniform(-0.5, 1.0),
                },
            ))
        # Right group
        for slot in range(per_side):
            t_offset = slot * 0.04
            x, y = self._bezier_point(0.0, r_p0, r_p1, r_p2, r_p3)
            ships.append(SpawnedShip(
                spawn_x=x, spawn_y=y,
                t_offset=t_offset, slot=slot, color=right_color,
                is_leader=(slot == 0),  # BLOQUE 58.10: front of pincer
                extra={
                    "p0": r_p0, "p1": r_p1, "p2": r_p2, "p3": r_p3,
                    "side": "right", "side_idx": slot,
                    "duration_s": 6.0 + rng.uniform(-0.5, 1.0),
                },
            ))

        return WavePatternResult(
            ships=ships,
            kind=self.kind,
            difficulty=self.difficulty,
            duration_s=ships[0].extra["duration_s"],
            seed_used=rng.randint(0, 2**31 - 1),
        )

    @staticmethod
    def _bezier_point(
        t: float,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
    ) -> tuple[float, float]:
        u = 1.0 - t
        x = (u**3) * p0[0] + 3 * (u**2) * t * p1[0] + 3 * u * (t**2) * p2[0] + (t**3) * p3[0]
        y = (u**3) * p0[1] + 3 * (u**2) * t * p1[1] + 3 * u * (t**2) * p2[1] + (t**3) * p3[1]
        return (x, y)
