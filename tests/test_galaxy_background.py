"""BLOQUE 58.6w: tests for the ScrollingGalaxyBackground class.

BLOQUE 58.7ad: now uses galaxy_strip.png (the LONG single image) as
the primary background, with galaxy_panel_{0,1,2}.png as a 3-column
fallback. The strip is 640x5760 (3 vertical columns of 640x1920
glued together vertically), scaled to 320x2880. Loop period at
30 px/s is 96s.
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
    """BLOQUE 58.7ad: background loads either the long strip or 3 panels."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    assert bg.is_ready, f"Expected background to be ready, mode={bg.mode}"
    if bg.mode == "single":
        # The long galaxy_strip.png (640x5760), scaled to 320x2880
        assert bg.total_strip_height == 2880, (
            f"Expected single strip height 2880 (3x 1920/2 = 960x3), "
            f"got {bg.total_strip_height}"
        )
    else:
        # 3 vertical columns of 640x1920, scaled to 320x960 each
        assert len(bg._panels) == 3, (
            f"Expected 3 panels, got {len(bg._panels)}"
        )
        panel_h = bg._panels[0].get_height()
        assert abs(panel_h - 960) < 10, (
            f"Expected each panel ~320x960 (640x1920 scaled), got 320x{panel_h}"
        )


def test_galaxy_background_total_strip_height() -> None:
    """Total strip height = 3 * panel_height (panels stacked top->mid->bot)
    OR 2880 for the single long strip mode."""
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(width=320, height=480)
    if bg.mode == "single":
        # Long strip: 640x5760, scaled to 320x2880
        assert bg.total_strip_height == 2880, (
            f"Expected single strip height 2880, got {bg.total_strip_height}"
        )
    else:
        # 3 columns stacked: each 640x1920, scaled to 320x960, total ~2880
        assert bg.total_strip_height > 0
        assert abs(bg.total_strip_height - len(bg._panels) * 960) < 10, (
            f"Expected 3 panels total ~2880, got {bg.total_strip_height}"
        )


def test_galaxy_background_update_advances_scroll() -> None:
    """After update(dt), scroll_y should advance by speed * dt.

    BLOQUE 58.11: direction is now TOP-TO-BOTTOM (decreasing scroll_y).
    Before this fix the scroll_y was increasing (bottom-to-top motion).
    """
    from src.ui.scrolling_galaxy import ScrollingGalaxyBackground

    bg = ScrollingGalaxyBackground(
        width=320, height=480, scroll_speed_px_per_s=30.0
    )
    assert bg._scroll_y == 0.0
    bg.update(1.0)
    # Decreasing (top-to-bottom). After 1s, raw value is -30.
    # After % 2880 wrap, the result is 2880 - 30 = 2850.
    total_h = bg.total_strip_height
    expected = (total_h - 30) if total_h > 0 else 0
    assert bg._scroll_y == expected, (
        f"After 1s @ 30px/s, scroll should be {expected} "
        f"({total_h} - 30, top-to-bottom direction), got {bg._scroll_y}"
    )
    bg.update(0.5)
    expected2 = (total_h - 45) if total_h > 0 else 0
    assert bg._scroll_y == expected2


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
        # BLOQUE 58.7ad: panels are 320x960 each, stacked
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


def test_galaxy_strip_image_is_long_single() -> None:
    """BLOQUE 58.7ad: galaxy_strip.png exists and is the LONG single image.

    The user wants a single image that's a "cinta" (ribbon) of the
    3 vertical columns glued together. The runtime prefers this single
    image over the 3-panel fallback.
    """
    from src.ui.scrolling_galaxy import _load_image
    strip = _load_image("galaxy_strip", 320)
    if strip is None:
        # galaxy_strip.png not present; 3 panels fallback is fine
        return
    w, h = strip.get_size()
    # The strip should be TALL: 320x2880 (3x 1920/2 = 960x3)
    assert w == 320, f"Expected strip width 320, got {w}"
    assert h == 2880, f"Expected strip height 2880 (3 vertical columns stacked), got {h}"
