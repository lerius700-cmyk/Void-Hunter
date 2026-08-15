"""BLOQUE 58.7y: split the new galaxy image into 3 vertical panels.

Reads the latest user-supplied galaxy image and saves 3 vertical thirds
as galaxy_panel_0/1/2.png, each 1920x640 (the same shape as the BLOQUE
58.6w panels). The ScrollingGalaxyBackground code in 'panels' mode will
stack them top->mid->bottom and the strip will repeat.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets" / "background"
SRC = Path(r"C:\Users\Lerius\.minimax\v2\assets\2026\08\14\22-01-06-202-asset_20260814-220106-202_975d0b97d479_f1d8ae8d-Wan_Image_Generate_Fondo vertical loopable para space-shooter mobile en orie.png")
DST = ASSETS

print(f"Loading: {SRC.name}")
img = Image.open(SRC)
print(f"Source size: {img.size}, mode: {img.mode}")
w, h = img.size
if w != h:
    print(f"WARNING: source is not square ({w}x{h}); splitting as 3 equal-height panels")
third = h // 3
panels = [img.crop((0, i * third, w, (i + 1) * third)) for i in range(3)]
for i, panel in enumerate(panels):
    out = DST / f"galaxy_panel_{i}.png"
    panel.save(out, format="PNG", optimize=True)
    print(f"  -> {out.name}  size={panel.size}")
print("Done.")
