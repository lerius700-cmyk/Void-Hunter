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
    """Guarantee a live pygame for every test.

    pygame.quit() in another module's teardown tears pygame down -- the
    video system AND the font subsystem. Restoring only the display is not
    enough: pygame.font.get_init() stays False and pygame.font.Font(None, 12)
    raises "font not initialized" (src/ui/gameplay_runtime.py:4269). So
    pygame.init() comes first -- it re-initialises the modules that are
    down without resetting the state of the ones that are up -- and the
    display mode is set afterwards, because init() opens no window.
    """
    import pygame

    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((320, 480))
    yield
