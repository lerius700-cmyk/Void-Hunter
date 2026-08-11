"""Capture: render the new dash heat bar HUD element (BLOQUE 58.8.1).

Visual proof that the Star Fox style dash overheat bar is in place:
- 4 frames showing different heat levels (0%, 40%, 75%, 100% overheat)
- Color shifts cyan -> yellow -> red as heat increases
- Threshold marker (small vertical line) shows where dash becomes available again
- DASH and PROPULSION share the same heat bar
- DASH: flat +10 per use (click, < 0.15s)
- PROPULSION: continuous +30/s while held (hold, >= 0.15s, x2 speed + light trail)
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
from src.core.settings import INTERNAL_W, INTERNAL_H
from src.ui.hud import HUD
from src.entities.player.player import Player

pygame.init()
W, H = 720, 220
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - DASH HEAT BAR (BLOQUE 58.8)")
screen.fill((8, 12, 24))

font_lg = pygame.font.SysFont("consolas", 18)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

# Title
title = font_lg.render("DASH HEAT BAR  -  BLOQUE 58.8 (Star Fox style overheat)", True, (255, 255, 255))
screen.blit(title, (12, 8))
sub = font_md.render("Color shifts cyan -> yellow -> red as heat builds. Threshold marker = resume point.", True, (180, 200, 255))
screen.blit(sub, (12, 28))

# 4 frames at different heat levels
hud = HUD()
hud._ensure_fonts()

heat_levels = [
    (0.0, "COOL  (dash available)"),
    (40.0, "WARM  (still OK)"),
    (75.0, "HOT  (almost overheated)"),
    (100.0, "OVERHEAT  (dash blocked)"),
]

cell_w = 160
for i, (heat, label) in enumerate(heat_levels):
    cx = 12 + i * (cell_w + 12)
    cy = 60
    # Mock player
    p = Player()
    p.dash_heat = heat
    # Mini HUD area
    cell_rect = pygame.Rect(cx, cy, cell_w - 6, 130)
    pygame.draw.rect(screen, (16, 22, 40), cell_rect)
    pygame.draw.rect(screen, (60, 60, 90), cell_rect, 1)
    # Draw just the heat bar
    hud._draw_dash_heat(screen, p, x=cx + 8, y=cy + 16, t=0.5)
    # Label
    lbl = font_sm.render(label, True, (220, 220, 220))
    screen.blit(lbl, (cx + 8, cy + 36))
    pct = font_sm.render(f"{heat:.0f}%", True, (180, 180, 200))
    screen.blit(pct, (cx + 8, cy + 50))

# Footer
foot = font_sm.render(
    "BLOQUE 58.8.1: shift click (< 0.15s) = DASH (+10 heat)  -  "
    "shift hold (>= 0.15s) = PROPULSION (+30/s heat, x2 speed, light trail)  -  "
    "auto-cancel at 100%",
    True, (140, 140, 160),
)
screen.blit(foot, (12, H - 16))

out_path = ROOT / "tools" / "playtest_out" / "polish_50_dash_heat_bar.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
pygame.quit()
