"""Theme manager — 6 themes with 30-frame fade transition (BLOQUE 12)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from typing import Any
from src.utils.palette import THEME_NAMES, get_theme


THEME_FADE_FRAMES = 30  # 0.25s @ 120 FPS per GDD §8


@dataclass
class ThemeManager:
    """Manages the current theme + 30-frame crossfade transition."""
    current_name: str = "blue_void"
    target_name: str = "blue_void"
    fade_t: float = 1.0  # 1.0 = no fade in progress; 0.0 = just started
    fading: bool = False

    def set_theme(self, name: str) -> None:
        """Start a 30-frame fade to the new theme."""
        if name not in THEME_NAMES:
            return
        if name == self.current_name and not self.fading:
            return
        self.target_name = name
        self.fade_t = 0.0
        self.fading = True

    def update(self) -> None:
        """Advance fade by 1 frame (called at 120 FPS)."""
        if not self.fading:
            return
        self.fade_t += 1.0
        if self.fade_t >= THEME_FADE_FRAMES:
            self.fading = False
            self.fade_t = 1.0
            self.current_name = self.target_name

    @property
    def progress(self) -> float:
        """0.0 to 1.0 progress of current fade."""
        if not self.fading:
            return 1.0
        return min(1.0, self.fade_t / THEME_FADE_FRAMES)

    def get_current(self) -> dict[str, Any]:
        return get_theme(self.current_name)

    def get_target(self) -> dict[str, Any]:
        return get_theme(self.target_name)

    def render_fade_overlay(self, target: pygame.Surface) -> None:
        """Render a black overlay at 0 alpha if not fading, or gradient if
        fading (used for crossfade between themes — caller composites).
        """
        if not self.fading:
            return
        # During fade, target is the new theme. Caller renders BOTH themes
        # and alpha-blends using `progress`.
        pass

    def reset(self) -> None:
        self.current_name = "blue_void"
        self.target_name = "blue_void"
        self.fade_t = 1.0
        self.fading = False
