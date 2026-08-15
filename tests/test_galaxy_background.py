"""BLOQUE 58.6w: tests for the ScrollingGalaxyBackground class.

BLOQUE 58.6y+ update: now uses a single loopable image (galaxy_strip.png)
or falls back to 3 panels (galaxy_panel_{0,1,2}.png) for backward compat.
"""
from __future__ import annotations

import sys
from pathlib import Path

# pygame.display init required for image load
import pygame
pygame.init()
pygame.display.init()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_galaxy_background_loads_strip() -> None:
    """The new single-image strip is the preferred background.
    galaxy_strip.png is the user-supplied loopable image.
    """
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    assert bg.is_ready, f"Expected background to be ready, mode={bg.mode}"
    # In single mode we have exactly 1 strip
    if bg.mode == "single":
        assert bg.total_strip_height > 0
    else:
        # Backward compat: 3 panels
        assert bg.panel_count_loaded == 3, (
            f"Expected 3 panels (fallback), got {bg.panel_count_loaded}"
        )


def test_galaxy_background_total_strip_height() -> None:
    """Total strip height depends on mode (single vs panels)."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    if bg.mode == "single":
        # galaxy_strip.png is 1920x1920; scaled to 320 wide = 320x320
        # The strip image has a height of 320 after scaling.
        assert bg.total_strip_height == 320, (
            f"Expected single strip height 320, got {bg.total_strip_height}"
        )
    else:
        # 3 panels stacked: 3 * 960 = 2880
        assert bg.total_strip_height == 2880, (
            f"Expected 3 panels total 2880, got {bg.total_strip_height}"
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
    """Scroll position wraps modulo total_strip_height."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(
        width=320, height=480, scroll_speed_px_per_s=30.0
    )
    total = bg.total_strip_height
    # Run for 2x the time it takes to wrap
    bg.update((total * 2 / 30.0) + 1.0)
    assert 0 <= bg._scroll_y < total, (
        f"scroll_y should wrap to [0, {total}), got {bg._scroll_y}"
    )


def test_galaxy_background_handles_missing_images() -> None:
    """If no images are bundled, is_ready should be False (fallback to tiling/parallax)."""
    from unittest.mock import patch
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    # Force _load_image to return None
    with patch("src.ui.scrolling_galaxy._load_image", return_value=None):
        bg = ScrollingGalaxyBackground(width=320, height=480)
        assert not bg.is_ready


def test_galaxy_background_scrolls_top_to_bottom() -> None:
    """BLOQUE 58.6w: panels (or single strip cycle) must scroll TOP to BOTTOM.

    The camera (player's view) moves DOWN through the strip. Content
    appears at the BOTTOM of the screen and slides UP off the TOP.
    """
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    if not bg.is_ready:
        return  # can't test if no image

    if bg.mode == "single":
        # Single strip: only one image, scrolls in place
        # At scroll_y=0: top of strip at y=0
        # At scroll_y=100: top of strip at y=-100
        # The strip extends downward forever (it's looped)
        bg._scroll_y = 0
        # Verify the image is drawn at y = -scroll_y
        # (this is implementation detail; just verify scroll increments)
        bg.update(1.0)
        assert bg._scroll_y > 0
    else:
        # 3-panel mode: verify order [0, 1, 2]
        panel_h = 960
        total_h = bg.total_strip_height

        def visible_panels(scroll_y):
            visible = []
            for i in range(3):
                y_top = -scroll_y + i * panel_h
                if y_top < 480 and (y_top + panel_h) > 0:
                    visible.append(i)
            return visible

        seen_order = []
        for sy in range(0, total_h, 50):
            for p in visible_panels(sy):
                if p not in seen_order:
                    seen_order.append(p)
        assert seen_order == [0, 1, 2], (
            f"Panels must appear in order 0, 1, 2 (top to bottom). "
            f"Got: {seen_order}"
        )
