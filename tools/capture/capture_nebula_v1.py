"""BLOQUE 58.14.1: capture the procedural nebula for visual verification.

Boot a fake game with 1 large procedural nebula and save a PNG.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import pygame  # noqa: E402

from src.core.settings import INTERNAL_H, INTERNAL_W  # noqa: E402
from src.systems.parallax import ParallaxBackground  # noqa: E402


def main() -> int:
    pygame.init()
    pygame.display.set_mode((INTERNAL_W * 4, INTERNAL_H * 4), pygame.RESIZABLE)
    internal = pygame.Surface((INTERNAL_W, INTERNAL_H))

    # 1 large off-center procedural nebula (gameplay background config)
    bg = ParallaxBackground(
        width=INTERNAL_W, height=INTERNAL_H,
        rng_seed=0xC0FFEE58,
        stars_per_layer=8,
        nebula_count=1,
        nebula_radius_min=100,
        nebula_radius_max=140,
        spawn_planets=False,
    )
    # Tick a bit so stars are placed
    bg.update(0.0)
    bg.draw(internal)

    scaled = pygame.transform.scale(
        internal, (INTERNAL_W * 4, INTERNAL_H * 4),
    )
    out_dir = ROOT / "tools" / "playtest_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "nebula_procedural_v1.png"
    pygame.image.save(scaled, str(out_path))
    print(f"saved: {out_path}")
    # Also capture the title-screen style (6 small nebulas)
    bg2 = ParallaxBackground(
        width=INTERNAL_W, height=INTERNAL_H,
        rng_seed=0xCAFE2026,
        stars_per_layer=12,
        nebula_count=6,
        nebula_radius_min=40,
        nebula_radius_max=80,
        spawn_planets=True,
    )
    bg2.update(0.0)
    internal2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
    bg2.draw(internal2)
    scaled2 = pygame.transform.scale(
        internal2, (INTERNAL_W * 4, INTERNAL_H * 4),
    )
    out_path2 = out_dir / "nebula_procedural_v1_title.png"
    pygame.image.save(scaled2, str(out_path2))
    print(f"saved: {out_path2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
