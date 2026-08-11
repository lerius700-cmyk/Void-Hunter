"""Capture: player propulsion with 1-second-delayed orange wake (BLOQUE 58.8.3).

Visual proof:
  - The bright orange P_WAKE particles are emitted at the player's
    position every frame during PROPULSION.
  - Each wake is INVISIBLE for 1 second (delay_s = 1.0s).
  - After 1 second, the wake becomes visible at the position where it
    was spawned (i.e. where the player was 1 second ago) and fades
    out over its life (0.8s).
  - The result: a delayed orange afterglow trail that "follows" the
    player (the wake particles are static, but new ones are
    continuously added at the player's NEW position, so the visible
    trail lags the ship by ~1 second).

Output: tools/playtest_out/polish_54_propulsion_wake.png
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
from src.systems.particle_engine import P_WAKE, ParticleEngine, KIND_CONFIG

pygame.init()
W, H = 720, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - propulsion wake / destello (BLOQUE 58.8.3)")
screen.fill((8, 12, 24))

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

title = font_lg.render(
    "PROPULSION  -  1s-delayed orange wake (BLOQUE 58.8.3)", True, (255, 255, 255),
)
screen.blit(title, (12, 10))
sub = font_md.render(
    "P_WAKE particles are invisible for 1s, then appear at where the player was 1s ago",
    True, (180, 200, 255),
)
screen.blit(sub, (12, 34))

# Simulate the wake: 6 seconds of player movement, each frame spawn a
# wake. Then advance particles 6s. Draw both player and wake.
import math
random.seed(42)

eng = ParticleEngine(pool_size=512, bounds=(W, H))

# Player path: a slow diagonal, then circle back
# At t=0: pos=(100, 200)
# At t=6: pos=(620, 280)
player_path = []
total_s = 6.0
dt_frame = 1.0 / 60.0
n_frames = int(total_s / dt_frame)
for i in range(n_frames):
    t = i * dt_frame
    # Diagonal then arc back
    if t < 3.0:
        px = 100 + (t / 3.0) * 500  # 100 -> 600
        py = 200 + math.sin(t * 0.5) * 30
    else:
        # Curve back
        angle = (t - 3.0) / 3.0 * math.pi
        px = 600 - math.sin(angle) * 300
        py = 200 + math.sin((t - 3.0) * 0.7) * 40
    player_path.append((px, py, t))

# Emit wake at the player's position every WAKE_INTERVAL
wake_interval_frames = int(PLAYER_PROPULSION_WAKE_INTERVAL_S / dt_frame)
for i, (px, py, t) in enumerate(player_path):
    if i % wake_interval_frames == 0:
        eng.emit(
            P_WAKE,
            px + random.uniform(-2, 2),
            py + random.uniform(-2, 2),
            vx=0.0, vy=0.0,
            life=PLAYER_PROPULSION_WAKE_LIFE_S,
            radius=10.0,
            color=(255, 160, 60),
            delay_s=PLAYER_PROPULSION_WAKE_DELAY_S,
        )

# Now advance the engine 6s of total time
for _ in range(n_frames):
    eng.update(dt_frame)

# Draw a faded path of the player (background)
for i, (px, py, t) in enumerate(player_path):
    if i % 2 == 0:
        continue
    alpha = 30
    faded = pygame.Surface((3, 3), pygame.SRCALPHA)
    faded.fill((100, 200, 255, alpha))
    screen.blit(faded, (int(px) - 1, int(py) - 1))

# Draw the wakes
wake_cfg = KIND_CONFIG[P_WAKE]
for p in eng._pool:
    if not p.active:
        continue
    if p.kind != P_WAKE:
        continue
    # Get a tinted surface for this particle
    r, g, b = p.color
    surf = eng._get_tinted_surface(p)
    if surf is None:
        continue
    # Apply alpha
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
# Arrow + label
arrow_font = font_sm.render("player NOW (t=6s)", True, (220, 220, 255))
screen.blit(arrow_font, (int(last_px) - 50, int(last_py) - 30))

# Mark the position 1s ago
one_s_frame = int(1.0 / dt_frame)
back_idx = max(0, n_frames - 1 - one_s_frame)
back_px, back_py, _ = player_path[back_idx]
# Render a small marker at the position the player was 1s ago
pygame.draw.circle(screen, (255, 220, 100), (int(back_px), int(back_py)), 4, 1)
marker = font_sm.render("player 1s ago (wake just appeared)", True, (255, 200, 100))
screen.blit(marker, (int(back_px) - 100, int(back_py) - 30))

# Footer / legend
foot_y = 380
foot1 = font_md.render("How it works:", True, (220, 220, 255))
screen.blit(foot1, (14, foot_y))
foot2 = font_sm.render(
    f"  1. Every {PLAYER_PROPULSION_WAKE_INTERVAL_S:.3f}s during PROPULSION, a P_WAKE particle is "
    f"emitted at the player's CURRENT position",
    True, (200, 200, 230),
)
screen.blit(foot2, (14, foot_y + 16))
foot3 = font_sm.render(
    f"  2. Each wake is INVISIBLE for {PLAYER_PROPULSION_WAKE_DELAY_S:.1f}s (delay_s field)",
    True, (200, 200, 230),
)
screen.blit(foot3, (14, foot_y + 30))
foot4 = font_sm.render(
    f"  3. After the delay, the wake becomes visible at its spawn point and fades over "
    f"{PLAYER_PROPULSION_WAKE_LIFE_S:.1f}s",
    True, (200, 200, 230),
)
screen.blit(foot4, (14, foot_y + 44))
foot5 = font_sm.render(
    "  4. Result: a 1-second-delayed orange afterglow that 'follows' the player",
    True, (255, 180, 80),
)
screen.blit(foot5, (14, foot_y + 58))
foot6 = font_sm.render(
    "  Color: (255, 160, 60) bright orange — distinct from yellow main trail and purple sub-boss",
    True, (255, 180, 80),
)
screen.blit(foot6, (14, foot_y + 72))

# Save
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "polish_54_propulsion_wake.png"
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
