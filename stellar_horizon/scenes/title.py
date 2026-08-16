"""Title screen scene."""
from __future__ import annotations

from pathlib import Path

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.core.scene_manager import Scene, SceneName
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


class TitleScene(Scene):
    name = SceneName.TITLE

    def __init__(self, midi_player: MidiPlayer, midi_path: str,
                 wave_json: Path = Path("stellar_horizon/waves/waves_act1.json"),
                 assets_dir: Path = Path("stellar_horizon/assets")) -> None:
        self.midi_player = midi_player
        self.midi_path = midi_path
        self.wave_json = wave_json
        self.assets_dir = assets_dir
        self._font = None
        self._big_font = None
        self._next: Scene | None = None

    def on_enter(self) -> None:
        self.midi_player.play(self.midi_path, loop=True)

    def on_exit(self) -> None:
        self.midi_player.fadeout(400)

    def update(self, dt: float, events: list) -> None:
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    from stellar_horizon.scenes.gameplay import GameplayScene
                    self._next = GameplayScene(
                        midi_player=self.midi_player,
                        wave_json=self.wave_json,
                        assets_dir=self.assets_dir,
                    )
                    return

    def draw(self, surface: pygame.Surface) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 16, bold=True)
            self._big_font = pygame.font.SysFont("monospace", 32, bold=True)
        surface.fill((10, 15, 31))
        title = self._big_font.render("STELLAR HORIZON", False, (240, 240, 240))
        surface.blit(title, (INTERNAL_W // 2 - title.get_width() // 2, INTERNAL_H // 3))
        sub = self._font.render("Press SPACE to start", False, (180, 180, 220))
        surface.blit(sub, (INTERNAL_W // 2 - sub.get_width() // 2, INTERNAL_H // 2))

    def next_scene(self):
        return self._next
