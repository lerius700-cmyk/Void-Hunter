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
        """BLOQUE 58.13: X-Crossing Compound.

        Two groups attack from opposite sides, meet at center in a
        perfect X, then escape on the SWAPPED sides.

        4 segments per ship:
          1 (1.5s): entry — from edge to center
          2 (0.8s): CROSS — center to OPPOSITE side
          3 (1.0s): cruise — continue along opposite side
          4 (1.5s): exit — off the far edge
        """
        per_side = min(7, 5 + level // 4)

        center_x = INTERNAL_W / 2
        center_y = INTERNAL_H * rng.uniform(0.3, 0.5)
        spread = 80.0 + rng.uniform(0, 40)

        s1_dur, s2_dur, s3_dur, s4_dur = 1.5, 0.8, 1.0, 1.5
        total_dur = s1_dur + s2_dur + s3_dur + s4_dur  # 4.8s

        l_s1 = (
            (-20, center_y - spread * 0.3),
            (center_x * 0.3, center_y - spread * 0.2),
            (center_x * 0.7, center_y + spread * 0.1),
            (center_x, center_y),
        )
        l_s2 = (
            (center_x, center_y),
            (center_x + spread * 0.3, center_y - spread * 0.2),
            (INTERNAL_W - center_x * 0.3, center_y + spread * 0.2),
            (INTERNAL_W + 20, center_y + spread * 0.3),
        )
        l_s3 = (
            (INTERNAL_W + 20, center_y + spread * 0.3),
            (INTERNAL_W - 30, center_y + spread * 0.4),
            (INTERNAL_W - 60, center_y + spread * 0.5),
            (INTERNAL_W + 20, center_y + spread * 0.6),
        )
        l_s4 = (
            (INTERNAL_W + 20, center_y + spread * 0.6),
            (INTERNAL_W + 30, center_y + spread * 0.7),
            (INTERNAL_W + 40, center_y + spread * 0.8),
            (INTERNAL_W + 60, center_y + spread * 0.9),
        )

        r_s1 = (
            (INTERNAL_W + 20, center_y + spread * 0.3),
            (INTERNAL_W - center_x * 0.3, center_y + spread * 0.2),
            (center_x * 0.7, center_y - spread * 0.1),
            (center_x, center_y),
        )
        r_s2 = (
            (center_x, center_y),
            (center_x - spread * 0.3, center_y + spread * 0.2),
            (center_x * 0.3, center_y - spread * 0.2),
            (-20, center_y - spread * 0.3),
        )
        r_s3 = (
            (-20, center_y - spread * 0.3),
            (30, center_y - spread * 0.4),
            (60, center_y - spread * 0.5),
            (-20, center_y - spread * 0.6),
        )
        r_s4 = (
            (-20, center_y - spread * 0.6),
            (-30, center_y - spread * 0.7),
            (-40, center_y - spread * 0.8),
            (-60, center_y - spread * 0.9),
        )

        left_color = (255, 100, 100)
        right_color = (100, 220, 255)

        ships: list[SpawnedShip] = []
        for slot in range(per_side):
            t_offset = slot * 0.04
            ships.append(SpawnedShip(
                spawn_x=l_s1[0][0], spawn_y=l_s1[0][1],
                t_offset=t_offset, slot=slot, color=left_color,
                is_leader=(slot == 0),
                extra={
                    "segments": [l_s1, l_s2, l_s3, l_s4],
                    "segment_durations": [s1_dur, s2_dur, s3_dur, s4_dur],
                    "side": "left", "side_idx": slot,
                    "duration_s": total_dur,
                },
            ))
            ships.append(SpawnedShip(
                spawn_x=r_s1[0][0], spawn_y=r_s1[0][1],
                t_offset=t_offset,
                slot=per_side + slot, color=right_color,
                is_leader=(slot == 0),
                extra={
                    "segments": [r_s1, r_s2, r_s3, r_s4],
                    "segment_durations": [s1_dur, s2_dur, s3_dur, s4_dur],
                    "side": "right", "side_idx": slot,
                    "duration_s": total_dur,
                },
            ))

        return WavePatternResult(
            ships=ships,
            kind=self.kind,
            difficulty=self.difficulty,
            duration_s=total_dur,
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
