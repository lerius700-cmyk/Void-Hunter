"""Capture the new galaxy background in isolation."""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Simulate .exe env
dist_assets = ROOT / "dist" / "void-hunter" / "_internal" / "Assets"
if dist_assets.is_dir():
    sys._MEIPASS = str(dist_assets.parent)
    sys.frozen = True
    sys.executable = str(ROOT / "dist" / "void-hunter" / "void-hunter.exe")

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.ui.scrolling_galaxy import ScrollingGalaxyBackground
bg = ScrollingGalaxyBackground(width=320, height=480, scroll_speed_px_per_s=30.0)
print(f"mode: {bg.mode}, total_strip_h: {bg.total_strip_height}")
# Render at scroll position 0
surf = pygame.Surface((320, 480))
surf.fill((0, 0, 0))
bg._scroll_y = 0
bg.draw(surf)
out = ROOT / "tools" / "playtest_out" / "galaxy_v1.28_top.png"
out.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(surf, str(out))
print(f"Saved {out}")
# Render at scroll position 500 (mid-strip)
bg._scroll_y = 500
surf2 = pygame.Surface((320, 480))
surf2.fill((0, 0, 0))
bg.draw(surf2)
out2 = ROOT / "tools" / "playtest_out" / "galaxy_v1.28_mid.png"
pygame.image.save(surf2, str(out2))
print(f"Saved {out2}")
# Render at scroll position 1500 (late-strip, ~2/3 through the loop)
bg._scroll_y = 1500
surf3 = pygame.Surface((320, 480))
surf3.fill((0, 0, 0))
bg.draw(surf3)
out3 = ROOT / "tools" / "playtest_out" / "galaxy_v1.28_late.png"
pygame.image.save(surf3, str(out3))
print(f"Saved {out3}")
