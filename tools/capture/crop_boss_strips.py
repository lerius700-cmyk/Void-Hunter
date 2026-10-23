"""BLOQUE 66.6: crop just the boss area from each captured runtime frame
(top 200 px of the 480 viewport), then build strips. This isolates the
boss visual from the parallax background / HUD.
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
ZOOM = 4
CROP_X = 40
CROP_Y = 0
CROP_W = 240
CROP_H = 200

def build(anim: str) -> None:
    cell_w = CROP_W * ZOOM
    cell_h = CROP_H * ZOOM
    pad = 8 * ZOOM
    canvas = Image.new("RGBA", (cell_w * 5 + pad * 4, cell_h * 2 + pad), (8, 8, 20, 255))
    for i in range(10):
        p = ROOT / f"tools/playtest_out/goliath_runtime_{anim}_f{i:02d}.png"
        im = Image.open(p).convert("RGBA").crop((CROP_X, CROP_Y, CROP_X + CROP_W, CROP_Y + CROP_H))
        big = im.resize((cell_w, cell_h), Image.NEAREST)
        row, col = i // 5, i % 5
        x = col * (cell_w + pad)
        y = row * (cell_h + pad)
        canvas.paste(big, (x, y))
    out = ROOT / f"tools/playtest_out/goliath_runtime_{anim}_crop_strip.png"
    canvas.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    for a in ["phase1_idle", "javelin", "laser", "purple_bullet"]:
        build(a)
