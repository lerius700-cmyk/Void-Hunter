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
        """BLOQUE 58.13: Pair Dance.

        5 PAIRS of ships on 2 parallel paths (10 ships at level 5+).
        Each pair shares one ParallelPathPair but takes different sides.
        The 3-segment compound bezier from BLOQUE 58.12 stays as the
        centerline; both parallel paths derive from it.
        """
        from src.movement.parallel_path import ParallelPathPair

        # 1. Choose entry side: top, left, or right
        entry_side = rng.choice(("top", "left", "right"))

        # 2. Build the 3-segment compound bezier (BLOQUE 58.12) — the
        #    centerline for the pair.
        p0, p1, p2, p3 = self._wavy_control_points(rng, entry_side)
        if entry_side == "left":
            entry_p0 = (-20, rng.uniform(INTERNAL_H * 0.2, INTERNAL_H * 0.4))
            entry_p3 = (INTERNAL_W * 0.2, INTERNAL_H * 0.4)
            entry_p1 = (INTERNAL_W * 0.05, entry_p0[1] + 30)
            entry_p2 = (INTERNAL_W * 0.10, entry_p3[1] - 30)
            exit_p0 = p3
            exit_p3 = (INTERNAL_W + 20, p3[1] + rng.uniform(-40, 40))
            exit_p1 = (INTERNAL_W + 5, exit_p0[1] + 10)
            exit_p2 = (INTERNAL_W + 10, exit_p3[1] - 10)
        elif entry_side == "right":
            entry_p0 = (INTERNAL_W + 20, rng.uniform(INTERNAL_H * 0.2, INTERNAL_H * 0.4))
            entry_p3 = (INTERNAL_W * 0.8, INTERNAL_H * 0.4)
            entry_p1 = (INTERNAL_W * 0.95, entry_p0[1] + 30)
            entry_p2 = (INTERNAL_W * 0.90, entry_p3[1] - 30)
            exit_p0 = p3
            exit_p3 = (-20, p3[1] + rng.uniform(-40, 40))
            exit_p1 = (-5, exit_p0[1] + 10)
            exit_p2 = (-10, exit_p3[1] - 10)
        else:  # top
            entry_p0 = (rng.uniform(40, INTERNAL_W - 40), -20)
            entry_p3 = (rng.uniform(40, INTERNAL_W - 40), INTERNAL_H * 0.25)
            entry_p1 = (entry_p0[0] + 30, INTERNAL_H * 0.05)
            entry_p2 = (entry_p3[0] - 30, INTERNAL_H * 0.10)
            exit_p0 = p3
            exit_p3 = (p3[0] + rng.uniform(-30, 30), INTERNAL_H + 20)
            exit_p1 = (p3[0], INTERNAL_H * 0.85)
            exit_p2 = (exit_p3[0], INTERNAL_H * 0.95)

        segments = [
            (entry_p0, entry_p1, entry_p2, entry_p3),
            (p0, p1, p2, p3),
            (exit_p0, exit_p1, exit_p2, exit_p3),
        ]
        segment_durations = [1.5, 3.5, 1.0]  # total 6s

        # 3. Build the ParallelPathPair
        pair = ParallelPathPair(segments, segment_durations, gap_px=14)
        total_duration = sum(segment_durations)

        # 4. Ship count: 3 pairs (6) at low levels, 5 pairs (10) at level 5+
        num_pairs = min(5, 3 + (level - 1) // 2)
        ship_count = num_pairs * 2

        # 5. Spawn one ship per side per pair, with phase offset per pair
        ships: list[SpawnedShip] = []
        base_t = rng.uniform(0.0, 0.05)
        for pair_idx in range(num_pairs):
            t_offset = base_t + pair_idx * 0.12
            base_hue = rng.random() * 360
            top_color = self._hue_to_rgb(base_hue, sat=0.85, val=0.95)
            bot_color = self._hue_to_rgb(base_hue + 15, sat=0.85, val=0.90)
            spawn_x, spawn_y = entry_p0
            for side, color in (("top", top_color), ("bot", bot_color)):
                is_leader = (side == "top")
                ships.append(SpawnedShip(
                    spawn_x=spawn_x,
                    spawn_y=spawn_y,
                    t_offset=t_offset,
                    slot=pair_idx * 2 + (0 if side == "top" else 1),
                    color=color,
                    is_leader=is_leader,
                    extra={
                        "parallel_pair": pair,
                        "side": side,
                    },
                ))

        return WavePatternResult(
            ships=ships,
            kind=self.kind,
            difficulty=self.difficulty,
            duration_s=total_duration,
            seed_used=rng.randint(0, 2**31 - 1),
        )

    # ------------------------------------------------------------------
    # BLOQUE 58.11: wavy control points (S-curve / dancing motion)
    # ------------------------------------------------------------------
    def _wavy_control_points(
        self,
        rng: random.Random,
        entry_side: str,
    ) -> tuple[tuple[float, float], ...]:
        """Generate 4 control points that make a wavy S-curve.

        Star Fox 64 enemies often "swoop" across the playfield in a
        dancing pattern: enter, swoop up, swoop down, exit. We achieve
        this by offsetting P1 and P2 in opposite vertical directions
        from a straight line between P0 and P3.
        """
        if entry_side == "top":
            p0 = (rng.uniform(20, INTERNAL_W - 20), -20)
            p3 = (rng.choice([20, INTERNAL_W - 20]), INTERNAL_H + 20)
            mid_y = (p0[1] + p3[1]) / 2
            # Wavy: first control UP, second control DOWN
            p1 = (rng.uniform(40, INTERNAL_W - 40), mid_y - 80)
            p2 = (rng.uniform(40, INTERNAL_W - 40), mid_y + 80)
        elif entry_side == "left":
            p0 = (-20, rng.uniform(20, INTERNAL_H * 0.5))
            p3 = (INTERNAL_W + 20, rng.uniform(INTERNAL_H * 0.5, INTERNAL_H - 20))
            mid_y = (p0[1] + p3[1]) / 2
            p1 = (INTERNAL_W * 0.3, mid_y - 80)
            p2 = (INTERNAL_W * 0.7, mid_y + 80)
        else:  # right
            p0 = (INTERNAL_W + 20, rng.uniform(20, INTERNAL_H * 0.5))
            p3 = (-20, rng.uniform(INTERNAL_H * 0.5, INTERNAL_H - 20))
            mid_y = (p0[1] + p3[1]) / 2
            p1 = (INTERNAL_W * 0.7, mid_y + 80)
            p2 = (INTERNAL_W * 0.3, mid_y - 80)
        return p0, p1, p2, p3

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

    # ------------------------------------------------------------------
    # BLOQUE 58.13: HSV → RGB for pair colors
    # ------------------------------------------------------------------
    @staticmethod
    def _hue_to_rgb(hue: float, sat: float = 0.85, val: float = 0.95) -> tuple[int, int, int]:
        """HSV to RGB. hue in [0, 360), sat/val in [0, 1]."""
        h = hue / 60.0
        c = val * sat
        x = c * (1 - abs(h % 2 - 1))
        m = val - c
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
        return (
            int((rp + m) * 255),
            int((gp + m) * 255),
            int((bp + m) * 255),
        )
