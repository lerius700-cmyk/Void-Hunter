"""Level generator (BLOQUE 58).

Generates a complete level structure for the roguelike:
  - 4 chained waves
  - sub-boss trigger after wave 2 (FIXED position)
  - final boss at the end (FIXED position)
  - boss identity randomized from pool of 4
  - boss entrance via procedural bezier path

Invariants (per user requirement):
  - Number of ships per wave is FIXED (not random)
  - Sub-boss appears at FIXED position (after wave 2)
  - Final boss appears at FIXED position (end of level)

What IS randomized per seed:
  - Formation type for each wave (11 families)
  - Bezier path for boss entrance
  - Boss identity (any of 4, with level bias)
  - Powerup drops between waves
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.roguelike.boss_pool import BossSelection, select_boss
from src.roguelike.formation_generator import (
    FormationFamily,
    FormationParams,
    ProceduralFormationGenerator,
)
from src.roguelike.powerup_pool import PowerupDrop, PowerupKind, select_powerup
from src.roguelike.rng import SeededRNG
from src.roguelike.seed import RoguelikeSeed


# BLOQUE 58 INVARIANTS: ship counts are FIXED per level (shmup balance).
# The same level always has the same number of enemies per wave.
LEVEL_SHIP_COUNTS: dict[int, list[int]] = {
    # level: [wave_1_count, wave_2_count, wave_3_count, wave_4_count]
    1: [12, 19, 14, 17],   # 62 total (BLOQUE 50)
    2: [15, 22, 18, 20],   # 75 total
    3: [18, 25, 22, 24],   # 89 total
}

# Enemy type cycle per level (4 waves, 4 enemy types, balanced)
LEVEL_ENEMY_TYPES: dict[int, list[str]] = {
    1: ["SCOUT", "CRUISER", "SCOUT", "HEAVY"],
    2: ["CRUISER", "HEAVY", "SCOUT", "SNIPER"],
    3: ["HEAVY", "SNIPER", "CRUISER", "DRONE"],
}

# Formation family weights per level (more specialty formations in later levels)
LEVEL_FORMATION_WEIGHTS: dict[int, list[float]] = {
    1: [0.30, 0.25, 0.20, 0.15, 0.05, 0.03, 0.01, 0.005, 0.005],  # basic-heavy
    2: [0.22, 0.20, 0.18, 0.15, 0.10, 0.08, 0.04, 0.02, 0.01],    # mixed
    3: [0.15, 0.15, 0.15, 0.15, 0.15, 0.10, 0.07, 0.05, 0.03],    # all-equal
}

# Speed range per level (slightly faster in later levels)
LEVEL_SPEED_RANGE: dict[int, tuple[int, int]] = {
    1: (30, 45),
    2: (35, 55),
    3: (45, 70),
}

# Telegraph time per level (slightly less in later levels = harder)
LEVEL_TELEGRAPH_RANGE: dict[int, tuple[int, int]] = {
    1: (35, 50),
    2: (30, 45),
    3: (25, 40),
}


class LevelEventKind(str, Enum):
    """Markers between wave segments."""
    WAVE = "wave"
    SUB_BOSS = "sub_boss"
    FINAL_BOSS = "final_boss"
    POWERUP_DROP = "powerup_drop"


@dataclass
class LevelEvent:
    """A single event in the level timeline (in execution order)."""
    kind: LevelEventKind
    # WAVE-specific
    wave_idx: int | None = None
    formation: dict[str, Any] | None = None
    # BOSS-specific
    boss_selection: BossSelection | None = None
    # POWERUP-specific
    powerup: PowerupDrop | None = None


@dataclass
class ProceduralLevel:
    """A complete procedurally generated level."""
    level_idx: int
    seed: int
    events: list[LevelEvent] = field(default_factory=list)

    def waves(self) -> list[LevelEvent]:
        return [e for e in self.events if e.kind == LevelEventKind.WAVE]

    def sub_boss(self) -> LevelEvent | None:
        for e in self.events:
            if e.kind == LevelEventKind.SUB_BOSS:
                return e
        return None

    def final_boss(self) -> LevelEvent | None:
        for e in self.events:
            if e.kind == LevelEventKind.FINAL_BOSS:
                return e
        return None

    def powerup_drops(self) -> list[LevelEvent]:
        return [e for e in self.events if e.kind == LevelEventKind.POWERUP_DROP]


def generate_procedural_level(
    level_idx: int,
    seed: int | None = None,
    *,
    num_waves: int = 4,
    include_sub_boss: bool = True,
) -> ProceduralLevel:
    """Generate a complete procedural level.

    Structure (BLOQUE 58 invariants):
      Wave 1 -> (powerup) -> Wave 2 -> SUB_BOSS -> Wave 3 -> (powerup)
      -> Wave 4 -> (powerup) -> FINAL_BOSS

    Args:
        level_idx: 1, 2, 3 (controls ship counts, enemy types, weights)
        seed: master seed (None = derive from level+attempt=1+salt=0)
        num_waves: number of chained waves before final boss (default 4)
        include_sub_boss: if True, sub-boss appears after wave 2
    """
    if seed is None:
        seed = RoguelikeSeed.derive(level_idx, 1, 0).master
    seed_obj = RoguelikeSeed(master=seed)
    gen = ProceduralFormationGenerator(seed=seed)
    ship_counts = LEVEL_SHIP_COUNTS[level_idx]
    enemy_types = LEVEL_ENEMY_TYPES[level_idx]
    fam_weights = LEVEL_FORMATION_WEIGHTS[level_idx]
    families = list(FormationFamily)
    speed_min, speed_max = LEVEL_SPEED_RANGE[level_idx]
    tele_min, tele_max = LEVEL_TELEGRAPH_RANGE[level_idx]

    level = ProceduralLevel(level_idx=level_idx, seed=seed)
    # 4 chained waves
    for wave_i in range(num_waves):
        # Formation type from the family pool (weighted)
        ftype = gen.rng.choices(families, fam_weights)
        # Count from FIXED table
        count = ship_counts[wave_i]
        # Spacing from RNG (procedural)
        spacing = gen.rng.randint(24, 32)
        # Speed and telegraph from RNG within level range
        speed = float(gen.rng.randint(speed_min, speed_max))
        telegraph = int(gen.rng.randint(tele_min, tele_max))
        # Enemy type from FIXED cycle
        enemy_type = enemy_types[wave_i % len(enemy_types)]
        formation = {
            "formation_type": ftype.value,
            "enemy_type": enemy_type,
            "count": count,
            "spacing_px": spacing,
            "entry_axis": "top",
            "pattern_speed": speed,
            "telegraph_frames": telegraph,
        }
        level.events.append(LevelEvent(
            kind=LevelEventKind.WAVE,
            wave_idx=wave_i,
            formation=formation,
        ))
        # Powerup drop after every wave except the last
        if wave_i < num_waves - 1:
            drop_seed = seed_obj.derive_slot_seed(wave_i, 999)  # 999 = drop slot
            level.events.append(LevelEvent(
                kind=LevelEventKind.POWERUP_DROP,
                powerup=select_powerup(seed=drop_seed),
            ))
        # Sub-boss after wave 2 (FIXED position, per user requirement)
        if wave_i == 1 and include_sub_boss:
            level.events.append(LevelEvent(
                kind=LevelEventKind.SUB_BOSS,
                boss_selection=select_boss(
                    seed=seed_obj.derive_wave_seed(wave_i),
                    level_idx=level_idx,
                ),
            ))
    # Final boss at the end (FIXED position)
    final_boss_seed = seed_obj.derive_wave_seed(num_waves)
    level.events.append(LevelEvent(
        kind=LevelEventKind.FINAL_BOSS,
        boss_selection=select_boss(
            seed=final_boss_seed,
            level_idx=level_idx,
        ),
    ))
    return level
