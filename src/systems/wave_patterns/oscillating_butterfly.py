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
        """BLOQUE 58.13: Orbital Breathing.

        6-8 ships distributed around an OrbitalPath. Each ship is at a
        different point on the orbit; the group looks like a swirling
        galaxy that "breathes" around the center.
        """
        from src.movement.orbital_path import OrbitalPath

        ship_count = min(8, 6 + (level - 1) // 2)
        cx = INTERNAL_W * rng.uniform(0.2, 0.8)
        cy = INTERNAL_H * rng.uniform(0.2, 0.8)
        radius_x = rng.uniform(100, 140)
        radius_y = rng.uniform(70, 100)
        duration_s = 6.0
        rotation_deg = rng.uniform(0, 360)

        orbital = OrbitalPath(
            center=(cx, cy),
            radius_x=radius_x,
            radius_y=radius_y,
            duration_s=duration_s,
            rotation_deg=rotation_deg,
        )

        base_hue = rng.random() * 360
        ships: list[SpawnedShip] = []
        for slot in range(ship_count):
            t_offset = (slot / ship_count) * duration_s
            hue = (base_hue + slot * (360 / max(1, ship_count))) % 360
            color = self._hue_to_rgb(hue, sat=0.85, val=0.95)
            is_leader = (slot == 0)
            ships.append(SpawnedShip(
                spawn_x=cx + radius_x,
                spawn_y=cy,
                t_offset=t_offset,
                slot=slot,
                color=color,
                is_leader=is_leader,
                extra={
                    "orbital": orbital,
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
