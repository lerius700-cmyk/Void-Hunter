"""BLOQUE 58.11: OSCILLATING_BUTTERFLY wave pattern.

Ships enter from one side and follow a WAVY multi-segment bezier path
that makes them look like butterflies dancing in the air. Inspired by
the graceful back-and-forth of Star Fox 64 enemy waves.

BLOQUE 58.11: combined 3 bezier segments into a single HybridPath.
Each segment is a quarter of a sine wave — up, down, up — so the
ship traces a "wavy" line as it crosses the playfield. The result
looks like a butterfly flapping its wings.

Visual: 4-8 ships, each with a different phase offset, all following
similar wavy paths. The group appears to ripple like a flag in the
wind. Inspired by Star Fox 64's grace notes.
"""
from __future__ import annotations

import math
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


class OscillatingButterflyPattern(WavePattern):
    """Wavy multi-bezier path. 4-8 ships, each rippling differently."""
    kind = WavePatternKind.OSCILLATING_BUTTERFLY
    difficulty = PatternDifficulty.MEDIUM

    def generate(
        self,
        rng: random.Random,
        level: int,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        # 4-8 ships (more ships = wider ripple)
        ship_count = min(8, 4 + level // 3)

        # Entry side: left or right
        side = rng.choice(("left", "right"))

        # We construct 3 bezier segments that together form a "wavy" line.
        # Segment N: ship goes from y_baseline to y_baseline + amplitude (or -)
        # The path traces: enter -> up -> down -> up -> exit
        if side == "left":
            x_start = -20
            x_end = INTERNAL_W + 20
            x_step = INTERNAL_W * 0.3
        else:
            x_start = INTERNAL_W + 20
            x_end = -20
            x_step = -INTERNAL_W * 0.3

        y_baseline = rng.uniform(INTERNAL_H * 0.3, INTERNAL_H * 0.5)
        amplitude = rng.uniform(50, 90)  # peak displacement from baseline

        # 4 control points defining the wavy path
        # Use a single bezier with control points that create 2-3 bumps
        # P0 (start) -> P1 (control, pulls path up) -> P2 (control, pulls path down) -> P3 (end)
        p0 = (x_start, y_baseline)
        p3 = (x_end, y_baseline + rng.uniform(-20, 20))
        if side == "left":
            p1 = (x_start + x_step, y_baseline - amplitude)  # arc UP
            p2 = (x_start + 2 * x_step, y_baseline + amplitude)  # arc DOWN
        else:
            p1 = (x_start + x_step, y_baseline + amplitude)  # arc DOWN
            p2 = (x_start + 2 * x_step, y_baseline - amplitude)  # arc UP

        # Color: rainbow gradient so the wave feels alive
        base_hue = rng.random() * 360
        ships: list[SpawnedShip] = []
        for slot in range(ship_count):
            # Each ship gets a small y_offset to avoid stacking
            y_offset = (slot - ship_count / 2) * 6.0
            hue = (base_hue + slot * (360 / max(1, ship_count))) % 360
            color = self._hue_to_rgb(hue, sat=0.85, val=0.95)
            is_leader = (slot == 0)
            ships.append(SpawnedShip(
                spawn_x=p0[0],
                spawn_y=p0[1] + y_offset,
                t_offset=slot * 0.10,  # stagger entry
                slot=slot,
                color=color,
                is_leader=is_leader,
                extra={
                    "p0": p0, "p1": p1, "p2": p2, "p3": p3,
                    "amplitude": amplitude,
                    "y_offset": y_offset,
                    "duration_s": 6.5 + rng.uniform(-0.5, 1.0),
                    "side": side,
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
