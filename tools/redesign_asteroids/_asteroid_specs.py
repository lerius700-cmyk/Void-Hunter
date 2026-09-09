"""The 5 asteroid variants to generate (BLOQUE 61).

All variants are MINE-ASTEROID closed lookalikes — brown rocky body with
Greek-key stripe band and 1-3 craters, only the silhouette differs.
The `round` variant is the canonical MINE-ASTEROID and will be reused as
the closed sprite for BLOQUE 63's MINE-ASTEROID enemy.

Each entry has:
  key: filesystem-safe identifier (used in paths)
  display_name: human-readable name
  prompt_fill: text appended to the standard prompt template
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AsteroidSpec:
    key: str
    display_name: str
    prompt_fill: str


ASTEROIDS: tuple[AsteroidSpec, ...] = (
    AsteroidSpec(
        key="round",
        display_name="Round (canonical MINE-ASTEROID closed)",
        prompt_fill=(
            "ROUND variant — squat potato shape, low eccentricity, lots of "
            "craters, the canonical MINE-ASTEROID closed state"
        ),
    ),
    AsteroidSpec(
        key="elongated",
        display_name="Elongated (horizontal stretched)",
        prompt_fill=(
            "ELONGATED variant — horizontal stretched, like a loaf of bread, "
            "single big Greek-key band"
        ),
    ),
    AsteroidSpec(
        key="spiked",
        display_name="Spiked (mineral protrusions)",
        prompt_fill=(
            "SPIKED variant — 3-4 sharp mineral protrusions sticking out, "
            "angular crystalline silhouette"
        ),
    ),
    AsteroidSpec(
        key="hollowed",
        display_name="Hollowed (big crater on one side)",
        prompt_fill=(
            "HOLLOWED variant — one big crater on one side, hint of "
            "MINE-ASTEROID open state without the ship"
        ),
    ),
    AsteroidSpec(
        key="cracked",
        display_name="Cracked (diagonal surface crack)",
        prompt_fill=(
            "CRACKED variant — one diagonal surface crack running across "
            "the body, surface damage"
        ),
    ),
)


def asteroid_by_key(key: str) -> AsteroidSpec:
    for a in ASTEROIDS:
        if a.key == key:
            return a
    raise KeyError(f"unknown asteroid key: {key!r}")
