"""BLOQUE 66.6: inspect phase1_idle to find where the spear pixels sit
across all 10 frames, so we can mask them off the backplate.
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
ASSETS = ROOT / "Assets/sprites/bosses/goliath" / "phase1_idle"
OUT = ROOT / "tools/playtest_out" / "phase1_idle_heatmap.png"

# For each pixel, count opaque occurrences across the 10 frames.
w, h = 96, 80
counts = [[0] * h for _ in range(w)]
for i in range(10):
    f = Image.open(ASSETS / f"frame_{i:02d}.png").convert("RGBA")
    a = f.split()[-1]
    for y in range(h):
        for x in range(w):
            if a.getpixel((x, y)) > 10:
                counts[x][y] += 1

# Visualize as a heatmap.
heat = Image.new("RGBA", (w, h), (0, 0, 0, 255))
heat_px = heat.load()
for y in range(h):
    for x in range(w):
        c = counts[x][y]
        if c == 0:
            heat_px[x, y] = (0, 0, 0, 255)
        elif c < 4:
            heat_px[x, y] = (60, 0, 80, 255)  # dynamic (rarely opaque)
        elif c < 8:
            heat_px[x, y] = (90, 90, 0, 255)
        elif c < 10:
            heat_px[x, y] = (140, 140, 50, 255)
        else:  # c == 10
            heat_px[x, y] = (255, 200, 80, 255)  # always opaque = stable

heat.resize((w * 6, h * 6), Image.NEAREST).save(OUT)
print(f"saved {OUT}")
print("color key:")
print("  yellow (10/10) = stable body, ALWAYS there")
print("  amber  (8-9)   = mostly stable")
print("  dark amber     = sometimes stable")
print("  purple (<4)    = dynamic (spear positions, etc.)")
