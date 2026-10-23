"""BLOQUE 66.6: 3-row preview v2 — base from build_body_backplate, the
spearless stable body silhouette.
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
ASSETS = ROOT / "Assets/sprites/bosses/goliath"
BACKPLATE_PATH = ROOT / "tools/playtest_out/goliath_body_backplate.png"
ZOOM = 4
PAD = 8


def big(im, z=ZOOM):
    return im.resize((im.width * z, im.height * z), Image.NEAREST)


def build(anim: str, backplate: Image.Image) -> None:
    cell_w = 96 * ZOOM
    cell_h = 80 * ZOOM
    canvas = Image.new(
        "RGBA",
        (cell_w * 10 + PAD * 11, cell_h * 3 + PAD * 4),
        (12, 12, 22, 255),
    )
    for i in range(10):
        src = Image.open(ASSETS / f"{anim}/frame_{i:02d}.png").convert("RGBA")
        composite = Image.alpha_composite(backplate, src)
        canvas.paste(big(src), (PAD + i * (cell_w + PAD), PAD))
        canvas.paste(big(backplate), (PAD + i * (cell_w + PAD), PAD * 2 + cell_h))
        canvas.paste(
            big(composite),
            (PAD + i * (cell_w + PAD), PAD * 3 + cell_h * 2),
        )
    canvas.save(ROOT / f"tools/playtest_out/goliath_backplate_{anim}_3row_v2.png")
    print(f"wrote goliath_backplate_{anim}_3row_v2.png")


if __name__ == "__main__":
    backplate = Image.open(BACKPLATE_PATH).convert("RGBA")
    for a in ["javelin", "laser", "purple_bullet", "death"]:
        build(a, backplate)
