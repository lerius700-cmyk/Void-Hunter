"""Debug: simulate the .exe environment to check why ScrollingGalaxyBackground
is not loading the panels.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Simulate the .exe environment by setting _MEIPASS to point at the dist folder
# (same as the .exe sees at runtime)
dist_assets = ROOT / "dist" / "void-hunter" / "_internal" / "Assets"
if dist_assets.is_dir():
    sys._MEIPASS = str(dist_assets.parent)
    sys.frozen = True
    sys.executable = str(ROOT / "dist" / "void-hunter" / "void-hunter.exe")
    print(f"[simulating .exe] _MEIPASS={sys._MEIPASS}")
else:
    print(f"[dev mode] Assets dir: {ROOT / 'Assets'}")

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.ui.scrolling_galaxy import ScrollingGalaxyBackground, _find_assets_dir, _load_image

print(f"assets dir found: {_find_assets_dir()}")
strip = _load_image("galaxy_strip", 320)
print(f"galaxy_strip loaded: {strip}")
for i in range(3):
    p = _load_image(f"galaxy_panel_{i}", 320)
    print(f"galaxy_panel_{i} loaded: {p}")
    if p:
        print(f"  size: {p.get_size()}")

bg = ScrollingGalaxyBackground(width=320, height=480)
print(f"\nScrollingGalaxyBackground:")
print(f"  mode: {bg.mode}")
print(f"  is_ready: {bg.is_ready}")
print(f"  total_strip_height: {bg.total_strip_height}")
print(f"  has _strip: {bg._strip is not None}")
print(f"  has _panels: {bg._panels}")
