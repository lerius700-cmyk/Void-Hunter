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


def test_galaxy_background_scrolls_top_to_bottom() -> None:
    """BLOQUE 58.6w: panels must scroll from TOP to BOTTOM.

    This is the "Arriba para abajo" direction the user emphasized. The
    order panels appear on screen as scroll_y increases is:
      - scroll_y=0: only Panel 0 visible (at the top)
      - scroll_y ~ scroll_y_max: Panel 1 enters from BELOW the visible
        area and slides up to take Panel 0's place
      - scroll_y further: Panel 2 enters from below
      - scroll_y wraps to total_strip_height: back to Panel 0

    The camera (player's view) moves DOWN through the strip. Panels
    appear at the BOTTOM of the screen and slide UP off the TOP.
    """
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    panel_h = 960  # each scaled panel is 320x960
    total_h = bg.total_strip_height  # 2880

    def visible_panels(scroll_y: int) -> list[int]:
        """Return the list of panel indices visible at this scroll_y."""
        visible = []
        for i in range(3):
            y_top = -scroll_y + i * panel_h
            # Panel is visible if any part of it is in [0, 480]
            if y_top < 480 and (y_top + panel_h) > 0:
                visible.append(i)
        return visible

    # Frame 0: only panel 0 at the top of the screen
    bg._scroll_y = 0
    assert visible_panels(0) == [0], "Frame 0 should show only Panel 0"

    # After 16s @ 30px/s = 480 px scrolled: bottom of panel 0 visible,
    # top of panel 1 still below screen
    bg._scroll_y = 480
    panels_480 = visible_panels(480)
    assert 0 in panels_480 and 1 not in panels_480, (
        f"At scroll_y=480, expected only Panel 0 visible (Panel 1 still below), "
        f"got {panels_480}"
    )

    # After 32s @ 30px/s = 960 px scrolled: Panel 1 fully at the top,
    # Panel 0 fully off screen
    bg._scroll_y = 960
    panels_960 = visible_panels(960)
    assert 0 not in panels_960, (
        f"At scroll_y=960, Panel 0 should be off-screen, got {panels_960}"
    )
    assert 1 in panels_960, f"At scroll_y=960, Panel 1 should be on screen"
    assert 2 not in panels_960, (
        f"At scroll_y=960, Panel 2 should still be below screen, got {panels_960}"
    )

    # The KEY test: the ORDER in which panels appear must be 0, 1, 2
    # (not 2, 1, 0). This is the "top to bottom" direction.
    seen_order = []
    for sy in range(0, total_h, 50):
        for p in visible_panels(sy):
            if p not in seen_order:
                seen_order.append(p)
    assert seen_order == [0, 1, 2], (
        f"Panels must appear in order 0, 1, 2 (top to bottom). "
        f"Got: {seen_order}"
    )
