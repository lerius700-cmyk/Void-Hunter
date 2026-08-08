"""VOID HUNTER — Game root (BLOQUE 14: SceneManager integration)."""
from __future__ import annotations

import sys

import pygame

from src.core.scene_manager import (
    GameState,
    Scene,
    SceneManager,
    StateError,
)
from src.core.settings import (
    FIXED_DT,
    FPS_TARGET,
    WINDOW_H,
    WINDOW_TITLE,
    WINDOW_W,
)
from src.ui.scenes import (
    ActClearedScene,
    ActIntroScene,
    BossFightScene,
    BossIntroScene,
    CreditsScene,
    GameOverScene,
    GameplayScene,
    PauseScene,
    TitleScene,
    VictoryScene,
)


class Game:
    """Game root. Owns the SceneManager and the main loop.

    BLOQUE 14: 9 states wired up; per-scene draw + update. Fixed-timestep
    accumulator runs at 120 FPS, render at native window refresh.
    """

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        self.screen: pygame.Surface = pygame.display.set_mode(
            (WINDOW_W, WINDOW_H),
            pygame.SCALED | pygame.RESIZABLE,
        )
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.scenes: SceneManager = SceneManager()
        self._register_scenes()
        self._running: bool = True
        self._accumulator: float = 0.0

    def _register_scenes(self) -> None:
        """Wire up all 9 game state scenes + PAUSE overlay."""
        def transition_to(state: GameState) -> None:
            if state == GameState.PAUSE:
                self.scenes.push_overlay(self.scenes.scenes.get(GameState.PAUSE))
                return
            # Pop any overlay before transitioning out
            if self.scenes.is_overlay_active():
                self.scenes.pop_overlay()
            try:
                self.scenes.transition_to(state)
            except StateError:
                pass  # invalid transition; ignore for now

        self.scenes.register_scene(GameState.TITLE, TitleScene(transition_to))
        self.scenes.register_scene(GameState.ACT_INTRO, ActIntroScene(transition_to, act=1))
        self.scenes.register_scene(GameState.GAMEPLAY, GameplayScene(transition_to))
        self.scenes.register_scene(GameState.BOSS_INTRO, BossIntroScene(transition_to))
        self.scenes.register_scene(GameState.BOSS_FIGHT, BossFightScene(transition_to))
        self.scenes.register_scene(GameState.ACT_CLEARED, ActClearedScene(transition_to))
        self.scenes.register_scene(GameState.GAME_OVER, GameOverScene(transition_to))
        self.scenes.register_scene(GameState.VICTORY, VictoryScene(transition_to))
        self.scenes.register_scene(GameState.CREDITS, CreditsScene(transition_to))
        self.scenes.register_scene(GameState.PAUSE, PauseScene(transition_to))

    def run(self) -> int:
        """Main loop with fixed-timestep accumulator (120 FPS)."""
        try:
            while self._running:
                # Handle window-level events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                # Fixed-timestep update with accumulator
                frame_time = self.clock.tick(FPS_TARGET) / 1000.0
                # Clamp frame_time to prevent death spiral
                frame_time = min(frame_time, 1.0 / 30.0)
                self._accumulator += frame_time
                while self._accumulator >= FIXED_DT:
                    self.scenes.update(FIXED_DT)
                    self._accumulator -= FIXED_DT
                # Render
                self.scenes.draw(self.screen)
                pygame.display.flip()
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()
        return 0


def main() -> int:
    return Game().run()


if __name__ == "__main__":
    sys.exit(main())
