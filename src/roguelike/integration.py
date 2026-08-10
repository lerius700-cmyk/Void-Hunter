"""Roguelike integration hooks (BLOQUE 57).

Connects the roguelike core to the existing game systems WITHOUT
modifying them. The hooks are opt-in: a CLI flag (--roguelike [seed])
enables procedural wave generation; without the flag, the existing
18-wave JSON setup is used unchanged.

API:
    is_roguelike_enabled() -> bool
    get_active_seed() -> int | None
    enable_roguelike(seed: int) -> None
    disable_roguelike() -> None
    generate_procedural_waves(level_idx, num_waves=6) -> list[dict]
"""
from __future__ import annotations

import os
from typing import Any

from src.roguelike.formation_generator import (
    FormationFamily,
    FormationParams,
    ProceduralFormationGenerator,
)
from src.roguelike.seed import RoguelikeSeed


# Module-level state. Initialized once on import.
_active_seed: int | None = None
_enabled: bool = False


def is_roguelike_enabled() -> bool:
    """True if --roguelike was passed on the CLI."""
    return _enabled


def get_active_seed() -> int | None:
    """The current run's master seed, or None if not in roguelike mode."""
    return _active_seed


def enable_roguelike(seed: int | None = None, salt: int = 0) -> int:
    """Enable procedural mode. Returns the seed used.

    If `seed` is None, derives one from level+attempt+salt.
    """
    global _active_seed, _enabled
    if seed is None:
        derived = RoguelikeSeed.derive(level_idx=1, attempt_number=1, salt=salt)
        seed = derived.master
    _active_seed = seed
    _enabled = True
    return seed


def disable_roguelike() -> None:
    """Disable procedural mode. Restores the default JSON-wave behavior."""
    global _active_seed, _enabled
    _active_seed = None
    _enabled = False


def generate_procedural_waves(
    level_idx: int,
    num_waves: int = 6,
    *,
    salt: int = 0,
) -> list[dict[str, Any]]:
    """Generate N waves procedurally for the given level.

    Each wave is a dict matching the WaveManager script format:
      {
        "act": int, "wave": int, "theme": str,
        "formation": {
          "formation_type": str, "enemy_type": str,
          "count": int, "spacing_px": int, "entry_axis": str,
          "pattern_speed": float, "telegraph_frames": int,
        },
        "kill_target": int, "time_limit_s": float, "sub_boss": None,
      }

    `family_weights` default to balanced: line/v/arc dominate,
    specialty families (spiral, hilera, x, diamond, box) are rare.
    """
    seed = enable_roguelike(salt=salt) if _active_seed is None else _active_seed
    gen = ProceduralFormationGenerator(seed=seed)
    waves: list[dict[str, Any]] = []
    # Default family weights: 5 main families get more, specialty less.
    families = list(FormationFamily)
    weights = [
        0.20,  # LINE
        0.18,  # V
        0.18,  # ARC
        0.14,  # STAIRCASE
        0.10,  # SPIRAL
        0.08,  # HILERA
        0.06,  # X
        0.04,  # DIAMOND
        0.02,  # BOX
    ]
    # Enemy types cycle through SCOUT/CRUISER/HEAVY/SNIPER for variety.
    enemy_types = ["SCOUT", "CRUISER", "HEAVY", "SCOUT", "SNIPER", "SCOUT"]
    for wave_i in range(num_waves):
        params = FormationParams(
            count=gen.rng.randint(5, 8),
            spacing_min=24,
            spacing_max=32,
            families=families,
            family_weights=weights,
        )
        # The generator's RNG state advances on every gen_formation call.
        formation_type = gen.rng.choices(families, weights)
        enemy_type = enemy_types[wave_i % len(enemy_types)]
        # Build the formation dict from the chosen family + sampled params
        waves.append({
            "act": level_idx,
            "wave": wave_i + 1,
            "theme": "roguelike_void",
            "formation": {
                "formation_type": formation_type.value,
                "enemy_type": enemy_type,
                "count": params.count,
                "spacing_px": gen.rng.randint(params.spacing_min, params.spacing_max),
                "entry_axis": "top",
                "pattern_speed": float(gen.rng.randint(30, 50)),
                "telegraph_frames": int(gen.rng.randint(25, 50)),
            },
            "kill_target": params.count,
            "time_limit_s": 30.0,
            "sub_boss": None,
        })
    return waves


def inject_roguelike_waves(wave_manager: Any) -> bool:
    """Inject procedurally generated waves into a WaveManager instance.

    The WaveManager is expected to expose a `scripts` list attribute
    that we can replace. If the integration is not enabled, returns
    False and does nothing.

    Returns True if waves were injected, False otherwise.
    """
    if not _enabled or _active_seed is None:
        return False
    new_scripts = generate_procedural_waves(level_idx=1, num_waves=6)
    if hasattr(wave_manager, "scripts"):
        wave_manager.scripts = new_scripts
        return True
    return False
