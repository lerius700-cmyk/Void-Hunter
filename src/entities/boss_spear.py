"""BLOQUE 52: GOLIATH's spear projectile.

The spear is a destructible boss projectile with:
  - HP (3 hits from the player to destroy it)
  - Serpentine (sinusoidal) motion around the initial aim direction
  - Lifetime (~6s before self-destructing if not hit)
  - On destroy: bifurcates into 3 smaller spear fragments in a cone

There are two kinds of spears:
  - main:    the giant's thrown spear, big, slow, heavy, 3 HP
  - fragment: a chunk split off the main spear, smaller, faster, 1 HP

Both damage the player on contact.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class BossSpear:
    """Single spear (main or fragment) in flight.

    Position uses a base direction (vx, vy) plus a serpentine wave
    perpendicular to it, with amplitude and frequency that grow over
    time so the spear becomes harder to dodge as it travels.
    """
    active: bool = False
    kind: str = "main"  # "main" or "fragment"

    # Position
    x: float = 0.0
    y: float = 0.0

    # Initial direction (unit vector at t=0)
    base_vx: float = 0.0
    base_vy: float = 1.0
    # Perpendicular unit vector (for the serpentine wave)
    perp_vx: float = 1.0
    perp_vy: float = 0.0

    # Speed along base direction (px/s)
    speed: float = 180.0

    # Serpentine wave (perpendicular displacement)
    wave_t: float = 0.0           # seconds since spawn
    wave_amp: float = 0.0         # px (perpendicular)
    wave_freq_hz: float = 1.6     # cycles per second
    # Amplitude growth per second (so it gets wilder over time)
    wave_amp_growth: float = 8.0

    # Combat
    # BLOQUE 58.56: x10 health. The spear was a 1-shot kill with 3 HP
    # which felt too fragile. Now it's a 30-HP mini-boss that takes
    # sustained fire to bring down, rewarding focused aim.
    hp: int = 30
    max_hp: int = 30
    damage: int = 2

    # Lifetime
    life: float = 6.0
    max_life: float = 6.0

    # Hit feedback
    flash_t: float = 0.0

    # Marker for the main spear (used for split logic)
    is_main: bool = True

    def hitbox(self) -> tuple[float, float, float, float]:
        """Return (cx, cy, w, h) for collision testing.

        Main spears are big and rectangular. Fragments are small and
        centered on the position.
        """
        if self.kind == "main":
            return (self.x, self.y, 26.0, 10.0)
        return (self.x, self.y, 10.0, 5.0)

    def apply_damage(self, amount: int) -> bool:
        """Returns True if this hit killed the spear."""
        if not self.active:
            return False
        self.hp -= amount
        self.flash_t = 0.08
        if self.hp <= 0:
            self.active = False
            return True
        return False

    def update(self, dt: float) -> None:
        """Advance straight-line motion + life + flash decay.

        BLOQUE 58.59: serpentine wave removed. The spear now travels in a
        straight line along its base direction. Curved motion (if desired)
        is handled by the new BezierPath / FlightFormation system, not by
        per-projectile oscillation.
        """
        if not self.active or dt <= 0.0:
            return
        # Advance wave time (kept as a counter but unused for position now)
        self.wave_t += dt
        # Position = base direction * speed * dt (pure straight line)
        self.x += self.base_vx * self.speed * dt
        self.y += self.base_vy * self.speed * dt
        # Life
        self.life -= dt
        if self.life <= 0.0:
            self.active = False
        # Flash
        if self.flash_t > 0.0:
            self.flash_t -= dt
            if self.flash_t < 0.0:
                self.flash_t = 0.0
