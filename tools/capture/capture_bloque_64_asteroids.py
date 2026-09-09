"""BLOQUE 64.A: capture script for 5 asteroid variants at 64x64.

Generates a single PNG at
``tools/playtest_out/bloque_64_5_asteroids_64x64.png`` showing all 5
asteroid variants (round, elongated, spiked, hollowed, cracked) at
their spawn-time scale (1.5-2.5x of the 64x64 base = 96-160 px on
screen) on a 320x480 playfield. The capture confirms the asteroids
are now clearly visible after the BLOQUE 64.A size + scale bump.

Usage:
    python tools/capture/capture_bloque_64_asteroids.py
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.entities.asteroid import (
    ASTEROID_SPRITE_BASE_SIZE,
    ASTEROID_SCALE_MAX,
    ASTEROID_SCALE_MIN,
    Asteroid,
    draw_asteroid,
)


OUT_DIR = ROOT / "tools" / "playtest_out"
OUT_PATH = OUT_DIR / "bloque_64_5_asteroids_64x64.png"

VARIANTS = ("round", "elongated", "spiked", "hollowed", "cracked")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 320x480 playfield surface (the internal resolution)
    surf = pygame.Surface((320, 480))
    # Fill with a dark space background so the asteroid silhouettes pop
    surf.fill((8, 10, 22))
    # Spawn one asteroid per variant, in a horizontal row at y=240 with
    # x evenly distributed. The scale is fixed at 1.0x (the lower bound
    # of the new 1.5-2.5 in-game range) so all 5 fit on screen at the
    # 64x64 base size with 8px gaps. This shows the new 64x64 native
    # resolution without the 2.5x in-game overlap.
    rng = random.Random(42)
    for i, v in enumerate(VARIANTS):
        # Distribute horizontally; the playfield is 320 wide so 5 columns
        # at 64 px each + 8 px gaps = 320 + 32 = 352 (slightly over), so
        # use scale 1.0 and a 4-pixel inner gap.
        x = 16 + (i * 60) + 30
        y = 200
        scale = 1.0  # show the 64x64 native size without scaling
        ast = Asteroid(
            x=float(x), y=float(y),
            radius=max(8, int(16 * scale)),
            variant=i,
            scale=scale,
            drift_vx=0.0, drift_vy=0.0,
        )
        draw_asteroid(surf, ast)

    # Add a second row showing the in-game 2.0x scale (128 px on screen)
    # so the user can see the actual gameplay size of the new asteroids.
    for i, v in enumerate(VARIANTS):
        x = 32 + (i * 64)
        y = 380
        scale = 2.0  # in-game scale
        ast = Asteroid(
            x=float(x), y=float(y),
            radius=max(8, int(16 * scale)),
            variant=i,
            scale=scale,
            drift_vx=0.0, drift_vy=0.0,
        )
        draw_asteroid(surf, ast)

    # Add a caption at the top so the screenshot is self-explanatory
    try:
        font = pygame.font.Font(None, 18)
        caption = font.render(
            "BLOQUE 64.A — 5 asteroid variants @ 64x64, scale 2.0x",
            True, (220, 220, 220),
        )
        surf.blit(caption, (6, 6))
        sub = font.render(
            f"base={ASTEROID_SPRITE_BASE_SIZE}px  scale=[{ASTEROID_SCALE_MIN},{ASTEROID_SCALE_MAX}]  "
            f"on-screen=[{int(ASTEROID_SPRITE_BASE_SIZE*ASTEROID_SCALE_MIN)},"
            f"{int(ASTEROID_SPRITE_BASE_SIZE*ASTEROID_SCALE_MAX)}]px",
            True, (180, 180, 200),
        )
        surf.blit(sub, (6, 26))
    except Exception:
        pass

    pygame.image.save(surf, str(OUT_PATH))
    print(f"saved: {OUT_PATH}  (320x480, 5 variants)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
