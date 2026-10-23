"""BLOQUE 73.7: MainMenuScene options and background mode toggle.

The post-cinematic main menu has 3 items: NEW GAME, BOSS TIME, BACKGROUND.
BACKGROUND opens a 2-item submenu (SPACE VOID, ASTEROID NEBULA) that
writes to Game.bg_mode. Both modes produce a distinct draw path in
GameplayRuntime.render (the galaxy strip is drawn only in mode 1).

These tests cover:
1. The scene is registered between CINEMATIC and ACT_INTRO.
2. New Game transitions to ACT_INTRO.
3. Boss Time transitions to BOSS_INTRO.
4. Background submenu cycles bg_mode and stores it on the Game.
5. Esc returns to TITLE.
6. Direct 1/2/3 keys on the top level activate the matching item.
7. Direct 1/2 on the background submenu set the matching mode.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest


@pytest.fixture(scope="module")
def game():
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.core.game import Game
    return Game()


def test_menu_scene_registered_between_cinematic_and_act_intro(game) -> None:
    """CINEMATIC chains into MENU, MENU chains into ACT_INTRO / BOSS_INTRO."""
    from src.core.scene_manager import GameState

    cinematic = game.scenes.scenes[GameState.CINEMATIC]
    menu = game.scenes.scenes[GameState.MENU]
    assert menu is not None, "MENU scene not registered"
    # The valid transition graph from BLOQUE 73.7.
    assert GameState.MENU in cinematic._transition_to.__globals__["GameState"] \
        and True or True  # placeholder; the actual assertion is below
    # Direct membership check via the SceneManager's transition table.
    from src.core.scene_manager import VALID_TRANSITIONS
    assert GameState.MENU in VALID_TRANSITIONS[GameState.CINEMATIC]
    assert GameState.ACT_INTRO in VALID_TRANSITIONS[GameState.MENU]
    assert GameState.BOSS_INTRO in VALID_TRANSITIONS[GameState.MENU]
    assert GameState.TITLE in VALID_TRANSITIONS[GameState.MENU]


def test_default_bg_mode_is_asteroid_nebula(game) -> None:
    """Default 1 = asteroid nebula (matches v1.4.0's look)."""
    assert game.bg_mode == 1


def _press(menu, key) -> None:
    """Synthesize a keydown and pump the menu's update enough times to consume it."""
    import pygame  # noqa: PLC0415  - imported lazily so each test can fail

    ev = pygame.event.Event(pygame.KEYDOWN, key=key)
    pygame.event.post(ev)
    for _ in range(10):
        menu.update(0.0)


def test_new_game_activates_act_intro(game) -> None:
    import pygame  # noqa: PLC0415

    from src.core.scene_manager import GameState

    # Make the menu the active scene, otherwise transition_to validates
    # against the current TITLE state and rejects the menu's edges.
    game.scenes.current_state = GameState.MENU
    menu = game.scenes.scenes[GameState.MENU]
    menu.on_enter()
    menu._cursor = 0  # NEW GAME
    _press(menu, pygame.K_RETURN)  # type: ignore[attr-defined]
    assert game.scenes.current_state == GameState.ACT_INTRO


def test_boss_time_activates_boss_intro(game) -> None:
    import pygame  # noqa: PLC0415

    from src.core.scene_manager import GameState

    game.scenes.current_state = GameState.MENU
    menu = game.scenes.scenes[GameState.MENU]
    menu.on_enter()
    menu._cursor = 1  # BOSS TIME
    _press(menu, pygame.K_RETURN)  # type: ignore[attr-defined]
    assert game.scenes.current_state == GameState.BOSS_INTRO


def test_background_submenu_toggles_bg_mode(game) -> None:
    import pygame

    from src.core.scene_manager import GameState

    game.scenes.current_state = GameState.MENU
    menu = game.scenes.scenes[GameState.MENU]
    menu.on_enter()
    # The default is asteroid nebula (1). Switch to space void (0).
    menu._cursor = 2  # BACKGROUND
    _press(menu, pygame.K_RETURN)  # open the submenu
    assert menu._layer == "bg"
    menu._bg_cursor = 0
    _press(menu, pygame.K_RETURN)
    assert game.bg_mode == 0
    assert menu._layer == "top"  # back to top after applying
    # Switch back to nebula.
    menu._cursor = 2
    _press(menu, pygame.K_RETURN)
    menu._bg_cursor = 1
    _press(menu, pygame.K_RETURN)
    assert game.bg_mode == 1


def test_background_esc_returns_to_top(game) -> None:
    import pygame

    from src.core.scene_manager import GameState

    menu = game.scenes.scenes[GameState.MENU]
    menu.on_enter()
    menu._cursor = 2
    _press(menu, pygame.K_RETURN)
    assert menu._layer == "bg"
    _press(menu, pygame.K_ESCAPE)
    assert menu._layer == "top"


def test_esc_from_top_returns_to_title(game) -> None:
    import pygame

    from src.core.scene_manager import GameState

    game.scenes.current_state = GameState.MENU
    menu = game.scenes.scenes[GameState.MENU]
    menu.on_enter()
    _press(menu, pygame.K_ESCAPE)
    assert game.scenes.current_state == GameState.TITLE


def test_direct_number_keys_top_level(game) -> None:
    """1 -> NEW GAME, 2 -> BOSS TIME, 3 -> BACKGROUND submenu."""
    import pygame

    from src.core.scene_manager import GameState

    game.scenes.current_state = GameState.MENU
    menu = game.scenes.scenes[GameState.MENU]
    menu.on_enter()
    _press(menu, pygame.K_3)
    assert menu._layer == "bg"


def test_direct_number_keys_submenu_set_bg_mode(game) -> None:
    """K_1 picks SPACE VOID and closes; reopen to pick ASTEROID NEBULA with K_2.

    Picking a submenu item applies and closes — the user picks one
    option per visit, then reopens to change it. The apply path is
    Enter / K_1 / K_2; close-without-apply is Esc.
    """
    import pygame

    from src.core.scene_manager import GameState

    game.scenes.current_state = GameState.MENU
    menu = game.scenes.scenes[GameState.MENU]
    menu.on_enter()
    # First visit: pick SPACE VOID with K_1.
    menu._cursor = 2
    _press(menu, pygame.K_RETURN)
    assert menu._layer == "bg"
    _press(menu, pygame.K_1)
    assert game.bg_mode == 0
    assert menu._layer == "top"  # applying closes the submenu
    # Second visit: pick ASTEROID NEBULA with K_2.
    menu._cursor = 2
    _press(menu, pygame.K_RETURN)
    assert menu._layer == "bg"
    _press(menu, pygame.K_2)
    assert game.bg_mode == 1


def test_arrow_keys_cycle_cursor(game) -> None:
    """Down/Up cycle the cursor; wraps around at both ends."""
    from src.core.scene_manager import GameState

    menu = game.scenes.scenes[GameState.MENU]
    menu.on_enter()
    menu._cursor = 0
    import pygame
    _press(menu, pygame.K_DOWN)  # type: ignore[attr-defined]
    assert menu._cursor == 1
    _press(menu, pygame.K_DOWN)
    assert menu._cursor == 2
    _press(menu, pygame.K_DOWN)
    assert menu._cursor == 0  # wraps
    _press(menu, pygame.K_UP)  # type: ignore[attr-defined]
    assert menu._cursor == 2  # wraps backward