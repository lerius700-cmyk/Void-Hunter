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
        """BLOQUE 58.13: 2 Parallel Snake Chains.

        2 INDEPENDENT chains on a single ParallelPathPair. Each chain:
        1 leader + 4 followers. The leader traces a sharp bezier curve
        (frequency 0.7-1.1, was 0.4-0.7), and followers copy the
        leader's recent positions (history-queue follow).
        """
        from src.movement.parallel_path import ParallelPathPair

        frequency = 0.7 + (level * 0.05)
        amplitude = 60.0 + rng.uniform(-15, 25)

        if rng.random() < 0.5:
            p0 = (-20, rng.uniform(60, INTERNAL_H * 0.4))
            p3 = (INTERNAL_W + 20, rng.uniform(INTERNAL_H * 0.6, INTERNAL_H - 60))
        else:
            p0 = (INTERNAL_W + 20, rng.uniform(60, INTERNAL_H * 0.4))
            p3 = (-20, rng.uniform(INTERNAL_H * 0.6, INTERNAL_H - 60))

        cx1 = INTERNAL_W * 0.3
        cx2 = INTERNAL_W * 0.7
        cy_center = INTERNAL_H / 2
        p1 = (cx1, cy_center - amplitude * frequency)
        p2 = (cx2, cy_center + amplitude * frequency)

        segments = [(p0, p1, p2, p3)]
        pair = ParallelPathPair(segments, [6.0], gap_px=14)
        duration_s = 6.0

        chain_count = 2
        followers_per_chain = 4
        delay_per_follower = 0.06
        inter_chain_offset = 0.04

        base_color = self._random_color(rng)
        ships: list[SpawnedShip] = []
        for chain_idx in range(chain_count):
            side = "top" if chain_idx == 0 else "bot"
            for slot in range(followers_per_chain + 1):
                t_offset = (chain_idx * inter_chain_offset
                            + slot * delay_per_follower)
                x, y = self._bezier_point(0.0, p0, p1, p2, p3)
                is_leader = (slot == 0)
                ships.append(SpawnedShip(
                    spawn_x=x,
                    spawn_y=y,
                    t_offset=t_offset,
                    slot=chain_idx * (followers_per_chain + 1) + slot,
                    color=base_color,
                    is_leader=is_leader,
                    extra={
                        "parallel_pair": pair,
                        "side": side,
                        "frequency": frequency,
                        "amplitude": amplitude,
                        "delay_per_follower": delay_per_follower,
                        "history_size": 60,
                        "duration_s": duration_s,
                    },
                ))

        return WavePatternResult(
            ships=ships,
            kind=self.kind,
            difficulty=self.difficulty,
            duration_s=duration_s,
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
