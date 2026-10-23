"""Build a side-by-side NO_BP / WITH_BP strip per animation."""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
OUT = ROOT / "tools/playtest_out"
ZOOM = 2

ANIMS = ["javelin", "phase1_idle"]


def build(anim: str) -> None:
    cell_w = 240 * ZOOM
    cell_h = 200 * ZOOM
    pad = 6 * ZOOM
    # Top row: NO_BP. Bottom row: WITH_BP.
    canvas = Image.new(
        "RGBA",
        (cell_w * 10 + pad * 11, cell_h * 2 + pad * 3),
        (8, 8, 20, 255),
    )
    for i in range(10):
        no_bp = Image.open(OUT / f"goliath_{anim}_f{i:02d}_NO_bp.png").convert("RGBA")
        with_bp = Image.open(OUT / f"goliath_{anim}_f{i:02d}_WITH_bp.png").convert("RGBA")
        canvas.paste(
            no_bp.resize((cell_w, cell_h), Image.NEAREST),
            (pad + i * (cell_w + pad), pad),
        )
        canvas.paste(
            with_bp.resize((cell_w, cell_h), Image.NEAREST),
            (pad + i * (cell_w + pad), pad * 2 + cell_h),
        )
    out = OUT / f"goliath_compare_{anim}.png"
    canvas.save(out)
    print(f"wrote {out}")


for a in ANIMS:
    build(a)
