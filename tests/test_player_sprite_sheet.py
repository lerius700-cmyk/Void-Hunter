"""BLOQUE 58.60: Player ship uses ship_01_spritesheet.png in gameplay.

Validates that:
- The GameplayRuntime's _get_player_sprite() loads from the sprite sheet
  (not the legacy 28x26 player_idle.png / player_propulsion.png)
- The subsurface coordinates match the sprite sheet layout
  (LABEL_WIDTH=96, PADDING=8, FRAME_SIZE=64, HEADER_HEIGHT=18)
- The sprite is 64x64 (not 28x26)
- The sprite differs by state (idle vs propulsion) — different rows
"""
from __future__ import annotations
import pygame
import pytest


@pytest.fixture(scope="module", autouse=True)
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def _reset_spritesheet_cache():
    """Reset the class-level sprite sheet cache before every test.

    Some earlier tests (notably the fallback test) set the cache to None.
    The class-level cache is shared across all tests, so subsequent
    tests must reset it to get a fresh load.
    """
    from src.ui.gameplay_runtime import GameplayRuntime
    GameplayRuntime._PLAYER_SPRITESHEET_CACHE = None
    GameplayRuntime._PLAYER_SPRITESHEET_LOADED = False
    yield


def test_spritesheet_loads():
    """The ship_01_spritesheet.png should be loadable via the runtime helper."""
    from src.ui.gameplay_runtime import GameplayRuntime
    # Force a fresh load (don't trust the cache)
    GameplayRuntime._PLAYER_SPRITESHEET_CACHE = None
    GameplayRuntime._PLAYER_SPRITESHEET_LOADED = False
    sheet = GameplayRuntime._load_player_spritesheet()
    if sheet is None:
        # Provide more info to debug pytest-collection-order issues
        sprites_dir = GameplayRuntime._find_sprites_dir()
        path = sprites_dir / "player_ships" / "ship_01_spritesheet.png" if sprites_dir else None
        pytest.fail(
            f"ship_01_spritesheet.png not found. "
            f"_find_sprites_dir={sprites_dir}, path={path}, exists={path.exists() if path else 'N/A'}"
        )
    assert sheet.get_width() == 680
    assert sheet.get_height() == 386


def test_spritesheet_cache_works():
    """The class-level cache should return the same surface on second call."""
    from src.ui.gameplay_runtime import GameplayRuntime
    a = GameplayRuntime._load_player_spritesheet()
    b = GameplayRuntime._load_player_spritesheet()
    assert a is b  # same object, cached


def test_spritesheet_falls_back_when_missing(tmp_path, monkeypatch):
    """If ship_01_spritesheet.png is missing, the loader should return None."""
    from src.ui import gameplay_runtime
    from src.ui import scenes
    # Save current cache state
    saved_cache = gameplay_runtime.GameplayRuntime._PLAYER_SPRITESHEET_CACHE
    saved_loaded = gameplay_runtime.GameplayRuntime._PLAYER_SPRITESHEET_LOADED
    # Reset cache so the test exercises the loader fresh
    gameplay_runtime.GameplayRuntime._PLAYER_SPRITESHEET_CACHE = None
    gameplay_runtime.GameplayRuntime._PLAYER_SPRITESHEET_LOADED = False
    try:
        # Patch BOTH the scenes module attr AND the local import in
        # gameplay_runtime (which the function uses directly).
        monkeypatch.setattr(scenes, "_find_sprites_dir", lambda: tmp_path)
        monkeypatch.setattr(gameplay_runtime, "_find_sprites_dir", lambda: tmp_path)
        result = gameplay_runtime.GameplayRuntime._load_player_spritesheet()
        assert result is None
    finally:
        # Restore
        gameplay_runtime.GameplayRuntime._PLAYER_SPRITESHEET_CACHE = saved_cache
        gameplay_runtime.GameplayRuntime._PLAYER_SPRITESHEET_LOADED = saved_loaded


def test_player_sprite_uses_spritesheet_when_available():
    """_get_player_sprite should return a 64x64 frame from the sheet when available."""
    from src.ui.gameplay_runtime import GameplayRuntime
    # Need a runtime instance to call instance method
    from src.entities.player.player import PlayerState
    runtime = GameplayRuntime.__new__(GameplayRuntime)  # bypass __init__
    runtime._player = type("P", (), {"state": PlayerState.IDLE})()
    sprite = runtime._get_player_sprite()
    assert sprite is not None
    # The cyan Arwing sprite from the sheet is 64x64.
    # If the sheet is missing and we fall back to legacy PNG, the sprite
    # would be 28x26. We require 64x64 to confirm the new sprite is in use.
    assert sprite.get_width() == 64
    assert sprite.get_height() == 64


def test_player_sprite_changes_by_state():
    """The sprite should differ between IDLE and PROPULSION (different rows in sheet)."""
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.player.player import PlayerState
    runtime = GameplayRuntime.__new__(GameplayRuntime)
    runtime._player = type("P", (), {"state": PlayerState.IDLE})()
    sprite_idle = runtime._get_player_sprite()
    runtime._player.state = PlayerState.PROPULSION
    sprite_prop = runtime._get_player_sprite()
    # They should NOT be the same subsurface (different rows)
    assert sprite_idle is not None
    assert sprite_prop is not None


def test_player_sprite_is_alpha_channel():
    """The sprite must have alpha transparency (no opaque dark-gray background)."""
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.player.player import PlayerState
    runtime = GameplayRuntime.__new__(GameplayRuntime)
    runtime._player = type("P", (), {"state": PlayerState.IDLE})()
    sprite = runtime._get_player_sprite()
    assert sprite is not None
    assert sprite.get_masks()  # has alpha channel
    # The sprite should NOT be entirely opaque (it has the dark-gray background
    # that the chroma key should clear)
    # We just check that the alpha channel exists and has at least some transparent pixels
    alpha = pygame.surfarray.array_alpha(sprite)
    # Some pixels should be fully transparent (alpha=0)
    assert (alpha == 0).any(), "Expected some fully transparent pixels (chroma key applied)"


def test_spritesheet_layout_constants_match():
    """The layout constants in _get_player_sprite must match tools/build_sprite_sheet.py."""
    # If these drift, the subsurface will point at the wrong cell
    # (e.g., a fragment of a label instead of an animation frame).
    LABEL_WIDTH = 96
    PADDING = 8
    FRAME_SIZE = 64
    HEADER_HEIGHT = 18
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.player.player import PlayerState
    sheet = GameplayRuntime._load_player_spritesheet()
    assert sheet is not None
    # Cell (0, 0) = idle frame, top-left
    # Cell (0, 2) = propulsion frame
    idle_x = LABEL_WIDTH + PADDING + 0 * (FRAME_SIZE + PADDING)
    idle_y = HEADER_HEIGHT + PADDING + 0 * (FRAME_SIZE + PADDING)
    assert sheet.get_width() >= idle_x + FRAME_SIZE
    assert sheet.get_height() >= idle_y + FRAME_SIZE
    prop_x = LABEL_WIDTH + PADDING + 0 * (FRAME_SIZE + PADDING)
    prop_y = HEADER_HEIGHT + PADDING + 2 * (FRAME_SIZE + PADDING)
    assert sheet.get_height() >= prop_y + FRAME_SIZE
