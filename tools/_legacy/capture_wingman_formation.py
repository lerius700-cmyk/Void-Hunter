"""Capture: render WINGMAN formation (V-shape leader-follower).

BLOQUE 58: visual proof for WINGMAN formation (BLOQUE 56).
Shows 1 leader at the apex + 4 wingmen trailing in a V.

Output: tools/playtest_out/polish_42_wingman_formation.png
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
from src.systems.wave_manager import parse_formation, spawn_formation
from src.core.settings import INTERNAL_W, INTERNAL_H

pygame.init()
SCALE = 3
screen = pygame.display.set_mode((INTERNAL_W * SCALE, INTERNAL_H * SCALE))
pygame.display.set_caption("VOID HUNTER — WINGMAN Formation")
screen.fill((8, 12, 24))

# WINGMAN formation with 5 ships (1 leader + 4 wingmen)
f = parse_formation({
    "formation_type": "wingman",
    "enemy_type": "SCOUT",
    "count": 5,
    "spacing_px": 32,
    "entry_axis": "top",
    "pattern_speed": 50,
    "telegraph_frames": 30,
})
spawns = spawn_formation(f)
print(f"WINGMAN: {len(spawns)} ships")

font_lg = pygame.font.SysFont("consolas", 22)
font_md = pygame.font.SysFont("consolas", 14)
title = font_lg.render("WINGMAN FORMATION (BLOQUE 56)", True, (255, 255, 255))
screen.blit(title, (16, 16))

# Draw the V-shape connecting line behind the ships
v_points: list[tuple[int, int]] = []
for sp in spawns:
    v_points.append((int(sp.x * SCALE), int(sp.y * SCALE)))
pygame.draw.lines(screen, (60, 120, 200), False, v_points, 2)

# Draw each ship: leader is bigger and gold, wingmen smaller and blue
for i, sp in enumerate(spawns):
    px, py = int(sp.x * SCALE), int(sp.y * SCALE)
    if i == 0:
        # Leader (apex, gold)
        color = (255, 200, 60)
        size = 12
        label = "LEADER"
    else:
        # Wingman
        color = (100, 180, 255)
        size = 9
        label = f"WINGMAN {i}"
    # Triangle ship pointing up
    pygame.draw.polygon(screen, color, [
        (px, py - size),
        (px - size * 0.7, py + size * 0.7),
        (px + size * 0.7, py + size * 0.7),
    ])
    pygame.draw.polygon(screen, (255, 255, 255), [
        (px, py - size),
        (px - size * 0.7, py + size * 0.7),
        (px + size * 0.7, py + size * 0.7),
    ], 1)
    # Label
    lbl = font_md.render(label, True, (220, 220, 220))
    screen.blit(lbl, (px + size + 4, py - 8))

# Draw connecting lines from leader to each wingman (the "follow" relationship)
leader = spawns[0]
for sp in spawns[1:]:
    pygame.draw.line(
        screen, (80, 80, 200),
        (int(leader.x * SCALE), int(leader.y * SCALE)),
        (int(sp.x * SCALE), int(sp.y * SCALE)),
        1,
    )

# Legend
legend = [
    "WINGMAN: V-shaped leader-follower (Star Fox / R-Type style)",
    "Yellow ship = leader at apex",
    "Blue ships = wingmen trailing in V",
    "Blue lines = follow relationship (leader.pos + offset)",
    "All ships share vy so V shape is preserved during descent",
]
for i, line in enumerate(legend):
    screen.blit(font_md.render(line, True, (200, 200, 200)), (16, 48 + i * 18))

out_path = ROOT / "tools" / "playtest_out" / "polish_42_wingman_formation.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
pygame.quit()
