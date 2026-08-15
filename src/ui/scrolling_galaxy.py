"""BLOQUE 58.6w: Scrolling galaxy background.

Loads 3 distinct galaxy panels (`Assets/background/galaxy_panel_{0,1,2}.png`),
stacks them into a single tall strip, and scrolls it downward at a constant
slow speed. The 3 panels have DIFFERENT content (different galaxy
arrangements), so the strip shows unique content from top to bottom and
wraps after the 3rd panel returns to the 1st.

User spec (2026-08-14):
  - HARD CUTS at seams (no blending) \u2014 the panels are intentionally
    different and the visible transitions are part of the look.
  - CONSTANT slow scroll (~30 px/s) for a "traveling through space" feel.
  - REPLACES the TilingImage gameplay background.
  - Active in: gameplay waves + sub-boss. NOT in boss fights or title.

Coordinate convention: 320x480 internal playfield. The panels are
640x1920 each; we scale them DOWN to 320 wide for the playfield and
stack them as 320x(480*3)=320x1440 vertical strip.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import pygame


# Module-level cache: load each panel ONCE per process
_panel_cache: dict[int, pygame.Surface] = {}


def _find_assets_dir() -> Optional[Path]:
    """Find the Assets/ directory. Same logic as src/audio/music.py."""
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "Assets")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).resolve().parent.parent.parent
    candidates.append(exe_dir / "Assets")
    candidates.append(exe_dir.parent / "Assets")
    for c in candidates:
        if c.is_dir():
            return c
    return None


def _load_panel(index: int, target_width: int) -> Optional[pygame.Surface]:
    """Load galaxy_panel_{index}.png and scale to target_width.

    We use plain pygame.image.load (no .convert()) so this works
    even when no video mode has been set (e.g. headless tests, or
    pygame.display.init() not called yet). The .convert() call would
    require a video surface and fail in those cases.
    """
    cache_key = (index, target_width)
    if cache_key in _panel_cache:
        return _panel_cache[cache_key]
    assets = _find_assets_dir()
    if assets is None:
        return None
    # Try png first, then jpg (defensive)
    for ext in (".png", ".jpg", ".jpeg"):
        path = assets / "background" / f"galaxy_panel_{index}{ext}"
        if path.is_file():
            try:
                surf = pygame.image.load(str(path))
            except pygame.error:
                return None
            # Scale to target_width preserving aspect
            src_w, src_h = surf.get_size()
            new_h = max(1, int(src_h * (target_width / float(src_w))))
            scaled = pygame.transform.scale(surf, (target_width, new_h))
            _panel_cache[cache_key] = scaled
            return scaled
    return None


class ScrollingGalaxyBackground:
    """Vertical-scrolling galaxy strip made of 3 stacked panels.

    The strip is 3 * panel_height tall. It scrolls DOWN at constant
    speed. When the bottom of the strip is reached, the top of the
    strip is back at the top of the screen \u2014 effectively the 3
    panels cycle in order (panel 0, 1, 2, 0, 1, 2, ...).

    Use:
        bg = ScrollingGalaxyBackground(width=320, height=480,
                                       scroll_speed_px_per_s=30.0)
        bg.update(dt)  # advance the scroll
        bg.draw(target)  # blit to the game surface
    """

    def __init__(
        self,
        width: int = 320,
        height: int = 480,
        scroll_speed_px_per_s: float = 30.0,
        panel_count: int = 3,
    ) -> None:
        self._w = width
        self._h = height
        self._scroll_speed: float = scroll_speed_px_per_s
        self._panel_count: int = panel_count
        self._scroll_y: float = 0.0  # 0 to total_strip_height
        # Load each panel and remember its scaled size
        self._panels: list[pygame.Surface] = []
        for i in range(panel_count):
            p = _load_panel(i, width)
            if p is not None:
                self._panels.append(p)
        # Total height of the stacked strip
        self._total_strip_h: int = sum(p.get_height() for p in self._panels)

    @property
    def is_ready(self) -> bool:
        """True if at least 2 panels are loaded and the strip can be drawn."""
        return len(self._panels) >= 2 and self._total_strip_h > 0

    @property
    def total_strip_height(self) -> int:
        return self._total_strip_h

    @property
    def panel_count_loaded(self) -> int:
        return len(self._panels)

    def update(self, dt: float) -> None:
        """Advance the scroll position by `dt` seconds."""
        if not self.is_ready:
            return
        self._scroll_y += self._scroll_speed * dt
        # Wrap at the total strip height \u2014 this is what makes the
        # 3 panels cycle indefinitely.
        if self._total_strip_h > 0:
            self._scroll_y = self._scroll_y % self._total_strip_h

    def draw(self, target: pygame.Surface) -> None:
        """Blit the 3 panels as a vertical strip covering the play area.

        The strip is offset by -scroll_y. We draw 4 copies of the strip
        to ensure the screen is always fully covered (the offset can
        put the visible window anywhere within the strip cycle).
        """
        if not self.is_ready:
            return
        screen_h = target.get_height()
        # We need to cover the screen + an extra strip's worth in case
        # the scroll offset puts us near the bottom of the visible strip.
        # Start drawing from -scroll_y (the top of the visible window
        # maps to scroll_y within the strip).
        y = -self._scroll_y
        # Draw the strip + 1 extra copy to cover the screen
        for _ in range(self._panel_count + 1):
            for panel in self._panels:
                ph = panel.get_height()
                # Only blit if the panel is on screen (or near it)
                if y + ph >= 0 and y < screen_h:
                    target.blit(panel, (0, int(y)))
                y += ph
