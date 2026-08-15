"""BLOQUE 58.6w: Scrolling galaxy background.

Loads a galaxy background image (single `Assets/background/galaxy_strip.png`
designed to be loopable, OR 3 stacked panels `galaxy_panel_{0,1,2}.png`)
and scrolls it downward at a constant slow speed.

The image is wrapped modulo its own height, so the strip cycles
indefinitely. The user-supplied `galaxy_strip.png` is the new design
(2026-08-14): a single 1920x1920 image with a vertical-loopable pattern
of galaxies that scrolls down (Arriba para abajo).

User spec (2026-08-14):
  - HARD CUTS at seams (no blending) \u2014 the strip is intentionally
    different from the previous panel set.
  - CONSTANT slow scroll (~30 px/s) for a "traveling through space" feel.
  - REPLACES the TilingImage gameplay background.
  - Active in: gameplay waves + sub-boss. NOT in boss fights or title.

Coordinate convention: 320x480 internal playfield. The galaxy strip is
scaled DOWN to 320 wide and scrolls vertically.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import pygame


# Module-level cache so we load each image only once per process
_strip_cache: dict[tuple[str, int], pygame.Surface] = {}


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


def _load_image(filename: str, target_width: int) -> Optional[pygame.Surface]:
    """Load a background image by filename and scale to target_width.

    Uses plain pygame.image.load (no .convert()) so this works even
    when no video mode has been set (e.g. headless tests, or
    pygame.display.init() not called yet).
    """
    cache_key = (filename, target_width)
    if cache_key in _strip_cache:
        return _strip_cache[cache_key]
    assets = _find_assets_dir()
    if assets is None:
        return None
    for ext in ("", ".png", ".jpg", ".jpeg"):
        path = assets / "background" / (filename + ext) if ext else assets / "background" / filename
        if path.is_file():
            try:
                surf = pygame.image.load(str(path))
            except pygame.error:
                return None
            src_w, src_h = surf.get_size()
            new_h = max(1, int(src_h * (target_width / float(src_w))))
            scaled = pygame.transform.scale(surf, (target_width, new_h))
            _strip_cache[cache_key] = scaled
            return scaled
    return None


class ScrollingGalaxyBackground:
    """Vertical-scrolling galaxy strip.

    Looks for `Assets/background/galaxy_strip.png` first (the new
    user-supplied loopable image). Falls back to 3 stacked panels
    (`galaxy_panel_{0,1,2}.png`) for backward compat with the
    BLOQUE 58.6w panel set. The strip scrolls DOWN at constant speed
    and wraps modulo its own height so it cycles indefinitely.

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
    ) -> None:
        self._w = width
        self._h = height
        self._scroll_speed: float = scroll_speed_px_per_s
        self._scroll_y: float = 0.0  # 0 to total_strip_height
        # Try the new single-strip image first; fall back to 3 panels.
        self._strip: Optional[pygame.Surface] = _load_image("galaxy_strip", width)
        self._mode: str = "single" if self._strip is not None else "panels"
        if self._strip is None:
            self._panels: list[pygame.Surface] = []
            for i in range(3):
                p = _load_image(f"galaxy_panel_{i}", width)
                if p is not None:
                    self._panels.append(p)
        else:
            self._panels = []
        # Total height of the strip (single or stacked)
        if self._strip is not None:
            self._total_strip_h = self._strip.get_height()
        else:
            self._total_strip_h = sum(p.get_height() for p in self._panels)

    @property
    def is_ready(self) -> bool:
        """True if the strip can be drawn (either single image or 2+ panels)."""
        if self._strip is not None:
            return self._total_strip_h > 0
        return len(self._panels) >= 2 and self._total_strip_h > 0

    @property
    def total_strip_height(self) -> int:
        return self._total_strip_h

    @property
    def mode(self) -> str:
        """Which mode the background loaded: 'single' or 'panels'."""
        return self._mode

    def update(self, dt: float) -> None:
        """Advance the scroll position by `dt` seconds.

        BLOQUE 58.11: scroll direction is now TOP-TO-BOTTOM (arriba
        para abajo). Before this fix the strip moved up; the user
        wanted objects to fall down the screen instead.
        """
        if not self.is_ready:
            return
        # Subtract so the strip's y-offset decreases over time, which
        # makes the visible content shift DOWNWARD on screen.
        self._scroll_y -= self._scroll_speed * dt
        if self._total_strip_h > 0:
            # Wrap into the [0, total_strip_h) range. After subtraction
            # scroll_y can be negative; use mod that handles that.
            self._scroll_y = self._scroll_y % self._total_strip_h

    def draw(self, target: pygame.Surface) -> None:
        """Blit the strip to the play area, offset by -scroll_y.

        The strip is a tall image that loops on itself. We draw it
        (and one extra copy below) so the screen is always fully
        covered regardless of scroll_y.

        BLOQUE 58.11: applies a runtime darkening vignette AFTER the
        strip is drawn. The vignette uses BLEND_RGBA_MULT with a soft
        radial gradient (lighter in the center, darker at edges).
        This deepens the contrast of the playfield WITHOUT affecting
        anything drawn after this call (enemies, particles, etc are
        drawn on top and remain at full brightness).
        """
        if not self.is_ready:
            return
        screen_h = target.get_height()
        y = -self._scroll_y
        if self._strip is not None:
            # Single-image mode: draw the strip twice (current + next)
            for _ in range(2):
                h = self._strip.get_height()
                if y + h >= 0 and y < screen_h:
                    target.blit(self._strip, (0, int(y)))
                y += h
        else:
            # Panels mode: draw all panels + 1 extra copy
            for _ in range(len(self._panels) + 1):
                for panel in self._panels:
                    h = panel.get_height()
                    if y + h >= 0 and y < screen_h:
                        target.blit(panel, (0, int(y)))
                    y += h
        # BLOQUE 58.11: apply runtime vignette. Multiply blend with a
        # soft radial gradient — center 100% (255), edges 60% (153).
        # This makes the corners and edges of the playfield look deeper
        # without affecting anything drawn after this.
        vignette = self._get_vignette(target.get_size())
        target.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def _get_vignette(self, size: tuple[int, int]) -> pygame.Surface:
        """BLOQUE 58.11: cached radial gradient (255 center, 153 edge)."""
        cache_key = ("vignette", size)
        if cache_key in _strip_cache:
            return _strip_cache[cache_key]
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w / 2.0, h / 2.0
        max_dist = (cx * cx + cy * cy) ** 0.5
        # For each pixel, compute distance and set color to 153..255
        for y in range(h):
            for x in range(w):
                dx, dy = x - cx, y - cy
                d = (dx * dx + dy * dy) ** 0.5 / max_dist
                # 0 at center, 1 at corners
                # Color goes from 255 (center) to 153 (edges, ~60%)
                v = int(255 - 102 * d)
                surf.set_at((x, y), (v, v, v, 255))
        _strip_cache[cache_key] = surf
        return surf
