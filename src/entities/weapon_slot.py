"""BLOQUE 72: WeaponSlot — single weapon slot in the player's inventory."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WeaponSlot:
    """One of 4 fixed weapon slots (A/S/D/F). Fill via powerup pickup, consume on fire.

    The slot starts empty (ammo=0). Picking up the matching weapon powerup
    adds ammo (capped at max_ammo; excess is silently dropped per spec).
    Firing the weapon consumes ammo per the weapon's fire rate.
    """
    letter: str          # "A" | "S" | "D" | "F"
    weapon_id: str       # "thick" | "laser" | "flame" | "double"
    ammo: int
    max_ammo: int

    @property
    def is_empty(self) -> bool:
        """True if the slot has no ammo and cannot fire."""
        return self.ammo <= 0

    def add_ammo(self, amount: int) -> None:
        """Add ammo, capped at max_ammo. Excess is silently dropped.

        Spec (section 4.2 / 5): "Stack behavior: cap at max_ammo,
        excess silently dropped (no excess storage)."
        """
        self.ammo = min(self.ammo + amount, self.max_ammo)

    def consume(self, amount: int) -> int:
        """Consume up to `amount` ammo. Returns the amount actually consumed.

        If amount > ammo, consumes all remaining and returns that amount.
        """
        consumed = min(amount, self.ammo)
        self.ammo -= consumed
        return consumed
