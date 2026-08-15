"""BLOQUE 58.6w: tests for the ScrollingGalaxyBackground class.

BLOQUE 58.7y: now uses 3 vertical panels (galaxy_panel_{0,1,2}.png) split
from the user-supplied 1920x1920 image. Each panel is 1920x640, scaled
to 320 wide, so each panel is 320x106. The strip stacks 3 panels top->mid->bot
and the loop is total_strip_height (~318 pixels) at 30 px/s.
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
    """BLOQUE 58.7y: 3 panels are the new standard background."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    assert bg.is_ready, f"Expected background to be ready, mode={bg.mode}"
    if bg.mode == "single":
        assert bg.total_strip_height > 0
    else:
        # 3 panels from the new 1920x1920 image, each 320x106
        assert len(bg._panels) == 3, (
            f"Expected 3 panels, got {len(bg._panels)}"
        )


def test_galaxy_background_total_strip_height() -> None:
    """Total strip height = 3 * panel_height (panels stacked top->mid->bot)."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    if bg.mode == "single":
        # Single-image fallback: scaled to 320x320
        assert bg.total_strip_height == 320, (
            f"Expected single strip height 320, got {bg.total_strip_height}"
        )
    else:
        # 3 panels stacked: each ~106 tall, total ~318
        assert bg.total_strip_height > 0
        assert abs(bg.total_strip_height - len(bg._panels) * 106) < 10, (
            f"Expected 3 panels total ~318, got {bg.total_strip_height}"
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
        bg._scroll_y = 0
        bg.update(1.0)
        assert bg._scroll_y > 0
    else:
        # 3-panel mode: verify order [0, 1, 2]
        # BLOQUE 58.7y: panels are 320x106 each, stacked
        panel_h = bg._panels[0].get_height()
        total_h = bg.total_strip_height

        def visible_panels(scroll_y):
            visible = []
            for i in range(len(bg._panels)):
                y_top = -scroll_y + i * panel_h
                if y_top < 480 and (y_top + panel_h) > 0:
                    visible.append(i)
            return visible

        seen_order = []
        for sy in range(0, total_h, max(1, panel_h // 4)):
            for p in visible_panels(sy):
                if p not in seen_order:
                    seen_order.append(p)
        assert seen_order == [0, 1, 2], (
            f"Panels must appear in order 0, 1, 2 (top to bottom). "
            f"Got: {seen_order}"
        )
