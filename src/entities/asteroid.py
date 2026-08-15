"""BLOQUE 58.12: Asteroid entity — brown rocky obstacles.

Inspired by Star Fox 64's iconic striped asteroids. The Greek-key stripe
pattern is drawn procedurally (no asset needed). Asteroids drift across
the playfield at a constant slow speed, can be shot (2-3 HP), and some
hide powerups (roguelike distribution: bomb, HP, weapon, score).

Aesthetic: 8-bit rocky, brown palette (140, 100, 60 base).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W


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
    rotation: float = 0.0  # current angle in degrees
    rotation_speed: float = 5.0  # deg/s
    # BLOQUE 58.12: which powerup this asteroid hides (if any).
    # None = no powerup. The kind is decided at spawn time.
    hidden_powerup: Optional[PowerupKind] = None
    # Whether the powerup has already been dropped (one-shot).
    powerup_dropped: bool = False
    # Whether this asteroid is active (drawn + collision).
    active: bool = True

    def update(self, dt: float) -> None:
        """Drift down + rotate."""
        self.x += self.drift_vx * dt
        self.y += self.drift_vy * dt
        self.rotation = (self.rotation + self.rotation_speed * dt) % 360.0

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
# Procedural sprite generation
# ---------------------------------------------------------------------------
# Brown palette for the rocky body
_BROWN_BASE = (140, 100, 60)
_BROWN_HI = (180, 140, 90)
_BROWN_SH = (90, 60, 30)
_BROWN_DEEP = (50, 30, 15)


def _make_asteroid_sprite(radius: int, rng: random.Random) -> pygame.Surface:
    """Generate a procedural rocky asteroid sprite with Greek-key stripes.

    The sprite is a square `2*radius x 2*radius` Surface with the rocky
    outline drawn in circles and the Greek-key stripe pattern overlaid.
    Cached by radius for reuse.
    """
    cache_key = ("asteroid_sprite", radius)
    if cache_key in _SPRITE_CACHE:
        return _SPRITE_CACHE[cache_key]
    size = radius * 2 + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    # 1. Rock outline: irregular polygon of points around the center
    n_points = 12 + rng.randint(0, 4)
    outline: list[tuple[int, int]] = []
    for i in range(n_points):
        a = (i / n_points) * 2 * math.pi
        r = radius * (0.85 + rng.random() * 0.25)
        x = int(cx + math.cos(a) * r)
        y = int(cy + math.sin(a) * r)
        outline.append((x, y))
    # 2. Fill the rock with the base brown
    pygame.draw.polygon(surf, _BROWN_BASE, outline)
    # 3. Shading: darker bottom-right, lighter top-left
    shade = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(radius, 0, -1):
        a = int(15 * (i / radius))
        pygame.draw.circle(shade, (*_BROWN_SH, a), (cx + 2, cy + 2), i)
    surf.blit(shade, (0, 0))
    # 4. Highlight: lighter top-left
    hi = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(radius // 2, 0, -1):
        a = int(20 * (1.0 - i / (radius / 2)))
        pygame.draw.circle(hi, (*_BROWN_HI, a), (cx - 3, cy - 3), i)
    surf.blit(hi, (0, 0))
    # 5. Greek-key stripe pattern (BLOQUE 58.12 Star Fox 64 vibe)
    # Draw 2-3 horizontal stripes with the iconic angular pattern.
    n_stripes = 2 + rng.randint(0, 1)
    for s in range(n_stripes):
        # Stripe Y position (slightly off-center)
        stripe_y = int(cy - radius * 0.5 + s * (radius * 0.55))
        stripe_h = max(2, radius // 5)
        # Stripe color: deep brown
        pygame.draw.rect(
            surf, _BROWN_DEEP,
            (cx - radius, stripe_y, radius * 2, stripe_h),
        )
        # Greek-key "teeth" along the stripe (zig-zag pattern)
        teeth_count = 5
        tooth_w = (radius * 2) // (teeth_count * 2)
        for t in range(teeth_count):
            tx0 = cx - radius + t * (tooth_w * 2)
            ty0 = stripe_y
            ty1 = stripe_y + stripe_h
            # Square tooth pointing up
            pygame.draw.rect(
                surf, _BROWN_DEEP,
                (tx0, ty0, tooth_w, stripe_h // 2),
            )
            # Square tooth pointing down
            pygame.draw.rect(
                surf, _BROWN_DEEP,
                (tx0 + tooth_w, ty1 - stripe_h // 2, tooth_w, stripe_h // 2),
            )
    # 6. Outline for visibility
    pygame.draw.polygon(surf, _BROWN_SH, outline, 1)
    _SPRITE_CACHE[cache_key] = surf
    return surf


_SPRITE_CACHE: dict[tuple, pygame.Surface] = {}


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
    """
    if x < 0:
        x = rng.uniform(24, INTERNAL_W - 24)
    if y < 0:
        y = rng.uniform(-80, 0)  # spawn just above the top
    radius = rng.choice([12, 14, 16, 18, 20, 24])
    hp = rng.choice([1, 2, 2, 3, 3])  # mostly 2-3 HP
    drift_vx = rng.uniform(-15, 15)
    drift_vy = rng.uniform(20, 50)
    rotation_speed = rng.uniform(-25, 25)
    has_powerup = rng.random() < 0.30  # 30% of asteroids have a powerup
    return Asteroid(
        x=x, y=y, radius=radius, hp=hp,
        drift_vx=drift_vx, drift_vy=drift_vy,
        rotation_speed=rotation_speed,
        hidden_powerup=(pick_random_powerup(rng) if has_powerup else None),
    )


def draw_asteroid(target: pygame.Surface, ast: Asteroid) -> None:
    """Draw a single asteroid at its current position with rotation."""
    if not ast.active:
        return
    sprite = _make_asteroid_sprite(ast.radius, random.Random(ast.x.__hash__()))
    # Rotate the sprite
    rotated = pygame.transform.rotate(sprite, ast.rotation)
    rect = rotated.get_rect(center=(int(ast.x), int(ast.y)))
    target.blit(rotated, rect)
