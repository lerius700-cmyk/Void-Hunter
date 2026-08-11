"""Capture: SUB_BOSS with rotation support (BLOQUE 58.6.5).

Visual proof that the sub-boss rotates to face its velocity direction:
  - DOWN: nose at bottom (0° rotation, default orientation)
  - UP:   nose at top    (180° rotation)
  - RIGHT: nose at right  (90° rotation)
  - LEFT:  nose at left   (270° rotation)

Plus the new PURPLE propulsion palette (P_SPARK + P_GLOW + P_SMOKE in
magenta/violet tones) — same particle system as the player propulsion
but recolored to a violet family so the sub-boss reads as a different
ship class than the player (yellow/cyan) and the bosses (orange/red).

Output: tools/playtest_out/polish_53_sub_boss_rotated.png
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
W, H = 720, 520
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - SUB_BOSS rotation + purple propulsion (BLOQUE 58.6.5)")
screen.fill((8, 12, 24))

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

title = font_lg.render(
    "SUB_BOSS  -  4-direction rotation + purple propulsion (BLOQUE 58.6.5)", True, (255, 255, 255),
)
screen.blit(title, (12, 10))
sub = font_md.render(
    "nose + engines rotate to face velocity  -  P_SPARK + P_GLOW + P_SMOKE in violet/magenta",
    True, (180, 200, 255),
)
screen.blit(sub, (12, 34))

cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
print(f"SUB_BOSS size: {cfg.width}x{cfg.height}")


def draw_sub_boss_sprite(target, cx, cy, w, h, t):
    """Reuse the closed-V silhouette from BLOQUE 58.6.2 + 58.6.5 (purple engines)."""
    wolf_base = (160, 170, 185)
    wolf_dark = (80, 90, 105)
    wolf_red = (220, 50, 60)
    cyan_eye = (80, 220, 240)
    pink_fang = (255, 100, 180)
    pink_fang_bright = (255, 200, 230)
    sx = w / 16.0
    sy = h / 10.0
    bob = int(round(math.sin(t * 2.0 * math.pi) * 1.0))
    cy_b = cy + bob
    engine_pulse = 0.7 + 0.3 * (0.5 + 0.5 * math.sin(t * 6.0))
    eye_pulse = 0.85 + 0.15 * math.sin(t * 3.0)
    body_top_y = cy_b - h // 2
    body_bot_y = cy_b + h // 2
    fang_tip_y = body_bot_y + max(1, int(round(sy)))
    pygame.draw.polygon(target, wolf_base, [
        (cx - max(2, int(round(3 * sx))), body_top_y + max(1, int(round(sy)))),
        (cx - max(5, int(round(7 * sx))), body_top_y),
        (cx, fang_tip_y),
        (cx - 1, body_bot_y - 1),
    ])
    pygame.draw.polygon(target, wolf_base, [
        (cx + max(2, int(round(3 * sx))), body_top_y + max(1, int(round(sy)))),
        (cx + max(5, int(round(7 * sx))), body_top_y),
        (cx, fang_tip_y),
        (cx + 1, body_bot_y - 1),
    ])
    pygame.draw.line(target, wolf_red,
                     (cx - max(4, int(round(6 * sx))), body_top_y),
                     (cx, fang_tip_y - 1), 1)
    pygame.draw.line(target, wolf_red,
                     (cx + max(4, int(round(6 * sx))), body_top_y),
                     (cx, fang_tip_y - 1), 1)
    pygame.draw.circle(target, pink_fang, (cx, fang_tip_y), 1)
    pygame.draw.circle(target, pink_fang_bright, (cx, fang_tip_y), 1)
    spine_y_top = body_top_y + max(1, int(round(2 * sy)))
    pygame.draw.line(target, wolf_dark, (cx, spine_y_top), (cx, body_bot_y - 1), 1)
    # PURPLE engines (BLOQUE 58.6.5)
    eng_c = (
        int(255 * engine_pulse),
        int(120 * engine_pulse),
        int(240 * engine_pulse),
    )
    eng_w = max(2, int(round(2 * sx)))
    eng_h = max(2, int(round(2 * sy)))
    pygame.draw.rect(target, eng_c, (cx - eng_w, body_top_y, eng_w, eng_h))
    pygame.draw.rect(target, eng_c, (cx + 1, body_top_y, eng_w, eng_h))
    mid_y = cy_b - 1
    body_w = max(1, int(round(1 * sx)))
    pygame.draw.polygon(target, wolf_base, [
        (cx, body_bot_y), (cx + body_w, mid_y),
        (cx, body_top_y + 1), (cx - body_w, mid_y),
    ])
    eye_scale = max(1.0, (sx + sy) / 2.0)
    eye_r1 = max(2, int(round(4 * eye_pulse * eye_scale)))
    eye_r2 = max(1, int(round(3 * eye_pulse * eye_scale)))
    eye_r3 = max(1, int(round(2 * eye_pulse * eye_scale)))
    pygame.draw.circle(target, (40, 80, 110), (cx, cy_b), eye_r1 + 1)
    pygame.draw.circle(target, cyan_eye, (cx, cy_b), eye_r1)
    pygame.draw.circle(target, (200, 240, 255), (cx, cy_b), eye_r2)
    pygame.draw.circle(target, (255, 255, 255), (cx, cy_b), eye_r3)


def draw_sub_boss_rotated(target, cx, cy, w, h, t, facing):
    """Draw sub-boss to scratch surface, rotate, blit (mirrors _draw_enemy)."""
    scratch = pygame.Surface((64, 64), pygame.SRCALPHA)
    scratch.fill((0, 0, 0, 0))
    draw_sub_boss_sprite(scratch, 32, 32, w, h, t)
    rotated = pygame.transform.rotate(scratch, facing)
    target.blit(rotated, (cx - rotated.get_width() // 2, cy - rotated.get_height() // 2))


# 4 panels showing each orientation
PANEL_W, PANEL_H = 170, 200
PANELS_X0, PANELS_Y0 = 14, 80
PANELS_GAP_X = 6

t = 0.6
orientations = [
    ("DOWN (vy>0)", "0 deg", 0, "entra por arriba", "sale por abajo"),
    ("RIGHT (vx>0)", "90 deg", 90, "entra por izquierda", "sale por derecha"),
    ("UP (vy<0)", "180 deg", 180, "entra por abajo", "sale por arriba"),
    ("LEFT (vx<0)", "270 deg", 270, "entra por derecha", "sale por izquierda"),
]

for i, (label, angle_str, facing, hint_in, hint_out) in enumerate(orientations):
    px = PANELS_X0 + i * (PANEL_W + PANELS_GAP_X)
    py = PANELS_Y0
    # Panel bg
    pygame.draw.rect(screen, (16, 22, 38), (px, py, PANEL_W, PANEL_H))
    pygame.draw.rect(screen, (40, 50, 80), (px, py, PANEL_W, PANEL_H), 1)
    # Header
    head = font_sm.render(label, True, (220, 220, 255))
    screen.blit(head, (px + 4, py + 4))
    ang = font_sm.render(angle_str, True, (200, 200, 230))
    screen.blit(ang, (px + 4, py + 16))
    # Sub-boss
    sb_cx = px + PANEL_W // 2
    sb_cy = py + 80
    draw_sub_boss_rotated(screen, sb_cx, sb_cy, cfg.width, cfg.height, t, facing)
    # Velocity arrow
    arr_color = (255, 220, 100)
    if facing == 0:  # down
        pygame.draw.polygon(screen, arr_color, [
            (sb_cx, sb_cy + 32), (sb_cx - 5, sb_cy + 22),
            (sb_cx + 5, sb_cy + 22),
        ])
    elif facing == 90:  # right
        pygame.draw.polygon(screen, arr_color, [
            (sb_cx + 32, sb_cy), (sb_cx + 22, sb_cy - 5),
            (sb_cx + 22, sb_cy + 5),
        ])
    elif facing == 180:  # up
        pygame.draw.polygon(screen, arr_color, [
            (sb_cx, sb_cy - 32), (sb_cx - 5, sb_cy - 22),
            (sb_cx + 5, sb_cy - 22),
        ])
    else:  # 270, left
        pygame.draw.polygon(screen, arr_color, [
            (sb_cx - 32, sb_cy), (sb_cx - 22, sb_cy - 5),
            (sb_cx - 22, sb_cy + 5),
        ])
    # Hints
    hi = font_sm.render(hint_in, True, (180, 200, 240))
    screen.blit(hi, (px + 4, py + 130))
    ho = font_sm.render(hint_out, True, (180, 200, 240))
    screen.blit(ho, (px + 4, py + 144))
    # Engine note
    en = font_sm.render("purple exhaust ->", True, (220, 100, 255))
    screen.blit(en, (px + 4, py + 162))

# Footer
foot_y = 305
foot1 = font_md.render("Propulsion palette (BLOQUE 58.6.5):", True, (220, 220, 255))
screen.blit(foot1, (14, foot_y))
foot2 = font_sm.render("  P_SPARK  (220, 100, 255)  bright magenta-violet", True, (200, 200, 230))
screen.blit(foot2, (14, foot_y + 18))
foot3 = font_sm.render("  P_GLOW   (200,  70, 240)  saturated magenta core", True, (200, 200, 230))
screen.blit(foot3, (14, foot_y + 32))
foot4 = font_sm.render("  P_SMOKE  (110,  50, 140)  dark violet puff", True, (200, 200, 230))
screen.blit(foot4, (14, foot_y + 46))
foot5 = font_sm.render("Engines  (255, 120, 240) throbbing purple at the back", True, (200, 200, 230))
screen.blit(foot5, (14, foot_y + 60))
foot6 = font_sm.render("Exhaust direction = OPPOSITE of velocity (follows rotation)", True, (180, 200, 255))
screen.blit(foot6, (14, foot_y + 78))

# Save
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "polish_53_sub_boss_rotated.png"
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
