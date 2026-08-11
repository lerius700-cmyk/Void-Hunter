"""Capture: redesigned HUD (BLOQUE 58.14).

Visual proof of the new didactic, organized, pixel-aligned HUD:
  - 3 left-column sections (VITALS, LOADOUT, TACTICAL)
  - 1 right-column section (SCORE)
  - Every value has a clear label (HP, RINGS, TECH, BOMBS, WEAPON, DASH, MULT)
  - All elements snap to a 4px grid, no overlap, no cut-off text
  - Dash heat shows state text (OK / WARM / HOT) for didactic feedback

Output: tools/playtest_out/polish_58_hud_redesign.png
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_INVULN"] = "1"
import sys
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
from src.core.settings import INTERNAL_W, INTERNAL_H

pygame.init()
W, H = 720, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - HUD redesign (BLOQUE 58.14)")

# Use the new HUD directly
from src.ui.hud import HUD
from src.entities.player import Player
from src.systems.weapon_system import WeaponSystem, WeaponPath, WeaponLevel
from src.systems.scoring_system import ScoringSystem

# Create a mock game state
player = Player()
player.hp = 28
player.hp_max = 30
player.gold_rings = 2
player.hp_doubled = False
player.tech_upgrades = ["HP_BOOST_10", "GOLIATH_SUMMON"]
player.bombs = 3
player.bombs_max = 3
player.dash_heat = 25.0  # mid-range

weapon = WeaponSystem()
weapon.path = WeaponPath.PLASMA
weapon.level = WeaponLevel.L2
weapon.xp = 8

scoring = ScoringSystem()
scoring.score = 12345
scoring.kills = 67
scoring.multiplier_index = 2  # 4x
scoring.streak_count = 5

# Render the HUD on a 320x480 internal surface
internal_surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
internal_surf.fill((8, 12, 24))

hud = HUD()
hud.draw(internal_surf, player, weapon, scoring, t=0.5)

# Scale 2x for visibility on the capture
SCALE = 2
scaled = pygame.transform.scale(internal_surf, (INTERNAL_W * SCALE, INTERNAL_H * SCALE))
screen.blit(scaled, (0, 0))

# Add labels
font = pygame.font.SysFont("consolas", 14)
font_small = pygame.font.SysFont("consolas", 10)

# Right-side annotation
ann_x = INTERNAL_W * SCALE + 16
y = 16
title = font.render("BLOQUE 58.14", True, (255, 255, 255))
screen.blit(title, (ann_x, y))
y += 22
subtitle = font_small.render("HUD redesign", True, (180, 220, 255))
screen.blit(subtitle, (ann_x, y))
y += 24
items = [
    "Sections:",
    "  VITALS  - HP / RINGS / TECH",
    "  LOADOUT - BOMBS / WEAPON+XP",
    "  TACTICAL- DASH heat / MULT",
    "  SCORE   - top right",
    "",
    "Design rules:",
    "  - 4px margin grid",
    "  - 6px section gap",
    "  - 2px row gap",
    "  - Every value has a label",
    "  - No element overflows",
    "    (max x = 316, max y < 120)",
    "  - Dash heat shows OK/WARM/HOT",
    "  - HP shows exact value 28/30",
    "  - Consolas font (deterministic)",
]
for line in items:
    color = (200, 220, 240) if line.startswith("  ") else (255, 255, 255)
    if line.endswith(":"):
        color = (180, 220, 255)
    screen.blit(font_small.render(line, True, color), (ann_x, y))
    y += 14

# Save
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "polish_58_hud_redesign.png"
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
