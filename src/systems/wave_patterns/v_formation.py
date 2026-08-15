"""BLOQUE 58.8: V_FORMATION wave pattern.

A rigid V formation (Star Fox 64 leader + wings). 5-9 ships total.
All ships move in a straight line at the same speed. The V offsets
are fixed (leader at front, wings trailing back at increasing angles).

Visual: classic bomber formation. Easy to read, predictable path.
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


class VFormationPattern(WavePattern):
    """Rigid V formation, fixed offsets, straight-line motion."""
    kind = WavePatternKind.V_FORMATION
    difficulty = PatternDifficulty.EASY

    def generate(
        self,
        rng: random.Random,
        level: int,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        # Ship count: 5-9 (always odd for symmetric V)
        ship_count = min(9, max(5, 5 + (level // 4) * 2))
        if ship_count % 2 == 0:
            ship_count += 1

        # Choose entry side
        entry_x = rng.uniform(40, INTERNAL_W - 40)
        entry_y = -20.0
        # Direction: 1 (left-to-right) or -1 (right-to-left)
        direction = rng.choice((-1, 1))

        # V spacing: leader in front, wings trail at 22px back, 16px out.
        # BLOQUE 58.11: wings now have a slight curve (each wing's y
        # offset is multiplied by a small slope factor so the V bends
        # gracefully as it moves, like a flying goose flock).
        wing_dx = 16.0 * direction
        wing_dy = 22.0
        # Curve: outer wings have extra dx to bend the V (graceful sweep)
        curve_factor = 0.15  # 0.0 = rigid V, 0.3 = strong curve

        # Build offsets: leader at (0,0), then alternating L/R
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for i in range(1, ship_count):
            side = 1 if i % 2 == 1 else -1
            magnitude = (i + 1) // 2  # 1, 1, 2, 2, 3, 3, ...
            # Add curve: outer wings sweep further out as they trail back
            curve_dx = side * wing_dx * magnitude * (1.0 + curve_factor * magnitude)
            offsets.append((curve_dx, wing_dy * magnitude))

        # Color: leader is bright, wings get progressively dimmer
        base_hue = rng.random() * 360
        ships: list[SpawnedShip] = []
        for slot, (ox, oy) in enumerate(offsets):
            ships.append(SpawnedShip(
                spawn_x=entry_x + ox,
                spawn_y=entry_y + oy,
                t_offset=0.0,           # V moves together, no stagger
                slot=slot,
                color=self._wing_color(base_hue, slot, ship_count),
                is_leader=(slot == 0),  # BLOQUE 58.10: leader glow ring
                extra={
                    "entry_x": entry_x,
                    "entry_y": entry_y,
                    "direction": direction,
                    "wing_offsets": offsets,
                    "duration_s": 5.0 + rng.uniform(0, 0.5),
                    "formation_id": rng.randint(0, 999_999),
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
    def _wing_color(base_hue: float, slot: int, total: int) -> tuple[int, int, int]:
        """Leader bright, wings dimmer."""
        # Convert hue to RGB
        h = base_hue / 60.0
        s = 0.9
        # Brightness drops with slot (away from leader)
        v = 0.95 - (slot / max(1, total - 1)) * 0.4
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
