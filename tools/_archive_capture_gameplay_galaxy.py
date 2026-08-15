"""Capture the gameplay background by directly running the runtime."""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Simulate the .exe env so it loads the bundled assets
dist_assets = ROOT / "dist" / "void-hunter" / "_internal" / "Assets"
if dist_assets.is_dir():
    sys._MEIPASS = str(dist_assets.parent)
    sys.frozen = True
    sys.executable = str(ROOT / "dist" / "void-hunter" / "void-hunter.exe")

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.ui.gameplay_runtime import GameplayRuntime

# No-op transition
def noop(s): pass

rt = GameplayRuntime(transition_to=noop, is_boss=False, act=1)
rt.on_enter()

# Tick a few frames so the player ship appears
for _ in range(30):
    rt.update(1.0 / 60.0)

# Capture the gameplay surface
surf = pygame.Surface((320, 480))
surf.fill((0, 0, 0))
rt.draw(surf)
out = ROOT / "tools" / "playtest_out" / "gameplay_v1.28.png"
out.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(surf, str(out))
print(f"Saved {out}")
print(f"galaxy_bg mode: {rt._galaxy_bg.mode}")
print(f"galaxy_bg total_strip_h: {rt._galaxy_bg.total_strip_height}")
print(f"galaxy_bg is_ready: {rt._galaxy_bg.is_ready}")
