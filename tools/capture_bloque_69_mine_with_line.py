"""BLOQUE 69: capture the MINE-ASTEROID opening at y=120 (first quarter).

The yellow line in the reference image was JUST a visual reference for
where the trigger is. The user clarified: "la linea amarilla solo era
una referencia" — it does NOT exist in the game. The trigger is
behavioral, not visual.

This capture shows the mine opening at y=120 (first quarter) with a
COORDINATE LABEL / GRID OVERLAY so the user can verify the trigger
position visually. The grid overlay is part of the CAPTURE (not the
game) — it does not pollute the runtime.

8 frames:
- frame_00: spawn (closed, off-screen above)
- frame_01: closed, drifted to y=80 (above trigger, still camo)
- frame_02: closed, just above trigger at y=119 (last frame before opening)
- frame_03: open1 (just crossed y=120, 0.0s into opening)
- frame_04: open2 (0.2s into opening)
- frame_05: open3 (0.4s into opening, first fire)
- frame_06: open3 + 1.0s (second fire)
- frame_07: open3 + 2.0s (third fire, deeper in playfield)

The composite is saved to tools/playtest_out/bloque_69_mine_with_line.png
so the user can verify the mine actually opens AT y=120.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
sys.path.insert(0, '.')
import pygame
pygame.init()
pygame.display.set_mode((320, 480))

import random
from src.entities.enemies.enemy import (
    create_enemy, EnemyKind, EnemyState, spawn_obstacle,
    OPENING_Y_THRESHOLD,
)
from src.systems.projectile import ProjectilePool
from PIL import Image as PImage, ImageDraw as PImageDraw, ImageFont as PImageFont

# Get a MINE_ASTEROID payload
payload = None
for seed in range(200):
    rng = random.Random(seed)
    if rng.random() < 0.25:
        kind, p = spawn_obstacle(rng)
        if kind == "mine_asteroid":
            payload = p
            break
assert payload

# Create the mine with drift
mine = create_enemy(EnemyKind.MINE_ASTEROID, payload["x"], payload["y"])
mine.vx = payload["drift_vx"]
mine.vy = payload["drift_vy"]
mine.mine_variant = 0  # round (visible)


def render_mine_to_surface(m):
    """Render the mine's current sprite. Returns (sprite, rect)."""
    path = m.animation_path
    full_path = f"Assets/sprites/{path}"
    sprite = pygame.image.load(full_path).convert_alpha()
    rect = sprite.get_rect(center=(int(m.x), int(m.y)))
    return sprite, rect


def draw_grid_overlay(surf, trigger_y):
    """Draw a coordinate label / grid overlay showing where y=120 is.

    The overlay is part of the CAPTURE only — not part of the game.
    It marks the trigger position so the user can verify visually
    that the mine opens AT y=120.
    """
    w, h = surf.get_size()
    # Draw horizontal dashed line at trigger_y (semi-transparent so
    # it doesn't hide the mine sprite)
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    dash_color = (255, 255, 100, 180)  # yellowish, semi-transparent
    for x in range(0, w, 8):
        pygame.draw.line(overlay, dash_color, (x, trigger_y),
                         (x + 4, trigger_y), 1)
    # Draw a small label on the right edge
    try:
        font = pygame.font.SysFont('consolas', 10)
    except Exception:
        font = pygame.font.Font(None, 10)
    label_surf = font.render(f"y={trigger_y} (trigger)", True, (255, 255, 100))
    label_surf.set_alpha(180)
    overlay.blit(label_surf, (w - label_surf.get_width() - 4, trigger_y - 14))
    surf.blit(overlay, (0, 0))


# Create a black playfield surface (320x480 internal)
playfield = pygame.Surface((320, 480))
playfield.fill((0, 0, 0))

# Reset mine to spawn position
mine.x = payload["x"]
mine.y = payload["y"]
mine.mine_state = "closed"
mine.has_opened = False
mine.mine_fire_cooldown = 0.0

# Simulate drift + state machine manually
TICK = 0.05
captures = []

# Frame 0: spawn
sprite, rect = render_mine_to_surface(mine)
sf = pygame.Surface((320, 480))
sf.fill((0, 0, 0))
sf.blit(sprite, rect)
captures.append(("00 spawn y={:.0f}".format(mine.y), sf))

