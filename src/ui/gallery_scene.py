"""Gallery scenes — in-game access to ship sprite sheets and cinematic videos.

BLOQUE 58.60: from the title screen, press S to open the sprite sheet gallery
or V to open the video gallery. Arrow keys cycle through ships/videos, ESC
returns to the title.

Two scenes, two states:
  - GallerySpriteScene (GameState.GALLERY_SPRITE) — shows ship_NN_spritesheet.png
  - GalleryVideoScene  (GameState.GALLERY_VIDEO)  — plays title or zoom video
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

import pygame

from src.core.scene_manager import GameState, Scene
from src.core.settings import INTERNAL_H, INTERNAL_W
from src.ui.scenes import _build_video_player


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _find_assets_root() -> Optional[Path]:
    """Locate the Assets/ root directory (handles dev + PyInstaller)."""
    import sys
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "Assets")
        candidates.append(Path(meipass) / "_internal" / "Assets")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).resolve().parents[2]
    candidates.append(exe_dir / "Assets")
    candidates.append(exe_dir / "_internal" / "Assets")
    candidates.append(exe_dir.parent / "Assets")
    for c in candidates:
        if c.is_dir():
            return c
    return None


def _load_ship_spritesheet(ship_id: int) -> Optional[pygame.Surface]:
    """Load and pre-scale a ship_NN_spritesheet.png to fit the 240x360 surface."""
    base = _find_assets_root()
    if base is None:
        return None
    path = base / "sprites" / "player_ships" / f"ship_0{ship_id}_spritesheet.png"
    if not path.is_file():
        return None
    img = pygame.image.load(str(path)).convert_alpha()
    # Scale to fit inside (INTERNAL_W-20, INTERNAL_H-60) maintaining aspect
    max_w = INTERNAL_W - 20
    max_h = INTERNAL_H - 60
    w, h = img.get_size()
    scale = min(max_w / w, max_h / h, 1.0)  # never upscale beyond native
    new_w = int(w * scale)
    new_h = int(h * scale)
    if (new_w, new_h) != (w, h):
        img = pygame.transform.smoothscale(img, (new_w, new_h))
    return img


# ------------------------------------------------------------------
# Gallery sprite scene
# ------------------------------------------------------------------

class GallerySpriteScene(Scene):
    """GALLERY_SPRITE — browse the 5 ship sprite sheets.

    Controls:
      LEFT/RIGHT or 1..5   switch ship
      TAB or V             jump to video gallery
      ESC                  return to title
    """

    SHIP_COUNT: int = 5
    SHIP_NAMES: tuple[str, ...] = (
        "ARWING",       # ship_01: Star Fox 64 style
        "DIAMOND",      # ship_02: red diamond
        "PHANTOM",      # ship_03: green camo delta
        "UFO",          # ship_04: yellow saucer
        "VOID",         # ship_05: purple neon teardrop
    )

    def __init__(self, transition_to) -> None:
        self._transition_to = transition_to
        self._current: int = 0  # 0..4 -> ship_01..ship_05
        self._t: float = 0.0
        self._cached: dict[int, Optional[pygame.Surface]] = {}

    def on_enter(self) -> None:
        self._t = 0.0

    def _get_sheet(self, ship_id: int) -> Optional[pygame.Surface]:
        if ship_id not in self._cached:
            self._cached[ship_id] = _load_ship_spritesheet(ship_id + 1)
        return self._cached[ship_id]

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.TITLE)
                return
            if event.key in (pygame.K_TAB, pygame.K_v):
                self._transition_to(GameState.GALLERY_VIDEO)
                return
            if event.key == pygame.K_RIGHT:
                self._current = (self._current + 1) % self.SHIP_COUNT
            elif event.key == pygame.K_LEFT:
                self._current = (self._current - 1) % self.SHIP_COUNT
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self._current = 0
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self._current = 1
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self._current = 2
            elif event.key in (pygame.K_4, pygame.K_KP4):
                self._current = 3
            elif event.key in (pygame.K_5, pygame.K_KP5):
                self._current = 4

    def draw(self, target: pygame.Surface) -> None:
        # Background — dark indigo
        target.fill((14, 10, 28))
        # Top header
        font_h = pygame.font.Font(None, 18)
        title = font_h.render("SHIP GALLERY", True, (180, 220, 255))
        _center_blit(target, title, 12)
        # Current ship name
        ship_id = self._current + 1
        name = self.SHIP_NAMES[self._current]
        name_text = font_h.render(f"SHIP 0{ship_id}  -  {name}", True, (255, 240, 140))
        _center_blit(target, name_text, 36)
        # Draw the sprite sheet centered
        sheet = self._get_sheet(self._current)
        if sheet is not None:
            x = (INTERNAL_W - sheet.get_width()) // 2
            y = 56
            target.blit(sheet, (x, y))
        else:
            font_e = pygame.font.Font(None, 12)
            err = font_e.render("(spritesheet not found)", True, (255, 100, 100))
            _center_blit(target, err, INTERNAL_H // 2)
        # Bottom help bar
        font_f = pygame.font.Font(None, 12)
        help_lines = [
            "<-  ->  or  1-5  switch ship",
            "TAB  or  V   video gallery",
            "ESC  back to title",
        ]
        for i, line in enumerate(help_lines):
            surf = font_f.render(line, True, (140, 160, 200))
            _center_blit(target, surf, INTERNAL_H - 36 + i * 11)
        # Ship counter
        counter = font_f.render(f"  {self._current + 1} / {self.SHIP_COUNT}  ", True, (200, 220, 255))
        target.blit(counter, (4, 4))


# ------------------------------------------------------------------
# Gallery video scene
# ------------------------------------------------------------------

class GalleryVideoScene(Scene):
    """GALLERY_VIDEO — play the 2 cinematic videos (V1 title + V2 zoom).

    Controls:
      TAB or S             jump to sprite gallery
      LEFT/RIGHT or 1..2   switch video
      ESC                  return to title
    """

    VIDEO_SUB_DIRS: tuple[str, ...] = ("title", "zoom")
    VIDEO_LABELS: tuple[str, ...] = (
        "TITLE  -  VOID HUNTER logo reveal + ambient + demo",
        "ZOOM   -  Ship close-up dolly-back to gameplay",
    )

    def __init__(self, transition_to) -> None:
        self._transition_to = transition_to
        self._current: int = 0  # 0..1 -> title, zoom
        self._t: float = 0.0
        self._video = _build_video_player("title", loop=True)
        self._cached_player: dict[int, object] = {0: self._video}

    def on_enter(self) -> None:
        self._t = 0.0
        self._ensure_player(self._current)

    def _ensure_player(self, idx: int) -> None:
        if idx in self._cached_player and self._cached_player[idx] is not None:
            self._video = self._cached_player[idx]
            self._video.play()
            return
        sub = self.VIDEO_SUB_DIRS[idx]
        player = _build_video_player(sub, loop=True)
        if player is not None:
            player.play()
        self._cached_player[idx] = player
        self._video = player

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.TITLE)
                return
            if event.key in (pygame.K_TAB, pygame.K_s):
                self._transition_to(GameState.GALLERY_SPRITE)
                return
            new_idx = self._current
            if event.key == pygame.K_RIGHT:
                new_idx = (self._current + 1) % len(self.VIDEO_SUB_DIRS)
            elif event.key == pygame.K_LEFT:
                new_idx = (self._current - 1) % len(self.VIDEO_SUB_DIRS)
            elif event.key in (pygame.K_1, pygame.K_KP1):
                new_idx = 0
            elif event.key in (pygame.K_2, pygame.K_KP2):
                new_idx = 1
            if new_idx != self._current:
                self._current = new_idx
                self._ensure_player(new_idx)
                return

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        if self._video is not None:
            self._video.draw(target)
        else:
            font_e = pygame.font.Font(None, 14)
            err = font_e.render(f"(video '{self.VIDEO_SUB_DIRS[self._current]}' not found)", True, (255, 100, 100))
            _center_blit(target, err, INTERNAL_H // 2)
        # Header / footer overlay
        font_h = pygame.font.Font(None, 18)
        title = font_h.render("VIDEO GALLERY", True, (180, 220, 255))
        _center_blit(target, title, 8)
        label = font_h.render(self.VIDEO_LABELS[self._current], True, (255, 240, 140))
        _center_blit(target, label, 28)
        # Help bar
        font_f = pygame.font.Font(None, 12)
        for i, line in enumerate([
            "<-  ->  or  1-2  switch video",
            "TAB  or  S   sprite gallery",
            "ESC  back to title",
        ]):
            surf = font_f.render(line, True, (140, 160, 200))
            _center_blit(target, surf, INTERNAL_H - 32 + i * 10)
        # Video counter
        counter = font_f.render(f"  {self._current + 1} / {len(self.VIDEO_SUB_DIRS)}  ", True, (200, 220, 255))
        target.blit(counter, (4, 4))


# ------------------------------------------------------------------
# Misc helper
# ------------------------------------------------------------------

def _center_blit(target: pygame.Surface, src: pygame.Surface, y: int) -> None:
    x = (target.get_width() - src.get_width()) // 2
    target.blit(src, (x, y))
