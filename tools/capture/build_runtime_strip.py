"""BLOQUE 66.6: combine 10 captured runtime frames into a 5x2 strip
(zoom 2x) so we can SEE if GOLIATH is "cortado" in any frame.
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
ZOOM = 2


def build(anim: str) -> None:
    cell_w = 320 * ZOOM
    cell_h = 480 * ZOOM
    pad = 12 * ZOOM
    canvas = Image.new("RGBA", (cell_w * 5 + pad * 4, cell_h * 2 + pad), (8, 8, 20, 255))
    for i in range(10):
        p = ROOT / f"tools/playtest_out/goliath_runtime_{anim}_f{i:02d}.png"
        im = Image.open(p).convert("RGBA")
        big = im.resize((cell_w, cell_h), Image.NEAREST)
        row, col = i // 5, i % 5
        x = col * (cell_w + pad)
        y = row * (cell_h + pad)
        canvas.paste(big, (x, y))
    out = ROOT / f"tools/playtest_out/goliath_runtime_{anim}_strip.png"
    canvas.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    for a in ["phase1_idle", "javelin", "laser", "purple_bullet"]:
        build(a)
