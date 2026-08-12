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
        # Display surface: full monitor size (BLOQUE 58.36f).
        # All game scenes draw to a 320x480 INTERNAL surface, which we then
        # blit scaled to the GAME AREA in the center of the monitor. The
        # side panels (left + right of the game area) are filled with a
        # parallax starfield. This makes the game reach all 4 edges of any
        # monitor (portrait game on landscape monitor) without black bars.
        # BLOQUE 31: honor VOID_HUNTER_SCALE env var (set by --scale CLI flag)
        # BLOQUE 58.35: accept scales 1..6 for 4K monitors.
        # BLOQUE 58.36f: accept FLOAT scale (e.g. 2.25) so the game area
        # fills the monitor height exactly (no black bar top/bottom).
        # BLOQUE 34: internal resolution is 320x480 (was 240x360).
        import os as _os
        from src.core.settings import INTERNAL_W as _IW, INTERNAL_H as _IH
        _scale_env = _os.environ.get("VOID_HUNTER_SCALE", "")
        # Parse float (was int 1..6 in BLOQUE 58.35; now float 1.0..6.0)
        _scale: float = 4.0
        try:
            _v = float(_scale_env)
            if 1.0 <= _v <= 6.0:
                _scale = _v
        except (ValueError, TypeError):
            pass
        self._scale: float = _scale
        # Detect monitor size (BLOQUE 58.36f: full-monitor window)
        try:
            _di = pygame.display.Info()
            _monitor_w, _monitor_h = int(_di.current_w), int(_di.current_h)
        except Exception:
            _monitor_w, _monitor_h = WINDOW_W, WINDOW_H
        # Window = full monitor (or fallback WINDOW_WxH)
        self._window_w: int = _monitor_w
        self._window_h: int = _monitor_h
        # Game area: filled-height, centered horizontally
        self._game_w: int = max(_IW, int(_IW * _scale))
        self._game_h: int = max(_IH, int(_IH * _scale))
        self._game_x: int = (self._window_w - self._game_w) // 2
        self._game_y: int = 0
        try:
            self.screen: pygame.Surface = pygame.display.set_mode(
                (self._window_w, self._window_h),
                pygame.RESIZABLE,
            )
        except pygame.error:
            self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
            self._window_w, self._window_h = WINDOW_W, WINDOW_H
            self._game_x = 0
        # BLOQUE 31: center the window on screen so it doesn't open off-screen
        try:
            _info = pygame.display.get_desktop_sizes() if hasattr(pygame.display, "get_desktop_sizes") else None
            if _info:
                _sw, _sh = _info[0]
                _ox = max(0, (_sw - self._window_w) // 2)
                _oy = max(0, (_sh - self._window_h) // 2)
                _os.environ["SDL_VIDEO_WINDOW_POS"] = f"{_ox},{_oy}"
                # Re-apply position by re-setting the window mode
                try:
                    self.screen = pygame.display.set_mode(
                        (self._window_w, self._window_h),
                        pygame.RESIZABLE,
                    )
                except pygame.error:
                    pass
        except Exception:
            pass
        # BLOQUE 58.36f: build the side-panel starfield. Fills the side
        # panels (left + right of the game area) with stars + slow downward
        # drift. This makes the side panels look like an extension of the
        # game's space background instead of black voids.
        self._side_panel: pygame.Surface = self._build_side_panel(
            self._window_w, self._window_h, self._game_w, self._game_x,
        )
        self._side_drift: float = 0.0
        # Internal rendering surface: 320x480 (INTERNAL_W x INTERNAL_H).
        # This is what every scene draws to.
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

    def _build_side_panel(
        self, window_w: int, window_h: int, game_w: int, game_x: int,
    ) -> pygame.Surface:
        """BLOQUE 58.36f: build a starfield surface for the side panels.

        The surface is window_w x window_h. The center game_w columns are
        left BLACK (the game area is drawn on top each frame). The left
        and right side panels are filled with 3 layers of stars:
          - Layer 1: tiny dim stars, ~1200 total, slow drift
          - Layer 2: brighter 1px stars, ~240 total, medium drift
          - Layer 3: 8 large + (5-pixel) feature stars
        All layers drift DOWN (matching the game's vertical scroll), so
        the side panels feel like an extension of the game space.
        Stars are placed deterministically (seeded random).
        """
        import random
        surf = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 255))  # pure black background
        # Game area columns are left black; only the side panels get stars
        left_w = game_x
        right_x = game_x + game_w
        right_w = window_w - right_x
        if left_w <= 0 and right_w <= 0:
            return surf  # no side panels (game fills the whole window)
        # Seed: deterministic starfield
        rng = random.Random(0xDEADBEEF)
        # ---- Layer 1: tiny dim background stars ----
        layer1_color = (90, 100, 130, 180)  # dim blue-white
        n_layer1 = 1200
        for _ in range(n_layer1):
            if rng.random() < 0.5 and left_w > 0:
                x = rng.randint(0, left_w - 1)
            elif right_w > 0:
                x = rng.randint(right_x, window_w - 1)
            else:
                continue
            y = rng.randint(0, window_h - 1)
            surf.set_at((x, y), layer1_color)
        # ---- Layer 2: brighter 1px stars (color variety) ----
        layer2_colors = [
            (200, 220, 255, 230),
            (255, 240, 200, 220),
            (255, 200, 200, 200),
            (180, 230, 255, 240),
        ]
        n_layer2 = 240
        for _ in range(n_layer2):
            if rng.random() < 0.5 and left_w > 0:
                x = rng.randint(0, left_w - 1)
            elif right_w > 0:
                x = rng.randint(right_x, window_w - 1)
            else:
                continue
            y = rng.randint(0, window_h - 1)
            color = rng.choice(layer2_colors)
            surf.set_at((x, y), color)
            if rng.random() < 0.5:
                halo = (color[0] // 3, color[1] // 3, color[2] // 3, 80)
                surf.set_at((x, y), halo)
        # ---- Layer 3: large + (5-pixel) feature stars ----
        for _ in range(8):
            if rng.random() < 0.5 and left_w > 0:
                x = rng.randint(2, left_w - 3)
            elif right_w > 0:
                x = rng.randint(right_x + 2, window_w - 3)
            else:
                continue
            y = rng.randint(2, window_h - 3)
            color = (255, 255, 255, 240)
            surf.set_at((x, y), color)
            dim = (color[0] // 2, color[1] // 2, color[2] // 2, 150)
            surf.set_at((x - 1, y), dim)
            surf.set_at((x + 1, y), dim)
            surf.set_at((x, y - 1), dim)
            surf.set_at((x, y + 1), dim)
        return surf

    def _present(self) -> None:
        """BLOQUE 58.36f: scale + blit the game to the center of the screen
        and draw the side panel starfield on the left/right.
        """
        # Clear the display first
        self.screen.fill((0, 0, 0))
        # Drift the side panel starfield (parallax, downward)
        self._side_drift = (self._side_drift + 0.5) % self._window_h
        drift_y = int(self._side_drift)
        # Blit the side panel starfield, scrolled by drift amount
        self.screen.blit(self._side_panel, (0, drift_y))
        if drift_y > 0:
            # Wrap the top portion that scrolled off
            self.screen.blit(self._side_panel, (0, drift_y - self._window_h))
        # Scale the internal game surface to the game area (centered)
        scaled = pygame.transform.scale(
            self.internal,
            (self._game_w, self._game_h),
        )
        self.screen.blit(scaled, (self._game_x, self._game_y))
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
