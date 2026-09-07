"""Tests for the ship sprite redesign pipeline (BLOQUE 59)."""
from __future__ import annotations

from PIL import Image

from tools.redesign_ships._palette_map import map_image_to_palette, nearest_palette_color
from src.utils.palette import PALETTE


def test_nearest_palette_color_returns_exact_match():
    """A color that's exactly in the palette returns itself."""
    palette_rgb = next(iter(PALETTE.values()))
    result = nearest_palette_color(palette_rgb)
    assert result == palette_rgb


def test_nearest_palette_color_finds_nearest():
    """A color near a palette entry returns that entry (Euclidean RGB)."""
    target = next(iter(PALETTE.values()))
    # Nudge each channel by +1
    near = (target[0] + 1, target[1] + 1, target[2] + 1)
    result = nearest_palette_color(near)
    assert result == target


def test_map_image_to_palette_uses_only_palette_colors():
    """Every pixel after mapping is within ±2 of a palette color."""
    # Create a small test image with random colors
    test_img = Image.new("RGB", (4, 4))
    pixels = test_img.load()
    for x in range(4):
        for y in range(4):
            pixels[x, y] = (50, 100, 150)  # arbitrary RGB
    mapped = map_image_to_palette(test_img)
    assert mapped.size == (4, 4)
    mapped_pixels = mapped.load()
    palette_set = set(PALETTE.values())
    for x in range(4):
        for y in range(4):
            rgb = mapped_pixels[x, y]
            # Check this pixel is within ±2 of some palette color
            found = False
            for p in palette_set:
                if all(abs(rgb[i] - p[i]) <= 2 for i in range(3)):
                    found = True
                    break
            assert found, f"pixel {rgb} not within ±2 of any palette color"
