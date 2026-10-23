"""BLOQUE 66.5: render GOLIATH's javelin frames as the game draws them.

BLOQUE 66.3 added a per-frame centroid offset to `_draw_goliath`, so a frame
whose body sits off-centre is blitted at a compensating x. This renders each
javelin frame at both clamp extremes so an off-centre frame's on-screen
position can be compared against a centred one.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

ROOT = Path(r"F:\AI\MM\void-hunter")
sys.path.insert(0, str(ROOT))

import pygame

pygame.init()
pygame.display.set_mode((320, 480))

from PIL import Image

from src.entities.enemies.boss import Boss, BossId
from src.ui.gameplay_runtime import GameplayRuntime
from src.ui.scenes import _load_sprite, get_sprite_centroid_offset

ANIM = "javelin"
BOSSW, BOSS_H = 96, 80
SCALE = 3
CELL_W, CELL_H = BOSSW * SCALE, BOSS_H * SCALE

rows = []
for frame in range(10):
    name = f"bosses/goliath/{ANIM}/frame_{frame:02d}.png"
    dx, dy = get_sprite_centroid_offset(name)
    sprite = _load_sprite(name)
    if sprite is None:
        continue

    # Measure where the body actually lands in world space.
    img = sprite.convert_alpha()
    cols = [
        x for x in range(BOSSW)
        if any(img.get_at((x, y))[3] > 32 for y in range(BOSS_H))
    ]
    body_min, body_max = min(cols), max(cols)

    for clamp_x, label in ((100.0, "L"), (220.0, "R")):
        rt = GameplayRuntime.__new__(GameplayRuntime)
        rt._t = 0.0
        boss = Boss()
        boss.id = BossId.GOLIATH
        boss.x = clamp_x
        boss.y = 80.0
        boss.animation_state = ANIM
        boss.animation_frame = frame
        rt._boss = boss
        rt._boss_shield_hits = 0
        rt._boss_shield_laser_t = 0.0
        rt._shield_flash_t = 0.0

        blit_x = int(boss.x) - BOSSW // 2 + dx
        canvas = pygame.Surface((320, 480), pygame.SRCALPHA)
        canvas.blit(sprite, (blit_x, int(boss.y) - BOSS_H // 2 + dy))
        rt._draw_shield(canvas, 0, 0)

        layer = Image.frombytes(
            "RGBA", (320, 480), pygame.image.tostring(canvas, "RGBA")
        ).convert("RGBA")
        bg = Image.new("RGBA", (320, 480), (16, 16, 34, 255))
        bg.alpha_composite(layer)
        # Crop a window centred on the blit so off-centre frames are obvious.
        crop = bg.convert("RGB").crop(
            (max(0, blit_x - 12), 20, max(0, blit_x - 12) + BOSSW, 20 + BOSS_H)
        ).resize((CELL_W, CELL_H), Image.NEAREST)
        rows.append((frame, clamp_x, label, dx, body_min, body_max, crop))

COLS = 4
grid_rows = (len(rows) + COLS - 1) // COLS
sheet = Image.new("RGB", (CELL_W * COLS, CELL_H * grid_rows), (16, 16, 34))
for i, (frame, clamp_x, label, dx, bmin, bmax, crop) in enumerate(rows):
    sheet.paste(crop, ((i % COLS) * CELL_W, (i // COLS) * CELL_H))
    print(
        f"  frame_{frame:02d} boss.x={clamp_x:.0f} {label}  dx={dx:>3d}  "
        f"body cols {bmin}..{bmax} -> world {int(clamp_x) - 48 + dx + bmin}"
        f"..{int(clamp_x) - 48 + dx + bmax}"
    )

out = ROOT / "tools" / "playtest_out" / f"goliath_{ANIM}_frames.png"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out)
print(f"saved {out}")
print("viewport is 0..319 — any world x outside that range is clipped")