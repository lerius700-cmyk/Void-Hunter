"""Render a frame of Void-Hunter's gameplay with the new AI galaxy
nebulas so the user can see them in context.

We boot the game, run a few frames of the wave-1 scene, then save
the internal 480x270 surface scaled up to 1920x1080 (4x).
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import sys
from pathlib import Path

import pygame
if not pygame.get_init():
    pygame.init()
if not pygame.mixer.get_init():
    try:
        pygame.mixer.init()
    except pygame.error:
        pass

ROOT = Path("D:/AI/void-hunter")
sys.path.insert(0, str(ROOT))

from src.systems.parallax import ParallaxBackground


def main() -> None:
    # 1920x1080 dummy display so convert_alpha works.
    pygame.display.set_mode((1920, 1080))
    # 1 large off-center nebula (matches gameplay_runtime config)
    bg = ParallaxBackground(
        width=480, height=270, rng_seed=0xC0FFEE58,
        stars_per_layer=8, nebula_count=1,
        nebula_radius_min=100, nebula_radius_max=140,
        spawn_planets=False,
    )
    # Advance time so the nebula drifts into a nice spot.
    for _ in range(int(0.6 * 60)):
        bg.update(1 / 60)
    # Render the background
    target = pygame.Surface((480, 270), pygame.SRCALPHA)
    bg.draw(target)
    # Overlay some text to show the wave + nebula info
    pygame.font.init()
    font = pygame.font.SysFont("monospace", 11, bold=True)
    label = font.render("ACT 1 - WAVE 1/6  [AI GALAXY NEBULA]", False,
                        (240, 240, 100))
    target.blit(label, (10, 10))
    out = pygame.transform.scale(target, (1920, 1080))
    out_dir = ROOT / "tools" / "playtest_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "nebula_ai_galaxy_v1.png"
    pygame.image.save(out, str(out_path))
    print(f"saved {out_path} (1920x1080)")
    # Also save a 2nd variant: 6 nebulas (title screen style)
    bg2 = ParallaxBackground(
        width=480, height=270, rng_seed=0xC0FFEE59,
        stars_per_layer=20, nebula_count=6,
        nebula_radius_min=40, nebula_radius_max=70,
        spawn_planets=True,
    )
    target2 = pygame.Surface((480, 270), pygame.SRCALPHA)
    bg2.draw(target2)
    label2 = font.render("TITLE SCREEN - 6 GALAXIES", False,
                         (240, 240, 100))
    target2.blit(label2, (10, 10))
    out2 = pygame.transform.scale(target2, (1920, 1080))
    out_path2 = out_dir / "nebula_ai_galaxy_title_v1.png"
    pygame.image.save(out2, str(out_path2))
    print(f"saved {out_path2} (1920x1080)")


if __name__ == "__main__":
    main()
