"""BLOQUE 58.12 + 61: Asteroid entity — brown rocky obstacles.

BLOQUE 58.12: Inspired by Star Fox 64's iconic striped asteroids. The
Greek-key stripe pattern is part of the AI-generated sprite.

BLOQUE 61: All 5 asteroid variants are MINE-ASTEROID closed lookalikes
generated with mcode-tools (1024x1024 base → LANCZOS resize to 32x32).
The procedural sprite generator was removed. Rotation was dropped to
make MINE-ASTEROID camouflage (BLOQUE 63) work.

Asteroids drift across the playfield at a constant slow speed, can be
shot (1-3 HP), and some hide powerups (roguelike distribution: bomb,
HP, weapon, score). 30% of asteroids hide a powerup.

Aesthetic: 8-bit rocky, brown palette (140, 100, 60 base), Greek-key
stripe bands from Star Fox 64.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
#: Directory containing the 5 AI-generated 32x32 asteroid PNGs
ASTEROID_SPRITES_DIR = Path(__file__).resolve().parent.parent.parent / "Assets" / "sprites" / "asteroids"
#: Number of distinct asteroid variants
NUM_ASTEROID_VARIANTS = 5
#: Base sprite size (the 32x32 PNG is scaled by ast.scale at render time)
ASTEROID_SPRITE_BASE_SIZE = 32
#: Allowed scale range from spawn
ASTEROID_SCALE_MIN = 0.7
ASTEROID_SCALE_MAX = 1.3


class PowerupKind(Enum):
    """BLOQUE 58.12: 4 powerup types that asteroids can hide.
    Distributed roguelike-style (random.choice from weighted pool).
    """
    BOMB = "bomb"                # +1 bomb (clears screen)
    HP = "hp"                    # +30 HP
    WEAPON = "weapon"            # upgrade weapon level
    SCORE = "score"              # +500 score


# Distribution weights (sums to 100). Roguelike = random pick.
POWERUP_WEIGHTS: dict[PowerupKind, int] = {
    PowerupKind.BOMB: 15,
    PowerupKind.HP: 30,
    PowerupKind.WEAPON: 20,
    PowerupKind.SCORE: 35,
}


@dataclass
class Asteroid:
    """A single rocky asteroid. Drifts down, can be shot or dodged."""
    x: float
    y: float
    radius: int
    hp: int
    drift_vx: float = 0.0   # horizontal drift speed (px/s)
    drift_vy: float = 30.0  # vertical drift speed (px/s, downward)
    # BLOQUE 61: removed rotation / rotation_speed. Asteroids are now
    # static sprites (no in-game rotation), making the MINE-ASTEROID
    # camouflage (BLOQUE 63) effective. The sprite itself is a
    # 32x32 PNG loaded by variant.
    variant: int = 0          # 0-4 index into the 5 AI-generated sprites
    scale: float = 1.0        # 0.7-1.3 from spawn, applied to the 32x32 base
    # BLOQUE 58.12: which powerup this asteroid hides (if any).
    # None = no powerup. The kind is decided at spawn time.
    hidden_powerup: Optional[PowerupKind] = None
    # Whether the powerup has already been dropped (one-shot).
    powerup_dropped: bool = False
    # Whether this asteroid is active (drawn + collision).
    active: bool = True

    def update(self, dt: float) -> None:
        """Drift down. No rotation (BLOQUE 61)."""
        self.x += self.drift_vx * dt
        self.y += self.drift_vy * dt

    def hit(self, damage: int = 1) -> bool:
        """Apply damage. Returns True if the asteroid was destroyed."""
        self.hp -= damage
        if self.hp <= 0:
            self.active = False
            return True
        return False

    def is_off_screen(self) -> bool:
        """True if the asteroid has drifted past the bottom of the playfield."""
        return self.y - self.radius > INTERNAL_H + 32


# ---------------------------------------------------------------------------
# Sprite loader (BLOQUE 61)
# ---------------------------------------------------------------------------
_ASTEROID_SPRITE_CACHE: dict[int, pygame.Surface] = {}


def _load_asteroid_sprite(variant: int) -> pygame.Surface:
    """Load (and cache) one of the 5 AI-generated 32x32 asteroid PNGs.

    Args:
        variant: 0-4 (round, elongated, spiked, hollowed, cracked).

    Returns:
        A 32x32 pygame.Surface (RGBA, with the asteroid's silhouette
        on a transparent background). If the variant is out of range
        or the file is missing, returns a fallback 32x32 transparent
        Surface so callers don't crash.
    """
    if variant in _ASTEROID_SPRITE_CACHE:
        return _ASTEROID_SPRITE_CACHE[variant]
    if not (0 <= variant < NUM_ASTEROID_VARIANTS):
        # Out of range: return a transparent fallback
        surf = pygame.Surface((ASTEROID_SPRITE_BASE_SIZE, ASTEROID_SPRITE_BASE_SIZE), pygame.SRCALPHA)
        _ASTEROID_SPRITE_CACHE[variant] = surf
        return surf
    # Variant file names: round.png, elongated.png, spiked.png, hollowed.png, cracked.png
    # Map variant index to filename via the same order as ASTEROIDS tuple
    variant_names = ("round", "elongated", "spiked", "hollowed", "cracked")
    fname = variant_names[variant]
    path = ASTEROID_SPRITES_DIR / f"{fname}.png"
    if not path.exists():
        # File missing: return a transparent fallback
        surf = pygame.Surface((ASTEROID_SPRITE_BASE_SIZE, ASTEROID_SPRITE_BASE_SIZE), pygame.SRCALPHA)
        _ASTEROID_SPRITE_CACHE[variant] = surf
        return surf
    surf = pygame.image.load(str(path)).convert_alpha()
    _ASTEROID_SPRITE_CACHE[variant] = surf
    return surf


# ---------------------------------------------------------------------------
# Powerup drops
# ---------------------------------------------------------------------------
@dataclass
class Powerup:
    """A powerup dropped by a destroyed asteroid. Drifts until collected."""
    x: float
    y: float
    kind: PowerupKind
    vy: float = 40.0  # drift down
    vx: float = 0.0
    age_s: float = 0.0
    max_age_s: float = 12.0  # despawn after this
    active: bool = True
    pulse: float = 0.0  # for visual pulsing

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.age_s += dt
        self.pulse = (self.pulse + dt * 4.0) % (2 * math.pi)
        if self.age_s > self.max_age_s:
            self.active = False

    def is_off_screen(self) -> bool:
        return self.y > INTERNAL_H + 24

    def draw(self, target: pygame.Surface) -> None:
        """Draw the powerup as a colored square with a letter inside."""
        if not self.active:
            return
        cx, cy = int(self.x), int(self.y)
        # Pulse size
        size = 8 + int(1.5 * math.sin(self.pulse))
        # Color by kind
        color = {
            PowerupKind.BOMB:    (255, 100, 100),
            PowerupKind.HP:      (100, 255, 100),
            PowerupKind.WEAPON:  (100, 180, 255),
            PowerupKind.SCORE:   (255, 220, 100),
        }[self.kind]
        # Background
        bg = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.rect(bg, (*color, 200), (0, 0, size * 2, size * 2), border_radius=2)
        pygame.draw.rect(bg, (255, 255, 255, 220), (0, 0, size * 2, size * 2), 1, border_radius=2)
        target.blit(bg, (cx - size, cy - size))
        # Letter
        letter = {
            PowerupKind.BOMB:    "B",
            PowerupKind.HP:      "+",
            PowerupKind.WEAPON:  "W",
            PowerupKind.SCORE:   "S",
        }[self.kind]
        try:
            font = pygame.font.Font(None, 12)
            text = font.render(letter, True, (0, 0, 0))
            target.blit(text, (cx - text.get_width() // 2, cy - text.get_height() // 2))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Factory: spawn asteroids for a wave
# ---------------------------------------------------------------------------
def pick_random_powerup(rng: random.Random) -> PowerupKind:
    """BLOQUE 58.12: roguelike pick from weighted distribution."""
    pool: list[PowerupKind] = []
    for kind, weight in POWERUP_WEIGHTS.items():
        pool.extend([kind] * weight)
    return rng.choice(pool)


def spawn_asteroid(
    rng: random.Random,
    x: float = -1,
    y: float = -1,
) -> Asteroid:
    """Spawn a single asteroid at random position (or override x/y).

    30% of asteroids hide a powerup (the user wanted 'una que otra').

    BLOQUE 61: variant (0-4) and scale (0.7-1.3) are picked at spawn
    time. radius is derived from scale: int(16 * scale) clamped to >= 8.
    """
    if x < 0:
        x = rng.uniform(24, INTERNAL_W - 24)
    if y < 0:
        y = rng.uniform(-80, 0)  # spawn just above the top
    variant = rng.randint(0, NUM_ASTEROID_VARIANTS - 1)
    scale = rng.uniform(ASTEROID_SCALE_MIN, ASTEROID_SCALE_MAX)
    radius = max(8, int(16 * scale))
    hp = rng.choice([1, 2, 2, 3, 3])  # mostly 2-3 HP
    drift_vx = rng.uniform(-15, 15)
    drift_vy = rng.uniform(20, 50)
    has_powerup = rng.random() < 0.30  # 30% of asteroids have a powerup
    return Asteroid(
        x=x, y=y, radius=radius, hp=hp,
        drift_vx=drift_vx, drift_vy=drift_vy,
        variant=variant, scale=scale,
        hidden_powerup=(pick_random_powerup(rng) if has_powerup else None),
    )


def draw_asteroid(target: pygame.Surface, ast: Asteroid) -> None:
    """Draw a single asteroid at its current position (no rotation)."""
    if not ast.active:
        return
    sprite = _load_asteroid_sprite(ast.variant)
    # Apply scale (smoothscale once per draw — sprites are 32x32 so it's cheap)
    if ast.scale != 1.0:
        scaled_size = max(1, int(ASTEROID_SPRITE_BASE_SIZE * ast.scale))
        sprite = pygame.transform.smoothscale(sprite, (scaled_size, scaled_size))
    rect = sprite.get_rect(center=(int(ast.x), int(ast.y)))
    target.blit(sprite, rect)
