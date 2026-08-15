"""BLOQUE 58.7ad: build the LONG galaxy strip (cinta).

The user wants a single image that has the 3 vertical panels GLUED
TOGETHER vertically. This is the "cinta" (ribbon) format: a single
tall image that scrolls down seamlessly.

Source: 1920x1920 galaxy image (square with 3 columns of galaxies).
Process:
  1. Split source into 3 vertical columns: 640x1920 each.
  2. Stack the 3 columns vertically into a single 640x5760 strip.
  3. Save as galaxy_strip.png (single long image, ready to scroll).

At runtime, ScrollingGalaxyBackground loads galaxy_strip.png first.
The strip is 640x5760 — when scaled to 320 wide, the height becomes
320x5760, which scrolls at 30 px/s for 192s (3.2 min) before looping.
The screen is 480 tall, so at any moment the player sees roughly 1/12
of the strip (one of the 3 columns partially).
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets" / "background"
SRC = Path(r"C:\Users\Lerius\.minimax\v2\assets\2026\08\14\22-01-06-202-asset_20260814-220106-202_975d0b97d479_f1d8ae8d-Wan_Image_Generate_Fondo vertical loopable para space-shooter mobile en orie.png")

print(f"Loading: {SRC.name}")
img = Image.open(SRC)
print(f"Source size: {img.size}, mode: {img.mode}")
w, h = img.size  # 1920, 1920

# Step 1: split into 3 vertical columns (640x1920 each)
col_w = w // 3  # 640
panels = [img.crop((i * col_w, 0, (i + 1) * col_w, h)) for i in range(3)]

# Step 2: stack vertically into a single 640x5760 strip
strip_w = col_w            # 640
strip_h = h * 3            # 5760
strip = Image.new(panels[0].mode, (strip_w, strip_h))
for i, panel in enumerate(panels):
    strip.paste(panel, (0, i * h))
    # Also save the individual panels for backward compat
    panel_path = ASSETS / f"galaxy_panel_{i}.png"
    panel.save(panel_path, format="PNG", optimize=True)
    print(f"  panel {i}: {panel_path.name} size={panel.size}")

# Step 3: save the combined strip
strip_path = ASSETS / "galaxy_strip.png"
strip.save(strip_path, format="PNG", optimize=True)
print(f"\n[OK] Long strip saved: {strip_path.name}  size={strip.size}")
print(f"  At 30 px/s scroll, loops every {strip_h / 30:.0f}s ({strip_h / 30 / 60:.1f} min)")
print(f"  Scaled to 320 wide: 320x{strip_h} (each panel = 320x{h})")
