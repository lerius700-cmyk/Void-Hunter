"""Capture: render all 11 flight formations in a 4x3 grid.

BLOQUE 58: visual proof for the 11 formation types
(8 from BLOQUE 41-44, +3 from BLOQUE 55, +2 from BLOQUE 56, -2 overlap = 11 total).

Output: tools/playtest_out/polish_43_all_formations.png
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_INVULN"] = "1"
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
from src.systems.wave_manager import parse_formation, spawn_formation, FORMATION_TYPES

pygame.init()

# Each cell: 160x180 (with the playfield inset at 320x480 / 4 scale = 80x120)
CELL_W = 200
CELL_H = 240
COLS = 4
ROWS = 3
HEADER_H = 50
PADDING = 10
SCREEN_W = COLS * CELL_W + PADDING * 2
SCREEN_H = ROWS * CELL_H + HEADER_H + PADDING * 2

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("VOID HUNTER — All 11 Formations")
screen.fill((8, 12, 24))

# Title
font_lg = pygame.font.SysFont("consolas", 24)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)
title = font_lg.render("11 FLIGHT FORMATIONS (BLOQUE 41-56)", True, (255, 255, 255))
screen.blit(title, (16, 12))

# Per-formation count: how many ships each gets for the visual
counts = {
    "line": 5, "v": 5, "arc": 5, "staircase": 5, "squadron": 5,
    "spiral": 8, "hilera": 5, "x": 5, "diamond": 5, "box": 8, "wingman": 5,
}

# Color per family for visual variety
family_colors = {
    "line": (100, 200, 255),
    "v": (255, 180, 100),
    "arc": (180, 255, 100),
    "staircase": (255, 100, 180),
    "squadron": (200, 200, 100),
    "spiral": (180, 100, 255),
    "hilera": (100, 255, 200),
    "x": (255, 100, 100),
    "diamond": (100, 180, 255),
    "box": (255, 220, 100),
    "wingman": (255, 180, 60),
}

# Each formation gets a small playfield (160x140 inside each cell)
PF_W, PF_H = 160, 140
for i, ftype in enumerate(FORMATION_TYPES):
    col = i % COLS
    row = i // COLS
    cell_x = PADDING + col * CELL_W
    cell_y = HEADER_H + PADDING + row * CELL_H
    # Cell background
    cell_rect = pygame.Rect(cell_x, cell_y, CELL_W - 5, CELL_H - 5)
    pygame.draw.rect(screen, (16, 22, 40), cell_rect)
    pygame.draw.rect(screen, (60, 60, 90), cell_rect, 1)
    # Family name
    name_lbl = font_md.render(ftype.upper(), True, (255, 255, 255))
    screen.blit(name_lbl, (cell_x + 8, cell_y + 6))
    # Subtitle: count
    sub = font_sm.render(f"{counts.get(ftype, 5)} ships", True, (140, 140, 160))
    screen.blit(sub, (cell_x + 8, cell_y + 24))
    # Generate spawns
    f = parse_formation({
        "formation_type": ftype,
        "enemy_type": "SCOUT",
        "count": counts.get(ftype, 5),
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 30,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    # Playfield origin (centered horizontally in the cell, top 32px from cell top)
    pf_x = cell_x + (CELL_W - 5 - PF_W) // 2
    pf_y = cell_y + 38
    # Playfield frame
    pf_rect = pygame.Rect(pf_x, pf_y, PF_W, PF_H)
    pygame.draw.rect(screen, (24, 30, 50), pf_rect)
    pygame.draw.rect(screen, (80, 80, 120), pf_rect, 1)
    # Spawn points (mapped to local playfield 320x480 -> PF_W x PF_H)
    color = family_colors.get(ftype, (200, 200, 200))
    for sp in spawns:
        lx = pf_x + (sp.x / 320.0) * PF_W
        ly = pf_y + (sp.y / 480.0) * PF_H
        # Triangle ship
        size = 6
        pygame.draw.polygon(screen, color, [
            (lx, ly - size),
            (lx - size * 0.6, ly + size * 0.5),
            (lx + size * 0.6, ly + size * 0.5),
        ])

# Legend
legend = font_sm.render(
    "BLOQUE 41-44: line/v/arc/staircase/squadron | "
    "BLOQUE 55: spiral/hilera/x | BLOQUE 56: diamond/box/wingman",
    True, (180, 180, 200),
)
screen.blit(legend, (16, SCREEN_H - 18))

out_path = ROOT / "tools" / "playtest_out" / "polish_43_all_formations.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
print(f"Formations rendered: {list(FORMATION_TYPES)}")
pygame.quit()
