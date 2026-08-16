"""Main game class: window, fixed-timestep loop, scene manager."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.core.clock import FixedClock
from stellar_horizon.core.scene_manager import SceneManager
from stellar_horizon.scenes.title import TitleScene
from stellar_horizon.settings import (
    DT_CLAMP, FIXED_DT, FPS_TARGET, INTERNAL_H, INTERNAL_W,
)


def _detect_scale() -> float:
    """Try to fill the monitor work area, like Void-Hunter does."""
    if sys.platform != "win32":
        return 4.0
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        rect = wintypes.RECT()
        if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0) and rect.bottom > rect.top:
            work_h = rect.bottom - rect.top
        else:
            work_h = 1080
        scale_h = max(1.0, work_h / INTERNAL_H)
        return float(min(scale_h, 6.0))
    except Exception:
        return 4.0


class Game:
    def __init__(self, assets_dir: Path | None = None) -> None:
        pygame.init()
        pygame.mixer.init()
        # assets_dir: default is stellar_horizon/assets (inside the stellar_horizon package)
        if assets_dir is None:
            assets_dir = Path(__file__).resolve().parent.parent / "assets"
        self.assets_dir = assets_dir
        scale = _detect_scale()
        win_w = int(INTERNAL_W * scale)
        win_h = int(INTERNAL_H * scale)
        self.internal = pygame.Surface((INTERNAL_W, INTERNAL_H))
        self.window = pygame.display.set_mode(
            (win_w, win_h), pygame.SCALED | pygame.RESIZABLE,
        )
        pygame.display.set_caption("STELLAR HORIZON")
        self.clock = FixedClock(FPS_TARGET)
        self.midi_player = MidiPlayer()
        title_midi = self.assets_dir / "midi" / "title.mid"
        title = TitleScene(
            self.midi_player,
            str(title_midi),
            wave_json=Path("stellar_horizon/waves/waves_act1.json"),
            assets_dir=self.assets_dir,
        )
        self.scenes = SceneManager(title)
        self._running = True
        self._accumulator = 0.0
        self._frame_count = 0

    def run(self) -> None:
        last = pygame.time.get_ticks() / 1000.0
        crash_log = Path("logs") / "stellar_horizon_crash.log"
        crash_log.parent.mkdir(parents=True, exist_ok=True)
        try:
            while self._running:
                # Read `now` at the START of the frame so `last` represents
                # the previous frame's start. Otherwise the post-tick_delay
                # gap collapses frame_time to ~0 and the accumulator never
                # reaches FIXED_DT (no events ever processed).
                now = pygame.time.get_ticks() / 1000.0
                self._tick_frame(last)
                last = now
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()

    def _tick_frame(self, last: float | None = None) -> None:
        """One frame: events, fixed-timestep updates, render, present.

        `last` is the time at the START of the PREVIOUS frame. `frame_time`
        is the wall-clock duration of the previous frame (clamped to DT_CLAMP).
        """
        if last is None:
            last = pygame.time.get_ticks() / 1000.0
        now = pygame.time.get_ticks() / 1000.0
        frame_time = min(now - last, DT_CLAMP)
        events = pygame.event.get()
        for ev in events:
            if ev.type == pygame.QUIT:
                self._running = False
                return
        self._accumulator += frame_time
        # Always run at least one update per frame so input events
        # are processed even when the very first frame hasn't yet
        # accumulated FIXED_DT. Subsequent updates drain the
        # accumulator for accurate fixed-timestep physics.
        self.scenes.update(FIXED_DT, events)
        self._accumulator -= FIXED_DT
        if self._accumulator < 0.0:
            self._accumulator = 0.0
        while self._accumulator >= FIXED_DT:
            self.scenes.update(FIXED_DT, events)
            self._accumulator -= FIXED_DT
        self.internal.fill((10, 15, 31))
        self.scenes.draw(self.internal)
        scaled = pygame.transform.scale(self.internal, self.window.get_size())
        self.window.blit(scaled, (0, 0))
        pygame.display.flip()
        self.clock.tick()
        self._frame_count += 1
