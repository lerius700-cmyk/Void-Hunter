"""Tests for BLOQUE 60 GOLIATH sprite rendering in _draw_goliath().

BLOQUE 60: _draw_goliath should try to load a sprite via _load_sprite()
using the boss's animation_path. If the sprite is available, it blits the
sprite (96x80) and returns. If the sprite is missing, the existing
procedural drawing is used as a graceful fallback.

This file verifies both branches by patching BOSS_CONFIGS and constructing
a minimal GameplayRuntime via __new__ (bypassing the heavy __init__).
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest
import pygame
pygame.init()
pygame.display.set_mode((1, 1))


def _make_runtime(boss_id: str = "goliath", animation_path: str = "bosses/goliath/idle/frame_00.png"):
    """Build a minimal GameplayRuntime instance for _draw_goliath smoke tests.

    Uses __new__ to bypass the heavy __init__ (which constructs the player,
    background, parallax, particle engine, etc.). Only sets the attributes
    _draw_goliath reads.
    """
    from unittest.mock import MagicMock
    from src.ui.gameplay_runtime import GameplayRuntime

    rt = GameplayRuntime.__new__(GameplayRuntime)
    rt._t = 0.0
    rt._boss_flash = {}
    # Runtime spear/shield state read by the procedural fallback
    rt._boss_shield_hits = 0
    rt._boss_spear_phase = "ready"
    rt._boss_spear_phase_t = 0.0
    # Boss — use a MagicMock so we can set arbitrary attributes
    rt._boss = MagicMock()
    rt._boss.id = boss_id
    rt._boss.x = 100.0
    rt._boss.y = 50.0
    rt._boss.phase = 1
    rt._boss.hp = 400
    rt._boss.max_hp = 400
    rt._boss.animation_path = animation_path
    return rt


def _patch_boss_configs():
    """Returns a context manager that patches BOSS_CONFIGS with a stub
    for "goliath" (a namespace object with width/height/color).
    """
    from unittest.mock import patch

    cfg_stub = type("C", (), {
        "width": 32,
        "height": 18,
        "color": (200, 200, 220),
    })()
    return patch("src.ui.gameplay_runtime.BOSS_CONFIGS", {"goliath": cfg_stub})


# ---------------------------------------------------------------------------
# Test 1: sprite path is used when the boss's animation_path resolves to a
#         real file on disk. The function blits and returns without
#         touching the procedural layers.
# ---------------------------------------------------------------------------
def test_draw_goliath_uses_sprite_when_animation_path_exists():
    """When the sprite file exists, _draw_goliath loads it via _load_sprite
    and blits the 96x80 surface. We verify the function doesn't raise and
    that _load_sprite populated _sprite_cache with a real Surface for the
    animation_path key.

    NOTE: pygame.image.load().convert_alpha() needs a video mode set.
    After test_gameplay_runtime.py's autouse pygame.quit(), the display
    module may be marked initialized but no video mode is active. We
    force a fresh set_mode here so convert_alpha works.
    """
    # Force a fresh video mode. Always call set_mode, even if display
    # reports as "initialized" — after a prior pygame.quit() the mode
    # can be lost while the module still reports init=True.
    if not pygame.get_init():
        pygame.init()
    pygame.display.set_mode((1, 1))

    from src.ui.scenes import _sprite_cache, _load_sprite

    # Sanity check: ensure the load actually works in this environment.
    # If the file isn't reachable, this test is effectively a no-op
    # verification (the procedural fallback test covers the missing-sprite
    # branch).
    pre_surf = _load_sprite("bosses/goliath/idle/frame_00.png")
    if pre_surf is None:
        pytest.skip(
            "Could not load goliath idle sprite (pygame uninitialized or "
            "Assets/sprites/bosses/goliath/idle/frame_00.png missing). "
            "Procedural fallback path is covered by test 2."
        )

    # Clean cache so we observe the load during _draw_goliath
    _sprite_cache.pop("bosses/goliath/idle/frame_00.png", None)

    rt = _make_runtime(
        boss_id="goliath",
        animation_path="bosses/goliath/idle/frame_00.png",
    )

    with _patch_boss_configs():
        target = pygame.Surface((320, 480))
        # Should not raise; the sprite path takes the early return.
        rt._draw_goliath(target, 0, 0)
        # _draw_goliath must have called _load_sprite on the boss's
        # animation_path. The cache now has the surface.
        assert "bosses/goliath/idle/frame_00.png" in _sprite_cache
        surf = _sprite_cache["bosses/goliath/idle/frame_00.png"]
        assert surf is not None
        # The sprite is 96x80 per the BLOQUE 60 spec.
        assert surf.get_width() == 96
        assert surf.get_height() == 80


# ---------------------------------------------------------------------------
# Test 2: procedural fallback when the sprite file is missing. The function
#         must NOT crash; the legacy aura/ember/torso/etc. layers must
#         still be drawn.
# ---------------------------------------------------------------------------
def test_draw_goliath_falls_back_to_procedural_when_sprite_missing():
    """When the sprite file does NOT exist, _draw_goliath falls through to
    the procedural drawing code (graceful degradation). No exception.
    """
    # Force a fresh video mode (see test 1 for rationale).
    if not pygame.get_init():
        pygame.init()
    pygame.display.set_mode((1, 1))

    from unittest.mock import patch
    from src.ui.scenes import _sprite_cache

    rt = _make_runtime(
        boss_id="goliath",
        animation_path="bosses/goliath/THIS_DOES_NOT_EXIST/frame_00.png",
    )

    with _patch_boss_configs():
        # Force a fresh load attempt for the missing path
        with patch.dict(_sprite_cache, {}, clear=True):
            target = pygame.Surface((320, 480))
            # Should not raise — procedural fallback path runs to completion
            rt._draw_goliath(target, 0, 0)
            # The miss was NOT cached as a successful load; the entry is
            # absent (because _load_sprite returns None for missing files
            # without caching) OR present-but-None if the cache keys it
            # under "absent". Either way, no successful surface was loaded.
            entry = _sprite_cache.get(
                "bosses/goliath/THIS_DOES_NOT_EXIST/frame_00.png"
            )
            assert entry is None
