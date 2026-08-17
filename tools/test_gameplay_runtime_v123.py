"""BLOQUE 58.14.4: render the new 2-galaxy gameplay background to a PNG.

Bypasses the full GameplayRuntime (which needs WaveChain etc.) and just
constructs a ParallaxBackground with the new gameplay config:
  - 2 large spiral galaxies (was 1)
  - radius 80-110 (was 100-140)
  - 8 stars/layer (sparse)

The previous config (legacy 6 + parallax 1) gave 4-5 visible galaxies
that "no tienen logica" per the user. The new 2-large matches the
boss scene's look (2-3 visible large spiral galaxies).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

from src.systems.parallax import ParallaxBackground
from src.core.settings import INTERNAL_W, INTERNAL_H


def main() -> int:
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    # EXACT config the new gameplay_runtime.py uses (lines 187-195)
    bg = ParallaxBackground(
        width=INTERNAL_W, height=INTERNAL_H,
        rng_seed=0xC0FFEE58,
        stars_per_layer=8,
        nebula_count=2,
        nebula_radius_min=80,
        nebula_radius_max=110,
        spawn_planets=False,
    )
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    for _ in range(120):
        bg.update(0.016)
    bg.draw(target)
    # Add a fake player ship + crosshair for scale reference
    pygame.draw.rect(target, (255, 100, 100),
                     (INTERNAL_W // 2 - 8, INTERNAL_H // 2 - 8, 16, 16), 1)
    pygame.draw.circle(target, (200, 200, 100), (INTERNAL_W // 2, INTERNAL_H // 2), 6, 1)
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "gameplay_v1.2.3_clean.png"
    pygame.image.save(target, str(out_path))
    print(f"Saved: {out_path}")
    print(f"Nebula count: {len(bg._nebula)}")
    for i, n in enumerate(bg._nebula):
        print(f"  nebula {i}: x={n.x:.0f} y={n.y:.0f} r={n.radius:.0f} sprite={n.sprite_variant}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
