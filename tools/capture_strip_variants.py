"""Capture the 4 BLOQUE 58.15 galaxy strip variants as PNGs for visual review.

Generates for each variant:
  - variant_N_playfield.png : 320x480 playfield view (what the player sees)
  - variant_N_strip.png     : 240x720 (downscaled 2x) view of the full 480x1440 strip
  - variant_N_scroll_TTs.png: playfield view at scroll T seconds (4 positions per variant)

Usage:
  python tools/capture_strip_variants.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Headless rendering
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.core.settings import INTERNAL_H, INTERNAL_W  # noqa: E402
from src.systems.parallax import (  # noqa: E402
    GALAXY_STRIP_H,
    GALAXY_STRIP_W,
    ParallaxBackground,
)

OUT_DIR = _ROOT / "release" / "strip_variants"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    pygame.init()
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    scroll_positions_s = (0.0, 5.0, 15.0, 30.0)
    for variant in range(4):
        bg = ParallaxBackground(rng_seed=0xC0FFEE58)
        bg.set_strip_variant(variant)
        # Playfield view at offset 0
        target.fill((0, 0, 0))
        bg.draw(target)
        pygame.image.save(target, str(OUT_DIR / f"variant_{variant}_playfield.png"))
        # Full strip (downscaled 2x for visibility)
        strip = bg._strip_surfaces[variant]  # noqa: SLF001
        scaled = pygame.transform.scale(
            strip, (GALAXY_STRIP_W // 2, GALAXY_STRIP_H // 2)
        )
        pygame.image.save(scaled, str(OUT_DIR / f"variant_{variant}_strip.png"))
        # Playfield views at 4 scroll positions
        for s in scroll_positions_s:
            bg._strip_y_offset = (s * 25.0) % GALAXY_STRIP_H  # noqa: SLF001
            target.fill((0, 0, 0))
            bg.draw(target)
            pygame.image.save(
                target, str(OUT_DIR / f"variant_{variant}_scroll_{int(s):02d}s.png")
            )
        print(f"  [ok] variant {variant}: playfield + strip + 4 scroll positions")
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
