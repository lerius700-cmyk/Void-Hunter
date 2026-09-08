"""The 8 ships to redesign (BLOQUE 59).

3 enemy templates (light/medium/heavy) covering 7 enemy types as variants,
plus 1 player ship (ship_01 redesign).

Each entry has:
  key: filesystem-safe identifier (used in paths)
  template: "light" | "medium" | "heavy" | "player"
  display_name: human-readable name
  prompt_fill: text appended to the standard prompt template
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShipSpec:
    key: str
    template: str
    display_name: str
    prompt_fill: str


SHIPS: tuple[ShipSpec, ...] = (
    # Light template (cyan/electric blue, small, pointy)
    ShipSpec(
        key="enemy_scout",
        template="light",
        display_name="Scout (light)",
        prompt_fill="small fast scout ship, narrow pointy wings, single thruster, compact triangular silhouette, cyan and electric blue color scheme",
    ),
    ShipSpec(
        key="enemy_drone",
        template="light",
        display_name="Drone (light)",
        prompt_fill="small boxy drone, four small thrusters in a square pattern, compact rectangular silhouette, cyan and electric blue color scheme",
    ),
    ShipSpec(
        key="enemy_kamikaze",
        template="light",
        display_name="Kamikaze (light)",
        prompt_fill="small triangular ship with central glowing core, sharp pointed nose, compact arrowhead silhouette, cyan and electric blue color scheme",
    ),
    # Medium template (navy blue/void, balanced)
    ShipSpec(
        key="enemy_sniper",
        template="medium",
        display_name="Sniper (medium)",
        prompt_fill="balanced fighter, medium swept-back wings, focused forward weapon hardpoint, mid-sized diamond silhouette, navy blue and dark void color scheme",
    ),
    ShipSpec(
        key="enemy_turret",
        template="medium",
        display_name="Turret (medium)",
        prompt_fill="round turret-style ship, omnidirectional weapon mount visible on top, mid-sized hexagonal silhouette, navy blue and dark void color scheme",
    ),
    # Heavy template (red/mars, large, armored)
    ShipSpec(
        key="enemy_heavy",
        template="heavy",
        display_name="Heavy (heavy)",
        prompt_fill="large armored warship, blocky angular hull, multiple turrets across the upper deck, thick armor plates, large imposing silhouette, red and mars orange color scheme",
    ),
    ShipSpec(
        key="enemy_cruiser",
        template="heavy",
        display_name="Cruiser (heavy)",
        prompt_fill="long elongated armored cruiser, multiple turrets along the upper hull spine, segmented armor sections, large elongated silhouette, red and mars orange color scheme",
    ),
    # Player ship (white + gold + red, hero)
    ShipSpec(
        key="player",
        template="player",
        display_name="Player ship (ship_01 redesign)",
        prompt_fill="hero ship, sleek aggressive silhouette, prominent cockpit, gold accents, white hull with gold highlights and red engine tips, heroic with more detail",
    ),
)


def ship_by_key(key: str) -> ShipSpec:
    for s in SHIPS:
        if s.key == key:
            return s
    raise KeyError(f"unknown ship key: {key!r}")
