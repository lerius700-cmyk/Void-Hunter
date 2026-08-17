"""Build a contact sheet PNG of all new sprites for quick review.

Arranges 20 enemies, 5 player variants, and 10 lasers into labelled rows
on a single 1920x1080 canvas, upscaled 6x from native so the pixel
art stays readable.
"""
from PIL import Image, ImageDraw, ImageFont
import os
import sys

SPRITES_DIR = "stellar_horizon/assets/sprites"
OUT = "tools/playtest_out/sprites_contact_sheet.png"

# Section: list of (label, filename, w, h)
SECTIONS = [
    ("ENEMIES  (20 sprites)", [
        ("01_red_dart",       "enemy_01.png"),
        ("02_purple_wedge",   "enemy_02.png"),
        ("03_orange_bomber",  "enemy_03.png"),
        ("04_blue_diamond",   "enemy_04.png"),
        ("05_green_alien",    "enemy_05.png"),
        ("06_yellow_saucer",  "enemy_06.png"),
        ("07_pink_destroyer", "enemy_07.png"),
        ("08_cyan_ghost",     "enemy_08.png"),
        ("09_white_armor",    "enemy_09.png"),
        ("10_black_stealth",  "enemy_10.png"),
        ("11_magenta_crystal","enemy_11.png"),
        ("12_lime_insect",    "enemy_12.png"),
        ("13_bronze_golem",   "enemy_13.png"),
        ("14_teal_aquatic",   "enemy_14.png"),
        ("15_coral_snake",    "enemy_15.png"),
        ("16_silver_chrome",  "enemy_16.png"),
        ("17_gold_royal",     "enemy_17.png"),
        ("18_violet_phantom", "enemy_18.png"),
        ("19_crimson_fanged", "enemy_19.png"),
        ("20_electric_arc",   "enemy_20.png"),
    ]),
    ("PLAYERS  (5 sprites)", [
        ("01_green_interceptor", "player_01.png"),
        ("02_blue_heavy",        "player_02.png"),
        ("03_white_ace",         "player_03.png"),
        ("04_red_speedster",     "player_04.png"),
        ("05_purple_void",       "player_05.png"),
    ]),
    ("LASERS  (10 sprites)", [
        ("01_yellow_plasma",   "laser_01.png"),
        ("02_red_pulse",       "laser_02.png"),
        ("03_blue_ion",        "laser_03.png"),
        ("04_green_acid",      "laser_04.png"),
        ("05_purple_void_orb", "laser_05.png"),
        ("06_orange_fireball", "laser_06.png"),
        ("07_white_piercing",  "laser_07.png"),
        ("08_pink_heart",      "laser_08.png"),
        ("09_cyan_ice",        "laser_09.png"),
        ("10_rainbow_streak",  "laser_10.png"),
    ]),
]

CELL = 96            # each sprite rendered in a 96x96 cell
LABEL_H = 22         # height of the label text under each sprite
PAD = 16
SECTION_GAP = 32
BG = (10, 15, 31)
TEXT = (220, 220, 240)
SECTION_COLOR = (255, 240, 100)

# Compute canvas size
def section_size(items):
    n = len(items)
    cols = min(n, 10)
    rows = (n + cols - 1) // cols
    w = PAD + cols * (CELL + PAD)
    h = LABEL_H + rows * (CELL + LABEL_H + PAD)
    return w, h, cols, rows

total_w = 0
total_h = PAD
for title, items in SECTIONS:
    w, h, _, _ = section_size(items)
    total_w = max(total_w, w)
    total_h += LABEL_H + h + SECTION_GAP
total_w += PAD

canvas = Image.new("RGB", (total_w, total_h), BG)
draw = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("consola.ttf", 13)
    font_b = ImageFont.truetype("consola.ttf", 16)
except OSError:
    font = ImageFont.load_default()
    font_b = font

y = PAD
for title, items in SECTIONS:
    draw.text((PAD, y), title, fill=SECTION_COLOR, font=font_b)
    y += LABEL_H
    _, _, cols, rows = section_size(items)
    for idx, (label, fname) in enumerate(items):
        col = idx % cols
        row = idx // cols
        x = PAD + col * (CELL + PAD)
        sy = y + row * (CELL + LABEL_H + PAD)
        # Cell background (subtle)
        draw.rectangle((x, sy, x + CELL, sy + CELL), outline=(40, 50, 80))
        # Sprite
        path = os.path.join(SPRITES_DIR, fname)
        if os.path.exists(path):
            sp = Image.open(path).convert("RGBA")
            # Scale up to fill CELL while keeping pixel art crisp
            scale = max(1, CELL // max(sp.size))
            sp = sp.resize((sp.size[0] * scale, sp.size[1] * scale), Image.NEAREST)
            ox = x + (CELL - sp.size[0]) // 2
            oy = sy + (CELL - sp.size[1]) // 2
            canvas.paste(sp, (ox, oy), sp)
        # Label
        draw.text((x, sy + CELL + 2), label, fill=TEXT, font=font)
    y += rows * (CELL + LABEL_H + PAD) + SECTION_GAP

os.makedirs(os.path.dirname(OUT), exist_ok=True)
canvas.save(OUT)
print(f"Saved: {OUT}  ({canvas.size[0]}x{canvas.size[1]})")
