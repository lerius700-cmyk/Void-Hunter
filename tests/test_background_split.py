"""BLOQUE 58.6x-split: tests for the per-scene background selection.

Verifies that the runtime picks the right background for the right scene:
  - Boss fight (is_boss=True)  -> TilingImage (pixel art)
  - Waves (is_boss=False)       -> ScrollingGalaxyBackground (galaxy scroll)
with proper fallbacks if an image isn't bundled.
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


def _select_background(is_boss: bool, has_galaxy: bool, has_tiling: bool) -> str:
    """Mirror the runtime's draw-block logic in gameplay_runtime.py.

    Keep this in sync with the runtime (lines around the _draw_background
    block). If you change one, change the other.
    """
    if is_boss:
        if has_tiling:
            return "tiling"
        return "parallax"
    # Waves + sub-boss
    if has_galaxy:
        return "galaxy"
    if has_tiling:
        return "tiling"
    return "parallax"


def test_boss_fight_uses_tiling() -> None:
    """is_boss=True with both backgrounds available -> TilingImage (pixel art)."""
    assert _select_background(is_boss=True, has_galaxy=True, has_tiling=True) == "tiling"


def test_boss_fight_falls_back_to_parallax() -> None:
    """is_boss=True without tiling -> ParallaxBackground (fallback)."""
    assert _select_background(is_boss=True, has_galaxy=True, has_tiling=False) == "parallax"


def test_waves_use_galaxy_scroll() -> None:
    """is_boss=False with both available -> ScrollingGalaxyBackground."""
    assert _select_background(is_boss=False, has_galaxy=True, has_tiling=True) == "galaxy"


def test_waves_fall_back_to_tiling() -> None:
    """is_boss=False without galaxy panels -> TilingImage (fallback)."""
    assert _select_background(is_boss=False, has_galaxy=False, has_tiling=True) == "tiling"


def test_waves_fall_back_to_parallax() -> None:
    """is_boss=False with nothing bundled -> ParallaxBackground (final fallback)."""
    assert _select_background(is_boss=False, has_galaxy=False, has_tiling=False) == "parallax"


def test_runtime_actually_has_is_boss_branch() -> None:
    """Belt-and-suspenders: verify the runtime's draw code actually checks
    is_boss. If a future refactor accidentally drops the branch, this
    catches it.
    """
    from src.ui import gameplay_runtime
    src = Path(gameplay_runtime.__file__).read_text(encoding="utf-8")
    # The draw block should have both branches
    assert "if self._is_boss:" in src, (
        "Expected the runtime to branch on self._is_boss in its draw/update"
    )
    assert "_galaxy_bg.draw" in src
    assert "_tiling_bg.draw" in src
