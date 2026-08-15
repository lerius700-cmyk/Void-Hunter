"""Preview the new 3-column strip at gameplay scale (320x5760)."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets" / "background"
OUT = ROOT / "tools" / "playtest_out" / "strip_v1.28_preview.png"
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
print(f"Strip: {strip.size}")
# Save a 320x480 window showing the top of the strip
top_window = strip.crop((0, 0, 320, 480))
top_window.save(OUT)
print(f"Top window saved: {OUT}")
