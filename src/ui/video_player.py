"""VideoPlayer — plays a sprite-sheet / PNG-sequence video on a pygame Surface.

BLOQUE 58.59: drives the title screen video (V1-G) and the cinematic
ship zoom (V2-G) on the in-game surface.

Usage:
    player = VideoPlayer(
        frames_dir=Path("Assets/video/title/frames"),
        manifest_path=Path("Assets/video/title/manifest.json"),
        loop=True,
    )
    player.play()
    # In scene.update():
    player.update(dt)
    # In scene.draw():
    player.draw(target_surface)
    # When done:
    if player.is_finished():
        transition_to_next_scene()

Resolution: source frames are loaded at native size (e.g. 240x360). At draw
time the player blits them onto the target surface, optionally scaled to
fill the target (default: scale to fit while keeping aspect ratio).
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Optional

import pygame


class VideoPlayer:
    """Plays a PNG-sequence video on a pygame Surface.

    The PNG sequence is loaded on first play() to avoid paying the load cost
    at __init__ (which can be called outside the game loop).
    """

    def __init__(
        self,
        frames_dir: Path,
        manifest_path: Path,
        loop: bool = False,
        autoplay: bool = True,
        scale_to_fit: bool = True,
    ) -> None:
        self._frames_dir = Path(frames_dir)
        self._manifest_path = Path(manifest_path)
        self._loop = loop
        self._autoplay = autoplay
        self._scale_to_fit = scale_to_fit
        # State
        self._frames: list[pygame.Surface] = []
        self._manifest: dict = {}
        self._frame_index: int = 0
        self._time_accum: float = 0.0
        self._playing: bool = False
        self._finished: bool = False
        # Source dimensions
        self._src_w: int = 0
        self._src_h: int = 0
        self._fps: int = 30
        self._frame_count: int = 0
        self._loop_start: int = 0
        self._loop_end: int = 0

    # ----- Loading -----

    def _load_manifest(self) -> None:
        """Load manifest.json with the video metadata."""
        if not self._manifest_path.is_file():
            return
        try:
            with self._manifest_path.open("r", encoding="utf-8") as f:
                self._manifest = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._manifest = {}
        self._fps = int(self._manifest.get("fps", 30))
        self._frame_count = int(self._manifest.get("frame_count", 0))
        w = int(self._manifest.get("width", 0))
        h = int(self._manifest.get("height", 0))
        self._src_w, self._src_h = w, h
        # Loop range (for V1, ambient+demo loop between frames 120-359)
        self._loop_start = int(self._manifest.get("loop_start_frame", 0))
        self._loop_end = int(self._manifest.get("loop_end_frame", self._frame_count - 1))

    def _ensure_loaded(self) -> None:
        """Lazily load all frames."""
        if self._frames:
            return
        self._load_manifest()
        if self._frame_count <= 0:
            # Try to count frames on disk
            pngs = sorted(self._frames_dir.glob("frame_*.png"))
            self._frame_count = len(pngs)
        # Load all frames
        for i in range(self._frame_count):
            path = self._frames_dir / f"frame_{i:04d}.png"
            if not path.is_file():
                # Insert a transparent placeholder so indices stay stable
                surf = pygame.Surface((self._src_w, self._src_h), pygame.SRCALPHA)
                self._frames.append(surf)
                continue
            try:
                surf = pygame.image.load(str(path)).convert_alpha()
                self._frames.append(surf)
            except pygame.error:
                surf = pygame.Surface((self._src_w, self._src_h), pygame.SRCALPHA)
                self._frames.append(surf)
        if not self._src_w and self._frames:
            self._src_w, self._src_h = self._frames[0].get_size()

    # ----- Public API -----

    def play(self) -> None:
        """Start (or restart) playback from frame 0."""
        self._ensure_loaded()
        self._frame_index = 0
        self._time_accum = 0.0
        self._playing = True
        self._finished = False

    def update(self, dt: float) -> None:
        """Advance frames based on elapsed time (in seconds)."""
        if not self._playing or self._finished:
            return
        if self._frame_count <= 0:
            return
        self._time_accum += dt
        frame_duration = 1.0 / max(1, self._fps)
        # Advance one or more frames
        while self._time_accum >= frame_duration:
            self._time_accum -= frame_duration
            self._advance_frame()

    def draw(self, target: pygame.Surface) -> None:
        """Blit the current frame onto target. Scales to fit if scale_to_fit=True."""
        self._ensure_loaded()
        if not self._frames:
            return
        if self._frame_index >= len(self._frames):
            return
        frame = self._frames[self._frame_index]
        if self._scale_to_fit:
            tw, th = target.get_size()
            if (tw, th) != (frame.get_width(), frame.get_height()):
                scaled = pygame.transform.scale(frame, (tw, th))
                target.blit(scaled, (0, 0))
                return
        target.blit(frame, (0, 0))

    def is_finished(self) -> bool:
        """True iff non-looping playback has reached the last frame."""
        return self._finished

    def is_playing(self) -> bool:
        return self._playing and not self._finished

    def get_progress(self) -> float:
        """0.0..1.0 progress through the (non-loop) playback."""
        if self._frame_count <= 0:
            return 0.0
        return min(1.0, self._frame_index / max(1, self._frame_count - 1))

    def reset(self) -> None:
        """Rewind to frame 0 without changing play state."""
        self._frame_index = 0
        self._time_accum = 0.0

    def stop(self) -> None:
        """Stop playback (keeps the current frame visible)."""
        self._playing = False

    # ----- Internals -----

    def _advance_frame(self) -> None:
        """Move to the next frame. Honors loop and loop_start/loop_end."""
        next_index = self._frame_index + 1
        if next_index >= self._frame_count:
            if self._loop:
                # If we have a defined loop range, jump to loop_start
                if self._loop_end > self._loop_start:
                    self._frame_index = self._loop_start
                else:
                    self._frame_index = 0
                self._time_accum = 0.0
            else:
                self._frame_index = self._frame_count - 1
                self._finished = True
                self._playing = False
            return
        self._frame_index = next_index
