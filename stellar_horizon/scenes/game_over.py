"""Game over screen scene."""
from __future__ import annotations

import sys
from pathlib import Path

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.core.scene_manager import Scene, SceneName
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


class GameOverScene(Scene):
    name = SceneName.GAME_OVER

    def __init__(self, midi_player: MidiPlayer, score: int = 0, victory: bool = False,
                 wave_json: Path = Path("stellar_horizon/waves/waves_act1.json"),
                 assets_dir: Path = Path("stellar_horizon/assets")) -> None:
        self.midi_player = midi_player
        self.score = score
        self.victory = victory
        self.wave_json = wave_json
        self.assets_dir = assets_dir
        self._font = None
        self._big_font = None
        self._next = None
        self._timer = 0.0

    def on_enter(self) -> None:
        midi = self.assets_dir / "midi" / "game_over.mid"
        if midi.exists():
            self.midi_player.play(str(midi), loop=True)

    def on_exit(self) -> None:
        self.midi_player.fadeout(400)

    def update(self, dt, events):
        self._timer += dt
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_r, pygame.K_RETURN):
                    from stellar_horizon.scenes.gameplay import GameplayScene
                    self._next = GameplayScene(
                        midi_player=self.midi_player,
                        wave_json=self.wave_json,
                        assets_dir=self.assets_dir,
                    )
                elif ev.key == pygame.K_q:
                    pygame.quit()
                    sys.exit(0)

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 14, bold=True)
            self._big_font = pygame.font.SysFont("monospace", 28, bold=True)
        surface.fill((10, 15, 31))
        msg = "VICTORY" if self.victory else "GAME OVER"
        color = (220, 220, 100) if self.victory else (220, 80, 80)
        title = self._big_font.render(msg, False, color)
        surface.blit(title, (INTERNAL_W // 2 - title.get_width() // 2, INTERNAL_H // 3))
        sub = self._font.render(f"Final score: {self.score}", False, (240, 240, 240))
        surface.blit(sub, (INTERNAL_W // 2 - sub.get_width() // 2, INTERNAL_H // 2))
        hint = self._font.render("R = retry   Q = quit", False, (180, 180, 220))
        surface.blit(hint, (INTERNAL_W // 2 - hint.get_width() // 2, INTERNAL_H // 2 + 30))

    def next_scene(self):
        return self._next
