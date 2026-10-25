"""BLOQUE 72 T7: PowerupKind expanded — 4 weapon kinds replace single WEAPON.

Per spec (docs/superpowers/specs/2026-09-09-asteroid-hit-and-powerup-system-design.md)
the old `PowerupKind.WEAPON` (a no-op that bumped weapon level) is replaced
by 4 distinct weapon kinds:
  THICK  (A) — thick shot       (max ammo 100)
  LASER  (S) — continuous laser (max ammo 200)
  FLAME  (D) — flamethrower     (max ammo  50)
  DOUBLE (F) — double blue beam (max ammo 150)

The MINE-ASTEROID drop pool expands from {BOMB, HP, WEAPON} (3 kinds) to
{BOMB, HP, THICK, LASER, FLAME, DOUBLE} (6 kinds), still excluding SCORE.
"""
from __future__ import annotations

import random

from src.entities.asteroid import PowerupKind, POWERUP_WEIGHTS
from src.entities.enemies.enemy import pick_mine_powerup


def test_powerup_kind_has_4_weapons() -> None:
    """The enum exposes THICK, LASER, FLAME, DOUBLE members."""
    assert hasattr(PowerupKind, "THICK")
    assert hasattr(PowerupKind, "LASER")
    assert hasattr(PowerupKind, "FLAME")
    assert hasattr(PowerupKind, "DOUBLE")


def test_old_weapon_kind_removed() -> None:
    """BLOQUE 72 T7: the old single `WEAPON` member is gone (replaced by 4)."""
    assert not hasattr(PowerupKind, "WEAPON")


def test_powerup_weights_sum_is_100() -> None:
    """Distribution weights must sum to 100 (roguelike = weighted pick)."""
    total = sum(POWERUP_WEIGHTS.values())
    assert total == 100, f"POWERUP_WEIGHTS sum is {total}, expected 100"


def test_pick_mine_powerup_picks_from_6_kinds() -> None:
    """BOMB, HP, THICK, LASER, FLAME, DOUBLE — SCORE excluded.

    200 picks should see at least 4 distinct kinds (statistically safe for
    an equal-weight 6-pool: P(only 3 kinds in 200 picks) ≈ 1e-25).
    """
    rng = random.Random(0xA57E2012)
    seen: set[PowerupKind] = set()
    for _ in range(200):
        seen.add(pick_mine_powerup(rng))
    # Pool must be a subset of the 6 expected kinds (SCORE excluded).
    expected_pool = {
        PowerupKind.BOMB,
        PowerupKind.HP,
        PowerupKind.THICK,
        PowerupKind.LASER,
        PowerupKind.FLAME,
        PowerupKind.DOUBLE,
    }
    assert seen.issubset(expected_pool), (
        f"pick_mine_powerup returned kinds outside the 6-kind pool: "
        f"{seen - expected_pool}"
    )
    assert len(seen) >= 4, (
        f"only {len(seen)} distinct kinds in 200 picks (expected >= 4): {seen}"
    )
