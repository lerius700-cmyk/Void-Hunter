"""Capture: render a Bezier curve with control points and ship markers.

BLOQUE 58: visual proof for BezierPath (BLOQUE 56).
Shows a cubic bezier curve from off-screen top through control points
to the GOLIATH anchor position, with the curve samples marked.

Output: tools/playtest_out/polish_41_bezier_curve.png
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
from src.systems.bezier_path import BezierPath, ControlPoint
from src.core.settings import INTERNAL_W, INTERNAL_H

pygame.init()
INTERNAL_W = 320
INTERNAL_H = 480
SCALE = 3
SCREEN_W, SCREEN_H = INTERNAL_W * SCALE, INTERNAL_H * SCALE
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("VOID HUNTER — Bezier Path Visualization")

# Dark space background
screen.fill((8, 12, 24))

# GOLIATH-style dramatic entrance path
path = BezierPath([
    ControlPoint(160, -40),    # off-screen top
    ControlPoint(60, 80),      # curve in from the left
    ControlPoint(260, 80),     # curve out to the right
    ControlPoint(160, 80),     # land at boss anchor
])

# Pre-bake for smooth render
path.prebake(steps=80)

# Draw the curve as a polyline (cyan, thick)
points: list[tuple[int, int]] = []
for i in range(len(path._cache) + 1):
    t = i / 80
    x, y = path.eval(t)
    points.append((int(x * SCALE), int(y * SCALE)))
pygame.draw.lines(screen, (0, 220, 255), False, points, 3)

# Draw control points (red dots with white outline)
for i, cp in enumerate(path._cps):
    cx, cy = int(cp.x * SCALE), int(cp.y * SCALE)
    pygame.draw.circle(screen, (255, 100, 100), (cx, cy), 8)
    pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 8, 2)
    font = pygame.font.SysFont("consolas", 16)
    label = font.render(f"P{i}", True, (255, 255, 255))
    screen.blit(label, (cx + 12, cy - 8))

# Draw sample points along the curve (yellow small dots)
for i in range(0, 81, 8):
    t = i / 80
    x, y = path.eval(t)
    pygame.draw.circle(
        screen, (255, 220, 80), (int(x * SCALE), int(y * SCALE)), 3
    )

# Draw a "ship" at the start and at the boss anchor
def draw_ship(x: float, y: float, color: tuple[int, int, int]) -> None:
    px, py = int(x * SCALE), int(y * SCALE)
    # Triangle ship pointing up
    pygame.draw.polygon(screen, color, [
        (px, py - 8),
        (px - 6, py + 6),
        (px + 6, py + 6),
    ])
    pygame.draw.polygon(screen, (255, 255, 255), [
        (px, py - 8),
        (px - 6, py + 6),
        (px + 6, py + 6),
    ], 1)

# Start: red ship (off-screen)
draw_ship(160, -40, (200, 60, 60))
# End: green ship (boss anchor)
draw_ship(160, 80, (60, 220, 100))

# Title + legend
font_lg = pygame.font.SysFont("consolas", 22)
font_md = pygame.font.SysFont("consolas", 14)
title = font_lg.render("BEZIER PATH (BLOQUE 56)", True, (255, 255, 255))
screen.blit(title, (16, 16))
legend = [
    "Cyan curve: cubic bezier (P0..P3)",
    "Red dots: control points",
    "Yellow dots: pre-baked samples (80 steps)",
    "Red ship: start | Green ship: GOLIATH anchor",
]
for i, line in enumerate(legend):
    screen.blit(font_md.render(line, True, (200, 200, 200)), (16, 48 + i * 18))

# Output
out_path = ROOT / "tools" / "playtest_out" / "polish_41_bezier_curve.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
pygame.quit()
