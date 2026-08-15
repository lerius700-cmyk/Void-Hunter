"""BLOQUE 58.12: capture the new sparse gameplay background."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT))
import pygame
pygame.init()
pygame.display.set_mode((320, 480))
from src.ui.gameplay_runtime import GameplayRuntime
rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
rt.on_enter()
rt.enable_procedural_patterns(seed=1, floor=1, spawn_interval=2.0)
out_dir = ROOT / "tools" / "playtest_out"
# Tick a few seconds so patterns spawn + parallax starts
for tick in range(240):
    rt.update(1.0 / 60.0)
surf = pygame.Surface((320, 480))
surf.fill((0, 0, 0))
rt.draw(surf)
out = out_dir / "v1.12_sparse_background.png"
pygame.image.save(surf, str(out))
print(f"Saved {out.name}")
