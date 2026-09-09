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
