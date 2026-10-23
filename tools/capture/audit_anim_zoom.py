"""Render one animation's frames at high zoom with a canvas grid, so missing
or clipped body parts are visible frame by frame.

Usage: python tools/capture/audit_anim_zoom.py <anim> [first] [last]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(r"F:\AI\MM\void-hunter")
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

ANIM = sys.argv[1] if len(sys.argv) > 1 else "javelin"
FIRST = int(sys.argv[2]) if len(sys.argv) > 2 else 0
LAST = int(sys.argv[3]) if len(sys.argv) > 3 else 9

SCALE = 6
CELL_W, CELL_H = 96 * SCALE, 80 * SCALE
PAD = 8

cols = 2
count = LAST - FIRST + 1
rows = (count + cols - 1) // cols
sheet = Image.new("RGB", (CELL_W * cols, CELL_H * rows), (14, 14, 30))

for i in range(count):
    frame = FIRST + i
    path = (
        ROOT / "Assets/sprites/bosses/goliath" / ANIM / f"frame_{frame:02d}.png"
    )
    img = Image.open(path).convert("RGBA")
    big = img.resize((CELL_W, CELL_H), Image.NEAREST)
    cell = Image.new("RGBA", (CELL_W, CELL_H), (14, 14, 30, 255))
    cell.alpha_composite(big)

    # Canvas border so an edge-touching silhouette reads as clipped.
    d = ImageDraw.Draw(cell)
    d.rectangle((0, 0, CELL_W - 1, CELL_H - 1), outline=(70, 70, 110, 255))
    # Anchor crosshair: canvas centre col 48, row 40.
    ax, ay = 48 * SCALE, 40 * SCALE
    d.line((ax - 10, ay, ax + 10, ay), fill=(90, 90, 130, 255))
    d.line((ax, ay - 10, ax, ay + 10), fill=(90, 90, 130, 255))

    # Measured silhouette margins.
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        l, t, r, b = bbox
        print(
            f"  {ANIM}/frame_{frame:02d}  bbox x[{l},{r - 1}] y[{t},{b - 1}]  "
            f"margins L={l} R={95 - (r - 1)} T={t} B={79 - (b - 1)}"
        )
        if l == 0 or t == 0 or r == 96 or b == 80:
            print(f"      ^^ TOUCHES CANVAS EDGE — silhouette looks clipped")
    else:
        print(f"  {ANIM}/frame_{frame:02d}  EMPTY")

    sheet.paste(cell.convert("RGB"), ((i % cols) * CELL_W, (i // cols) * CELL_H))

out = ROOT / "logs" / f"zoom_{ANIM}_{FIRST}_{LAST}.png"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out)
print(f"saved {out}")