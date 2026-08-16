"""MIDI playback via pygame.mixer.music (native MIDI support)."""
from __future__ import annotations

import pygame


class MidiPlayer:
    def __init__(self, volume: float = 0.6) -> None:
        self.volume = volume
        pygame.mixer.music.set_volume(volume)

    def play(self, midi_path: str, loop: bool = True) -> None:
        pygame.mixer.music.load(midi_path)
        pygame.mixer.music.play(-1 if loop else 0)

    def stop(self) -> None:
        pygame.mixer.music.stop()

    def fadeout(self, ms: int = 800) -> None:
        pygame.mixer.music.fadeout(ms)
