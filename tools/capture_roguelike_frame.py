"""Capture: render a single frame of the roguelike mode.

BLOQUE 58: visual proof for the full roguelike redesign.
Shows the level structure: 4 chained waves + sub-boss + final boss +
powerup drops, all in a single annotated frame.

Output: tools/playtest_out/polish_44_roguelike_level.png
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
from src.roguelike import (
    generate_procedural_level,
    LevelEventKind,
    PowerupKind,
)

pygame.init()
SCALE = 3
W, H = 320 * SCALE, 480 * SCALE
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER — Roguelike Level (BLOQUE 58)")
screen.fill((8, 12, 24))

font_lg = pygame.font.SysFont("consolas", 22)
font_md = pygame.font.SysFont("consolas", 14)
font_sm = pygame.font.SysFont("consolas", 11)

# Title
title = font_lg.render("ROGUELIKE LEVEL (BLOQUE 58)", True, (255, 255, 255))
screen.blit(title, (12, 8))
sub = font_md.render("seed=42  |  Act 1  |  full procedural", True, (180, 200, 255))
screen.blit(sub, (12, 34))

# Generate the level
level = generate_procedural_level(level_idx=1, seed=42)

# Layout: vertical timeline of events
x = 24
y = 70
line_h = 52
events = level.events
for i, e in enumerate(events):
    kind = e.kind.value
    if kind == "wave":
        f = e.formation
        ftype = f["formation_type"]
        count = f["count"]
        enemy = f["enemy_type"]
        # Wave card
        pygame.draw.rect(screen, (20, 40, 70), (x, y, 270, line_h - 6), border_radius=4)
        pygame.draw.rect(screen, (80, 140, 220), (x, y, 270, line_h - 6), 1, border_radius=4)
        lbl = font_md.render(f"WAVE {e.wave_idx + 1}", True, (255, 255, 255))
        screen.blit(lbl, (x + 8, y + 4))
        info = font_sm.render(
            f"{ftype:>10s}  x{count:>2d}  {enemy:<8s}  spd={f['pattern_speed']:.0f}  tele={f['telegraph_frames']}",
            True, (220, 220, 240),
        )
        screen.blit(info, (x + 8, y + 24))
    elif kind == "sub_boss":
        bid = e.boss_selection.boss_id.value
        pygame.draw.rect(screen, (90, 50, 30), (x, y, 270, line_h - 6), border_radius=4)
        pygame.draw.rect(screen, (255, 160, 60), (x, y, 270, line_h - 6), 1, border_radius=4)
        lbl = font_md.render("!! SUB-BOSS !!", True, (255, 200, 100))
        screen.blit(lbl, (x + 8, y + 4))
        info = font_sm.render(f"boss={bid}  (fixed position, identity randomized)", True, (240, 200, 160))
        screen.blit(info, (x + 8, y + 24))
    elif kind == "final_boss":
        bid = e.boss_selection.boss_id.value
        pygame.draw.rect(screen, (90, 30, 30), (x, y, 270, line_h - 6), border_radius=4)
        pygame.draw.rect(screen, (255, 80, 80), (x, y, 270, line_h - 6), 2, border_radius=4)
        lbl = font_md.render("!! FINAL BOSS !!", True, (255, 100, 100))
        screen.blit(lbl, (x + 8, y + 4))
        info = font_sm.render(
            f"boss={bid}  bezier entrance (procedural path)",
            True, (255, 200, 200),
        )
        screen.blit(info, (x + 8, y + 24))
    elif kind == "powerup_drop":
        pk = e.powerup.kind.value
        pygame.draw.rect(screen, (30, 60, 50), (x, y, 270, line_h - 6), border_radius=4)
        pygame.draw.rect(screen, (100, 220, 140), (x, y, 270, line_h - 6), 1, border_radius=4)
        lbl = font_md.render("POWERUP DROP", True, (180, 240, 200))
        screen.blit(lbl, (x + 8, y + 4))
        info = font_sm.render(f"+ {pk}", True, (200, 240, 220))
        screen.blit(info, (x + 8, y + 24))
    y += line_h
    if y > H - 80:
        break

# Legend
legend_y = H - 60
font_xs = pygame.font.SysFont("consolas", 10)
legend_items = [
    "BLOQUE 58 INVARIANTS: ship counts fixed (12/19/14/17), sub-boss fixed at wave 3, final boss fixed at end",
    "ROGUELIKE: formation_type + bezier entrance + boss identity + powerup drops are seed-randomized",
]
for i, line in enumerate(legend_items):
    screen.blit(font_xs.render(line, True, (180, 180, 200)), (12, legend_y + i * 14))

out_path = ROOT / "tools" / "playtest_out" / "polish_44_roguelike_level.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
print(f"Events in level: {len(level.events)}")
print(f"  waves: {len(level.waves())}")
print(f"  sub-boss: {level.sub_boss().boss_selection.boss_id.value if level.sub_boss() else 'none'}")
print(f"  final-boss: {level.final_boss().boss_selection.boss_id.value if level.final_boss() else 'none'}")
print(f"  powerup-drops: {len(level.powerup_drops())}")
pygame.quit()
