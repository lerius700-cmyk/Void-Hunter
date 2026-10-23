"""BLOQUE 73.7 regression net: the BACKGROUND menu option must actually
change the gameplay background.

BLOQUE 73.6 shipped a BACKGROUND submenu (SPACE VOID / ASTEROID NEBULA)
that wrote `Game.bg_mode`, and BLOQUE 73.7 shipped the `bg_mode` draw
branch in `GameplayRuntime.draw`. Neither release actually worked:

* `GameplayRuntime` is not a `Scene`, so it never received the `_game`
  back-reference that `_register_with_back_ref()` injects into scenes.
  `getattr(self, "_game", None)` was always `None`, so `bg_mode` was
  always the default 1 and the `bg_mode == 0` branch was dead code.
* The `bg_mode == 1` branch drew only the galaxy strip; the parallax
  layer was inside the `bg_mode == 0` branch, so the nebula lost the
  "parallax encima" composition the spec and the v1.6.3 release notes
  describe.

The BLOQUE 73.6 spec explicitly demanded a pixel-comparison test for
exactly this class of bug ("verificar que draw() esté en el path de
render con un test que compare píxeles con/sin strip"). That test did
not exist until now, which is why both defects shipped.

These tests lock the three invariants:
1. The runtime holds the Game back-reference (the root cause).
2. bg_mode 0 and bg_mode 1 render measurably different frames.
3. The nebula is the rich one; Space Void is the sparse one.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest


INTERNAL_W = 320
INTERNAL_H = 480


@pytest.fixture(scope="module")
def game():
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.core.game import Game

    return Game()


@pytest.fixture(scope="module")
def runtime(game):
    """The gameplay runtime, entered so its backgrounds are loaded."""
    from src.core.scene_manager import GameState

    gp = game.scenes.scenes[GameState.GAMEPLAY]
    gp.on_enter()
    return gp._rt


def _raw(surface) -> bytes:
    import pygame

    return pygame.image.tobytes(surface, "RGB")


def _lit_pixels(surface) -> int:
    """Count pixels that are not pure black."""
    buf = _raw(surface)
    return sum(
        1
        for i in range(0, len(buf), 3)
        if buf[i] or buf[i + 1] or buf[i + 2]
    )


def _render(runtime, game, bg_mode: int):
    """Draw one full frame with the given background mode."""
    import pygame

    game.bg_mode = bg_mode
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    surf.fill((0, 0, 0))
    runtime.draw(surf)
    return surf


def test_gameplay_runtime_holds_the_game_backref(game, runtime) -> None:
    """Root cause: the runtime never got `_game`, so bg_mode was always 1.

    GameplayRuntime is constructed by GameplayScene, which IS a Scene and
    DOES get the back-reference. The runtime has to be handed it
    explicitly.
    """
    assert getattr(runtime, "_game", None) is game


def test_bg_mode_changes_the_rendered_frame(game, runtime) -> None:
    """SPACE VOID and ASTEROID NEBULA must not render the same frame.

    Before the fix both modes rendered identically (144k differing pixels
    is 94% of the frame; the unfixed build differed by ~0%).
    """
    s_void = _render(runtime, game, 0)
    s_nebula = _render(runtime, game, 1)

    assert _raw(s_void) != _raw(s_nebula), (
        "bg_mode 0 and bg_mode 1 rendered identical frames — the "
        "background selector is inert again"
    )

    a = _raw(s_void)
    b = _raw(s_nebula)
    differing = sum(1 for x, y in zip(a, b) if x != y)
    assert differing > len(a) * 0.5, (
        f"only {differing}/{len(a)} bytes differ between modes; the "
        f"background is barely changing"
    )


def test_nebula_is_richer_than_space_void(game, runtime) -> None:
    """The nebula is the dense procedural look; Space Void is the sparse one."""
    lit_void = _lit_pixels(_render(runtime, game, 0))
    lit_nebula = _lit_pixels(_render(runtime, game, 1))

    assert lit_nebula > lit_void * 2, (
        f"nebula lit={lit_nebula} is not meaningfully denser than "
        f"space void lit={lit_void}"
    )


def test_galaxy_strip_is_ready_and_drawn(game, runtime) -> None:
    """The procedural strip must be loaded, not silently skipped.

    This is the exact historical bug: the strip was updated every frame
    but never drawn, so the pixels were discarded and the user saw an
    empty screen.
    """
    import pygame

    assert runtime._galaxy_bg is not None
    assert runtime._galaxy_bg.is_ready, (
        "the ScrollingGalaxyBackground never loaded — ASTEROID NEBULA "
        "would fall back to the tiling image"
    )

    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    surf.fill((0, 0, 0))
    runtime._galaxy_bg.draw(surf)
    assert _lit_pixels(surf) > INTERNAL_W * INTERNAL_H * 0.5, (
        "the galaxy strip drew (almost) nothing — it is not in the render path"
    )


def test_menu_writes_bg_mode_and_runtime_reads_it(game) -> None:
    """The menu's choice must be the value the runtime reads.

    Both sides of the contract, so a future refactor that renames one of
    them fails here instead of silently going inert.
    """
    import pygame

    from src.core.scene_manager import GameState

    menu = game.scenes.scenes[GameState.MENU]
    assert getattr(menu, "_game", None) is game

    def press(key: int) -> None:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        for _ in range(10):
            menu.update(0.0)

    game.bg_mode = 1
    # Top layer: move to BACKGROUND and open the submenu.
    menu._cursor = 2
    press(pygame.K_RETURN)
    assert menu._layer == "bg", "BACKGROUND did not open the submenu"

    # Submenu: pick SPACE VOID (index 0) and apply it.
    menu._bg_cursor = 0
    press(pygame.K_RETURN)
    assert game.bg_mode == 0, "the menu did not write bg_mode"

    gp = game.scenes.scenes[GameState.GAMEPLAY]
    gp.on_enter()
    assert getattr(gp._rt, "_game", None) is game
    assert getattr(gp._rt._game, "bg_mode") == 0

    # Restore the default for the other tests.
    game.bg_mode = 1
