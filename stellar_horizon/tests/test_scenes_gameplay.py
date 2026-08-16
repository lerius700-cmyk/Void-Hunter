# stellar_horizon/tests/test_scenes_gameplay.py
import os
from pathlib import Path
import pytest
import pygame

from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.scenes.title import TitleScene
from stellar_horizon.scenes.game_over import GameOverScene
from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.tools.make_placeholder_bgs import make_placeholder_backgrounds
from stellar_horizon.tools.make_placeholder_midi import make_placeholder_midi


@pytest.fixture(scope="module", autouse=True)
def init_mixer():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.mixer.init()
    yield
    pygame.mixer.quit()


@pytest.fixture
def assets_dir(tmp_path):
    bg_dir = tmp_path / "backgrounds"
    midi_dir = tmp_path / "midi"
    make_placeholder_backgrounds(bg_dir)
    midi_dir.mkdir(parents=True, exist_ok=True)
    make_placeholder_midi(midi_dir / "act1.mid", seconds=2)
    make_placeholder_midi(midi_dir / "game_over.mid", seconds=2)
    return tmp_path


def test_title_scene_constructs(assets_dir):
    midi = MidiPlayer()
    s = TitleScene(midi, str(assets_dir / "midi" / "act1.mid"))
    assert s.name == "title"


def test_gameplay_scene_constructs(assets_dir):
    midi = MidiPlayer()
    s = GameplayScene(
        midi_player=midi,
        wave_json=Path("stellar_horizon/waves/waves_act1.json"),
        assets_dir=assets_dir,
    )
    assert s.name == "gameplay"


def test_gameplay_scene_on_enter_starts_wave(assets_dir):
    midi = MidiPlayer()
    s = GameplayScene(
        midi_player=midi,
        wave_json=Path("stellar_horizon/waves/waves_act1.json"),
        assets_dir=assets_dir,
    )
    s.on_enter()
    assert s.player is not None
    assert s.wave_manager is not None


def test_game_over_constructs(assets_dir):
    midi = MidiPlayer()
    s = GameOverScene(midi, score=12345, victory=False)
    assert s.score == 12345
    assert s.victory is False
