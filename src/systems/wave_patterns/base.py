"""BLOQUE 58.8: Base class for procedural wave patterns.

A WavePattern is a deterministic recipe for spawning a group of enemies
given a seeded RNG and a difficulty level. Each pattern produces a list
of SpawnedShip records that the runtime converts to Enemy objects.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

import math
import random

from src.core.settings import INTERNAL_W, INTERNAL_H


class WavePatternKind(Enum):
    """5 patterns inspired by Star Fox 64 wave variety."""
    BEZIER_SWEEP = "bezier_sweep"           # curve sweep, all ships
    V_FORMATION = "v_formation"             # rigid V, fixed offsets
    LEADER_FOLLOWER_CHAIN = "leader_chain"  # leader + history queue
    DICE_FIVE_GRID = "dice_five_grid"       # 5 ships in dice-5
    PINCER_CROSS = "pincer_cross"           # two mirror bezier curves


class PatternDifficulty(Enum):
    """Difficulty tier of a pattern (used by manager for curve)."""
    EASY = auto()       # 1-2: V_FORMATION, DICE_FIVE_GRID
    MEDIUM = auto()     # 3-4: LEADER_FOLLOWER_CHAIN, BEZIER_SWEEP
    HARD = auto()       # 5+:  PINCER_CROSS, mixed


@dataclass(frozen=True)
class SpawnedShip:
    """A single ship to spawn from a pattern.

    `spawn_x, spawn_y` is the initial position.
    `t_offset` is the time offset (seconds) so leader/sweep stagger works.
    `slot` is the formation slot index (for V_FORMATION / DICE_FIVE_GRID).
    `color` is optional RGB tint for the engine trail / sprite.
    `is_leader` is True for the ship that leads the formation. BLOQUE 58.10:
    the runtime uses this to draw a glow ring around the leader so the
    player can tell which ship is "the first one".
    `extra` carries pattern-specific data (bezier control points, etc).
    """
    spawn_x: float
    spawn_y: float
    t_offset: float = 0.0
    slot: int = 0
    color: Optional[tuple[int, int, int]] = None
    is_leader: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class WavePatternResult:
    """The output of a pattern's `generate()` call."""
    ships: list[SpawnedShip]
    kind: WavePatternKind
    difficulty: PatternDifficulty
    duration_s: float            # how long this wave should run
    seed_used: int               # for replay determinism


class WavePattern(ABC):
    """Abstract base for all 5 patterns.

    Subclasses implement `generate(rng, level)` to produce a list of
    SpawnedShip records. The manager is responsible for converting these
    to actual Enemy instances and attaching the right paths.
    """
    kind: WavePatternKind
    difficulty: PatternDifficulty

    @abstractmethod
    def generate(
        self,
        rng: random.Random,
        level: int,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        """Return the list of ships + duration for this wave."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers (subclasses can use these)
    # ------------------------------------------------------------------
    @staticmethod
    def _clamp_x(x: float, margin: float = 16.0) -> float:
        return max(margin, min(INTERNAL_W - margin, x))

    @staticmethod
    def _clamp_y(y: float, margin: float = 8.0) -> float:
        return max(margin, min(INTERNAL_H - margin, y))

    @staticmethod
    def _playfield_center() -> tuple[float, float]:
        return (INTERNAL_W / 2.0, INTERNAL_H / 2.0)

    @staticmethod
    def _random_color(rng: random.Random) -> tuple[int, int, int]:
        """Random bright color (R, G, B) biased toward saturated values."""
        h = rng.random() * 360
        s = 0.7 + rng.random() * 0.3
        v = 0.85 + rng.random() * 0.15
        return _hsv_to_rgb(h, s, v)


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """h in [0,360), s,v in [0,1]. Standard HSV to RGB."""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        rp, gp, bp = c, x, 0
    elif h < 120:
        rp, gp, bp = x, c, 0
    elif h < 180:
        rp, gp, bp = 0, c, x
    elif h < 240:
        rp, gp, bp = 0, x, c
    elif h < 300:
        rp, gp, bp = x, 0, c
    else:
        rp, gp, bp = c, 0, x
    return (int((rp + m) * 255), int((gp + m) * 255), int((bp + m) * 255))
