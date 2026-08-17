"""BLOQUE 58.14.4: visual test for the new galaxy sprites.

Renders the gameplay background with 1 large nebula using the new
galaxy_sprite_0N.png at the actual gameplay radius (100-140), and
saves a screenshot to tools/playtest_out/nebula_v2_test.png.

If the result looks like a real spiral galaxy (arms, stars, dust lanes)
we know the v1.2.2 nebula fix is working.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src/ is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from src.systems.parallax import ParallaxBackground
from src.core.settings import INTERNAL_W, INTERNAL_H


def main() -> int:
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    # Use the SAME config the game uses for gameplay:
    # 1 large nebula, radius 100-140, sparse stars.
    bg = ParallaxBackground(
        width=INTERNAL_W,
        height=INTERNAL_H,
        stars_per_layer=12,
        nebula_count=1,
        nebula_radius_min=100,
        nebula_radius_max=140,
        spawn_planets=False,
    )
    # Force the nebula to the center for a clear shot
    bg._nebula[0].x = INTERNAL_W * 0.5
    bg._nebula[0].y = INTERNAL_H * 0.5
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    bg.update(0.016)
    bg.draw(target)
    # Add a fake player ship in the center for scale reference
    pygame.draw.rect(target, (255, 100, 100),
                     (INTERNAL_W // 2 - 8, INTERNAL_H // 2 - 8, 16, 16), 1)
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "nebula_v2_test.png"
    pygame.image.save(target, str(out_path))
    # Also save a title-screen density version (6 nebulas, small)
    bg2 = ParallaxBackground(
        width=INTERNAL_W,
        height=INTERNAL_H,
        stars_per_layer=50,
        nebula_count=6,
        nebula_radius_min=30,
        nebula_radius_max=60,
        spawn_planets=False,
    )
    target2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
    bg2.update(0.016)
    bg2.draw(target2)
    out_path2 = out_dir / "nebula_v2_title_test.png"
    pygame.image.save(target2, str(out_path2))
    print(f"Saved: {out_path}")
    print(f"Saved: {out_path2}")
    print(f"Nebula sprite: {bg._nebula[0].surface.get_size()}, "
          f"variant={bg._nebula[0].sprite_variant}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
