"""BLOQUE 58.7z: split the galaxy image into 3 VERTICAL columns.

The user wants a tall vertical strip that's 3x the image height. We split
the 1920x1920 image into 3 vertical columns (640x1920 each) and stack
them. When scaled to 320 wide, each panel is 320x1920, total strip is
320x5760 (3x the original 320x320).

This matches the BLOQUE 58.6w approach (3 panels of 640x1920 stacked
into a 640x5760 strip), but using the new 1920x1920 source image.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets" / "background"
SRC = Path(r"C:\Users\Lerius\.minimax\v2\assets\2026\08\14\22-01-06-202-asset_20260814-220106-202_975d0b97d479_f1d8ae8d-Wan_Image_Generate_Fondo vertical loopable para space-shooter mobile en orie.png")

print(f"Loading: {SRC.name}")
img = Image.open(SRC)
print(f"Source size: {img.size}, mode: {img.mode}")
w, h = img.size
# 3 vertical columns: each 640x1920
col_w = w // 3
panels = [img.crop((i * col_w, 0, (i + 1) * col_w, h)) for i in range(3)]
for i, panel in enumerate(panels):
    out = ASSETS / f"galaxy_panel_{i}.png"
    panel.save(out, format="PNG", optimize=True)
    print(f"  -> {out.name}  size={panel.size}")
print("Done. 3 vertical columns stacked into a 640x5760 strip (1920x1920 source).")
