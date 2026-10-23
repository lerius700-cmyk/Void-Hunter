"""BLOQUE 73.7: capture the new MainMenuScene at 3x zoom, with the
3 top-level items highlighted and the BACKGROUND submenu open.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.core.game import Game
from src.core.scene_manager import GameState

out = ROOT / "tools" / "playtest_out"
out.mkdir(parents=True, exist_ok=True)

g = Game()
g.scenes.current_state = GameState.MENU  # force menu active
menu = g.scenes.scenes[GameState.MENU]
menu.on_enter()

# Frame 1: top level, cursor on NEW GAME
menu._cursor = 0
surf = pygame.Surface((320, 480))
surf.fill((0, 0, 0))
menu.draw(surf)
pygame.image.save(pygame.transform.scale(surf, (320 * 3, 480 * 3)),
                 str(out / "menu_top_newgame.png"))

# Frame 2: top level, cursor on BOSS TIME
menu._cursor = 1
surf = pygame.Surface((320, 480))
surf.fill((0, 0, 0))
menu.draw(surf)
pygame.image.save(pygame.transform.scale(surf, (320 * 3, 480 * 3)),
                 str(out / "menu_top_bosstime.png"))

# Frame 3: BACKGROUND submenu open
menu._cursor = 2
menu._activate()  # opens submenu
surf = pygame.Surface((320, 480))
surf.fill((0, 0, 0))
menu.draw(surf)
pygame.image.save(pygame.transform.scale(surf, (320 * 3, 480 * 3)),
                 str(out / "menu_bg_submenu.png"))

# Frame 4: pick SPACE VOID (cursor 0 in submenu) — already from previous test
menu._bg_cursor = 0
surf = pygame.Surface((320, 480))
surf.fill((0, 0, 0))
menu.draw(surf)
pygame.image.save(pygame.transform.scale(surf, (320 * 3, 480 * 3)),
                 str(out / "menu_bg_space_void.png"))

# Frame 5: pick ASTEROID NEBULA (cursor 1 in submenu)
menu._bg_cursor = 1
surf = pygame.Surface((320, 480))
surf.fill((0, 0, 0))
menu.draw(surf)
pygame.image.save(pygame.transform.scale(surf, (320 * 3, 480 * 3)),
                 str(out / "menu_bg_asteroid_nebula.png"))

print("wrote 5 menu captures to", out)
for p in sorted(out.glob("menu_*.png")):
    print("  -", p.name)