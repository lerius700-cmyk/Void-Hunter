"""Upscale the internal-resolution PNGs to display size (4x) so the user
can see what the game looks like on the actual 960x1440 screen.

This is purely a documentation/visual tool — not part of the game.
"""
from __future__ import annotations

import os
from pathlib import Path
import pygame

OUT = Path(__file__).resolve().parent / "visualize_out"
OUT_4X = Path(__file__).resolve().parent / "visualize_out_4x"
OUT_4X.mkdir(exist_ok=True)

pygame.init()
screen = pygame.display.set_mode((1, 1))

for png in sorted(OUT.glob("*.png")):
    img = pygame.image.load(str(png)).convert()
    scaled = pygame.transform.scale(img, (img.get_width() * 4, img.get_height() * 4))
    out_path = OUT_4X / png.name
    pygame.image.save(scaled, str(out_path))
    print(f"  {png.name}: {img.get_size()} -> {scaled.get_size()} -> {out_path.name}")

print(f"\nDone. {OUT_4X}")
