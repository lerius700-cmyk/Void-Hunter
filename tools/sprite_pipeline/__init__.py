"""BLOQUE 74: the sprite pipeline.

    tools/sprite_pipeline/audit.py    measure the art, classify it
    tools/sprite_pipeline/repair.py   fix what can be fixed
    tools/sprite_pipeline/run.py      the whole pipeline, in one command
"""
from __future__ import annotations

import os


def ensure_display(size: tuple[int, int] = (320, 480)) -> None:
    """Give pygame a video mode, headless when the machine has none.

    `convert_alpha()` needs a display surface. On a machine without a
    display the first set_mode() raises pygame.error, so the dummy SDL
    driver is enabled and the display module is re-initialised: the
    pipeline is an offline tool and must not need a screen to run.
    """
    import pygame

    try:
        pygame.display.set_mode(size)
        return
    except pygame.error:
        pass

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.display.quit()
    pygame.display.init()
    pygame.display.set_mode(size)
