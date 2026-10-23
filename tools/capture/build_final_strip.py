"""BLOQUE 66.6: build a 5x2 strip per animation from final_*.png frames."""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
OUT = ROOT / "tools/playtest_out"
ZOOM = 4
PAD = 8

ANIMS = ["phase1_idle", "javelin", "laser", "purple_bullet"]


def build(anim: str) -> None:
    cell_w = 240 * ZOOM
    cell_h = 200 * ZOOM
    canvas = Image.new(
        "RGBA",
        (cell_w * 5 + PAD * 6, cell_h * 2 + PAD * 3),
        (12, 12, 22, 255),
    )
    for i in range(10):
        p = OUT / f"final_{anim}_f{i:02d}.png"
        im = Image.open(p).convert("RGBA")
        big = im.resize((cell_w, cell_h), Image.NEAREST)
        row, col = i // 5, i % 5
        canvas.paste(big, (PAD + col * (cell_w + PAD), PAD + row * (cell_h + PAD)))
    canvas.save(OUT / f"final_{anim}_strip.png")
    print(f"wrote final_{anim}_strip.png")


for a in ANIMS:
    build(a)
