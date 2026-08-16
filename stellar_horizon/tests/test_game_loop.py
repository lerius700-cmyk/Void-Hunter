# stellar_horizon/tests/test_game_loop.py
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest
import pygame

from stellar_horizon.core.game import Game


def test_game_constructs():
    g = Game()
    assert g._running is True
    assert g.internal.get_size() == (480, 270)
    pygame.quit()


def test_game_processes_one_frame():
    g = Game()
    g._accumulator = 0.0
    initial_updates = g._frame_count
    g._tick_frame()
    assert g._frame_count == initial_updates + 1
    pygame.quit()
