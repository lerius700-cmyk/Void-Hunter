"""BLOQUE 58.8: DICE_FIVE_GRID wave pattern.

5 ships arranged in a dice-5 pattern (4 corners + 1 center) around a
dynamic point that moves through the playfield. The point follows a
random straight path with a slight curve.

Visual: a tight cluster of 5 ships moving in formation like a "5 on a
die". Rigid relative positions, no individual ship curves.
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


class DiceFiveGridPattern(WavePattern):
    """5 ships in dice-5 formation, orbiting a dynamic central point."""
    kind = WavePatternKind.DICE_FIVE_GRID
    difficulty = PatternDifficulty.EASY

    # Dice-5 layout: 4 corners + 1 center
    # Offsets relative to the center point
    SPACING = 20.0  # px between ships
    DICE_OFFSETS = [
        (-SPACING, -SPACING),  # top-left
        (+SPACING, -SPACING),  # top-right
        (0.0,      0.0),         # center
        (-SPACING, +SPACING),  # bottom-left
        (+SPACING, +SPACING),  # bottom-right
    ]

    def generate(
        self,
        rng: random.Random,
        level: int,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        # The "dynamic point" starts at top and moves down with
        # a slight horizontal drift (like a die falling).
        start_x = rng.uniform(60, INTERNAL_W - 60)
        start_y = -20.0
        # Horizontal drift
        end_x = start_x + rng.uniform(-60, 60)
        end_x = max(40, min(INTERNAL_W - 40, end_x))
        end_y = INTERNAL_H + 20.0

        # The dynamic point also has a control point for slight curve
        control_x = (start_x + end_x) / 2 + rng.uniform(-30, 30)
        control_y = (start_y + end_y) / 2

        # Color: each ship gets a different bright color from a 5-color palette
        palette = [
            (255,  80,  80),  # red    (top-left)
            ( 80, 255,  80),  # green  (top-right)
            (255, 240,  80),  # yellow (center)
            ( 80, 160, 255),  # blue   (bottom-left)
            (255,  80, 255),  # pink   (bottom-right)
        ]
        # Optionally shuffle the palette so colors aren't always same position
        if rng.random() < 0.5:
            palette = list(palette)
            rng.shuffle(palette)

        ships: list[SpawnedShip] = []
        for slot, (ox, oy) in enumerate(self.DICE_OFFSETS):
            # BLOQUE 58.10: center ship of the dice is the "leader"
            is_leader = (ox == 0.0 and oy == 0.0)
            ships.append(SpawnedShip(
                spawn_x=start_x + ox,
                spawn_y=start_y + oy,
                t_offset=0.0,    # dice moves as one
                slot=slot,
                color=palette[slot],
                is_leader=is_leader,
                extra={
                    "start_x": start_x, "start_y": start_y,
                    "end_x": end_x, "end_y": end_y,
                    "control_x": control_x, "control_y": control_y,
                    "dice_offsets": list(self.DICE_OFFSETS),
                    "duration_s": 5.0 + rng.uniform(0, 1.0),
                },
            ))

        return WavePatternResult(
            ships=ships,
            kind=self.kind,
            difficulty=self.difficulty,
            duration_s=ships[0].extra["duration_s"],
            seed_used=rng.randint(0, 2**31 - 1),
        )
