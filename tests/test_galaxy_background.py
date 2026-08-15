"""BLOQUE 58.6w: tests for the ScrollingGalaxyBackground class."""
from __future__ import annotations

import sys
from pathlib import Path

# pygame.display must be initialized for image.load().convert() to work
import pygame
pygame.init()
pygame.display.init()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_galaxy_background_loads_3_panels() -> None:
    """When Assets/background/galaxy_panel_{0,1,2}.png are present,
    ScrollingGalaxyBackground should load all 3.
    """
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    assert bg.is_ready, f"Expected background to be ready, got {bg.panel_count_loaded} panels"
    assert bg.panel_count_loaded == 3, (
        f"Expected 3 panels, got {bg.panel_count_loaded}"
    )


def test_galaxy_background_total_strip_height() -> None:
    """Total strip height = sum of all panel heights. Each panel was
    640x1920; scaled to 320 wide they become 320x960 (height scales
    proportionally). 3 panels stacked = 2880."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    # 640x1920 scaled to 320 wide = 320x960 each. 3 panels stacked = 2880.
    assert bg.total_strip_height == 2880, (
        f"Expected total strip height 2880, got {bg.total_strip_height}"
    )


def test_galaxy_background_update_advances_scroll() -> None:
    """After update(dt), scroll_y should advance by speed * dt."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(
        width=320, height=480, scroll_speed_px_per_s=30.0
    )
    assert bg._scroll_y == 0.0
    bg.update(1.0)
    assert bg._scroll_y == 30.0, f"After 1s @ 30px/s, scroll should be 30, got {bg._scroll_y}"
    bg.update(0.5)
    assert bg._scroll_y == 45.0


def test_galaxy_background_wraps_at_strip_height() -> None:
    """Scroll position wraps modulo total_strip_height so the strip
    cycles indefinitely."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(
        width=320, height=480, scroll_speed_px_per_s=30.0
    )
    # 5760 / 30 = 192 seconds to wrap once. After 200s we should be
    # at scroll_y = (200 - 192) * 30 = 240.
    bg.update(200.0)
    assert 0 <= bg._scroll_y < bg.total_strip_height, (
        f"scroll_y should be in [0, total_strip_height), got {bg._scroll_y}"
    )
    assert abs(bg._scroll_y - 240.0) < 0.01, (
        f"After 200s @ 30px/s with 5760 wrap, expected 240, got {bg._scroll_y}"
    )


def test_galaxy_background_handles_missing_panels() -> None:
    """If no panels are bundled, is_ready should be False (and the
    runtime will fall back to TilingImage or parallax)."""
    import os
    from unittest.mock import patch
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    # Force _load_panel to return None for all indices
    with patch("src.ui.scrolling_galaxy._load_panel", return_value=None):
        bg = ScrollingGalaxyBackground(width=320, height=480)
        assert not bg.is_ready
        assert bg.panel_count_loaded == 0
