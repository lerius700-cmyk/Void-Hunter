"""Roguelike core for void-hunter (BLOQUE 57).

Provides deterministic seed strategy, seedable RNG, procedural formation
generation, run lifecycle, anti-stuck detection, distribution telemetry,
and replay. The module is self-contained and opt-in: existing 18-wave
JSON setup continues to work as default. Activate procedural mode via
`--roguelike [seed]` on the CLI.

Industry references (BLOQUE 57 design):
  - Slay the Spire: seed = charSelect + ascension + floor
  - Hades: seed = boon_rng_state (weighted)
  - Enter the Gungeon: master_seed + offset
  - Spelunky: level_seed (full procedural)
  - Dead Cells: biomes fixed, scrolls random

Hard rules:
  - No numpy / scipy (per GDD section 0)
  - No `import random` global (all RNG goes through SeededRNG)
  - splitmix64 PRNG (period 2^64, no attractor at 0)
"""
from __future__ import annotations

from src.roguelike.seed import RoguelikeSeed
from src.roguelike.rng import SeededRNG
from src.roguelike.formation_generator import (
    FormationFamily,
    FormationParams,
    ProceduralFormationGenerator,
)
from src.roguelike.run import RoguelikeRun
from src.roguelike.anti_stuck import StuckPatternDetector
from src.roguelike.telemetry import DistributionTelemetry
from src.roguelike.replay import ReplaySystem, ReplayDivergenceError

__all__ = [
    "FormationFamily",
    "FormationParams",
    "ProceduralFormationGenerator",
    "ReplayDivergenceError",
    "ReplaySystem",
    "RoguelikeRun",
    "RoguelikeSeed",
    "SeededRNG",
    "StuckPatternDetector",
    "DistributionTelemetry",
]
