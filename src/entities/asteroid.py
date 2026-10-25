"""BLOQUE 58.12 + 61 + 64.A: Asteroid entity — brown rocky obstacles.

BLOQUE 58.12: Inspired by Star Fox 64's iconic striped asteroids. The
Greek-key stripe pattern is part of the AI-generated sprite.

BLOQUE 61: All 5 asteroid variants are MINE-ASTEROID closed lookalikes
generated with mcode-tools (1024x1024 base → LANCZOS resize to 32x32).
The procedural sprite generator was removed. Rotation was dropped to
make MINE-ASTEROID camouflage (BLOQUE 63) work.

BLOQUE 64.A:
  - Sprite size bumped 32x32 → 64x64 (more readable on screen).
  - Spawn scale range bumped 0.7-1.3 → 1.5-2.5 (96-160 px on screen).
  - Asteroids are now INDESTRUCTIBLE. ``hit()`` is a no-op that always
    returns False. The MINE-ASTEROID is the only "asteroid-like" thing
    the player can shoot (BLOQUE 63); regular asteroids are pure
    obstacles the player must dodge.
  - The ``hp`` field is removed from the ``Asteroid`` dataclass (it was
    a leftover from the pre-BLOQUE 64.A implementation). The
    ``spawn_asteroid`` factory no longer picks an HP value.

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
#: Directory containing the 5 AI-generated 64x64 asteroid PNGs
ASTEROID_SPRITES_DIR = Path(__file__).resolve().parent.parent.parent / "Assets" / "sprites" / "asteroids"
#: Number of distinct asteroid variants
NUM_ASTEROID_VARIANTS = 5
#: Base sprite size (the 64x64 PNG is scaled by ast.scale at render time).
#: BLOQUE 64.A: 32 → 64 so the Greek-key stripe and craters are readable.
ASTEROID_SPRITE_BASE_SIZE = 64
#: Allowed scale range from spawn.
#: BLOQUE 64.A: 0.7-1.3 → 1.5-2.5 (96-160 px on a 320x480 playfield).
ASTEROID_SCALE_MIN = 1.5
ASTEROID_SCALE_MAX = 2.5


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
    """A single rocky asteroid. Drifts down, can be dodged but not destroyed.

    BLOQUE 64.A: the ``hp`` field was removed; ``hit()`` is a no-op that
    always returns False. MINE-ASTEROID (the camouflaged enemy) is the
    only asteroid-looking thing the player can shoot — regular asteroids
    are pure obstacles.

    BLOQUE 71: ``hit()`` now sets ``hit_timer`` for visual feedback
    (palette-swap white flash) but still returns False (indestructible).
    """
    x: float
    y: float
    radius: int
    drift_vx: float = 0.0   # horizontal drift speed (px/s)
    drift_vy: float = 30.0  # vertical drift speed (px/s, downward)
    # BLOQUE 61: removed rotation / rotation_speed. Asteroids are now
    # static sprites (no in-game rotation), making the MINE-ASTEROID
    # camouflage (BLOQUE 63) effective. The sprite itself is a
    # 64x64 PNG loaded by variant.
    variant: int = 0          # 0-4 index into the 5 AI-generated sprites
    scale: float = 1.0        # 1.5-2.5 from spawn, applied to the 64x64 base
    # BLOQUE 58.12: which powerup this asteroid hides (if any).
    # None = no powerup. The kind is decided at spawn time.
    # BLOQUE 64.A: kept for API compatibility (the field is no longer
    # ever consumed because the asteroid is indestructible). The 30%
    # powerup rate was effectively a "destroy an asteroid to get a
    # powerup" feature; with indestructibility, that path is closed.
    # Powerups now come from MINE-ASTEROID kills (50% drop per BLOQUE 63).
    hidden_powerup: Optional[PowerupKind] = None
    # Whether the powerup has already been dropped (one-shot).
    powerup_dropped: bool = False
    # Whether this asteroid is active (drawn + collision).
    active: bool = True
    # BLOQUE 71: white flash on hit (palette-swap render when > 0)
    hit_timer: float = 0.0

    def update(self, dt: float) -> None:
        """Drift down. No rotation (BLOQUE 61). BLOQUE 71: tick hit_timer."""
        self.x += self.drift_vx * dt
        self.y += self.drift_vy * dt
        if self.hit_timer > 0.0:
            self.hit_timer = max(0.0, self.hit_timer - dt)

    def hit(self, damage: int = 1) -> bool:
        """BLOQUE 64.A + 71: set hit_timer for visual flash, return False.

        ``damage`` is accepted for API compatibility but is ignored.
        Always returns False (never destroyed). The hit_timer triggers
        a brief white palette-swap in the renderer.
        """
        del damage
        from src.core.settings import HIT_FLASH_DURATION_S
        self.hit_timer = HIT_FLASH_DURATION_S
        return False

    def is_off_screen(self) -> bool:
        """True if the asteroid has drifted past the bottom of the playfield."""
        return self.y - self.radius > INTERNAL_H + 32


# ---------------------------------------------------------------------------
# Sprite loader (BLOQUE 61)
# ---------------------------------------------------------------------------
_ASTEROID_SPRITE_CACHE: dict[int, pygame.Surface] = {}


def _load_asteroid_sprite(variant: int) -> pygame.Surface:
    """Load (and cache) one of the 5 AI-generated 64x64 asteroid PNGs.

    BLOQUE 64.A: 32x32 → 64x64. The sprite is cached on the module
    level, so the first load does the I/O and subsequent draws return
    the same Surface.

    Args:
        variant: 0-4 (round, elongated, spiked, hollowed, cracked).

    Returns:
        A 64x64 pygame.Surface (RGBA, with the asteroid's silhouette
        on a transparent background). If the variant is out of range
        or the file is missing, returns a fallback 64x64 transparent
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

    BLOQUE 64.A: the 30% powerup rate is preserved on the dataclass
    field (kept for API compatibility) but is no longer surfaced in
    gameplay because the asteroid is indestructible. Powerups now come
    exclusively from MINE-ASTEROID kills (50% drop per BLOQUE 63).

    BLOQUE 64.A: scale range bumped to 1.5-2.5 (was 0.7-1.3). radius
    is still derived from scale: int(16 * scale) clamped to >= 8.
    """
    if x < 0:
        x = rng.uniform(24, INTERNAL_W - 24)
    if y < 0:
        y = rng.uniform(-80, 0)  # spawn just above the top
    variant = rng.randint(0, NUM_ASTEROID_VARIANTS - 1)
    scale = rng.uniform(ASTEROID_SCALE_MIN, ASTEROID_SCALE_MAX)
    radius = max(8, int(16 * scale))
    drift_vx = rng.uniform(-15, 15)
    drift_vy = rng.uniform(20, 50)
    has_powerup = rng.random() < 0.30  # kept for API compat (not consumed)
    return Asteroid(
        x=x, y=y, radius=radius,
        drift_vx=drift_vx, drift_vy=drift_vy,
        variant=variant, scale=scale,
        hidden_powerup=(pick_random_powerup(rng) if has_powerup else None),
    )


def draw_asteroid(target: pygame.Surface, ast: Asteroid) -> None:
    """Draw a single asteroid at its current position (no rotation)."""
    if not ast.active:
        return
    sprite = _load_asteroid_sprite(ast.variant)
    # Apply scale (smoothscale once per draw — sprites are 64x64 so it's cheap)
    if ast.scale != 1.0:
        scaled_size = max(1, int(ASTEROID_SPRITE_BASE_SIZE * ast.scale))
        sprite = pygame.transform.smoothscale(sprite, (scaled_size, scaled_size))
    rect = sprite.get_rect(center=(int(ast.x), int(ast.y)))
    target.blit(sprite, rect)


# ---------------------------------------------------------------------------
# BLOQUE 71.1: shape-aware hit flash render (replaces palette-swap)
# ---------------------------------------------------------------------------
def _build_white_flash_overlay(sprite: pygame.Surface, opacity: float) -> pygame.Surface:
    """Build a white-tinted silhouette of `sprite` at `opacity` (0..1).

    The overlay matches `sprite`'s alpha mask exactly (only non-transparent
    pixels get white). The overlay's per-pixel alpha is `sprite.alpha * opacity`,
    so the original sprite shows through at `(1 - opacity)` strength.

    Result: instead of a fully-white square, the player sees the original
    sprite with a translucent white wash on top — the SHAPE of the object
    is preserved and visible, not replaced.
    """
    w, h = sprite.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    # Use the sprite's actual per-pixel alpha so the overlay is shape-aware.
    for x in range(w):
        for y in range(h):
            r, g, b, a = sprite.get_at((x, y))
            if a == 0:
                continue
            overlay.set_at((x, y), (255, 255, 255, int(a * opacity)))
    return overlay


# ---------------------------------------------------------------------------
# BLOQUE 71: hit flash render (palette-swap to white)
# ---------------------------------------------------------------------------
# Kept for back-compat with the T1 fix (which removed the old palette-swap body
# but kept this stub around). The actual flash is now built via
# `_build_white_flash_overlay` + blit. Nothing else should reference this.
_WHITE_FLASH_LUT: dict[tuple[int, int, int], tuple[int, int, int]] = {}


def _build_white_flash_lut() -> None:
    """BLOQUE 71.1: deprecated. The flash is now built via the overlay helper.

    This function remains for back-compat with code that imports the symbol
    (none after the refactor). The LUT is unused.
    """
    global _WHITE_FLASH_LUT
    if _WHITE_FLASH_LUT is not None:
        return
    _WHITE_FLASH_LUT = {}


def draw_asteroid_with_hit_flash(target: pygame.Surface, ast: "Asteroid") -> None:
    """BLOQUE 71.1: draw the asteroid, applying a 70% white flash overlay if hit_timer > 0.

    If hit_timer is 0, behaves identically to draw_asteroid (full sprite).
    If > 0, draws the original sprite first, then a 70%-opaque white
    silhouette on top. The overlay respects the sprite's alpha mask, so
    the result is the SHAPE of the asteroid (not a white square), with
    the original sprite still visible underneath at 30%.
    The flash decays as hit_timer decrements toward 0.
    """
    from src.core.settings import HIT_FLASH_OPACITY
    if not ast.active:
        return
    sprite = _load_asteroid_sprite(ast.variant)
    if ast.scale != 1.0:
        scaled_size = max(1, int(ASTEROID_SPRITE_BASE_SIZE * ast.scale))
        sprite = pygame.transform.smoothscale(sprite, (scaled_size, scaled_size))

    rect = sprite.get_rect(center=(int(ast.x), int(ast.y)))
    if ast.hit_timer > 0.0:
        # 1. Draw the original sprite so the shape is visible underneath.
        target.blit(sprite, rect)
        # 2. Build a shape-aware white silhouette at 70% opacity and overlay it.
        overlay = _build_white_flash_overlay(sprite, HIT_FLASH_OPACITY)
        target.blit(overlay, rect)
    else:
        target.blit(sprite, rect)
