"""Process generated sprite sheet strips into final per-entity sheet PNGs.

Input: `_sheet_<name>.png` files containing 6 frames in a horizontal
row on a dark navy background.

Output: `<name>_sheet.png` files containing 6 frames composited into
a single strip at the target sprite size, ready for the game to load
and cycle.

For each source strip:
1. Remove the auto-detected background color (corners sample).
2. Split into 6 equal vertical sections.
3. For each section, find the content bounding box, crop, and
   NEAREST-resize to the target sprite size.
4. Composite the 6 final frames into a horizontal strip and save.

Target sizes (matching the static sprite library):
  player / scout / cruiser / heavy / bombers / ufo / kamikaze
    and player_01..05 / enemy_01..20: 16x16 per frame -> strip 96x16
  boss: 48x48 per frame -> strip 288x48
  player_bullet / enemy_bullet / laser_01..10: 8x8 per frame -> strip 48x8
"""
from PIL import Image
import os
import sys

SPRITES_DIR = "stellar_horizon/assets/sprites"

# (source, target, frame_w, frame_h, frame_count)
JOBS = [
    # 7 active sprites.
    ("_sheet_player.png",        "player_sheet.png",        16, 16, 6),
    ("_sheet_scout.png",         "scout_sheet.png",         16, 16, 6),
    ("_sheet_cruiser.png",       "cruiser_sheet.png",       16, 16, 6),
    ("_sheet_heavy.png",         "heavy_sheet.png",         16, 16, 6),
    ("_sheet_boss.png",          "boss_sheet.png",          48, 48, 6),
    ("_sheet_player_bullet.png", "player_bullet_sheet.png",  8,  8, 6),
    ("_sheet_enemy_bullet.png",  "enemy_bullet_sheet.png",   8,  8, 6),
    # 5 player variants.
    ("_sheet_player_01.png",     "player_01_sheet.png",     16, 16, 6),
    ("_sheet_player_02.png",     "player_02_sheet.png",     16, 16, 6),
    ("_sheet_player_03.png",     "player_03_sheet.png",     16, 16, 6),
    ("_sheet_player_04.png",     "player_04_sheet.png",     16, 16, 6),
    ("_sheet_player_05.png",     "player_05_sheet.png",     16, 16, 6),
    # 20 enemy variants.
    ("_sheet_enemy_01.png",      "enemy_01_sheet.png",      16, 16, 6),
    ("_sheet_enemy_02.png",      "enemy_02_sheet.png",      16, 16, 6),
    ("_sheet_enemy_03.png",      "enemy_03_sheet.png",      16, 16, 6),
    ("_sheet_enemy_04.png",      "enemy_04_sheet.png",      16, 16, 6),
    ("_sheet_enemy_05.png",      "enemy_05_sheet.png",      16, 16, 6),
    ("_sheet_enemy_06.png",      "enemy_06_sheet.png",      16, 16, 6),
    ("_sheet_enemy_07.png",      "enemy_07_sheet.png",      16, 16, 6),
    ("_sheet_enemy_08.png",      "enemy_08_sheet.png",      16, 16, 6),
    ("_sheet_enemy_09.png",      "enemy_09_sheet.png",      16, 16, 6),
    ("_sheet_enemy_10.png",      "enemy_10_sheet.png",      16, 16, 6),
    ("_sheet_enemy_11.png",      "enemy_11_sheet.png",      16, 16, 6),
    ("_sheet_enemy_12.png",      "enemy_12_sheet.png",      16, 16, 6),
    ("_sheet_enemy_13.png",      "enemy_13_sheet.png",      16, 16, 6),
    ("_sheet_enemy_14.png",      "enemy_14_sheet.png",      16, 16, 6),
    ("_sheet_enemy_15.png",      "enemy_15_sheet.png",      16, 16, 6),
    ("_sheet_enemy_16.png",      "enemy_16_sheet.png",      16, 16, 6),
    ("_sheet_enemy_17.png",      "enemy_17_sheet.png",      16, 16, 6),
    ("_sheet_enemy_18.png",      "enemy_18_sheet.png",      16, 16, 6),
    ("_sheet_enemy_19.png",      "enemy_19_sheet.png",      16, 16, 6),
    ("_sheet_enemy_20.png",      "enemy_20_sheet.png",      16, 16, 6),
    # 10 laser variants.
    ("_sheet_laser_01.png",      "laser_01_sheet.png",       8,  8, 6),
    ("_sheet_laser_02.png",      "laser_02_sheet.png",       8,  8, 6),
    ("_sheet_laser_03.png",      "laser_03_sheet.png",       8,  8, 6),
    ("_sheet_laser_04.png",      "laser_04_sheet.png",       8,  8, 6),
    ("_sheet_laser_05.png",      "laser_05_sheet.png",       8,  8, 6),
    ("_sheet_laser_06.png",      "laser_06_sheet.png",       8,  8, 6),
    ("_sheet_laser_07.png",      "laser_07_sheet.png",       8,  8, 6),
    ("_sheet_laser_08.png",      "laser_08_sheet.png",       8,  8, 6),
    ("_sheet_laser_09.png",      "laser_09_sheet.png",       8,  8, 6),
    ("_sheet_laser_10.png",      "laser_10_sheet.png",       8,  8, 6),
]


def remove_navy_bg(img: Image.Image, threshold: int = 32) -> Image.Image:
    w, h = img.size
    px = img.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg = (
        sum(c[0] for c in corners) // 4,
        sum(c[1] for c in corners) // 4,
        sum(c[2] for c in corners) // 4,
    )
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if abs(r - bg[0]) <= threshold and abs(g - bg[1]) <= threshold and abs(b - bg[2]) <= threshold:
                op[x, y] = (0, 0, 0, 0)
            else:
                op[x, y] = (r, g, b, a)
    return out


def crop_to_content(img: Image.Image, pad: int = 2) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(img.size[0], r + pad)
    b = min(img.size[1], b + pad)
    return img.crop((l, t, r, b))


def process(src: str, dst: str, fw: int, fh: int, fc: int) -> None:
    src_path = os.path.join(SPRITES_DIR, src)
    dst_path = os.path.join(SPRITES_DIR, dst)
    img = Image.open(src_path).convert("RGBA")
    img = remove_navy_bg(img)
    w, h = img.size
    # Split into fc equal vertical sections.
    section_w = w // fc
    sections = []
    for i in range(fc):
        sec = img.crop((i * section_w, 0, (i + 1) * section_w, h))
        sec = crop_to_content(sec, pad=2)
        sec = sec.resize((fw, fh), Image.NEAREST)
        sections.append(sec)
    # Composite into a horizontal strip.
    strip = Image.new("RGBA", (fw * fc, fh), (0, 0, 0, 0))
    for i, sec in enumerate(sections):
        strip.paste(sec, (i * fw, 0), sec)
    strip.save(dst_path)
    print(f"  {src} -> {dst} ({fw * fc}x{fh}, {fc} frames of {fw}x{fh})")


if __name__ == "__main__":
    print("Processing sprite sheets...")
    for src, dst, fw, fh, fc in JOBS:
        if not os.path.exists(os.path.join(SPRITES_DIR, src)):
            print(f"  [SKIP] {src} (not found)")
            continue
        process(src, dst, fw, fh, fc)
    print("Done.")