# Drift through the closed zone (y < 120), capturing at key y values
target_ys = [80, 119]  # ABOVE the trigger, last frame is y=119
for target_y in target_ys:
    while mine.y < target_y:
        mine.update(TICK, 160.0, 400.0)
        if mine.state == EnemyState.DEAD:
            break
    sprite, rect = render_mine_to_surface(mine)
    sf = pygame.Surface((320, 480))
    sf.fill((0, 0, 0))
    sf.blit(sprite, rect)
    captures.append(("{:02d} closed y={:.0f} (above trigger)".format(
        len(captures), mine.y), sf))
    if mine.state == EnemyState.DEAD:
        break

# Now let it cross y=120 — the mine should open on the first tick
while mine.mine_state == "closed":
    mine.update(TICK, 160.0, 400.0)
    if mine.state == EnemyState.DEAD:
        break
sprite, rect = render_mine_to_surface(mine)
sf = pygame.Surface((320, 480))
sf.fill((0, 0, 0))
sf.blit(sprite, rect)
captures.append(("{:02d} open1 y={:.0f} (AT trigger)".format(
    len(captures), mine.y), sf))

# Advance through open1 -> open2 -> open3
while mine.mine_state != "open3":
    mine.update(TICK, 160.0, 400.0)
    if mine.state == EnemyState.DEAD:
        break
sprite, rect = render_mine_to_surface(mine)
sf = pygame.Surface((320, 480))
sf.fill((0, 0, 0))
sf.blit(sprite, rect)
captures.append(("{:02d} open3 y={:.0f} (just opened)".format(
    len(captures), mine.y), sf))

# Continue ticking for 2 more captures (post-open3 firing)
for t_post in (1.0, 2.0):
    target_t = t_post
    t_in_open3 = 0.0
    while t_in_open3 < target_t:
        mine.update(TICK, 160.0, 400.0)
        t_in_open3 += TICK
        if mine.state == EnemyState.DEAD:
            break
    sprite, rect = render_mine_to_surface(mine)
    sf = pygame.Surface((320, 480))
    sf.fill((0, 0, 0))
    sf.blit(sprite, rect)
    captures.append(("{:02d} open3 +{:.0f}s y={:.0f}".format(
        len(captures), t_post, mine.y), sf))
    if mine.state == EnemyState.DEAD:
        break

# Now draw the grid overlay on each capture (showing where y=120 is)
for _, sf in captures:
    draw_grid_overlay(sf, OPENING_Y_THRESHOLD)

# Composite into a single PNG
cell_w = 160  # half-size of 320
cell_h = 240  # half-size of 480
cols = 4
rows = 2
pad = 4
W = cols * cell_w + (cols + 1) * pad
H = rows * cell_h + (rows + 1) * pad + 40  # +40 for footer
out = PImage.new('RGB', (W, H), (16, 16, 24))
draw = PImageDraw.Draw(out)
try:
    font = PImageFont.truetype('consola.ttf', 11)
except Exception:
    font = PImageFont.load_default()

for i, (label, surf) in enumerate(captures):
    row = i // cols
    col = i % cols
    x = pad + col * (cell_w + pad)
    y = pad + row * (cell_h + pad)
    # Convert pygame surface to PIL
    raw = pygame.image.tostring(surf, 'RGB')
    pil = PImage.frombytes('RGB', (320, 480), raw)
    pil = pil.resize((cell_w, cell_h), PImage.NEAREST)
    out.paste(pil, (x, y))
    draw.text((x + 2, y + cell_h - 16), label, fill=(220, 220, 220), font=font)

draw.text((pad, H - 14),
          'BLOQUE 69 - MINE-ASTEROID opens at y=120 (first quarter). '
          'Dashed line in the capture marks the trigger position. '
          'NO yellow line in the actual game.',
          fill=(180, 220, 180), font=font)

import os
os.makedirs('tools/playtest_out', exist_ok=True)
out_path = 'tools/playtest_out/bloque_69_mine_with_line.png'
out.save(out_path)
print(f"Saved: {out_path}  size: {out.size}")
print(f"OPENING_Y_THRESHOLD = {OPENING_Y_THRESHOLD}")
print(f"Captured {len(captures)} frames showing the mine opening at y=120.")
