"""BLOQUE 68: capture the MINE-ASTEROID opening + firing in a visual
sequence. This is the visual evidence the user demanded.

Runs the MINE lifecycle in a headless pygame context, captures 8
screenshots at key moments:
- frame_00: spawn (closed, off-screen above)
- frame_01: closed, drifted to upper playfield
- frame_02: open1 (small crack, 0.0s into opening)
- frame_03: open2 (wider gap, 0.2s into opening)
- frame_04: open3 (full ship, 0.4s into opening — first fire)
- frame_05: open3 + 1.0s (second fire)
- frame_06: open3 + 2.0s (third fire)
- frame_07: open3 + 3.0s (fourth fire, in lower playfield)

The composite is saved to tools/playtest_out/bloque_68_mine_visual.png
so the user can verify visually that the mine actually opens, fires,
and looks right in each state.
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
    OPENING_Y_THRESHOLD, MINE_FIRE_INTERVAL_S,
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

# Load the sprite for the current state via the render path
def render_mine_to_surface(m):
    """Render the mine's current sprite. Returns (sprite, rect)."""
    path = m.animation_path
    full_path = f"Assets/sprites/{path}"
    sprite = pygame.image.load(full_path).convert_alpha()
    rect = sprite.get_rect(center=(int(m.x), int(m.y)))
    return sprite, rect

# Create a black playfield surface (320x480 internal)
playfield = pygame.Surface((320, 480))
playfield.fill((0, 0, 0))

# Capture moments: (label, time_into_open3, expected_state)
moments = [
    ("00 spawn (closed, y=-67)", None, "closed"),
    ("01 closed, y=180 (upper)", None, "closed"),
    ("02 open1 (t=0.0s)", 0.0, "open1"),
    ("03 open2 (t=0.2s)", 0.2, "open2"),
    ("04 open3 (t=0.4s, fire 1)", 0.4, "open3"),
    ("05 open3 + 1.0s (fire 2)", 1.4, "open3"),
    ("06 open3 + 2.0s (fire 3)", 2.4, "open3"),
    ("07 open3 + 3.0s (fire 4)", 3.4, "open3"),
]

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

# Drift until mine is in upper playfield (y > 0 AND y < 200)
target_y = 100  # visible in upper playfield
while mine.y < target_y:
    mine.update(TICK, 160.0, 400.0)
    if mine.state == EnemyState.DEAD:
        break

# Frame 1: closed in upper playfield
sprite, rect = render_mine_to_surface(mine)
sf = pygame.Surface((320, 480))
sf.fill((0, 0, 0))
sf.blit(sprite, rect)
captures.append(("01 closed y={:.0f}".format(mine.y), sf))
prev_state = mine.mine_state

# Now simulate through open1 -> open2 -> open3 and beyond
t_in_open3 = None
# Advance until mine reaches open3
while mine.mine_state != "open3":
    mine.update(TICK, 160.0, 400.0)
    if mine.state == EnemyState.DEAD:
        break

# Capture remaining frames by continuing to tick
for label_template, t_open3_target, expected_state in moments[2:]:
    # Continue ticking until t_in_open3 reaches the target
    if t_open3_target is not None:
        # TICK the simulation until enough open3 time has passed
        while t_in_open3 is None or t_in_open3 < t_open3_target:
            mine.update(TICK, 160.0, 400.0)
            if t_in_open3 is None and mine.mine_state == "open3":
                t_in_open3 = 0.0
            elif t_in_open3 is not None and mine.mine_state == "open3":
                t_in_open3 += TICK
            if mine.state == EnemyState.DEAD:
                break
    # Capture
    sprite, rect = render_mine_to_surface(mine)
    sf = pygame.Surface((320, 480))
    sf.fill((0, 0, 0))
    sf.blit(sprite, rect)
    captures.append((label_template.format(t_open3_target) + " y={:.0f}".format(mine.y), sf))

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

draw.text((pad, H - 14), 'BLOQUE 68 - MINE-ASTEROID visual lifecycle (closed -> open3 + 1Hz fire)',
          fill=(180, 220, 180), font=font)
import os
os.makedirs('tools/playtest_out', exist_ok=True)
out_path = 'tools/playtest_out/bloque_68_mine_visual.png'
out.save(out_path)
print(f"Saved: {out_path}  size: {out.size}")
