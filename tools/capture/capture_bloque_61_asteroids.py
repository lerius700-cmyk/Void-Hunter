"""Capture the 5 BLOQUE 61 asteroid variants in a single frame.

Headless 320x480 capture. Spawns one asteroid per variant (round,
elongated, spiked, hollowed, cracked) at evenly spaced positions across
the playfield, renders one frame with the new sprite loader, and saves
the PNG to ``tools/playtest_out/bloque_61_5_variants.png``.

This is the visual verification step for BLOQUE 61: the user must
confirm that the 5 sprites look like MINE-ASTEROID closed lookalikes
(brown rocky body + Greek-key stripe band + 1-3 craters) and that the
silhouettes are visually distinct.
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

from src.core.settings import INTERNAL_W
from src.entities.asteroid import Asteroid, _load_asteroid_sprite, draw_asteroid

VARIANT_NAMES = ("round", "elongated", "spiked", "hollowed", "cracked")
SPACING = 64  # px between asteroid centers
START_X = 32  # first asteroid at x=32 (centered on first column)
ROW_Y = INTERNAL_W and (200)  # not used; see below

# Place 5 asteroids on a horizontal row centered vertically in the playfield
ROW_Y_PIXEL = 200
SCALES = (0.9, 1.1, 0.8, 1.2, 1.0)  # one per variant — ensures the
# "scale" jitter is visible too. Not required to be deterministic; we
# just want the user to see different sizes side by side.

# 320x480 surface with a deep-space background (matches gameplay)
surf = pygame.Surface((320, 480))
surf.fill((8, 8, 20))

# Seed is fixed for reproducibility
rng = random.Random(61)

for i, variant in enumerate(VARIANT_NAMES):
    # 5 columns, evenly spaced across the 320px playfield
    x = 32 + i * SPACING
    if x > 288:  # don't go off the right edge
        x = 288 - (4 - i) * 8
    y = ROW_Y_PIXEL
    # Different scales so the "scale variation" feature is visible
    scale = SCALES[i]
    ast = Asteroid(
        x=float(x), y=float(y),
        radius=int(16 * scale), hp=2,
        variant=i, scale=scale,
        drift_vx=0.0, drift_vy=0.0,
    )
    draw_asteroid(surf, ast)

# Optional: render variant labels under each asteroid (small text)
try:
    font = pygame.font.Font(None, 14)
    for i, variant in enumerate(VARIANT_NAMES):
        x = 32 + i * SPACING
        if x > 288:
            x = 288 - (4 - i) * 8
        text = font.render(variant, True, (200, 200, 200))
        surf.blit(text, (x - text.get_width() // 2, ROW_Y_PIXEL + 32))
except Exception:
    pass

# Save
out = ROOT / "tools" / "playtest_out" / "bloque_61_5_variants.png"
out.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(surf, str(out))
print(f"saved {out}")

# Quick sanity: print the 5 cached sprite sizes
for v in range(5):
    s = _load_asteroid_sprite(v)
    print(f"  variant {v} ({VARIANT_NAMES[v]}): {s.get_size()} cached={s is _load_asteroid_sprite(v)}")
