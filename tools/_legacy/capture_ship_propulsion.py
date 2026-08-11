"""Capture: Ship in PROPULSION state (BLOQUE 58.30 visual proof).

The ship palette switches to BLUE + WHITE when state == PROPULSION
(matching the Tron trail). This capture shows the difference
between the normal palette (left) and the propulsion palette (right).
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_INVULN"] = "1"
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import math
import pygame
pygame.init()

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.entities.player.player import Player, PlayerState
from src.ui.gameplay_runtime import GameplayRuntime

W, H = 720, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - Ship PROPULSION palette (BLOQUE 58.30)")
screen.fill((4, 8, 16))

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

title = font_lg.render(
    "SHIP PALETTE  -  normal (left) vs PROPULSION (right)  (BLOQUE 58.30)", True, (255, 255, 255),
)
screen.blit(title, (12, 10))
sub = font_md.render(
    "When the propulsor activates, the ship turns BLUE + WHITE to match the Tron trail.",
    True, (180, 220, 255),
)
screen.blit(sub, (12, 34))

# Build a runtime-like draw: we just call _draw_player with a fake ox/oy
rt = GameplayRuntime.__new__(GameplayRuntime)
rt._player = Player()
rt._t = 0.0
rt._player.x = 200
rt._player.y = 240
rt._player.tilt = 0.0
rt._player.current_tilt = 0.0
rt._player.nose_angle = 0.0
rt._player.current_nose_angle = 0.0
rt._player.dash_iframes_left = 0
rt._player.respawn_invuln = 0.0
rt._player.dash_heat = 0.0
rt._muzzle_flash = 0.0

# Left ship: IDLE state (normal palette)
rt._player.state = PlayerState.IDLE
rt._draw_player(screen, 0, 0)
label = font_sm.render("IDLE (normal)", True, (220, 220, 255))
screen.blit(label, (175, 270))

# Right ship: PROPULSION state (blue+white)
rt._player.x = 520
rt._player.state = PlayerState.PROPULSION
rt._draw_player(screen, 0, 0)
label = font_sm.render("PROPULSION (blue+white)", True, (140, 200, 255))
screen.blit(label, (455, 270))

# Footer
foot1 = font_sm.render(
    "BLOQUE 58.30: when in PROPULSION, body=w, wings=blue, canopy=cyan-white, ", True, (200, 200, 230),
)
screen.blit(foot1, (12, 430))
foot2 = font_sm.render(
    "                stripe=royal-blue, engines=white-blue, wing-tip lasers=blue",
    True, (200, 200, 230),
)
screen.blit(foot2, (12, 444))

out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "polish_58_ship_propulsion.png"
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
