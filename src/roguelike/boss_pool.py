"""Boss pool (BLOQUE 58).

Selects one of 4 bosses (GOLIATH, HYDRA, PHANTOM, NEMESIS) by seed.
Each boss gets a procedural bezier entrance path (control points derived
from the seed). The pool respects level bias: Act 1 prefers GOLIATH,
Act 2 prefers HYDRA, etc., but any of the 4 can appear in any level.

BLOQUE 58 invariant: the final boss appears at the END of the level
(fixed position). Only the IDENTITY of the boss and its entrance path
are randomized.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.entities.enemies.boss import BossId
from src.systems.bezier_path import BezierPath, ControlPoint
from src.roguelike.rng import SeededRNG


# Level bias: each level has a weight distribution over the 4 bosses.
# Act 1 = GOLIATH-heavy, Act 2 = HYDRA-heavy, etc. — but the OTHER
# bosses can still appear (the pool is "any of 4 can come out").
LEVEL_BIAS: dict[int, dict[BossId, float]] = {
    1: {BossId.GOLIATH: 0.55, BossId.HYDRA: 0.30, BossId.PHANTOM: 0.10, BossId.NEMESIS: 0.05},
    2: {BossId.GOLIATH: 0.20, BossId.HYDRA: 0.45, BossId.PHANTOM: 0.25, BossId.NEMESIS: 0.10},
    3: {BossId.GOLIATH: 0.10, BossId.HYDRA: 0.20, BossId.PHANTOM: 0.40, BossId.NEMESIS: 0.30},
}


@dataclass(frozen=True)
class BossSelection:
    """Result of boss pool sampling: identity + procedural entrance path."""
    boss_id: BossId
    bezier_path: BezierPath
    entrance_speed: float  # px/s along the curve


def select_boss(seed: int, level_idx: int) -> BossSelection:
    """Pick a boss by seed with level bias, generate a procedural entrance.

    Args:
        seed: 64-bit master seed for this level
        level_idx: 1, 2, 3 (or higher). Determines bias weights.

    Returns:
        BossSelection with the chosen BossId and a procedural BezierPath.
    """
    rng = SeededRNG(seed=seed)
    # Pick from biased pool
    bias = LEVEL_BIAS.get(level_idx, LEVEL_BIAS[3])  # default to act-3
    boss_ids = list(bias.keys())
    weights = list(bias.values())
    chosen = rng.choices(boss_ids, weights)
    # Generate procedural bezier entrance (4 control points, dramatic S-curve)
    start_x = 160.0 + (rng.random() - 0.5) * 100.0  # slight horizontal jitter
    start_y = -40.0
    # Anchor: each boss has a different y position
    anchor_y = {BossId.GOLIATH: 80.0, BossId.HYDRA: 70.0, BossId.PHANTOM: 80.0, BossId.NEMESIS: 60.0}.get(
        chosen, 80.0
    )
    # Two control points create an S-curve that swings in from one side
    cp1_x = rng.random() * 320.0  # anywhere across the playfield
    cp1_y = rng.random() * 40.0 + 20.0  # top quadrant
    cp2_x = (320.0 - cp1_x) if rng.random() < 0.5 else cp1_x
    cp2_y = rng.random() * 30.0 + 40.0  # middle
    path = BezierPath([
        ControlPoint(start_x, start_y),
        ControlPoint(cp1_x, cp1_y),
        ControlPoint(cp2_x, cp2_y),
        ControlPoint(160.0, anchor_y),
    ])
    path.prebake(steps=60)
    # Entrance speed scales with boss difficulty
    entrance_speed = {
        BossId.GOLIATH: 50.0,
        BossId.HYDRA: 55.0,
        BossId.PHANTOM: 60.0,
        BossId.NEMESIS: 65.0,
    }.get(chosen, 50.0)
    return BossSelection(boss_id=chosen, bezier_path=path, entrance_speed=entrance_speed)
