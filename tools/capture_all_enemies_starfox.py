"""Capture: render all 8 redesigned enemy ships (BLOQUE 58.5).

BLOQUE 58.5: visual proof for the nose-DOWN orientation fix.
Socratic insight: enemies move DOWN toward the player, so the nose
(front, direction of motion) must point DOWN. All enemy sprites
have been flipped 180° accordingly. Engines (back of ship) are at
the TOP, wings sweep BACKWARD-AND-UP. SUB_BOSS also gets:
  - Subtle vertical bob (2 Hz, ±1 px) for "warp thrust" feel
  - Engine pulse (6 Hz) for HOT exhaust glow

Output: tools/playtest_out/polish_47_all_enemies_nosedown.png
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
from src.entities.enemies.enemy import ENEMY_CONFIGS, EnemyKind

pygame.init()
SCALE = 4

# Layout: 4 cols x 2 rows, each cell 160x180
CELL_W, CELL_H = 200, 220
COLS, ROWS = 4, 2
HEADER_H = 60
PADDING = 8
W = COLS * CELL_W + PADDING * 2
H = ROWS * CELL_H + HEADER_H + PADDING * 2 + 30
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER — All enemy ships (BLOQUE 58.4)")
screen.fill((8, 12, 24))

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

# Title
title = font_lg.render("ALL ENEMY SHIPS - nose DOWN (BLOQUE 58.6)", True, (255, 255, 255))
screen.blit(title, (12, 8))
sub = font_md.render(
    "Enemies move DOWN, so nose points DOWN. SUB_BOSS = menacing V silhouette (fangs converge at V apex, cyan eye).",
    True, (180, 200, 255),
)
screen.blit(sub, (12, 30))

# Per-enemy drawing functions, mirroring gameplay_runtime._draw_enemy
def draw_silver(x, y, w, h, color):
    return (170, 180, 195) if color == "silver" else color

ENEMIES = [
    (EnemyKind.SCOUT, "SCOUT", "small fast dart"),
    (EnemyKind.CRUISER, "CRUISER", "delta wing + twin cannons"),
    (EnemyKind.HEAVY, "HEAVY", "armored carrier"),
    (EnemyKind.KAMIKAZE, "KAMIKAZE", "suicide dart"),
    (EnemyKind.SNIPER, "SNIPER", "anchored laser"),
    (EnemyKind.DRONE, "DRONE", "small scout"),
    (EnemyKind.TURRET, "TURRET", "rotating 3-spread"),
    (EnemyKind.SUB_BOSS, "SUB_BOSS", "menacing alien hunter"),
]

# We draw each enemy inline (copy of the gameplay_runtime code)
# so the visual is reproducible without spinning up the whole game.
t = 0.0  # local time for animations

def draw_enemy(target, kind, cx, cy, w, h, t):
    if kind == EnemyKind.SCOUT:
        silver = (170, 180, 195)
        silver_dark = (90, 100, 115)
        cyan = (80, 220, 240)
        # Body vertical dart, nose at bottom
        body_top_y = cy - h // 2
        body_bot_y = cy + h // 2
        shoulder_y = body_top_y + 1
        wing_tip_y = shoulder_y - 1
        pygame.draw.polygon(target, silver, [
            (cx, body_bot_y),
            (cx + 1, cy + 1), (cx + 2, shoulder_y),
            (cx + w // 2, wing_tip_y),
            (cx, body_top_y - 1),
            (cx - w // 2, wing_tip_y),
            (cx - 2, shoulder_y), (cx - 1, cy + 1),
        ])
        wing_hi = (200, 210, 225)
        pygame.draw.line(target, wing_hi, (cx + 2, shoulder_y), (cx + w // 2, wing_tip_y), 1)
        pygame.draw.line(target, wing_hi, (cx - 2, shoulder_y), (cx - w // 2, wing_tip_y), 1)
        pygame.draw.line(target, silver_dark, (cx, body_top_y), (cx, body_bot_y - 1), 1)
        pygame.draw.circle(target, cyan, (cx, cy), 2)
        pygame.draw.circle(target, (180, 240, 255), (cx, cy), 1)
        pygame.draw.rect(target, (255, 200, 80), (cx - 1, body_top_y - 1, 2, 1))
    elif kind == EnemyKind.CRUISER:
        silver = (160, 170, 185)
        silver_dark = (85, 95, 110)
        green = (100, 220, 100)
        green_dark = (50, 140, 60)
        body_top_y = cy - h // 2
        body_bot_y = cy + h // 2
        pygame.draw.polygon(target, silver, [
            (cx, body_bot_y), (cx + w // 3, body_top_y + 2),
            (cx + w // 2, body_top_y + 3), (cx + w // 2 - 1, body_top_y + 1),
            (cx + w // 2, body_top_y - 1), (cx, body_top_y - 1),
            (cx - w // 2, body_top_y - 1), (cx - w // 2 + 1, body_top_y + 1),
            (cx - w // 2, body_top_y + 3), (cx - w // 3, body_top_y + 2),
        ])
        pygame.draw.polygon(target, silver_dark, [
            (cx, body_bot_y - 1), (cx + w // 4, body_top_y + 3),
            (cx + w // 4, body_top_y + 2), (cx, body_top_y + 1),
            (cx - w // 4, body_top_y + 2), (cx - w // 4, body_top_y + 3),
        ])
        wing_hi = (195, 205, 220)
        pygame.draw.line(target, wing_hi, (cx, body_bot_y), (cx + w // 2, body_top_y - 1), 1)
        pygame.draw.line(target, wing_hi, (cx, body_bot_y), (cx - w // 2, body_top_y - 1), 1)
        pygame.draw.rect(target, green_dark, (cx - w // 3, cy - 1, 1, 3))
        pygame.draw.rect(target, green_dark, (cx + w // 3, cy - 1, 1, 3))
        pygame.draw.circle(target, green, (cx, cy + 1), 2)
        pygame.draw.circle(target, (200, 255, 200), (cx, cy + 1), 1)
        pygame.draw.rect(target, (255, 200, 80), (cx - w // 3 - 1, body_top_y - 1, 2, 1))
        pygame.draw.rect(target, (255, 200, 80), (cx + w // 3 - 1, body_top_y - 1, 2, 1))
    elif kind == EnemyKind.HEAVY:
        silver = (150, 160, 175)
        silver_dark = (80, 90, 105)
        red = (220, 60, 70)
        red_dark = (130, 30, 35)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(target, silver, rect)
        pygame.draw.rect(target, silver_dark, rect.inflate(-max(2, w // 4), -max(2, h // 4)))
        pygame.draw.rect(target, (190, 200, 215), rect, 1)
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            tcx = cx + dx * (w // 2 - 2)
            tcy = cy + dy * (h // 2 - 2)
            pygame.draw.circle(target, silver_dark, (tcx, tcy), 2)
            pygame.draw.circle(target, red, (tcx, tcy), 1)
        pygame.draw.circle(target, red_dark, (cx, cy), 3)
        pygame.draw.circle(target, red, (cx, cy), 2)
        pygame.draw.circle(target, (255, 200, 200), (cx, cy), 1)
        pygame.draw.rect(target, red_dark, (cx - 1, cy + 1, 2, h // 2 - 2))
        pygame.draw.circle(target, red, (cx, cy + h // 2 - 1), 1)
        pygame.draw.circle(target, (255, 80, 80), (cx - 3, cy + h // 2 - 2), 1)
        pygame.draw.circle(target, (80, 220, 100), (cx + 3, cy + h // 2 - 2), 1)
        pygame.draw.rect(target, (255, 200, 80), (cx - w // 4, cy - h // 2, 2, 1))
        pygame.draw.rect(target, (255, 200, 80), (cx + w // 4 - 2, cy - h // 2, 2, 1))
    elif kind == EnemyKind.KAMIKAZE:
        silver = (180, 130, 80)
        silver_dark = (110, 70, 30)
        orange = (255, 140, 50)
        orange_bright = (255, 220, 130)
        pygame.draw.polygon(target, silver, [
            (cx - w // 2, cy - h // 2), (cx + w // 2, cy - h // 2), (cx, cy + h // 2),
        ])
        pygame.draw.polygon(target, silver_dark, [
            (cx - w // 3, cy - h // 2 + 1), (cx + w // 3, cy - h // 2 + 1), (cx, cy + h // 3),
        ])
        pulse = 200 + int(55 * math.sin(t * 8))
        pygame.draw.circle(target, (pulse, 80, 30), (cx, cy), 2)
        pygame.draw.circle(target, orange_bright, (cx, cy), 1)
        pygame.draw.circle(target, orange, (cx - 1, cy - h // 2), 1)
        pygame.draw.circle(target, orange, (cx + 1, cy - h // 2), 1)
        pygame.draw.circle(target, (255, 255, 200), (cx, cy - h // 2 - 1), 1)
    elif kind == EnemyKind.SNIPER:
        silver = (160, 170, 190)
        silver_dark = (85, 95, 115)
        blue = (100, 160, 255)
        blue_bright = (180, 220, 255)
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(target, silver, rect)
        pygame.draw.rect(target, silver_dark, rect.inflate(-2, -2))
        pygame.draw.rect(target, (195, 205, 220), rect, 1)
        pygame.draw.circle(target, blue, (cx, cy), 2)
        pygame.draw.circle(target, blue_bright, (cx, cy), 1)
        pygame.draw.rect(target, blue, (cx - 1, cy + h // 2, 2, 4))
        pygame.draw.circle(target, blue_bright, (cx, cy + h // 2 + 4), 1)
        pygame.draw.rect(target, silver_dark, (cx - w // 3, cy - h // 2 + 1, 1, h - 2))
        pygame.draw.rect(target, silver_dark, (cx + w // 3, cy - h // 2 + 1, 1, h - 2))
    elif kind == EnemyKind.DRONE:
        silver = (170, 180, 195)
        silver_dark = (90, 100, 115)
        cyan = (80, 220, 240)
        points = []
        for i in range(8):
            a = i * math.pi / 4 + math.pi / 8
            points.append((cx + int(math.cos(a) * w / 2), cy + int(math.sin(a) * h / 2)))
        pygame.draw.polygon(target, silver, points)
        inner_pts = []
        for i in range(8):
            a = i * math.pi / 4
            inner_pts.append((cx + int(math.cos(a) * w / 4), cy + int(math.sin(a) * h / 4)))
        pygame.draw.polygon(target, silver_dark, inner_pts)
        pygame.draw.circle(target, cyan, (cx, cy), 1)
        pygame.draw.circle(target, (200, 240, 255), (cx, cy), 1)
    elif kind == EnemyKind.TURRET:
        silver = (170, 180, 195)
        silver_dark = (90, 100, 115)
        pink = (255, 100, 180)
        pink_bright = (255, 180, 220)
        points = []
        for i in range(6):
            a = i * math.pi / 3 + math.pi / 6
            points.append((cx + int(math.cos(a) * w / 2), cy + int(math.sin(a) * h / 2)))
        pygame.draw.polygon(target, silver, points)
        inner_pts = []
        for i in range(6):
            a = i * math.pi / 3
            inner_pts.append((cx + int(math.cos(a) * w / 3), cy + int(math.sin(a) * h / 3)))
        pygame.draw.polygon(target, silver_dark, inner_pts)
        angle = t * 3
        for spoke in range(3):
            a = angle + spoke * (2 * math.pi / 3)
            ex = cx + int(math.cos(a) * w / 3)
            ey = cy + int(math.sin(a) * h / 3)
            pygame.draw.line(target, pink, (cx, cy), (ex, ey), 1)
            pygame.draw.circle(target, pink_bright, (ex, ey), 1)
        pygame.draw.circle(target, pink, (cx, cy), 2)
        pygame.draw.circle(target, pink_bright, (cx, cy), 1)
    elif kind == EnemyKind.SUB_BOSS:
        # BLOQUE 58.6.1: MENACING V SILHOUETTE — fangs converge at V apex, cyan eye, sharp nose DOWN
        wolf_base = (160, 170, 185)
        wolf_dark = (80, 90, 105)
        wolf_red = (220, 50, 60)
        cyan_eye = (80, 220, 240)
        pink_fang = (255, 100, 180)
        pink_fang_bright = (255, 200, 230)
        body_top_y = cy - h // 2
        body_bot_y = cy + h // 2
        shoulder_y = body_top_y + 2
        mid_wing_y = cy - 1
        wing_tip_dx = w
        wing_tip_y = shoulder_y - 1
        fang_tip_y = body_bot_y + 1
        fang_tip_x_l = cx - 1
        fang_tip_x_r = cx + 1
        # 1) 2 SHARP FANGS angling DOWN-AND-INWARD, CONVERGING at V apex
        pygame.draw.polygon(target, wolf_base, [
            (cx - 2, body_top_y + 1), (cx - 4, body_top_y),
            (fang_tip_x_l, fang_tip_y), (cx - 2, body_bot_y - 1),
        ])
        pygame.draw.polygon(target, wolf_base, [
            (cx + 2, body_top_y + 1), (cx + 4, body_top_y),
            (fang_tip_x_r, fang_tip_y), (cx + 2, body_bot_y - 1),
        ])
        pygame.draw.line(target, wolf_red, (cx - 3, body_top_y + 1), (fang_tip_x_l, fang_tip_y - 1), 1)
        pygame.draw.line(target, wolf_red, (cx + 3, body_top_y + 1), (fang_tip_x_r, fang_tip_y - 1), 1)
        pygame.draw.circle(target, pink_fang, (fang_tip_x_l, fang_tip_y), 1)
        pygame.draw.circle(target, pink_fang, (fang_tip_x_r, fang_tip_y), 1)
        pygame.draw.circle(target, pink_fang_bright, (fang_tip_x_l, fang_tip_y), 1)
        pygame.draw.circle(target, pink_fang_bright, (fang_tip_x_r, fang_tip_y), 1)
        # 2) WINGS behind the fangs (swept back)
        pygame.draw.polygon(target, wolf_base, [
            (cx - 1, shoulder_y), (cx - 4, shoulder_y - 1),
            (cx - wing_tip_dx, wing_tip_y), (cx - wing_tip_dx, wing_tip_y + 2),
            (cx - 2, mid_wing_y),
        ])
        pygame.draw.polygon(target, wolf_base, [
            (cx + 1, shoulder_y), (cx + 4, shoulder_y - 1),
            (cx + wing_tip_dx, wing_tip_y), (cx + wing_tip_dx, wing_tip_y + 2),
            (cx + 2, mid_wing_y),
        ])
        # 3) ENGINES at top
        eng_y = body_top_y
        pygame.draw.rect(target, (255, 180, 60), (cx - 1, eng_y, 1, 2))
        pygame.draw.rect(target, (255, 180, 60), (cx, eng_y, 1, 2))
        # 4) MAIN BODY — sharp nose at BOTTOM
        pygame.draw.polygon(target, wolf_base, [
            (cx, body_bot_y), (cx + 3, mid_wing_y + 1),
            (cx + 1, shoulder_y), (cx, body_top_y + 1),
            (cx - 1, shoulder_y), (cx - 3, mid_wing_y + 1),
        ])
        pygame.draw.line(target, wolf_dark, (cx, body_top_y + 1), (cx, body_bot_y - 1), 1)
        # 5) MENACING CYAN EYE
        eye_pulse = 0.85 + 0.15 * math.sin(t * 3.0)
        eye_r1 = int(4 * eye_pulse)
        eye_r2 = int(3 * eye_pulse)
        eye_r3 = int(2 * eye_pulse)
        pygame.draw.circle(target, (40, 80, 110), (cx, cy), eye_r1 + 1)
        pygame.draw.circle(target, cyan_eye, (cx, cy), eye_r1)
        pygame.draw.circle(target, (200, 240, 255), (cx, cy), eye_r2)
        pygame.draw.circle(target, (255, 255, 255), (cx, cy), eye_r3)
        # 6) Wing leading-edge highlights + red accent
        wing_hi = (195, 205, 220)
        pygame.draw.line(target, wing_hi, (cx - 1, shoulder_y), (cx - wing_tip_dx, wing_tip_y), 1)
        pygame.draw.line(target, wing_hi, (cx + 1, shoulder_y), (cx + wing_tip_dx, wing_tip_y), 1)
        pygame.draw.line(target, wolf_red, (cx - 2, shoulder_y + 1), (cx - wing_tip_dx + 1, wing_tip_y + 1), 1)
        pygame.draw.line(target, wolf_red, (cx + 2, shoulder_y + 1), (cx + wing_tip_dx - 1, wing_tip_y + 1), 1)
        # 7) Wingtip running lights
        pygame.draw.circle(target, (255, 80, 80), (cx - wing_tip_dx, wing_tip_y), 1)
        pygame.draw.circle(target, (255, 80, 80), (cx + wing_tip_dx, wing_tip_y), 1)
        # 8) Subtle outer red halo
        halo = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
        halo_alpha = 40 + int(20 * math.sin(t * 6))
        pygame.draw.ellipse(halo, (*wolf_red, halo_alpha), (0, 0, w + 16, h + 16), 1)
        target.blit(halo, (cx - (w + 16) // 2, cy - (h + 16) // 2))

# Draw each enemy
for i, (kind, name, desc) in enumerate(ENEMIES):
    col = i % COLS
    row = i // COLS
    cell_x = PADDING + col * CELL_W
    cell_y = HEADER_H + PADDING + row * CELL_H
    # Cell background
    cell_rect = pygame.Rect(cell_x, cell_y, CELL_W - 5, CELL_H - 5)
    pygame.draw.rect(screen, (16, 22, 40), cell_rect)
    pygame.draw.rect(screen, (60, 60, 90), cell_rect, 1)
    # Name
    name_lbl = font_md.render(name, True, (255, 255, 255))
    screen.blit(name_lbl, (cell_x + 8, cell_y + 6))
    # Description
    desc_lbl = font_sm.render(desc, True, (140, 140, 160))
    screen.blit(desc_lbl, (cell_x + 8, cell_y + 24))
    # Get the enemy config to use the right size
    cfg = ENEMY_CONFIGS[kind]
    w, h = cfg.width, cfg.height
    # Center of the cell, leaving space for the title
    cx = cell_x + (CELL_W - 5) // 2
    cy = cell_y + 36 + h
    # Scale up for visibility (4x)
    draw_w = w * 4
    draw_h = h * 4
    draw_enemy(screen, kind, cx, cy, draw_w, draw_h, t)

# Footer
foot = font_sm.render(
    "BLOQUE 58.6.1: all 8 enemy sprites nose-DOWN + SUB_BOSS menacing V silhouette  -  visual only, gameplay unchanged",
    True, (140, 140, 160),
)
screen.blit(foot, (12, H - 18))

out_path = ROOT / "tools" / "playtest_out" / "polish_47_all_enemies_nosedown.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
print(f"Enemies rendered: {[e[1] for e in ENEMIES]}")
pygame.quit()
