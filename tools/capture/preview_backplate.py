"""BLOQUE 66.6: produce a 3-row preview of all 10 javelin frames:
  row 1: BEFORE  (raw javelin/frame_NN.png)
  row 2: phase1_idle/frame_00  (the stable backplate reference)
  row 3: AFTER   (alpha_composite(phase1_idle, javelin))

Stitched into a single PNG so we can verify the composite makes
every javelin frame look complete without breaking the existing
ones.
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
OUT = ROOT / "Assets/sprites/bosses/goliath"
ZOOM = 4
PAD = 6

base = Image.open(OUT / "phase1_idle/frame_00.png").convert("RGBA")


def big(im, z=ZOOM):
    return im.resize((im.width * z, im.height * z), Image.NEAREST)


def build(anim: str, out_path: str) -> None:
    cell_w = 96 * ZOOM
    cell_h = 80 * ZOOM
    canvas = Image.new(
        "RGBA",
        (cell_w * 10 + PAD * 11, cell_h * 3 + PAD * 4),
        (12, 12, 22, 255),
    )
    for i in range(10):
        src = Image.open(OUT / f"{anim}/frame_{i:02d}.png").convert("RGBA")
        composite = Image.alpha_composite(base, src)
        # Row 0: BEFORE
        canvas.paste(big(src), (PAD + i * (cell_w + PAD), PAD))
        # Row 1: BASE
        canvas.paste(big(base), (PAD + i * (cell_w + PAD), PAD * 2 + cell_h))
        # Row 2: AFTER
        canvas.paste(big(composite), (PAD + i * (cell_w + PAD), PAD * 3 + cell_h * 2))
    canvas.save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    for a in ["javelin", "laser", "purple_bullet"]:
        build(a, f"tools/playtest_out/goliath_backplate_{a}_3row.png")
