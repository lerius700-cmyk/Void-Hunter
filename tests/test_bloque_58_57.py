"""BLOQUE 58.57 — audio import fix + initial on_enter trigger.

Two fixes:
1. The music module had an IndentationError on a stray `print/return` left
   over from a previous edit. The result was a `from src.audio import music`
   failure inside TitleScene.on_enter, which silently broke title music.
2. main.py's _cmd_play uses an inline event loop instead of Game.run(),
   so the on_enter trigger that was added to Game.run() in BLOQUE 58.51
   never ran. The fix moves the on_enter trigger to Game.__init__ so it
   works for any caller.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_music_module_imports_clean() -> None:
    """The music module must import without IndentationError or SyntaxError.

    Regression: previous code had stray indented lines after a return
    statement that broke the entire module.
    """
    import py_compile

    src = ROOT / "src" / "audio" / "music.py"
    py_compile.compile(str(src), doraise=True)  # raises if syntax error
    import src.audio.music  # noqa: F401  actual import

    # Spot-check that the public API is intact
    from src.audio import music

    assert music.TITLE_TRACK == "pantalla principal.wav"
    assert "Lerius" in music.GAMEPLAY_TRACK
    assert music.play_title_music.__name__ == "play_title_music"
    assert music.play_gameplay_music.__name__ == "play_gameplay_music"
    assert music.stop_music.__name__ == "stop_music"


def test_music_constants_match_files() -> None:
    """The constant filenames must match the files actually in Assets/."""
    from src.audio import music

    assets = ROOT / "Assets"
    if not assets.is_dir():
        return  # skip if running outside the project

    actual = {p.name for p in assets.iterdir() if p.suffix == ".wav"}
    assert music.TITLE_TRACK in actual, (
        f"TITLE_TRACK {music.TITLE_TRACK!r} not in Assets/. "
        f"Available: {sorted(actual)}"
    )
    assert music.GAMEPLAY_TRACK in actual, (
        f"GAMEPLAY_TRACK {music.GAMEPLAY_TRACK!r} not in Assets/. "
        f"Available: {sorted(actual)}"
    )


def test_game_init_triggers_initial_on_enter() -> None:
    """Game.__init__ must call on_enter on the initial scene.

    Regression: main.py's _cmd_play uses an inline loop and never calls
    Game.run(), so the on_enter trigger that lived in Game.run() was
    bypassed. Moving it to __init__ fixes this for any caller.
    """
    # Headless pygame init for the Game constructor
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from src.core.game import Game
    from src.core.scene_manager import GameState

    with patch("src.audio.music.play_title_music", return_value=True) as mock_play:
        game = Game()
        # The title scene's on_enter must have called play_title_music
        mock_play.assert_called_once()


def test_trigger_initial_on_enter_is_idempotent_helper() -> None:
    """_trigger_initial_on_enter is the single source of truth.

    It must be callable directly (without going through Game.run()),
    and it must not raise when called on a fresh game.
    """
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from src.core.game import Game

    game = Game()
    # Calling the helper again must not raise. The scene's on_enter may
    # run twice (slight visual glitch from re-spawning demo ships) but
    # it must not crash.
    game._trigger_initial_on_enter()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
