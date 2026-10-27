"""BLOQUE 74: shared pytest fixtures.

Several test modules used to call pygame.quit() in teardown, which left the
video system uninitialised for whatever ran next. That turned seven of the
documented "pre-existing failures" into pure collection-order accidents: the
same tests pass in isolation and fail depending on where pytest put them.
The fixture below makes the video system survive every test, so the suite's
result no longer depends on alphabetical order.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest


@pytest.fixture(autouse=True)
def _live_video_system():
    """Guarantee a live video mode for every test.

    pygame.quit() in another module's teardown tears the video system down;
    pygame.display.set_mode() brings it back. Only the display is restored
    -- the rest of pygame's state stays as the previous module left it.
    """
    import pygame

    if not pygame.display.get_init():
        pygame.display.set_mode((320, 480))
    yield
