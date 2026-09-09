"""Tests for src.systems.tile_manager.TileManager."""
from pathlib import Path

import pytest


def test_tile_manager_loads_six_tiles():
    from src.systems.tile_manager import TileManager
    tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
    tm = TileManager(tiles_dir)
    assert tm.get_height() == 2880


def test_tile_manager_raises_on_missing_dir():
    from src.systems.tile_manager import TileManager
    with pytest.raises(FileNotFoundError):
        TileManager(Path(r"D:\AI\void-hunter\does\not\exist"))


def test_tile_manager_draw_runs_without_error(monkeypatch):
    """Draw must work with a mock pygame surface."""
    from src.systems.tile_manager import TileManager
    import pygame
    pygame.init()
    target = pygame.Surface((320, 480))
    tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
    tm = TileManager(tiles_dir)
    tm.draw(target, scroll_y=0.0)  # must not raise
    tm.draw(target, scroll_y=480.0)  # boundary
    tm.draw(target, scroll_y=2880.0)  # wrap boundary


def test_tile_manager_all_six_tiles_loaded():
    from src.systems.tile_manager import TileManager
    tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
    tm = TileManager(tiles_dir)
    assert len(tm._tile_surfaces) == 6


def test_each_tile_is_320x480():
    from src.systems.tile_manager import TileManager
    tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
    tm = TileManager(tiles_dir)
    for i, surf in enumerate(tm._tile_surfaces):
        assert surf.get_size() == (320, 480), f"Tile {i + 1} is {surf.get_size()}, expected (320, 480)"


def test_get_height_returns_2880():
    from src.systems.tile_manager import TileManager
    tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
    tm = TileManager(tiles_dir)
    assert tm.get_height() == 6 * 480  # 2880


def test_scroll_y_wraps_modulo_2880():
    """scroll_y > 2880 should wrap to (scroll_y % 2880)."""
    from src.systems.tile_manager import TileManager
    import pygame
    pygame.init()
    target = pygame.Surface((320, 480))
    tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
    tm = TileManager(tiles_dir)
    # No assertion needed — must not raise for any scroll_y
    for sy in [0.0, 479.0, 480.0, 481.0, 1440.0, 2879.0, 2880.0, 5760.0, -1.0]:
        tm.draw(target, scroll_y=sy)


def test_tile_manager_tiles_horizontally_for_wide_target():
    """If the target is wider than TILE_W, the tile tiles to fill the width."""
    from src.systems.tile_manager import TileManager
    import pygame
    pygame.init()
    tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
    tm = TileManager(tiles_dir)
    # Target 960x480 (3x the tile width)
    target = pygame.Surface((960, 480))
    tm.draw(target, scroll_y=0.0)
    # Pixel at x=0, 320, 640 should all be tile color (the three tile copies)
    assert target.get_at((0, 100))[0:3] == target.get_at((320, 100))[0:3]
    assert target.get_at((320, 100))[0:3] == target.get_at((640, 100))[0:3]


def test_tile_manager_rotates_tiles_180():
    """Per user request, each tile is visually rotated 180° at load time."""
    from src.systems.tile_manager import TileManager
    from PIL import Image
    import pygame
    pygame.init()
    tiles_dir = Path(r"D:\AI\void-hunter\Assets\background\tiles\act1")
    tm = TileManager(tiles_dir)
    # Compare a pixel at (x, y) of the loaded surface vs the source PNG.
    # If rotated 180, pixel(x, y) in surface should equal pixel(W-x, H-y) in source.
    raw = Image.open(tiles_dir / "tile_01_atmosphere_exit.png")
    raw_w, raw_h = raw.size
    # Sample a few pixels: the rotated surface at (0, 0) should match raw at (W-1, H-1).
    src_pixel_tl = raw.getpixel((0, 0))
    src_pixel_br = raw.getpixel((raw_w - 1, raw_h - 1))
    loaded_pixel_tl = tm._tile_surfaces[0].get_at((0, 0))[:3]
    loaded_pixel_br = tm._tile_surfaces[0].get_at((raw_w - 1, raw_h - 1))[:3]
    # The surface's top-left should match the source's bottom-right.
    assert src_pixel_br == loaded_pixel_tl, f"Expected {src_pixel_br}, got {loaded_pixel_tl}"
    # And the surface's bottom-right should match the source's top-left.
    assert src_pixel_tl == loaded_pixel_br, f"Expected {src_pixel_tl}, got {loaded_pixel_br}"
