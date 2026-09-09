"""Tests for ParallaxBackground.use_tile_sequence mode."""
from pathlib import Path

import pygame

pygame.init()


def test_parallax_bg_with_use_tile_sequence_true():
    from src.systems.parallax import ParallaxBackground
    bg = ParallaxBackground(
        width=320, height=480,
        use_tile_sequence=True,
        tiles_dir=Path(r"D:\AI\void-hunter\Assets\background\tiles\act1"),
    )
    assert bg._tile_manager is not None


def test_parallax_bg_default_use_tile_sequence_false():
    from src.systems.parallax import ParallaxBackground
    bg = ParallaxBackground(width=320, height=480)
    assert bg._tile_manager is None


def test_parallax_bg_tile_mode_draw_runs():
    from src.systems.parallax import ParallaxBackground
    bg = ParallaxBackground(
        width=320, height=480,
        use_tile_sequence=True,
        tiles_dir=Path(r"D:\AI\void-hunter\Assets\background\tiles\act1"),
    )
    target = pygame.Surface((320, 480))
    bg._strip_y_offset = 0.0
    bg.draw(target)  # must not raise
    bg._strip_y_offset = 1440.0
    bg.draw(target)
    bg._strip_y_offset = 2879.0
    bg.draw(target)
