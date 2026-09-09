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
