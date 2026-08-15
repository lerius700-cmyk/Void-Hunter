"""BLOQUE 58.7y: capture a preview of the 3 stacked panels as one strip.

Builds a single tall image (320 wide x 1920 tall) showing the strip
scaled to gameplay width, so we can verify the hard cuts look OK.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets" / "background"
OUT = ROOT / "tools" / "playtest_out" / "strip_v1.27_preview.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

panels = [Image.open(ASSETS / f"galaxy_panel_{i}.png") for i in range(3)]
w_target = 320
scaled = [p.resize((w_target, int(p.height * w_target / p.width))) for p in panels]
total_h = sum(s.height for s in scaled)
strip = Image.new("RGB", (w_target, total_h))
y = 0
for s in scaled:
    strip.paste(s, (0, y))
    y += s.height
strip.save(OUT)
print(f"Strip: {strip.size}, output: {OUT}")
