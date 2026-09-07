"""Nearest-color palette mapper (BLOQUE 59).

Maps arbitrary RGB pixels to the closest color in the 64-color palette
defined in `src/utils/palette.py`. Uses Euclidean distance in RGB space.
"""
from __future__ import annotations

from PIL import Image

from src.utils.palette import PALETTE


def nearest_palette_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Return the palette color with minimum Euclidean distance to `rgb`."""
    r, g, b = rgb
    best = None
    best_dist = float("inf")
    for color in PALETTE.values():
        d = (color[0] - r) ** 2 + (color[1] - g) ** 2 + (color[2] - b) ** 2
        if d < best_dist:
            best_dist = d
            best = color
    return best


def map_image_to_palette(img: Image.Image) -> Image.Image:
    """Return a new RGB image where every pixel is the nearest palette color."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    out = Image.new("RGB", img.size)
    src = img.load()
    dst = out.load()
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            dst[x, y] = nearest_palette_color(src[x, y])
    return out
