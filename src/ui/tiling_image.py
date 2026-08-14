"""BLOQUE 58.45: Tiling background image.

Replaces (or layers behind) the parallax starfield with a static
artwork that scrolls forward and tiles seamlessly. The user's image
(3000x3000, in `Assets/imagen fondo del juego.jpg`) is loaded once,
scaled to fit the game width, and drawn as a vertical "tape" that
moves downward (the same direction the player progresses).

Key features:
  - Image is loaded from `Assets/`, found via the same path resolution
    as the music module (`_find_assets_dir`)
  - The image is scaled ONCE to the game width, preserving its square
    aspect ratio (so it becomes 320x320, 480x480, etc.)
  - A vertical "ribbon" of N tile-copies is drawn, with the whole
    ribbon moving down at a constant speed
  - When a tile moves off the bottom of the screen, the ribbon
    naturally wraps because we keep drawing the same image
  - Optional: a top fade gradient so the image blends into the play
    area frame

The `scroll_speed_px_per_s` controls how fast the ribbon moves. A
low value (~12 px/s) makes the background feel like a slow starfield;
higher values feel like flying through space.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import pygame


# Module-level cache so we load the image only once across multiple
# GameplayRuntime instances (defensive — the runtime is single-instance
# but the cache makes the API safer).
_image_cache: Optional[pygame.Surface] = None
_scaled_cache: Optional[tuple[int, pygame.Surface]] = None  # (width, surface)


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


def _find_background_image() -> Optional[Path]:
    assets = _find_assets_dir()
    if assets is None:
        return None
    # Try a few common names
    for name in (
        "imagen fondo del juego.jpg",
        "imagen fondo del juego.png",
        "background.jpg",
        "background.png",
    ):
        path = assets / name
        if path.is_file():
            return path
    return None


def _load_image(target_width: int) -> Optional[pygame.Surface]:
    """Load the background image and scale it to `target_width`.
    Caches the result so subsequent calls are free.
    """
    global _image_cache, _scaled_cache
    if _scaled_cache is not None and _scaled_cache[0] == target_width:
        return _scaled_cache[1]
    if _image_cache is None:
        path = _find_background_image()
        if path is None:
            return None
        try:
            _image_cache = pygame.image.load(str(path)).convert()
        except pygame.error:
            return None
    src = _image_cache
    src_w, src_h = src.get_size()
    scale = target_width / float(src_w)
    new_h = max(1, int(src_h * scale))
    scaled = pygame.transform.scale(src, (target_width, new_h))
    _scaled_cache = (target_width, scaled)
    return scaled


class TilingImage:
    """Vertical-scrolling tiled background image.

    The image is drawn as a vertical ribbon that moves downward. The
    ribbon contains 3 copies of the image stacked, so as the top copy
    moves off the bottom of the screen, the next copy is already
    visible. The visual effect is a seamless "tape" of repeated art.

    Use:
        bg = TilingImage(width=320, scroll_speed=12.0)
        bg.update(dt)  # advance the scroll
        bg.draw(target)  # blit to the game surface
    """

    def __init__(
        self,
        width: int = 320,
        height: int = 480,
        scroll_speed_px_per_s: float = 12.0,
        image: Optional[pygame.Surface] = None,
    ) -> None:
        self._w = width
        self._h = height
        self._scroll_y: float = 0.0
        self._scroll_speed: float = scroll_speed_px_per_s
        self._image: Optional[pygame.Surface] = image
        if self._image is None:
            self._image = _load_image(width)
        # If image loaded, image height; otherwise 0
        self._tile_h: int = self._image.get_height() if self._image else 0

    @property
    def is_ready(self) -> bool:
        """True if the image is loaded and can be drawn."""
        return self._image is not None

    @property
    def tile_height(self) -> int:
        return self._tile_h

    def update(self, dt: float) -> None:
        """Advance the scroll position by `dt` seconds."""
        if self._image is None:
            return
        self._scroll_y += self._scroll_speed * dt
        # Wrap when we've scrolled a full tile — the visible position
        # of the top tile cycles within [0, tile_h).
        if self._tile_h > 0:
            self._scroll_y = self._scroll_y % self._tile_h

    def draw(self, target: pygame.Surface) -> None:
        """Blit the tiled image as a vertical ribbon covering the
        play area. The ribbon is composed of multiple copies of the
        image stacked, all shifted by the current scroll position.
        """
        if self._image is None:
            return
        # We need at least 2 copies to cover the screen + the scroll
        # offset. Add one extra to be safe.
        copies = (self._h // self._tile_h) + 3
        y = -self._scroll_y
        for _ in range(copies):
            target.blit(self._image, (0, int(y)))
            y += self._tile_h
        # If there are remaining pixels at the bottom (tile_h doesn't
        # divide the screen evenly), the last copy fills the rest.
