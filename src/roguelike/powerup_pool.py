"""Powerup pool (BLOQUE 58).

Picks a powerup by seed from a weighted pool. Used between waves
to give the player a random reward.

Pool:
  - gold_ring (50%): +2 HP, 3-stack = HP double
  - heal_small (20%): +5 HP instant
  - bomb (15%): +1 bomb
  - damage_boost (10%): +10% damage for 30s (not implemented in-game yet)
  - nothing (5%): no powerup this wave

BLOQUE 58 invariant: powerups are RANDOM, but the drop chance and pool
are fixed (not affected by player skill or run state).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.roguelike.rng import SeededRNG


class PowerupKind(str, Enum):
    """Available powerup types in the roguelike pool."""
    GOLD_RING = "gold_ring"
    HEAL_SMALL = "heal_small"
    BOMB = "bomb"
    DAMAGE_BOOST = "damage_boost"
    NOTHING = "nothing"


# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS: dict[PowerupKind, float] = {
    PowerupKind.GOLD_RING: 0.50,
    PowerupKind.HEAL_SMALL: 0.20,
    PowerupKind.BOMB: 0.15,
    PowerupKind.DAMAGE_BOOST: 0.10,
    PowerupKind.NOTHING: 0.05,
}


@dataclass(frozen=True)
class PowerupDrop:
    """Result of powerup pool sampling."""
    kind: PowerupKind
    seed: int  # sub-seed for the powerup's internal randomness


def select_powerup(seed: int, weights: dict[PowerupKind, float] | None = None) -> PowerupDrop:
    """Pick a powerup by seed from the weighted pool.

    Args:
        seed: 64-bit sub-seed (e.g., `seed.derive_drop_seed()`)
        weights: Optional custom weights. Defaults to DEFAULT_WEIGHTS.
    """
    rng = SeededRNG(seed=seed)
    pool = weights if weights is not None else DEFAULT_WEIGHTS
    kinds = list(pool.keys())
    w = list(pool.values())
    chosen = rng.choices(kinds, w)
    return PowerupDrop(kind=chosen, seed=seed)
