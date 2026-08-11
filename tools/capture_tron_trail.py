"""Capture: Tron-style light trail (BLOQUE 58.11).

Visual proof of the Tron trail:
  - Continuous chain of cyan wall segments behind the ship
  - Each segment is a thick line (3 layers: edge halo, cyan body, white core)
  - Segments fade over ~2.5s
  - Max 240 segments cap (so the trail doesn't accumulate forever)
  - Enemies that touch the trail take 3x bullet damage

Output: tools/playtest_out/polish_56_tron_trail.png
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
from src.systems.tron_trail import TronTrail
from src.core.settings import (
    INTERNAL_W, INTERNAL_H,
    TRON_TRAIL_DAMAGE_MULT, TRON_TRAIL_SEGMENT_LENGTH,
    TRON_TRAIL_SEGMENT_THICKNESS, TRON_TRAIL_MAX_AGE_S,
    TRON_TRAIL_SPAWN_INTERVAL_S, TRON_TRAIL_MAX_SEGMENTS,
)

pygame.init()
W, H = 720, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - Tron light trail (BLOQUE 58.11)")
screen.fill((4, 8, 16))

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

title = font_lg.render(
    "TRON TRAIL  -  continuous cyan wall, fades in 2.5s (BLOQUE 58.11)", True, (255, 255, 255),
)
screen.blit(title, (12, 10))
sub = font_md.render(
    f"enemies touching the trail take {TRON_TRAIL_DAMAGE_MULT:.0f}x bullet damage  -  "
    f"max {TRON_TRAIL_MAX_SEGMENTS} segments cap  -  spawned at ~55 Hz",
    True, (180, 220, 255),
)
screen.blit(sub, (12, 34))

# Create a trail and simulate the player moving through a curve
trail = TronTrail(
    max_segments=TRON_TRAIL_MAX_SEGMENTS,
    segment_length=TRON_TRAIL_SEGMENT_LENGTH,
    segment_thickness=TRON_TRAIL_SEGMENT_THICKNESS,
    max_age=TRON_TRAIL_MAX_AGE_S,
    spawn_interval_s=TRON_TRAIL_SPAWN_INTERVAL_S,
)

# Simulate 5 seconds of player movement along a curve, while propelling
total_s = 5.0
dt_frame = 1.0 / 60.0
n_frames = int(total_s / dt_frame)
ship_path = []
for i in range(n_frames):
    t = i * dt_frame
    # S-curve: start left, swing right, return
    if t < 2.0:
        px = 80 + (t / 2.0) * 560
        py = 240 + math.sin(t * 1.5) * 60
    else:
        px = 640 - ((t - 2.0) / 3.0) * 560
        py = 240 + math.sin((t - 2.0) * 1.5) * 60
    # Compute angle (direction of travel)
    if i < n_frames - 1:
        next_t = (i + 1) * dt_frame
        if next_t < 2.0:
            nx = 80 + (next_t / 2.0) * 560
            ny = 240 + math.sin(next_t * 1.5) * 60
        else:
            nx = 640 - ((next_t - 2.0) / 3.0) * 560
            ny = 240 + math.sin((next_t - 2.0) * 1.5) * 60
        angle = math.atan2(ny - py, nx - px)
    else:
        angle = ship_path[-1][2] if ship_path else 0.0
    ship_path.append((px, py, angle))

# Spawn trail at the back of the ship, aging it frame by frame so the
# segment ages are realistic (a segment spawned at frame i has age
# (n_frames - i) * dt_frame at draw time, not 5s like in the previous
# capture script which aged all segments uniformly).
for i, (px, py, angle) in enumerate(ship_path):
    # Use a fixed back offset (8 px) so the trail is right behind the ship
    trail.spawn_if_ready(px, py, angle, 8.0, dt_frame)
    # Age everything by one frame each spawn (so the head is always
    # age 0 and the tail is the oldest)
    trail.update(dt_frame)

# Draw a faint "ship path" line in the background
for i, (px, py, _) in enumerate(ship_path):
    if i % 2 != 0:
        continue
    pt = pygame.Surface((3, 3), pygame.SRCALPHA)
    pt.fill((60, 100, 140, 80))
    screen.blit(pt, (int(px) - 1, int(py) - 1))

# Draw the trail
trail.draw(screen, (0, 0))

# Draw a fake "player" at the end of the path (the current ship position)
last_px, last_py, last_angle = ship_path[-1]
ship = pygame.Surface((20, 14), pygame.SRCALPHA)
pygame.draw.polygon(ship, (200, 220, 255), [
    (10, 14), (16, 6), (10, 2), (4, 6),
])
pygame.draw.circle(ship, (80, 220, 240), (10, 7), 2)
# Rotate the ship to match the angle
ship_rotated = pygame.transform.rotate(ship, -math.degrees(last_angle))
screen.blit(ship_rotated, (int(last_px) - ship_rotated.get_width() // 2,
                            int(last_py) - ship_rotated.get_height() // 2))
arrow_font = font_sm.render("ship (player)", True, (220, 220, 255))
screen.blit(arrow_font, (int(last_px) - 30, int(last_py) + 12))

# Mark the trail start (oldest segment, near the start of the path)
first_px, first_py, _ = ship_path[0]
pygame.draw.circle(screen, (255, 220, 100), (int(first_px), int(first_py)), 3, 1)
marker = font_sm.render("trail start (5s ago)", True, (255, 200, 100))
screen.blit(marker, (int(first_px) - 30, int(first_py) - 20))

# Footer / legend
foot_y = 380
foot1 = font_md.render("How the Tron trail works:", True, (220, 220, 255))
screen.blit(foot1, (14, foot_y))
foot2 = font_sm.render(
    f"  1. While in PROPULSION, a new wall segment spawns every {TRON_TRAIL_SPAWN_INTERVAL_S*1000:.0f}ms (~55 Hz)",
    True, (200, 200, 230),
)
screen.blit(foot2, (14, foot_y + 16))
foot3 = font_sm.render(
    f"  2. Each segment is a {TRON_TRAIL_SEGMENT_LENGTH:.0f}px long, {TRON_TRAIL_SEGMENT_THICKNESS:.0f}px thick line at the ship's BACK",
    True, (200, 200, 230),
)
screen.blit(foot3, (14, foot_y + 30))
foot4 = font_sm.render(
    f"  3. Each segment fades over {TRON_TRAIL_MAX_AGE_S:.1f}s, then disappears",
    True, (200, 200, 230),
)
screen.blit(foot4, (14, foot_y + 44))
foot5 = font_sm.render(
    f"  4. Enemies that touch the trail take {TRON_TRAIL_DAMAGE_MULT:.0f}x bullet damage (3 HP per touch, with 0.15s cooldown per enemy)",
    True, (0, 220, 255),
)
screen.blit(foot5, (14, foot_y + 58))
foot6 = font_sm.render(
    f"  5. Trail cap: {TRON_TRAIL_MAX_SEGMENTS} segments max (~3s of continuous propulsion)",
    True, (200, 200, 230),
)
screen.blit(foot6, (14, foot_y + 72))

# Save
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "polish_56_tron_trail.png"
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
