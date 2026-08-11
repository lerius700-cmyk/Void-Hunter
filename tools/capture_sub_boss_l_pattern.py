"""Capture: 4-entry movement cycle for SUB_BOSS (BLOQUE 58.6.4).

Visual proof of the new movement rule:
  Entry 0: top -> bottom (straight line, no L)
  Entry 1: bottom -> right (L to side wall, vertical then horizontal)
  Entry 2: right -> left   (straight line, no L)
  Entry 3: left -> down    (L to top/bottom wall, horizontal then vertical)
  Entry 4: down -> up      (straight line, no L)
  Entry 5: up -> left      (L to side wall)
  ... and so on, alternating L-to-side and L-to-top/bottom every 2 entries.

BLOQUE 58.6.4 invariant: the sub-boss ALWAYS re-enters through the same
wall it just exited (opposite direction). The L pattern only changes WHICH
side wall (or top/bottom) it exits through, not the re-entry wall.

Output: tools/playtest_out/polish_52_sub_boss_l_pattern.png
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
from src.entities.enemies.enemy import EnemyKind, ENEMY_CONFIGS

pygame.init()
W, H = 760, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - SUB_BOSS L pattern (BLOQUE 58.6.4)")
screen.fill((8, 12, 24))

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

title = font_lg.render(
    "SUB_BOSS  -  4-entry movement cycle with L turns (BLOQUE 58.6.4)", True, (255, 255, 255),
)
screen.blit(title, (12, 10))
sub = font_md.render(
    "Same wall re-entry  -  L to side walls / L to top-bottom alternates every 2 entries",
    True, (180, 200, 255),
)
screen.blit(sub, (12, 34))

cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
print(f"SUB_BOSS size: {cfg.width}x{cfg.height}, speed={cfg.speed}")


def draw_sub_boss_hunter(
    target: pygame.Surface, cx: int, cy: int, w: int, h: int, t: float,
) -> None:
    """Reuse the clean wide V silhouette from BLOQUE 58.6.2 capture."""
    wolf_base = (160, 170, 185)
    wolf_dark = (80, 90, 105)
    wolf_red = (220, 50, 60)
    cyan_eye = (80, 220, 240)
    pink_fang = (255, 100, 180)
    pink_fang_bright = (255, 200, 230)
    bob = int(round(math.sin(t * 2.0 * math.pi) * 1.0))
    cy_b = cy + bob
    engine_pulse = 0.7 + 0.3 * (0.5 + 0.5 * math.sin(t * 6.0))
    eye_pulse = 0.85 + 0.15 * math.sin(t * 3.0)
    body_top_y = cy_b - h // 2
    body_bot_y = cy_b + h // 2
    shoulder_y = body_top_y + 2
    fang_tip_y = body_bot_y + 1
    fang_tip_x_l = cx
    fang_tip_x_r = cx
    pygame.draw.polygon(target, wolf_base, [
        (cx - 3, body_top_y + 1), (cx - 7, body_top_y),
        (fang_tip_x_l, fang_tip_y), (cx - 1, body_bot_y - 1),
    ])
    pygame.draw.polygon(target, wolf_base, [
        (cx + 3, body_top_y + 1), (cx + 7, body_top_y),
        (fang_tip_x_r, fang_tip_y), (cx + 1, body_bot_y - 1),
    ])
    pygame.draw.line(target, wolf_red, (cx - 6, body_top_y), (fang_tip_x_l, fang_tip_y - 1), 1)
    pygame.draw.line(target, wolf_red, (cx + 6, body_top_y), (fang_tip_x_r, fang_tip_y - 1), 1)
    pygame.draw.circle(target, pink_fang, (fang_tip_x_l, fang_tip_y), 1)
    pygame.draw.circle(target, pink_fang, (fang_tip_x_r, fang_tip_y), 1)
    pygame.draw.circle(target, pink_fang_bright, (fang_tip_x_l, fang_tip_y), 1)
    pygame.draw.circle(target, pink_fang_bright, (fang_tip_x_r, fang_tip_y), 1)
    spine_y_top = shoulder_y
    spine_y_bot = body_bot_y - 1
    pygame.draw.line(target, wolf_dark, (cx, spine_y_top), (cx, spine_y_bot), 1)
    eng_y = body_top_y
    eng_c = (
        int(255 * engine_pulse),
        int(180 * engine_pulse),
        int(60 * engine_pulse),
    )
    pygame.draw.rect(target, eng_c, (cx - 1, eng_y, 1, 2))
    pygame.draw.rect(target, eng_c, (cx, eng_y, 1, 2))
    mid_y = cy_b - 1
    pygame.draw.polygon(target, wolf_base, [
        (cx, body_bot_y),
        (cx + 1, mid_y),
        (cx, body_top_y + 1),
        (cx - 1, mid_y),
    ])
    eye_r1 = int(4 * eye_pulse)
    eye_r2 = int(3 * eye_pulse)
    eye_r3 = int(2 * eye_pulse)
    pygame.draw.circle(target, (40, 80, 110), (cx, cy_b), eye_r1 + 1)
    pygame.draw.circle(target, cyan_eye, (cx, cy_b), eye_r1)
    pygame.draw.circle(target, (200, 240, 255), (cx, cy_b), eye_r2)
    pygame.draw.circle(target, (255, 255, 255), (cx, cy_b), eye_r3)


# Draw 6 mini-panels (one per entry) showing the movement
PANEL_W, PANEL_H = 180, 160
PANELS_X0, PANELS_Y0 = 14, 80
PANELS_GAP_X = 8
PANELS_GAP_Y = 12

entries = [
    # (label, wall_in, path, wall_out, kind)
    ("0: top -> bot", "top", "v", "bottom", "straight"),
    ("1: bot -> right (L)", "bottom", "L-right", "right", "L-to-side"),
    ("2: right -> left", "right", "h", "left", "straight"),
    ("3: left -> down (L)", "left", "L-down", "down", "L-to-v"),
    ("4: down -> up", "down", "v", "up", "straight"),
    ("5: up -> left (L)", "up", "L-left", "left", "L-to-side"),
]

t = 0.6  # mid-pulse
for i, (label, wall_in, path, wall_out, kind) in enumerate(entries):
    col = i % 3
    row = i // 3
    px = PANELS_X0 + col * (PANEL_W + PANELS_GAP_X)
    py = PANELS_Y0 + row * (PANEL_H + PANELS_GAP_Y)
    # Panel bg
    pygame.draw.rect(screen, (16, 22, 38), (px, py, PANEL_W, PANEL_H))
    pygame.draw.rect(screen, (40, 50, 80), (px, py, PANEL_W, PANEL_H), 1)
    # Header
    head = font_sm.render(label, True, (220, 220, 255))
    screen.blit(head, (px + 4, py + 4))
    kind_color = (255, 200, 100) if "L" in kind else (160, 200, 240)
    k = font_sm.render(kind, True, kind_color)
    screen.blit(k, (px + 4, py + 16))
    # Internal mini-map (scale 320x480 -> PANEL_W x PANEL_H)
    INNER_X = px + 8
    INNER_Y = py + 30
    INNER_W = PANEL_W - 16
    INNER_H = PANEL_H - 38
    sx = INNER_W / INTERNAL_W
    sy = INNER_H / INTERNAL_H
    # Bg
    pygame.draw.rect(screen, (4, 8, 16), (INNER_X, INNER_Y, INNER_W, INNER_H))
    pygame.draw.rect(screen, (60, 80, 120), (INNER_X, INNER_Y, INNER_W, INNER_H), 1)
    # Draw path
    color_path = (255, 180, 100) if "L" in kind else (140, 180, 220)
    if path == "v":
        if wall_in == "top":
            x0 = INNER_X + INNER_W * 0.5
            y0 = INNER_Y - 6
            x1 = x0
            y1 = INNER_Y + INNER_H + 6
        else:  # bottom
            x0 = INNER_X + INNER_W * 0.5
            y0 = INNER_Y + INNER_H + 6
            x1 = x0
            y1 = INNER_Y - 6
        pygame.draw.line(screen, color_path, (x0, y0), (x1, y1), 1)
    elif path == "h":
        if wall_in == "right":
            x0 = INNER_X + INNER_W + 6
            y0 = INNER_Y + INNER_H * 0.5
            x1 = INNER_X - 6
            y1 = y0
        else:  # left
            x0 = INNER_X - 6
            y0 = INNER_Y + INNER_H * 0.5
            x1 = INNER_X + INNER_W + 6
            y1 = y0
        pygame.draw.line(screen, color_path, (x0, y0), (x1, y1), 1)
    elif path == "L-right":
        # enter from bottom, go up, turn right, exit right
        x_enter = INNER_X + INNER_W * 0.5
        y_enter = INNER_Y + INNER_H + 6
        y_turn = INNER_Y + INNER_H * 0.6
        x_exit = INNER_X + INNER_W + 6
        y_exit = y_turn
        pygame.draw.line(screen, color_path, (x_enter, y_enter), (x_enter, y_turn), 1)
        pygame.draw.line(screen, color_path, (x_enter, y_turn), (x_exit, y_exit), 1)
    elif path == "L-left":
        # enter from top, go down, turn left, exit left
        x_enter = INNER_X + INNER_W * 0.5
        y_enter = INNER_Y - 6
        y_turn = INNER_Y + INNER_H * 0.4
        x_exit = INNER_X - 6
        y_exit = y_turn
        pygame.draw.line(screen, color_path, (x_enter, y_enter), (x_enter, y_turn), 1)
        pygame.draw.line(screen, color_path, (x_enter, y_turn), (x_exit, y_exit), 1)
    elif path == "L-down":
        # enter from left, go right, turn down, exit bottom
        y_enter = INNER_Y + INNER_H * 0.5
        x_enter = INNER_X - 6
        x_turn = INNER_X + INNER_W * 0.4
        y_exit = INNER_Y + INNER_H + 6
        x_exit = x_turn
        pygame.draw.line(screen, color_path, (x_enter, y_enter), (x_turn, y_enter), 1)
        pygame.draw.line(screen, color_path, (x_turn, y_enter), (x_exit, y_exit), 1)
    # Draw the sub-boss at the entry point (so we see the alien hunter)
    # Map entry to a position in the panel
    if wall_in == "top":
        sb_cx = INNER_X + INNER_W * 0.5
        sb_cy = INNER_Y + 18
    elif wall_in == "bottom":
        sb_cx = INNER_X + INNER_W * 0.5
        sb_cy = INNER_Y + INNER_H - 18
    elif wall_in == "right":
        sb_cx = INNER_X + INNER_W - 18
        sb_cy = INNER_Y + INNER_H * 0.5
    elif wall_in == "left":
        sb_cx = INNER_X + 18
        sb_cy = INNER_Y + INNER_H * 0.5
    draw_sub_boss_hunter(screen, int(sb_cx), int(sb_cy), cfg.width, cfg.height, t)
    # Tag the entry wall with a small arrow
    arrow_color = (255, 220, 140)
    if wall_in == "top":
        pygame.draw.polygon(screen, arrow_color, [
            (int(sb_cx) - 3, INNER_Y - 2),
            (int(sb_cx) + 3, INNER_Y - 2),
            (int(sb_cx), INNER_Y + 2),
        ])
    elif wall_in == "bottom":
        pygame.draw.polygon(screen, arrow_color, [
            (int(sb_cx) - 3, INNER_Y + INNER_H + 2),
            (int(sb_cx) + 3, INNER_Y + INNER_H + 2),
            (int(sb_cx), INNER_Y + INNER_H - 2),
        ])
    elif wall_in == "right":
        pygame.draw.polygon(screen, arrow_color, [
            (INNER_X + INNER_W + 2, int(sb_cy) - 3),
            (INNER_X + INNER_W + 2, int(sb_cy) + 3),
            (INNER_X + INNER_W - 2, int(sb_cy)),
        ])
    elif wall_in == "left":
        pygame.draw.polygon(screen, arrow_color, [
            (INNER_X - 2, int(sb_cy) - 3),
            (INNER_X - 2, int(sb_cy) + 3),
            (INNER_X + 2, int(sb_cy)),
        ])

# Footer / legend
foot_y = 480
foot1 = font_md.render("Pattern:", True, (220, 220, 255))
screen.blit(foot1, (14, foot_y))
foot2 = font_sm.render(
    "Entries 0/2/4: straight (vertical or horizontal). 1/3/5: L turn. "
    "L-to-side alternates with L-to-top-bottom every 2 entries.",
    True, (180, 200, 255),
)
screen.blit(foot2, (14, foot_y + 18))
foot3 = font_sm.render(
    "Same wall rule: the sub-boss ALWAYS re-enters through the same wall it just exited.",
    True, (180, 200, 255),
)
screen.blit(foot3, (14, foot_y + 32))
foot4 = font_sm.render(
    "Wall sequence: top -> bottom -> right -> left -> down -> up -> left -> ...",
    True, (180, 200, 255),
)
screen.blit(foot4, (14, foot_y + 46))
foot5 = font_sm.render(
    "HP 400 (20x)  -  speed unchanged  -  no sine wobble  -  wrap-around ON",
    True, (200, 220, 140),
)
screen.blit(foot5, (14, foot_y + 64))
foot6 = font_sm.render(
    "Bigger 24x14 hitbox (BLOQUE 58.6.3)  -  propulsion animation: P_FIRE + P_SMOKE",
    True, (200, 220, 140),
)
screen.blit(foot6, (14, foot_y + 78))

# Save
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "polish_52_sub_boss_l_pattern.png"
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
