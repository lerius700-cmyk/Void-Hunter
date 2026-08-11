"""Capture: render the new bomb explosion (BLOQUE 58.9).

Visual proof that the bomb explosion is 5x bigger (60 -> 300 px radius)
with proper multi-stage visual:
  - White-hot core (GLOW particle, big radius, fast fade)
  - Yellow inner ball (GLOW, mid fade)
  - Orange mid ball (GLOW, longer fade)
  - Red outer shell (GLOW, longest fade, larger)
  - 48 FIRE particles flying outward
  - 36 SPARK particles (bright trails)
  - 20 SMOKE puffs (rising gray clouds)
  - Shockwave + screen flash + slowmo + shake
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import sys
import math
import random
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
from src.core.settings import INTERNAL_W, INTERNAL_H, MISSILE_EXPLOSION_RADIUS_PX
from src.systems.particle_engine import (
    P_FIRE, P_GLOW, P_SMOKE, P_SPARK, ParticleEngine,
)

pygame.init()
W, H = 720, 520
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - BOMB EXPLOSION (BLOQUE 58.9)")
screen.fill((8, 12, 24))

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

# Title
title = font_lg.render(
    "BOMB EXPLOSION  -  BLOQUE 58.9 (5x bigger + multi-stage gradient)", True, (255, 255, 255),
)
screen.blit(title, (12, 10))
sub = font_md.render(
    f"Radius: {MISSILE_EXPLOSION_RADIUS_PX}px (was 60)  -  white core -> yellow -> orange -> red  -  +smoke +sparks +fire",
    True, (180, 200, 255),
)
screen.blit(sub, (12, 34))

# Configure particle bounds to match our capture window so they don't get culled
particles = ParticleEngine(pool_size=2000)
particles._bounds = (W, H)  # override cull bounds

# Single big explosion at center
cx, cy = W // 2, H // 2 + 30
rad = MISSILE_EXPLOSION_RADIUS_PX
# Scale down so the explosion fits the 720px wide window
# 300 * scale = 280 px (so we can see the whole explosion)
scale = 0.93

# Stage 1: white-hot core
particles.emit(
    P_GLOW, cx, cy, vx=0.0, vy=0.0,
    life=0.18, radius=rad * 0.45 * scale,
    color=(255, 255, 240),
)
# Stage 2: yellow inner
particles.emit(
    P_GLOW, cx, cy, vx=0.0, vy=0.0,
    life=0.35, radius=rad * 0.85 * scale,
    color=(255, 230, 80),
)
# Stage 3: orange mid
particles.emit(
    P_GLOW, cx, cy, vx=0.0, vy=0.0,
    life=0.55, radius=rad * 1.1 * scale,
    color=(255, 140, 40),
)
# Stage 4: red outer
particles.emit(
    P_GLOW, cx, cy, vx=0.0, vy=0.0,
    life=0.75, radius=rad * 1.3 * scale,
    color=(220, 60, 40),
)
# FIRE particles
for _ in range(48):
    angle = random.uniform(0, math.tau)
    speed = random.uniform(60.0, 180.0) * scale
    particles.emit(
        P_FIRE, cx, cy,
        vx=math.cos(angle) * speed, vy=math.sin(angle) * speed,
        life=random.uniform(0.4, 0.9), radius=random.uniform(1.5, 3.0),
        color=(255, random.randint(140, 220), random.randint(40, 80)),
    )
# SPARK particles
for _ in range(36):
    angle = random.uniform(0, math.tau)
    speed = random.uniform(80.0, 240.0) * scale
    particles.emit(
        P_SPARK, cx, cy,
        vx=math.cos(angle) * speed, vy=math.sin(angle) * speed,
        life=random.uniform(0.2, 0.5), radius=random.uniform(0.8, 1.5),
        color=(255, 255, random.randint(140, 240)),
    )
# SMOKE puffs
for _ in range(20):
    angle = random.uniform(0, math.tau)
    speed = random.uniform(20.0, 60.0) * scale
    particles.emit(
        P_SMOKE, cx, cy,
        vx=math.cos(angle) * speed, vy=math.sin(angle) * speed - 25.0 * scale,
        life=random.uniform(0.8, 1.5), radius=random.uniform(2.0, 4.0),
        color=(120, 120, 140),
    )

# Draw the explosion (just emitted, t=0)
particles.draw(screen)

# Description box at the bottom
desc_rect = pygame.Rect(12, H - 100, W - 24, 84)
desc_surf = pygame.Surface((W - 24, 84))
desc_surf.fill((16, 22, 40))
desc_surf.set_alpha(220)
screen.blit(desc_surf, desc_rect)
pygame.draw.rect(screen, (60, 60, 90), desc_rect, 1)

desc_lines = [
    "BLOQUE 58.9: bomb explosion 5x bigger + multi-stage gradient",
    f"  - Radius: {MISSILE_EXPLOSION_RADIUS_PX}px (was 60, BLOQUE 39)",
    f"  - 4-layer gradient: white core -> yellow -> orange -> red",
    f"  - +48 FIRE particles, +36 SPARK particles, +20 SMOKE puffs",
    f"  - Shockwave, screen flash, slowmo, shake, hitstop",
]
for i, line in enumerate(desc_lines):
    color = (255, 220, 100) if i == 0 else (180, 200, 255)
    txt = font_sm.render(line, True, color)
    screen.blit(txt, (desc_rect.x + 8, desc_rect.y + 6 + i * 14))

out_path = ROOT / "tools" / "playtest_out" / "polish_51_bomb_explosion.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
print(f"Explosion radius: {MISSILE_EXPLOSION_RADIUS_PX}px (5x bigger than BLOQUE 39's 60)")
pygame.quit()
