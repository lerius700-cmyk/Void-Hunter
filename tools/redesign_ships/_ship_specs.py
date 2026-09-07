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
        prompt_fill="small fast scout ship, narrow pointy wings, single thruster, compact ~20x14 pixels equivalent, cyan and electric blue color scheme",
    ),
    ShipSpec(
        key="enemy_drone",
        template="light",
        display_name="Drone (light)",
        prompt_fill="small boxy drone, four small thrusters, compact ~20x14 pixels equivalent, cyan and electric blue color scheme",
    ),
    ShipSpec(
        key="enemy_kamikaze",
        template="light",
        display_name="Kamikaze (light)",
        prompt_fill="small triangular ship with central glowing core, pointed nose, compact ~20x14 pixels equivalent, cyan and electric blue color scheme",
    ),
    # Medium template (navy blue/void, balanced)
    ShipSpec(
        key="enemy_sniper",
        template="medium",
        display_name="Sniper (medium)",
        prompt_fill="balanced fighter, medium wings, focused weapon hardpoint, mid-sized ~24x18 pixels equivalent, navy blue and dark void color scheme",
    ),
    ShipSpec(
        key="enemy_turret",
        template="medium",
        display_name="Turret (medium)",
        prompt_fill="round turret-style ship, omnidirectional weapon mount, mid-sized ~24x18 pixels equivalent, navy blue and dark void color scheme",
    ),
    # Heavy template (red/mars, large, armored)
    ShipSpec(
        key="enemy_heavy",
        template="heavy",
        display_name="Heavy (heavy)",
        prompt_fill="large armored ship, blocky hull, multiple turrets, thick armor, large ~30x22 pixels equivalent, red and mars orange color scheme",
    ),
    ShipSpec(
        key="enemy_cruiser",
        template="heavy",
        display_name="Cruiser (heavy)",
        prompt_fill="long armored cruiser, multiple turrets along the hull, large ~30x22 pixels equivalent, red and mars orange color scheme",
    ),
    # Player ship (white + gold + red, hero)
    ShipSpec(
        key="player",
        template="player",
        display_name="Player ship (ship_01 redesign)",
        prompt_fill="hero ship, sleek aggressive silhouette, prominent cockpit, gold accents, white hull with gold highlights and red engine tips, heroic ~30x24 pixels equivalent with more detail",
    ),
)


def ship_by_key(key: str) -> ShipSpec:
    for s in SHIPS:
        if s.key == key:
            return s
    raise KeyError(f"unknown ship key: {key!r}")
