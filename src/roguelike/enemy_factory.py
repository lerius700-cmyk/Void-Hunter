"""BLOQUE 58.8: Procedural enemy variety by seed.

The roguelike picks enemy params procedurally from the seed so each
run has slightly different enemies. This adds variety without changing
the core enemy archetypes.

Variations per enemy (driven by RNG):
  - speed: ±25%
  - hp:   ±20%
  - fire_rate: ±30%
  - color tint: HSL hue shift ±30 degrees
  - weapon: 70% default, 15% shotgun, 10% burst, 5% sniper

This is applied per-ship during pattern spawn, so a BEZIER_SWEEP can
have 5 different ship variants even within the same wave.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


# Base enemy archetypes (5 of the 8 from the entity system).
# The remaining 3 (KAMIKAZE, SNIPER, TURRET) are reserved for special
# spawns and not in the procedural pool.
BASE_ARCHETYPES = ["SCOUT", "CRUISER", "HEAVY", "DRONE", "CARRIER"]


@dataclass(frozen=True)
class ProceduralEnemy:
    """The output of the enemy factory.

    `kind` is the base archetype (SCOUT, CRUISER, etc).
    `speed_mult` is the speed multiplier (1.0 = normal).
    `hp_mult` is the HP multiplier.
    `fire_rate_mult` is the fire rate multiplier.
    `color_tint` is the HSL hue shift in degrees (positive).
    `weapon_variant` is one of: "default", "shotgun", "burst", "sniper".
    """
    kind: str
    speed_mult: float = 1.0
    hp_mult: float = 1.0
    fire_rate_mult: float = 1.0
    color_tint: float = 0.0
    weapon_variant: str = "default"


def make_procedural_enemy(
    rng: random.Random,
    base_kind: str = "SCOUT",
    level: int = 1,
) -> ProceduralEnemy:
    """Generate a procedural enemy variant.

    The base_kind is one of BASE_ARCHETYPES. The variations are
    driven by the RNG, so given the same seed + level + base_kind,
    the result is deterministic.

    Args:
        rng: seeded random.Random instance
        base_kind: archetype to base from (SCOUT, CRUISER, etc)
        level: floor/level number (1+). Higher = more variance.

    Returns:
        ProceduralEnemy with variations applied
    """
    if base_kind not in BASE_ARCHETYPES:
        base_kind = "SCOUT"

    # Variance scales with level (capped at level 6)
    variance = min(level, 6) / 6.0   # 0.17 to 1.0

    # Speed: ±25% at full variance
    speed_mult = 1.0 + (rng.uniform(-0.25, 0.25) * variance)
    # HP: ±20%
    hp_mult = 1.0 + (rng.uniform(-0.20, 0.20) * variance)
    # Fire rate: ±30%
    fire_rate_mult = 1.0 + (rng.uniform(-0.30, 0.30) * variance)
    # Color tint: HSL hue shift ±30 degrees
    color_tint = rng.uniform(-30.0, 30.0) * variance

    # Weapon variant (weighted)
    roll = rng.random()
    if roll < 0.70:
        weapon_variant = "default"
    elif roll < 0.85:
        weapon_variant = "shotgun"
    elif roll < 0.95:
        weapon_variant = "burst"
    else:
        weapon_variant = "sniper"

    return ProceduralEnemy(
        kind=base_kind,
        speed_mult=speed_mult,
        hp_mult=hp_mult,
        fire_rate_mult=fire_rate_mult,
        color_tint=color_tint,
        weapon_variant=weapon_variant,
    )


def make_enemy_mix(
    rng: random.Random,
    count: int,
    level: int = 1,
) -> list[ProceduralEnemy]:
    """Generate a list of procedural enemies (e.g., for a pattern's group).

    Distribution: more SCOUT/CRUISER at low levels, more HEAVY/DRONE
    at high levels.

    Args:
        rng: seeded random
        count: how many enemies to generate
        level: difficulty level (1+)

    Returns:
        List of ProceduralEnemy
    """
    # Weighted distribution
    if level <= 2:
        weights = [0.6, 0.2, 0.05, 0.1, 0.05]  # SCOUT-heavy
    elif level <= 4:
        weights = [0.4, 0.3, 0.1, 0.15, 0.05]  # mixed
    else:
        weights = [0.25, 0.3, 0.2, 0.15, 0.1]   # balanced

    enemies: list[ProceduralEnemy] = []
    for _ in range(count):
        base = rng.choices(BASE_ARCHETYPES, weights=weights, k=1)[0]
        enemies.append(make_procedural_enemy(rng, base, level))
    return enemies
