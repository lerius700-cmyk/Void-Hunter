"""Capture: spectral/neon propulsion wake (BLOQUE 58.8.4).

Visual proof of the LAYERED 3-particle wake:
  - Layer 1: P_GLOW (16x16 soft orange halo) — outer ethereal glow
  - Layer 2: P_WAKE (16x16 magenta-pink body) — bright neon core
  - Layer 3: P_SPARK (1x1 hot white center) — hot inner dot

The 3 layers overlap, with each layer appearing ~0.05s after the
previous one (color shift effect). Combined with the soft radial
gradient on P_WAKE (4 concentric circles), this gives the
"spectral neon — ethereal but colorful" feel the user asked for.

Output: tools/playtest_out/polish_55_propulsion_wake_spectral.png
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_INVULN"] = "1"
import sys
import math
import random
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
from src.core.settings import (
    INTERNAL_W, INTERNAL_H,
    PLAYER_PROPULSION_WAKE_DELAY_S,
    PLAYER_PROPULSION_WAKE_LIFE_S,
    PLAYER_PROPULSION_WAKE_INTERVAL_S,
)
from src.systems.particle_engine import (
    P_WAKE, P_GLOW, P_SPARK, ParticleEngine,
)

pygame.init()
W, H = 720, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - spectral/neon propulsion wake (BLOQUE 58.8.4)")
screen.fill((4, 4, 12))  # very dark background so neon glows pop

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

title = font_lg.render(
    "PROPULSION  -  spectral/neon wake (BLOQUE 58.8.4)", True, (255, 255, 255),
)
screen.blit(title, (12, 10))
sub = font_md.render(
    "3-layer burst per wake: P_GLOW halo (orange) + P_WAKE body (magenta) + P_SPARK core (white)",
    True, (180, 200, 255),
)
screen.blit(sub, (12, 34))

random.seed(42)

eng = ParticleEngine(pool_size=512, bounds=(W, H))

# Simulate the wake: 6 seconds of player movement along a curved path.
# At each wake emission, spawn 3 layered particles (P_GLOW + P_WAKE + P_SPARK)
# at the player's position.
total_s = 6.0
dt_frame = 1.0 / 60.0
n_frames = int(total_s / dt_frame)
player_path = []
for i in range(n_frames):
    t = i * dt_frame
    if t < 3.0:
        px = 100 + (t / 3.0) * 500
        py = 200 + math.sin(t * 0.5) * 30
    else:
        angle = (t - 3.0) / 3.0 * math.pi
        px = 600 - math.sin(angle) * 300
        py = 200 + math.sin((t - 3.0) * 0.7) * 40
    player_path.append((px, py, t))

# Emit wakes every WAKE_INTERVAL seconds
wake_interval_frames = int(PLAYER_PROPULSION_WAKE_INTERVAL_S / dt_frame)
for i, (px, py, t) in enumerate(player_path):
    if i % wake_interval_frames != 0:
        continue
    wx = px + random.uniform(-2, 2)
    wy = py + random.uniform(-2, 2)
    # Layer 1: outer halo (orange)
    eng.emit(
        P_GLOW, wx, wy,
        vx=0.0, vy=0.0,
        life=PLAYER_PROPULSION_WAKE_LIFE_S * 1.1,
        radius=16.0,
        color=(255, 140, 60),
        delay_s=PLAYER_PROPULSION_WAKE_DELAY_S,
    )
    # Layer 2: body (magenta-pink neon)
    eng.emit(
        P_WAKE, wx, wy,
        vx=0.0, vy=0.0,
        life=PLAYER_PROPULSION_WAKE_LIFE_S,
        radius=16.0,
        color=(255, 110, 200),
        delay_s=PLAYER_PROPULSION_WAKE_DELAY_S + 0.05,
    )
    # Layer 3: hot white center
    eng.emit(
        P_SPARK, wx, wy,
        vx=0.0, vy=0.0,
        life=PLAYER_PROPULSION_WAKE_LIFE_S * 0.7,
        radius=1.0,
        color=(255, 255, 255),
        delay_s=PLAYER_PROPULSION_WAKE_DELAY_S + 0.1,
    )

# Advance the engine 6s of total time
for _ in range(n_frames):
    eng.update(dt_frame)

# Draw a faded path of the player (background)
for i, (px, py, t) in enumerate(player_path):
    if i % 2 == 0:
        continue
    faded = pygame.Surface((3, 3), pygame.SRCALPHA)
    faded.fill((100, 200, 255, 30))
    screen.blit(faded, (int(px) - 1, int(py) - 1))

# Draw all particles (sorted so P_GLOW draws first, then P_WAKE, then P_SPARK)
# — order matters for the layered neon look.
particles = []
for p in eng._pool:
    if not p.active:
        continue
    if p.kind not in (P_GLOW, P_WAKE, P_SPARK):
        continue
    particles.append(p)
# Sort: P_GLOW first (back), then P_WAKE (middle), then P_SPARK (front)
order = {P_GLOW: 0, P_WAKE: 1, P_SPARK: 2}
particles.sort(key=lambda p: order.get(p.kind, 99))

for p in particles:
    surf = eng._get_tinted_surface(p)
    if surf is None:
        continue
    if p._alpha < 255:
        surf = surf.copy()
        surf.set_alpha(p._alpha)
    cx = int(p.x - surf.get_width() * 0.5)
    cy = int(p.y - surf.get_height() * 0.5)
    screen.blit(surf, (cx, cy))

# Mark the player's CURRENT position (end of path)
last_px, last_py, _ = player_path[-1]
ship = pygame.Surface((20, 14), pygame.SRCALPHA)
pygame.draw.polygon(ship, (200, 220, 255), [
    (10, 14), (16, 6), (10, 2), (4, 6),
])
pygame.draw.circle(ship, (80, 220, 240), (10, 7), 2)
screen.blit(ship, (int(last_px) - 10, int(last_py) - 7))
arrow_font = font_sm.render("player NOW", True, (220, 220, 255))
screen.blit(arrow_font, (int(last_px) - 30, int(last_py) - 30))

# Mark the position 1s ago
one_s_frame = int(1.0 / dt_frame)
back_idx = max(0, n_frames - 1 - one_s_frame)
back_px, back_py, _ = player_path[back_idx]
pygame.draw.circle(screen, (255, 220, 100), (int(back_px), int(back_py)), 4, 1)
marker = font_sm.render("player 1s ago (wakes just appeared)", True, (255, 200, 100))
screen.blit(marker, (max(0, int(back_px) - 110), int(back_py) - 30))

# Footer / legend
foot_y = 380
foot1 = font_md.render("3 layered particles per wake (BLOQUE 58.8.4):", True, (220, 220, 255))
screen.blit(foot1, (14, foot_y))
foot2 = font_sm.render(
    "  P_GLOW  (16x16, soft orange 255,140, 60)  -  outer ethereal halo",
    True, (255, 160, 100),
)
screen.blit(foot2, (14, foot_y + 16))
foot3 = font_sm.render(
    "  P_WAKE  (16x16, magenta-pink 255,110,200)  -  neon body w/ 4-layer radial gradient",
    True, (255, 130, 200),
)
screen.blit(foot3, (14, foot_y + 30))
foot4 = font_sm.render(
    "  P_SPARK (1x1,   hot white 255,255,255)  -  tiny bright center",
    True, (255, 255, 255),
)
screen.blit(foot4, (14, foot_y + 44))
foot5 = font_sm.render(
    f"  Each layer has a +0.05s delay shift (delay {PLAYER_PROPULSION_WAKE_DELAY_S}s -> {PLAYER_PROPULSION_WAKE_DELAY_S+0.1}s)",
    True, (200, 200, 230),
)
screen.blit(foot5, (14, foot_y + 58))
foot6 = font_sm.render(
    "  Color shift effect: orange halo appears first, then magenta body, then white core",
    True, (200, 200, 230),
)
screen.blit(foot6, (14, foot_y + 72))

# Save
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "polish_55_propulsion_wake_spectral.png"
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
