#!/usr/bin/env python3
"""Procedural tile generator for Void Hunter background.

Produces 6 tiles of 320x480 each (1 viewport). The level designer sequences
them per level section. Each tile is a self-contained "beat":
  1. open_sun     — open space, sun visible
  2. enter_belt   — first asteroids appearing
  3. mid_belt     — moderate asteroid density
  4. peak_belt    — maximum density, enclosed
  5. exit_belt    — thinning, space returning
  6. open_stars   — open space, many stars

Output: 6 PNGs in tools/tiles/output/, each 320x480.
Re-run: 1-2 seconds.
"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# -------- Config --------
WIDTH = 320
HEIGHT = 480                # 1 viewport
SEED = 42
OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 16-color palette (consistent with ribbon_weapon)
PAL = np.array([
    [4,   8,  20],   # 0  deep space
    [10, 18,  40],   # 1  deep blue
    [24, 36,  70],   # 2  mid blue
    [40, 20,  60],   # 3  deep purple
    [60, 30,  80],   # 4  nebula purple
    [180, 70, 20],   # 5  sun corona
    [240,140, 50],   # 6  sun edge
    [255,200,100],   # 7  sun mid
    [255,240,180],   # 8  sun core
    [50, 40,  35],   # 9  asteroid dark
    [90, 75,  65],   # 10 asteroid mid
    [140,120,100],   # 11 asteroid light
    [200,200,220],   # 12 highlight
    [160,160,180],   # 13 star dim
    [240,240,250],   # 14 star bright
    [255,255,255],   # 15 white (rare)
], dtype=np.uint8)


def make_canvas():
    return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)


def fill_background(canvas, palette_idx=0):
    canvas[:] = PAL[palette_idx]


def dither_nebula(canvas, top_y, bot_y, intensity, palette_idx=1):
    """Bayer 4x4 dither to add nebula color in a vertical band."""
    BAYER_4 = np.array([
        [0,  8,  2, 10],
        [12, 4, 14,  6],
        [3, 11,  1,  9],
        [15, 7, 13,  5],
    ]) / 16.0
    for y in range(top_y, min(bot_y, HEIGHT)):
        progress = (y - top_y) / max(1, (bot_y - top_y))
        local = intensity * (1.0 - abs(progress - 0.5) * 1.6)
        local = max(0, local)
        for x in range(WIDTH):
            if BAYER_4[y % 4, x % 4] < local * 0.4:
                canvas[y, x] = PAL[palette_idx]


def place_stars(canvas, count, bright_ratio=0.2, cluster_chance=0.1):
    """Random single stars + occasional 2x2 clusters."""
    for _ in range(count):
        x = random.randint(0, WIDTH - 1)
        y = random.randint(0, HEIGHT - 1)
        if random.random() < bright_ratio:
            color = PAL[14]
        else:
            color = PAL[13]
        canvas[y, x] = color
        if random.random() < cluster_chance and y + 1 < HEIGHT and x + 1 < WIDTH:
            canvas[y + 1, x] = color
            canvas[y, x + 1] = color
            canvas[y + 1, x + 1] = color


def draw_sun(canvas, cx, cy, radius):
    """Concentric-band sun. cy can be negative (off-screen)."""
    bands = [
        (radius,        radius * 1.6,  PAL[5]),
        (radius * 0.85, radius,        PAL[6]),
        (radius * 0.65, radius * 0.85, PAL[7]),
        (radius * 0.40, radius * 0.65, PAL[8]),
        (0,             radius * 0.40, PAL[8]),
    ]
    for r_in, r_out, color in bands:
        y, x = np.ogrid[:HEIGHT, :WIDTH]
        dist2 = (x - cx) ** 2 + (y - cy) ** 2
        mask = (dist2 <= r_out ** 2) & (dist2 > r_in ** 2)
        canvas[mask] = color


def draw_asteroid(arr, cx, cy, size):
    """Single irregular pixel-art asteroid."""
    n_verts = random.randint(7, 11)
    points = []
    for i in range(n_verts):
        angle = i * (2 * math.pi / n_verts) + random.uniform(-0.25, 0.25)
        r = size * random.uniform(0.75, 1.0)
        x = int(round(cx + r * math.cos(angle)))
        y = int(round(cy + r * math.sin(angle)))
        x = max(0, min(WIDTH - 1, x))
        y = max(0, min(HEIGHT - 1, y))
        points.append((x, y))
    pil = Image.fromarray(arr)
    draw = ImageDraw.Draw(pil)
    draw.polygon(points, fill=tuple(int(c) for c in PAL[10]))
    draw.polygon(points, outline=tuple(int(c) for c in PAL[9]))
    arr = np.array(pil)
    if size > 18:
        hx = cx + size * 0.25
        hy = cy - size * 0.25
        hr = max(1, int(size * 0.22))
        y_g, x_g = np.ogrid[:HEIGHT, :WIDTH]
        hmask = (x_g - hx) ** 2 + (y_g - hy) ** 2 <= hr ** 2
        current = arr[:, :, 0].astype(int)
        light_mask = (current > 70) & (current < 130) & hmask
        arr[light_mask] = PAL[11]
    for _ in range(random.randint(1, 3)):
        cr = max(1, int(size * random.uniform(0.12, 0.25)))
        ccx = int(cx + random.uniform(-size * 0.3, size * 0.3))
        ccy = int(cy + random.uniform(-size * 0.2, size * 0.2))
        y_g, x_g = np.ogrid[:HEIGHT, :WIDTH]
        cmask = (x_g - ccx) ** 2 + (y_g - ccy) ** 2 <= cr ** 2
        arr[cmask] = PAL[9]
    return arr


def place_asteroids(canvas, count, size_range):
    for _ in range(count):
        cx = random.randint(-40, WIDTH + 40)
        cy = random.randint(20, HEIGHT - 20)
        size = random.randint(*size_range)
        canvas[:] = draw_asteroid(canvas, cx, cy, size)[:]
    return canvas


# -------- Tile definitions --------
def tile_open_sun(rng):
    """Open space with sun visible. Few stars, no asteroids."""
    c = make_canvas()
    fill_background(c, 0)
    dither_nebula(c, 0, int(HEIGHT * 0.6), 0.2, palette_idx=3)  # subtle purple
    draw_sun(c, cx=WIDTH - 60, cy=60, radius=55)  # upper-right sun
    place_stars(c, 18, bright_ratio=0.25)
    return c


def tile_enter_belt(rng):
    """Entering the belt. Sun smaller, first asteroids."""
    c = make_canvas()
    fill_background(c, 0)
    dither_nebula(c, int(HEIGHT * 0.2), HEIGHT, 0.25, palette_idx=1)
    draw_sun(c, cx=WIDTH - 200, cy=20, radius=30)  # small distant sun
    place_stars(c, 12, bright_ratio=0.15)
    c = place_asteroids(c, 4, (12, 28))
    return c


def tile_mid_belt(rng):
    """Mid-belt. Moderate density."""
    c = make_canvas()
    fill_background(c, 0)
    dither_nebula(c, 0, HEIGHT, 0.3, palette_idx=4)  # full nebula
    place_stars(c, 0)  # no stars, occluded
    c = place_asteroids(c, 8, (15, 40))
    return c


def tile_peak_belt(rng):
    """Peak density. Enclosed."""
    c = make_canvas()
    fill_background(c, 0)
    dither_nebula(c, 0, HEIGHT, 0.35, palette_idx=4)
    place_stars(c, 0)
    c = place_asteroids(c, 14, (15, 50))
    return c


def tile_exit_belt(rng):
    """Exiting. Thinning."""
    c = make_canvas()
    fill_background(c, 0)
    dither_nebula(c, int(HEIGHT * 0.3), HEIGHT, 0.3, palette_idx=1)
    place_stars(c, 5, bright_ratio=0.3)
    c = place_asteroids(c, 5, (10, 30))
    return c


def tile_open_stars(rng):
    """Open space with many stars. No asteroids."""
    c = make_canvas()
    fill_background(c, 0)
    dither_nebula(c, int(HEIGHT * 0.4), HEIGHT, 0.2, palette_idx=1)
    place_stars(c, 50, bright_ratio=0.3, cluster_chance=0.15)
    return c


# -------- Main --------
TILES = [
    ("tile_01_open_sun",   tile_open_sun),
    ("tile_02_enter_belt", tile_enter_belt),
    ("tile_03_mid_belt",   tile_mid_belt),
    ("tile_04_peak_belt",  tile_peak_belt),
    ("tile_05_exit_belt",  tile_exit_belt),
    ("tile_06_open_stars", tile_open_stars),
]


def main():
    rng = random.Random(SEED)
    for name, fn in TILES:
        # Re-seed the per-tile randomness for reproducibility
        random.seed(SEED)
        np.random.seed(SEED)
        canvas = fn(rng)
        path = OUT_DIR / f"{name}.png"
        Image.fromarray(canvas).save(path, optimize=True)
        # Quick stats
        flat = canvas.reshape(-1, 3)
        unique = len(set(map(tuple, flat[::100])))  # sampled
        print(f"  {name}: {path.name} ({WIDTH}x{HEIGHT}, ~{unique} unique colors)")

    # Build a contact sheet for quick review
    sheet = np.zeros((HEIGHT, WIDTH * 6 + 5 * 4, 3), dtype=np.uint8)
    sheet[:] = PAL[0]
    for i, (name, _) in enumerate(TILES):
        canvas = np.array(Image.open(OUT_DIR / f"{name}.png").convert("RGB"))
        x0 = i * (WIDTH + 4)
        sheet[:, x0:x0 + WIDTH] = canvas
    Image.fromarray(sheet).save(OUT_DIR / "_contact_sheet.png", optimize=True)
    print(f"\nContact sheet: {OUT_DIR / '_contact_sheet.png'}")

    # Stacked preview (one column showing all 6 tiles vertically)
    stacked = np.zeros((HEIGHT * 6, WIDTH, 3), dtype=np.uint8)
    for i, (name, _) in enumerate(TILES):
        canvas = np.array(Image.open(OUT_DIR / f"{name}.png").convert("RGB"))
        stacked[i * HEIGHT:(i + 1) * HEIGHT] = canvas
    Image.fromarray(stacked).save(OUT_DIR / "_stacked_preview.png", optimize=True)
    print(f"Stacked preview: {OUT_DIR / '_stacked_preview.png'} ({stacked.shape[1]}x{stacked.shape[0]})")

    print(f"\nDone. {len(TILES)} tiles generated in <2s.")


if __name__ == "__main__":
    main()
