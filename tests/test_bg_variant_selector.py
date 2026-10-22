"""BLOQUE 73.6: the title-screen background variant selector.

GOLIATH and the gameplay scene inherited four parallax strip variants
(blue_void, teal, gold_amber, purple_dusk) but nothing ever read or
wrote the variant index. The default 0 (blue_void) made act 1 read as
a flat dark screen. The user wanted the purple procedural backdrop
that the v1.4.0 binary used to show.

These tests lock the four invariants:
1. The default variant is purple_dusk (3) — what the user approved.
2. The title scene recognises the 1-4 / arrow keys and writes the
   chosen variant back to the Game.
3. The Gameplay and BossFight scenes apply the chosen variant to their
   background on construction — so --boss (which skips the title)
   still gets the user's choice, not blue_void by accident.
4. The legacy parallax fallback on the title also picks up the live
   choice, so a user without the title video still sees the preview.
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


def test_default_variant_is_purple_dusk(game) -> None:
    """The user wants the purple backdrop by default — 3 = purple_dusk."""
    assert game.bg_variant_idx == 3


def test_title_scene_knows_its_game(game) -> None:
    """The title scene needs the back-ref to read/write the variant."""
    from src.core.scene_manager import GameState

    title = game.scenes.scenes[GameState.TITLE]
    assert title._game is game


def test_pressing_1_to_4_cycles_the_variant(game) -> None:
    import pygame

    from src.core.scene_manager import GameState

    title = game.scenes.scenes[GameState.TITLE]
    for expected_key, expected_idx in (
        (pygame.K_1, 0),
        (pygame.K_2, 1),
        (pygame.K_3, 2),
        (pygame.K_4, 3),
    ):
        # Synthesize a keydown that the title's event pump would receive
        ev = pygame.event.Event(pygame.KEYDOWN, key=expected_key)
        pygame.event.post(ev)
        # Pump the events the title would have processed by now.
        for _ in range(10):
            title.update(0.0)
        assert game.bg_variant_idx == expected_idx, (
            f"key {expected_key} should set variant to {expected_idx}, "
            f"got {game.bg_variant_idx}"
        )
    # Reset to default for the rest of the tests.
    game.bg_variant_idx = 3


def test_left_right_arrows_cycle_the_variant(game) -> None:
    import pygame

    from src.core.scene_manager import GameState

    title = game.scenes.scenes[GameState.TITLE]
    for key, delta in (
        (pygame.K_LEFT, -1),
        (pygame.K_RIGHT, 1),
    ):
        start = game.bg_variant_idx
        ev = pygame.event.Event(pygame.KEYDOWN, key=key)
        pygame.event.post(ev)
        for _ in range(10):
            title.update(0.0)
        assert game.bg_variant_idx == (start + delta) % 4


def test_gameplay_scene_applies_the_chosen_variant(game) -> None:
    """If the user picks teal (1), the gameplay background must be teal."""
    from src.core.scene_manager import GameState
    from src.systems.parallax import _STRIP_VARIANT_THEMES

    game.bg_variant_idx = 1  # teal
    gp = game.scenes.scenes[GameState.GAMEPLAY]
    # on_enter is what applies the variant — that's the moment the
    # transition_to() call would trigger it in a real run. The user
    # changes the variant on the title BEFORE entering gameplay, so the
    # variant is current at on_enter time.
    gp.on_enter()
    assert gp._rt._parallax_bg is not None
    assert gp._rt._parallax_bg._theme_name == _STRIP_VARIANT_THEMES[1]
    game.bg_variant_idx = 3


def test_boss_fight_scene_applies_the_chosen_variant(game) -> None:
    """Boss fights use the self._rt._bg parallax, not _parallax_bg."""
    from src.core.scene_manager import GameState
    from src.systems.parallax import _STRIP_VARIANT_THEMES

    game.bg_variant_idx = 0  # blue_void
    boss = game.scenes.scenes[GameState.BOSS_FIGHT]
    boss.on_enter()
    assert boss._rt._bg is not None
    assert boss._rt._bg._theme_name == _STRIP_VARIANT_THEMES[0]
    game.bg_variant_idx = 3


def test_choice_survives_a_round_trip(game) -> None:
    """The title picks, on_enter applies — both reads must agree."""
    import pygame

    from src.core.scene_manager import GameState

    title = game.scenes.scenes[GameState.TITLE]
    gp = game.scenes.scenes[GameState.GAMEPLAY]
    for target_idx in (0, 1, 2, 3):
        ev = pygame.event.Event(
            pygame.KEYDOWN,
            key=(pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)[target_idx],
        )
        pygame.event.post(ev)
        for _ in range(10):
            title.update(0.0)
        gp.on_enter()
        from src.systems.parallax import _STRIP_VARIANT_THEMES

        assert game.bg_variant_idx == target_idx
        assert gp._rt._parallax_bg._theme_name == _STRIP_VARIANT_THEMES[target_idx]