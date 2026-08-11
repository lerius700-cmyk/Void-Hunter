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
    SubBossIntroScene,  # BLOQUE 50
    TitleScene,
    VictoryScene,
)


class Game:
    """Game root. Owns the SceneManager and the main loop.

    BLOQUE 14: 9 states wired up; per-scene draw + update. Fixed-timestep
    accumulator runs at 120 FPS, render at native window refresh.
    """

    def __init__(self, easy: bool = False) -> None:
        if not pygame.get_init():
            pygame.init()
        # BLOQUE 29: enable mouse + show cursor for mouse aiming
        try:
            pygame.mouse.set_visible(True)
        except pygame.error:
            pass
        # Display surface: WINDOW_W x WINDOW_H (960x1440 = 4x scaled).
        # All game scenes draw to a 240x360 INTERNAL surface, which we then
        # blit scaled to the display. This is the standard "low-res internal,
        # high-res display" pattern (Celeste, Shovel Knight, etc.) — avoids
        # integer-coordinate drift at 4x and keeps all game logic in one
        # coordinate system.
        # BLOQUE 31: honor VOID_HUNTER_SCALE env var (set by --scale CLI flag)
        import os as _os
        _scale_env = _os.environ.get("VOID_HUNTER_SCALE", "")
        if _scale_env.isdigit() and int(_scale_env) in (1, 2, 3):
            _scale = int(_scale_env)
            _ww = 240 * _scale
            _wh = 360 * _scale
        else:
            _scale = 4
            _ww = WINDOW_W
            _wh = WINDOW_H
        self._scale = _scale
        try:
            self.screen: pygame.Surface = pygame.display.set_mode(
                (_ww, _wh),
                pygame.SCALED | pygame.RESIZABLE,
            )
        except pygame.error:
            self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        # BLOQUE 31: center the window on screen so it doesn't open off-screen
        try:
            _info = pygame.display.get_desktop_sizes() if hasattr(pygame.display, "get_desktop_sizes") else None
            if _info:
                _sw, _sh = _info[0]
                _ox = max(0, (_sw - _ww) // 2)
                _oy = max(0, (_sh - _wh) // 2)
                _os.environ["SDL_VIDEO_WINDOW_POS"] = f"{_ox},{_oy}"
                # Re-apply position by re-setting the window mode
                try:
                    self.screen = pygame.display.set_mode(
                        (_ww, _wh),
                        pygame.SCALED | pygame.RESIZABLE,
                    )
                except pygame.error:
                    pass
        except Exception:
            pass
        # Internal rendering surface: 240x360 (INTERNAL_W x INTERNAL_H).
        # This is what every scene draws to.
        from src.core.settings import INTERNAL_H as _IH, INTERNAL_W as _IW
        self.internal: pygame.Surface = pygame.Surface((_IW, _IH))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        # Audio: shared engine, null-safe if mixer fails to init
        try:
            from src.audio.synth import AudioEngine
            self.audio: AudioEngine | None = AudioEngine()
        except Exception:
            self.audio = None
        self.easy: bool = easy  # BLOQUE 28: easy mode flag
        self.scenes: SceneManager = SceneManager()
        self._register_scenes()
        self._running: bool = True
        self._accumulator: float = 0.0

    def _present(self) -> None:
        """Scale the internal 240x360 surface to the display and present."""
        # Clear the display first (in case of window resize artifacts)
        self.screen.fill((0, 0, 0))
        # Scale internal to display
        scaled = pygame.transform.scale(
            self.internal,
            (self.screen.get_width(), self.screen.get_height()),
        )
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

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
        self.scenes.register_scene(GameState.GAMEPLAY, GameplayScene(transition_to, audio=self.audio))
        # BLOQUE 58.23: pass the shared audio engine to BOSS_INTRO and
        # SUB_BOSS_INTRO. The previous versions did `AudioEngine()` in
        # on_enter, which re-initialized pygame.mixer and re-baked all
        # SFX + BGM (~1.2s freeze) right when the wave cleared.
        self.scenes.register_scene(GameState.BOSS_INTRO, BossIntroScene(transition_to, audio=self.audio))
        self.scenes.register_scene(GameState.BOSS_FIGHT, BossFightScene(transition_to, act=1, audio=self.audio))
        self.scenes.register_scene(GameState.ACT_CLEARED, ActClearedScene(transition_to))
        self.scenes.register_scene(GameState.GAME_OVER, GameOverScene(transition_to))
        self.scenes.register_scene(GameState.VICTORY, VictoryScene(transition_to))
        self.scenes.register_scene(GameState.CREDITS, CreditsScene(transition_to))
        # BLOQUE 50: sub-boss mid-wave warning (yellow)
        self.scenes.register_scene(GameState.SUB_BOSS_INTRO, SubBossIntroScene(transition_to, audio=self.audio))
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
                # Clear internal surface
                self.internal.fill((0, 0, 0))
                # Draw scenes to the 240x360 internal surface
                self.scenes.draw(self.internal)
                # Scale internal to display and present
                self._present()
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()
        return 0


def main() -> int:
    return Game().run()


if __name__ == "__main__":
    sys.exit(main())
