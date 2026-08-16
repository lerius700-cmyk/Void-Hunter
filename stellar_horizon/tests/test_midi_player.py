# stellar_horizon/tests/test_midi_player.py
import os
import tempfile
from pathlib import Path

import pygame
import pytest

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.tools.make_placeholder_midi import make_placeholder_midi


@pytest.fixture(scope="module", autouse=True)
def init_mixer():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.mixer.init()
    yield
    pygame.mixer.quit()


@pytest.fixture
def midi_path(tmp_path):
    p = tmp_path / "test.mid"
    make_placeholder_midi(p, seconds=2)
    return p


def test_midi_player_constructs():
    p = MidiPlayer()
    assert p is not None


def test_midi_player_plays_file(midi_path):
    p = MidiPlayer()
    p.play(str(midi_path), loop=False)
    p.stop()
