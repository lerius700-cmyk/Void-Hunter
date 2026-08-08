"""VOID HUNTER — Game root class (BLOQUE 0 stub).

BLOQUE 0: opens a window at 120 FPS, clears the screen, and exits on ESC/QUIT.
Full implementation (scene stack, fixed-timestep accumulator, scene manager)
lands in BLOQUE 14 (GameStateMachine).

Description: minimal Game bootstrap. Window + clock + clear. No game logic.
Dependencies: pygame, src.core.settings.
"""
from __future__ import annotations

import sys

import pygame

from src.core.settings import (
    FPS_TARGET,
    WINDOW_H,
    WINDOW_TITLE,
    WINDOW_W,
)


class Game:
    """BLOQUE 0 placeholder Game. Replaced by scene-stack Game in BLOQUE 14.

    Responsibilities at this stage:
        - Initialize pygame + display.
        - Tick the clock at FPS_TARGET.
        - Clear to black each frame.
        - Handle ESC / QUIT to close gracefully.
    """

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        # mixer init is opt-in: BLOQUE 13 will pre-bake SFX and call init explicitly.
        self.screen: pygame.Surface = pygame.display.set_mode(
            (WINDOW_W, WINDOW_H),
            pygame.SCALED | pygame.RESIZABLE,
        )
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self._running: bool = True

    def run(self) -> int:
        """Main loop. Returns 0 on clean exit, 1 on error."""
        try:
            while self._running:
                self._handle_events()
                self._update()
                self._draw()
                self.clock.tick(FPS_TARGET)
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()
        return 0

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._running = False

    def _update(self) -> None:
        """No-op at BLOQUE 0. Logic lands in BLOQUE 14."""
        return

    def _draw(self) -> None:
        """Clear to black. Visual layers land in BLOQUE 14."""
        self.screen.fill((0, 0, 0))
        pygame.display.flip()


def main() -> int:
    """Module-level entry, used by `pyproject.toml` script entry point."""
    return Game().run()


if __name__ == "__main__":
    sys.exit(main())
