"""BLOQUE 66.6: side-by-side 6x zoom of every javelin frame so we can
visually audit which frames look "complete" vs "cortado".
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
ASSETS = ROOT / "Assets/sprites/bosses/goliath" / "javelin"
OUT = ROOT / "logs/zoom_javelin_compare.png"

ZOOM = 6
PAD = 8

frames = [Image.open(ASSETS / f"frame_{i:02d}.png").convert("RGBA") for i in range(10)]

cell_w = 96 * ZOOM
cell_h = 80 * ZOOM

# Two rows: top row is the source sprite at 6x; bottom row is the same with a
# 1-pixel alpha outline drawn so we can see transparent regions clearly.
canvas = Image.new(
    "RGBA",
    (cell_w * 5 + PAD * 6, cell_h * 2 + PAD * 3),
    (12, 12, 22, 255),
)
for i in range(10):
    src = frames[i].resize((cell_w, cell_h), Image.NEAREST)
    canvas.paste(src, (PAD + (i % 5) * (cell_w + PAD), PAD + (i // 5) * (cell_h + PAD)))

canvas.save(OUT)
print(f"wrote {OUT}")
