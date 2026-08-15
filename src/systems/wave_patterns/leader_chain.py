"""BLOQUE 58.8: LEADER_FOLLOWER_CHAIN wave pattern.

One leader ship follows a random bezier path. N followers each read
the leader's position from a rolling history queue, with increasing
delay. This is the "follow the leader" snake pattern from Star Fox.

Visual: a chain of ships curving through the playfield, each trailing
slightly behind the previous. Frequency of oscillation = how curvy
the leader's path is.
"""
from __future__ import annotations

import random
from collections import deque
from typing import Optional

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.systems.wave_patterns.base import (
    PatternDifficulty,
    SpawnedShip,
    WavePattern,
    WavePatternKind,
    WavePatternResult,
)


class LeaderFollowerChainPattern(WavePattern):
    """Leader + history-queue followers in a bezier snake."""
    kind = WavePatternKind.LEADER_FOLLOWER_CHAIN
    difficulty = PatternDifficulty.MEDIUM

    def generate(
        self,
        rng: random.Random,
        level: int,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        # 1. Generate leader's bezier control points
        # The leader enters from one side and curves through the playfield.
        # Frequency parameter: how curvy the path is. The user clarified
        # "serpentine" referred to frequency, not amplitude. We control
        # frequency by varying the control point spread.
        frequency = 0.4 + (level * 0.05)  # 0.4 (calm) to ~1.4 (serpentine)
        amplitude = 60.0 + rng.uniform(-15, 25)  # px swing

        # Entry from left or right
        if rng.random() < 0.5:
            p0 = (-20, rng.uniform(60, INTERNAL_H * 0.4))
            p3 = (INTERNAL_W + 20, rng.uniform(INTERNAL_H * 0.6, INTERNAL_H - 60))
        else:
            p0 = (INTERNAL_W + 20, rng.uniform(60, INTERNAL_H * 0.4))
            p3 = (-20, rng.uniform(INTERNAL_H * 0.6, INTERNAL_H - 60))

        # Control points create the curve. Frequency controls how much
        # the curve oscillates in the middle.
        cx1 = INTERNAL_W * 0.3
        cx2 = INTERNAL_W * 0.7
        cy_center = INTERNAL_H / 2
        # Higher frequency = more swing in control points
        p1 = (cx1, cy_center - amplitude * frequency)
        p2 = (cx2, cy_center + amplitude * frequency)

        # 2. Ship count: leader + 3-5 followers
        ship_count = min(6, 4 + level // 5)

        # 3. Each follower's t_offset = position in queue
        # History queue has 60 entries (1 second at 60fps)
        # Each follower's effective t_offset is N frames back
        delay_per_follower = 0.10  # 0.10s = 6 frames at 60fps

        base_color = self._random_color(rng)
        ships: list[SpawnedShip] = []
        for slot in range(ship_count):
            t_offset = slot * delay_per_follower
            # Leader starts at the bezier position at t=0
            x, y = self._bezier_point(0.0, p0, p1, p2, p3)
            ships.append(SpawnedShip(
                spawn_x=x,
                spawn_y=y,
                t_offset=t_offset,
                slot=slot,
                color=base_color,
                is_leader=(slot == 0),  # BLOQUE 58.10: leader glow ring
                extra={
                    "p0": p0, "p1": p1, "p2": p2, "p3": p3,
                    "frequency": frequency,
                    "amplitude": amplitude,
                    "delay_per_follower": delay_per_follower,
                    "history_size": 60,
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
