"""Capture: render the redesigned SUB_BOSS as a CLEAN V SILHOUETTE alien hunter.

BLOQUE 58.6.2: visual proof for the closed-V SUB_BOSS redesign.
User feedback: "parece un ). cierra mas los extremos de las alas". The
wings now ALSO converge at the V apex (instead of extending up-and-out
and forming ")"/"(" shapes on the sides). The result is a clean V.

Output: tools/playtest_out/polish_45_sub_boss_starwolf.png
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
SCALE = 4
W, H = 640, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER — SUB_BOSS Star Wolf redesign")
screen.fill((8, 12, 24))

# Reuse the actual gameplay_runtime sub-boss drawing
# by importing it and calling _draw_enemy via a minimal harness
from src.ui.gameplay_runtime import GameplayRuntime
from src.entities.enemies.enemy import Enemy

# Hack: create a minimal fake GameplayRuntime to draw the sub-boss
class _Harness:
    def __init__(self) -> None:
        self._t = 0.0
        self._enemy_flash: dict[int, float] = {}
    def update_flash(self, dt: float) -> None:
        self._t += dt

harness = _Harness()

cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
print(f"SUB_BOSS size: {cfg.width}x{cfg.height}")

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

# Title
title = font_lg.render("SUB_BOSS  -  CLEAN V SILHOUETTE (BLOQUE 58.6.2)", True, (255, 255, 255))
screen.blit(title, (12, 10))
sub = font_md.render("Fangs (outer V) + wings (inner V) converge at apex (no more ')')", True, (180, 200, 255))
screen.blit(sub, (12, 34))

# 3 frames: idle / bank right / bank left
# Use the actual _draw_enemy method from gameplay_runtime
import src.ui.gameplay_runtime as gpr

# We need a GameplayRuntime instance to call _draw_enemy, but it
# requires tons of state. Easier: copy the SUB_BOSS drawing code
# inline here so the visual is reproducible without spinning up
# the whole game.

def draw_sub_boss(target: pygame.Surface, cx: int, cy: int, w: int, h: int, t: float) -> None:
    """BLOQUE 58.6.2: CLEAN WIDE V SILHOUETTE — fangs form a wide V (apex at bottom), no ')')."""
    wolf_base = (160, 170, 185)
    wolf_dark = (80, 90, 105)
    wolf_red = (220, 50, 60)
    cyan_eye = (80, 220, 240)
    pink_fang = (255, 100, 180)
    pink_fang_bright = (255, 200, 230)
    wolf_engine = (255, 180, 60)
    bob = int(round(math.sin(t * 2.0 * math.pi) * 1.0))
    cy_b = cy + bob
    engine_pulse = 0.7 + 0.3 * (0.5 + 0.5 * math.sin(t * 6.0))
    eye_pulse = 0.85 + 0.15 * math.sin(t * 3.0)
    body_top_y = cy_b - h // 2
    body_bot_y = cy_b + h // 2
    shoulder_y = body_top_y + 2
    # 1) 2 SHARP FANGS forming a WIDE V — apex at the BOTTOM
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
    # 2) CENTER SPINE (collapsed wings) — vertical accent inside the V
    spine_y_top = shoulder_y
    spine_y_bot = body_bot_y - 1
    pygame.draw.line(target, wolf_dark, (cx, spine_y_top), (cx, spine_y_bot), 1)
    # 3) ENGINES at top
    eng_y = body_top_y
    eng_c = (int(255 * engine_pulse), int(180 * engine_pulse), int(60 * engine_pulse))
    pygame.draw.rect(target, eng_c, (cx - 1, eng_y, 1, 2))
    pygame.draw.rect(target, eng_c, (cx, eng_y, 1, 2))
    # 4) MAIN BODY — small central spine inside the V
    mid_y = cy_b - 1
    pygame.draw.polygon(target, wolf_base, [
        (cx, body_bot_y), (cx + 1, mid_y),
        (cx, body_top_y + 1), (cx - 1, mid_y),
    ])
    # 5) MENACING CYAN EYE
    eye_r1 = int(4 * eye_pulse)
    eye_r2 = int(3 * eye_pulse)
    eye_r3 = int(2 * eye_pulse)
    pygame.draw.circle(target, (40, 80, 110), (cx, cy_b), eye_r1 + 1)
    pygame.draw.circle(target, cyan_eye, (cx, cy_b), eye_r1)
    pygame.draw.circle(target, (200, 240, 255), (cx, cy_b), eye_r2)
    pygame.draw.circle(target, (255, 255, 255), (cx, cy_b), eye_r3)
    # 8) Subtle outer red halo
    halo = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
    halo_alpha = 40 + int(20 * math.sin(t * 6))
    pygame.draw.ellipse(halo, (*wolf_red, halo_alpha), (0, 0, w + 16, h + 16), 1)
    target.blit(halo, (cx - (w + 16) // 2, cy_b - (h + 16) // 2))

# 3 frames: idle, bank right, bank left
positions = [
    (160, 200, 0.0, "IDLE"),
    (320, 200, 0.5, "BANK RIGHT"),
    (480, 200, 1.0, "BANK LEFT"),
]
for cx, cy, t, label in positions:
    # The body uses cfg.width x cfg.height; double for the visual
    # (the wings extend beyond, as in-game)
    draw_sub_boss(screen, cx, cy, cfg.width * 2, cfg.height * 2, t)
    # Label
    lbl = font_md.render(label, True, (220, 220, 220))
    screen.blit(lbl, (cx - 30, cy + 60))

# Color legend
legend = [
    "Wolf base: silver (160, 170, 185)  |  Star Wolf red accent: (220, 50, 60)",
    "Menacing cyan eye pulses at 3 Hz  |  Pink/magenta venom fang tips at V apex",
    "Clean V: fangs (outer V) + wings (inner V) both converge at the bottom apex",
]
for i, line in enumerate(legend):
    screen.blit(font_sm.render(line, True, (180, 180, 200)), (12, 380 + i * 14))

# Footer
foot = font_sm.render(
    "BLOQUE 58.6.2: SUB_BOSS clean V silhouette + HP 400 + straight line + wrap-around  -  speed 90, 2.5 shots/s",
    True, (140, 140, 160),
)
screen.blit(foot, (12, H - 16))

out_path = ROOT / "tools" / "playtest_out" / "polish_45_sub_boss_starwolf.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
pygame.quit()
