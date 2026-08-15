"""BLOQUE 58.8: BEZIER_SWEEP wave pattern.

A group of 4-8 ships all share the same random bezier curve (P_0..P_3).
They sweep the screen together, each with a small t_offset stagger so
they form a moving line along the curve.

Visual: feels like a comet trail following an S-curve from one side
of the playfield to the other.
"""
from __future__ import annotations

import random
from typing import Optional

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.systems.wave_patterns.base import (
    PatternDifficulty,
    SpawnedShip,
    WavePattern,
    WavePatternKind,
    WavePatternResult,
)


class BezierSweepPattern(WavePattern):
    """Random bezier curve, ships sweep across the playfield."""
    kind = WavePatternKind.BEZIER_SWEEP
    difficulty = PatternDifficulty.MEDIUM

    def generate(
        self,
        rng: random.Random,
        level: int,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        # 1. Choose entry side: top, left, or right (not bottom - we want
        #    ships to come INTO the playfield, not exit at start)
        entry_side = rng.choice(("top", "left", "right"))

        # 2. Generate control points P_0..P_3
        p0, p1, p2, p3 = self._random_control_points(rng, entry_side)

        # 3. Ship count scales with level (4-8)
        ship_count = min(8, 4 + level // 3)

        # 4. Stagger t_offsets so they form a moving line
        ships: list[SpawnedShip] = []
        base_t = rng.uniform(0.0, 0.05)
        for slot in range(ship_count):
            t_offset = base_t + slot * 0.06   # 0.06s between ships
            # Each ship starts at the curve position at t_offset
            x, y = self._bezier_point(t_offset, p0, p1, p2, p3)
            # Color: HSL hue based on slot, same family for group cohesion
            color = self._slot_color(rng, slot, ship_count)
            ships.append(SpawnedShip(
                spawn_x=x,
                spawn_y=y,
                t_offset=t_offset,
                slot=slot,
                color=color,
                is_leader=(slot == 0),  # BLOQUE 58.10: leader (front of sweep)
                extra={
                    "p0": p0, "p1": p1, "p2": p2, "p3": p3,
                    "duration_s": 5.5 + rng.uniform(-0.5, 1.0),
                    "curve_id": rng.randint(0, 999_999),
                },
            ))

        return WavePatternResult(
            ships=ships,
            kind=self.kind,
            difficulty=self.difficulty,
            duration_s=ships[0].extra["duration_s"] if ships else 5.5,
            seed_used=rng.randint(0, 2**31 - 1),
        )

    # ------------------------------------------------------------------
    # Curve generation
    # ------------------------------------------------------------------
    def _random_control_points(
        self,
        rng: random.Random,
        entry_side: str,
    ) -> tuple[tuple[float, float], ...]:
        """Generate 4 control points that create a nice sweeping curve.

        The curve starts off-screen (P_0), bends through the playfield
        (P_1, P_2), and exits on the opposite side (P_3).
        """
        if entry_side == "top":
            # Enter from top, exit through bottom-left or bottom-right
            p0 = (rng.uniform(20, INTERNAL_W - 20), -20)
            p3 = (rng.choice([20, INTERNAL_W - 20]), INTERNAL_H + 20)
            p1 = (rng.uniform(40, INTERNAL_W - 40), INTERNAL_H * 0.3)
            p2 = (rng.uniform(40, INTERNAL_W - 40), INTERNAL_H * 0.7)
        elif entry_side == "left":
            # Enter from left, exit through right
            p0 = (-20, rng.uniform(20, INTERNAL_H * 0.5))
            p3 = (INTERNAL_W + 20, rng.uniform(INTERNAL_H * 0.5, INTERNAL_H - 20))
            p1 = (INTERNAL_W * 0.3, rng.uniform(20, INTERNAL_H * 0.5))
            p2 = (INTERNAL_W * 0.7, rng.uniform(INTERNAL_H * 0.5, INTERNAL_H - 20))
        else:  # right
            p0 = (INTERNAL_W + 20, rng.uniform(20, INTERNAL_H * 0.5))
            p3 = (-20, rng.uniform(INTERNAL_H * 0.5, INTERNAL_H - 20))
            p1 = (INTERNAL_W * 0.7, rng.uniform(20, INTERNAL_H * 0.5))
            p2 = (INTERNAL_W * 0.3, rng.uniform(INTERNAL_H * 0.5, INTERNAL_H - 20))
        return p0, p1, p2, p3

    @staticmethod
    def _bezier_point(
        t: float,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
    ) -> tuple[float, float]:
        """Cubic Bezier at parameter t in [0,1]."""
        u = 1.0 - t
        x = (u**3) * p0[0] + 3 * (u**2) * t * p1[0] + 3 * u * (t**2) * p2[0] + (t**3) * p3[0]
        y = (u**3) * p0[1] + 3 * (u**2) * t * p1[1] + 3 * u * (t**2) * p2[1] + (t**3) * p3[1]
        return (x, y)

    @staticmethod
    def _slot_color(rng: random.Random, slot: int, total: int) -> tuple[int, int, int]:
        """Group color: one base hue, slots get slight variations."""
        base_hue = rng.random() * 360
        # All ships share the base hue; brightness varies by slot
        v = 0.9 - (slot / max(1, total)) * 0.3
        s = 0.9
        h = base_hue / 60.0
        c = v * s
        x = c * (1 - abs(h % 2 - 1))
        if h < 1:
            rp, gp, bp = c, x, 0
        elif h < 2:
            rp, gp, bp = x, c, 0
        elif h < 3:
            rp, gp, bp = 0, c, x
        elif h < 4:
            rp, gp, bp = 0, x, c
        elif h < 5:
            rp, gp, bp = x, 0, c
        else:
            rp, gp, bp = c, 0, x
        m = v - c
        return (int((rp + m) * 255), int((gp + m) * 255), int((bp + m) * 255))
