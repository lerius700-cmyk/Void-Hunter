"""Capture the 6 Act 1 tiles as they appear in-game (tile sequence mode).

For each scroll position [0, 480, 960, 1440, 1920, 2400], instantiates
ParallaxBackground with use_tile_sequence=True, draws to a Surface, saves PNG.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import src...` works regardless of cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pygame

pygame.init()

OUT_DIR = Path(r"D:\AI\void-hunter\tools\playtest_out")
OUT_DIR.mkdir(parents=True, exist_ok=True)

from src.systems.parallax import ParallaxBackground

tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
bg = ParallaxBackground(
    width=320, height=480,
    use_tile_sequence=True,
    tiles_dir=tiles_dir,
    spawn_planets=False,  # skip planets for cleaner capture
)

target = pygame.Surface((320, 480))
for i, scroll_y in enumerate([0, 480, 960, 1440, 1920, 2400], start=1):
    bg._strip_y_offset = float(scroll_y)
    target.fill((4, 8, 20))  # clear with deep_space color
    bg.draw(target)
    out_path = OUT_DIR / f"bloque_64_act1_scroll_{i:02d}_y{scroll_y:04d}.png"
    pygame.image.save(target, str(out_path))
    print(f"Saved: {out_path.name}")

print("Done. 6 frames in tools/playtest_out/.")
