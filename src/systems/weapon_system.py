"""Weapon system — 3 elemental paths (plasma/ion/shock) with 3 levels + special.

Per GDD §3:
  - plasma: fire-rate / pierce / splash — bonus vs Heavy/Cruiser/Turret/Carrier
  - ion:    pierce / chain — bonus vs Scout/Drone/Sniper
  - shock:  knockback / splash / slow — bonus vs Kamikaze/Sniper/Heavy

Each path has 3 levels (10/25/50 kills) and unlocks a special at L3.
Special consumes 1 bomb.

Description: state-only; produces bullet specs the ProjectilePool consumes.
             No direct mutation of pools — keeps coupling low for testing.
Dependencies: dataclass, settings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.core.settings import (
    PLAYER_BOMBS_MAX,
)


class WeaponPath(Enum):
    PLASMA = "plasma"
    ION = "ion"
    SHOCK = "shock"


class WeaponLevel(Enum):
    L1 = 1
    L2 = 2
    L3 = 3


# XP thresholds for level-up
XP_PER_KILL = 1
XP_PER_KILL_ELEMENT_BONUS = 2
XP_THRESHOLD_L2 = 10
XP_THRESHOLD_L3 = 25
XP_THRESHOLD_SPECIAL = 50

# Special names
SPECIAL_NAMES = {
    WeaponPath.PLASMA: "INFERNO",
    WeaponPath.ION: "CHAIN_LIGHTNING",
    WeaponPath.SHOCK: "QUAKE",
}

# Element bonus map (which enemy archetypes are weak to which path)
ELEMENT_BONUS_TARGETS: dict[WeaponPath, set[str]] = {
    WeaponPath.PLASMA: {"heavy", "cruiser", "turret", "carrier"},
    WeaponPath.ION: {"scout", "drone", "sniper"},
    WeaponPath.SHOCK: {"kamikaze", "sniper", "heavy"},
}

# Per-level bullet configuration
@dataclass(frozen=True)
class _BulletSpec:
    count: int                  # bullets per shot
    spread_deg: float           # spread angle for multi-bullet
    damage: int                 # per-bullet damage
    pierce: int                 # pierce count
    speed_mult: float           # speed multiplier
    trail: bool                 # has trail
    color: tuple[int, int, int]


PLASMA_SPECS: dict[WeaponLevel, _BulletSpec] = {
    WeaponLevel.L1: _BulletSpec(count=1, spread_deg=0.0,  damage=1, pierce=0, speed_mult=1.0, trail=True,  color=(255, 180, 80)),
    WeaponLevel.L2: _BulletSpec(count=2, spread_deg=0.0,  damage=2, pierce=0, speed_mult=1.125, trail=True, color=(255, 140, 60)),
    WeaponLevel.L3: _BulletSpec(count=3, spread_deg=8.0,  damage=3, pierce=0, speed_mult=1.25, trail=True, color=(255, 100, 40)),
}
ION_SPECS: dict[WeaponLevel, _BulletSpec] = {
    WeaponLevel.L1: _BulletSpec(count=1, spread_deg=0.0,  damage=1, pierce=1, speed_mult=1.0, trail=True,  color=(80, 200, 255)),
    WeaponLevel.L2: _BulletSpec(count=2, spread_deg=0.0,  damage=2, pierce=2, speed_mult=1.125, trail=True, color=(120, 220, 255)),
    WeaponLevel.L3: _BulletSpec(count=3, spread_deg=6.0,  damage=3, pierce=3, speed_mult=1.25, trail=True, color=(180, 240, 255)),
}
SHOCK_SPECS: dict[WeaponLevel, _BulletSpec] = {
    WeaponLevel.L1: _BulletSpec(count=1, spread_deg=0.0, damage=1, pierce=0, speed_mult=0.625, trail=True, color=(180, 80, 220)),
    WeaponLevel.L2: _BulletSpec(count=2, spread_deg=0.0, damage=2, pierce=0, speed_mult=0.75,  trail=True, color=(220, 120, 255)),
    WeaponLevel.L3: _BulletSpec(count=1, spread_deg=0.0, damage=3, pierce=0, speed_mult=0.875, trail=True, color=(255, 140, 255)),
}

SPECS_BY_PATH: dict[WeaponPath, dict[WeaponLevel, _BulletSpec]] = {
    WeaponPath.PLASMA: PLASMA_SPECS,
    WeaponPath.ION: ION_SPECS,
    WeaponPath.SHOCK: SHOCK_SPECS,
}


@dataclass
class WeaponSystem:
    """3 paths × 3 levels + special unlock tracking."""
    path: WeaponPath = WeaponPath.PLASMA
    level: WeaponLevel = WeaponLevel.L1
    xp: int = 0
    special_unlocked: bool = False
    bombs_max: int = PLAYER_BOMBS_MAX
    bombs: int = PLAYER_BOMBS_MAX
    # Cooldown tracking (set by player FSM via wants_to_shoot)
    fire_cd: float = 0.0
    # Element bonus kills (for scoring/feedback)
    kills_with_element_bonus: int = 0
    # Stats
    total_kills: int = 0
    # Pending fire request (set by Player.wants_to_shoot or wants_to_charge_release)
    pending_fire: bool = False
    pending_special: bool = False
    pending_charge_level: int = 0  # 1/2/3

    def set_path(self, path: WeaponPath) -> None:
        """Switch weapon path. Resets XP and level (caller decides)."""
        self.path = path
        self.level = WeaponLevel.L1
        self.xp = 0
        self.special_unlocked = False

    def get_spec(self) -> _BulletSpec:
        return SPECS_BY_PATH[self.path][self.level]

    def on_kill(self, enemy_archetype: str = "") -> None:
        """Called by collision system on enemy death."""
        self.total_kills += 1
        element_match = enemy_archetype in ELEMENT_BONUS_TARGETS.get(self.path, set())
        if element_match:
            self.xp += XP_PER_KILL_ELEMENT_BONUS
            self.kills_with_element_bonus += 1
        else:
            self.xp += XP_PER_KILL
        # Level-up checks
        if not self.special_unlocked and self.xp >= XP_THRESHOLD_SPECIAL:
            self.special_unlocked = True
            self.level = WeaponLevel.L3
        elif self.level == WeaponLevel.L1 and self.xp >= XP_THRESHOLD_L2:
            self.level = WeaponLevel.L2
        elif self.level == WeaponLevel.L2 and self.xp >= XP_THRESHOLD_L3:
            self.level = WeaponLevel.L3

    def request_fire(self, charge_level: int = 0) -> None:
        """Called when player.wants_to_shoot or wants_to_charge_release."""
        self.pending_fire = True
        if charge_level > 0:
            self.pending_charge_level = charge_level

    def request_special(self) -> bool:
        """Try to fire special. Returns True if accepted, False if no bomb."""
        if not self.special_unlocked:
            return False
        if self.bombs <= 0:
            return False
        self.bombs -= 1
        self.pending_special = True
        return True

    def consume_pending(self) -> tuple[bool, bool, int]:
        """Atomically read+clear pending flags. Returns
        (fire_now, special_now, charge_level)."""
        fire = self.pending_fire
        special = self.pending_special
        level = self.pending_charge_level
        self.pending_fire = False
        self.pending_special = False
        self.pending_charge_level = 0
        return (fire, special, level)

    def reset(self) -> None:
        """Full reset (new run)."""
        self.path = WeaponPath.PLASMA
        self.level = WeaponLevel.L1
        self.xp = 0
        self.special_unlocked = False
        self.bombs = self.bombs_max
        self.fire_cd = 0.0
        self.kills_with_element_bonus = 0
        self.total_kills = 0
        self.pending_fire = False
        self.pending_special = False
        self.pending_charge_level = 0

    @property
    def special_name(self) -> str:
        return SPECIAL_NAMES[self.path]
