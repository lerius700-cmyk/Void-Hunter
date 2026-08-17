"""BLOQUE 58.14.4: visual test for the GAMEPLAY background after
the 2-large-galaxy refactor. Simulates the new gameplay background
(parallax_bg with nebula_count=2, radius 80-110) and saves a PNG.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from src.systems.parallax import ParallaxBackground
from src.core.settings import INTERNAL_W, INTERNAL_H


def main() -> int:
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    # The new gameplay config: 2 large spiral galaxies
    bg = ParallaxBackground(
        width=INTERNAL_W,
        height=INTERNAL_H,
        stars_per_layer=8,
        nebula_count=2,
        nebula_radius_min=80,
        nebula_radius_max=110,
        spawn_planets=False,
    )
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    for _ in range(60):
        bg.update(0.016)
    bg.draw(target)
    # Add a fake player ship
    pygame.draw.rect(target, (255, 100, 100),
                     (INTERNAL_W // 2 - 8, INTERNAL_H // 2 - 8, 16, 16), 1)
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "gameplay_bg_v1.2.3_2galaxies.png"
    pygame.image.save(target, str(out_path))
    print(f"Saved: {out_path}")
    print(f"Visible nebulas: {len(bg._nebula)}")
    for i, n in enumerate(bg._nebula):
        print(f"  nebula {i}: x={n.x:.0f} y={n.y:.0f} r={n.radius:.0f} "
              f"sprite_variant={n.sprite_variant}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
