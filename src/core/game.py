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

    @staticmethod
    def _detect_work_area() -> tuple[int, int, int, int]:
        """BLOQUE 58.36g-taskbar: return (x, y, w, h) of the primary
        monitor's WORK AREA (screen area minus the taskbar and any
        docked toolbars). Uses SPI_GETWORKAREA on Windows; falls back
        to a hard-coded reasonable default on other platforms.

        For an LG 4480x1080 ultrawide with a 48px bottom taskbar, this
        returns (0, 0, 4480, 1032). Without this, the window would be
        sized to the full 1080px height and the bottom edge would slip
        behind the taskbar.
        """
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                rect = wintypes.RECT()
                ok = user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
                if ok and rect.right > rect.left and rect.bottom > rect.top:
                    return (rect.left, rect.top,
                            rect.right - rect.left, rect.bottom - rect.top)
            except Exception:
                pass
        # Fallback: hard-coded reasonable default. We avoid creating a
        # pygame display here because that would change the SDL video
        # driver state mid-init.
        return (0, 0, 1920, 1080)

    def __init__(self, easy: bool = False) -> None:
        if not pygame.get_init():
            pygame.init()
        # BLOQUE 29: enable mouse + show cursor for mouse aiming
        try:
            pygame.mouse.set_visible(True)
        except pygame.error:
            pass
        # BLOQUE 58.36g-taskbar: detect the Windows WORK AREA (screen area
        # excluding the taskbar). For an LG 4480x1080 ultrawide with the
        # taskbar at the bottom, the work area is typically 4480x1032.
        # We size the window to fit the work-area height exactly and
        # center it horizontally on the work area, so:
        #   - top + bottom edges reach the LG monitor's USABLE edges
        #   - the window never overlaps the taskbar
        #   - mouse coords map to game coords 1:1 (reticle works)
        _work_x, _work_y, _work_w, _work_h = self._detect_work_area()
        # Get requested scale from env var (BLOQUE 31: --scale CLI flag).
        # BLOQUE 58.35: int 1..6; BLOQUE 58.36g: float 1.0..6.0.
        import os as _os
        from src.core.settings import INTERNAL_W as _IW, INTERNAL_H as _IH
        _scale_env = _os.environ.get("VOID_HUNTER_SCALE", "")
        _scale: float = 4.0
        try:
            _v = float(_scale_env)
            if 1.0 <= _v <= 6.0:
                _scale = _v
        except (ValueError, TypeError):
            pass
        # Cap scale at what fits the work area (with 2% safety margin so
        # the window border doesn't clip). For LG 1032-tall work area:
        # max scale = 1032/480 = 2.15; default --scale 3 (4.0) gets capped.
        _fit_h = (_work_h * 0.98) / _IH
        _fit_w = (_work_w * 0.98) / _IW
        _scale = max(1.0, min(_scale, _fit_h, _fit_w))
        self._scale: float = _scale
        # Window: vertical rectangle (portrait), exact fit to work area.
        _ww: int = int(_IW * _scale)
        _wh: int = int(_IH * _scale)
        # Center within the work area (NOT the full monitor — using work
        # area means the window is centered between the left/right edges
        # of the usable screen, not the full ultrawide).
        _ox = _work_x + (_work_w - _ww) // 2
        _oy = _work_y  # top of work area (above taskbar)
        # Create the window at the exact requested size. We do NOT pass
        # pygame.SCALED here because that flag tells SDL to scale the
        # window to fit the desktop, which would change the actual window
        # size from what we requested and break the mouse-to-game coord
        # mapping (the reticle would land at the wrong position).
        try:
            self.screen: pygame.Surface = pygame.display.set_mode(
                (_ww, _wh),
                pygame.RESIZABLE,
            )
        except pygame.error:
            self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
            _ww, _wh = WINDOW_W, WINDOW_H
        # Move + size the OS window to the work-area-centered position.
        # SDL_VIDEO_WINDOW_POS is unreliable when set after init (the env
        # var only takes effect for the NEXT window creation), so we use
        # the Win32 SetWindowPos API directly via pygame's WM info.
        if sys.platform == "win32":
            try:
                import ctypes
                _hwnd = pygame.display.get_wm_info().get("window")
                if _hwnd:
                    _SWP_NOZORDER = 0x0004
                    _SWP_SHOWWINDOW = 0x0040
                    ctypes.windll.user32.SetWindowPos(
                        int(_hwnd), 0, int(_ox), int(_oy),
                        int(_ww), int(_wh),
                        _SWP_NOZORDER | _SWP_SHOWWINDOW,
                    )
            except Exception:
                pass
        # Internal rendering surface: 320x480 (INTERNAL_W x INTERNAL_H).
        # Every scene draws to this; the display surface gets the internal
        # surface scaled to fill it (uniformly).
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
        # BLOQUE 58.46: session-level score that survives scene transitions
        # (gameplay → boss → act_cleared). The new boss/act-cleared runtime
        # would otherwise start at 0, losing the player's accumulated score.
        self.session_score: int = 0
        self._register_scenes()
        self._running: bool = True
        self._accumulator: float = 0.0
        # BLOQUE 58.57: trigger the initial scene's on_enter from __init__.
        # main.py's _cmd_play uses an inline loop that does NOT call
        # Game.run(), so on_enter must run here. Without this, the title
        # scene's on_enter side effects (most importantly: START MUSIC) never
        # fire and the user gets a silent title screen. Symptom was reported
        # 5+ times; root cause was that Game.run()'s on_enter trigger was
        # bypassed by main.py's inline loop.
        self._trigger_initial_on_enter()

    def _trigger_initial_on_enter(self) -> None:
        """Call on_enter on whichever scene SceneManager starts in.

        SceneManager.__init__ sets current_state but never calls on_enter —
        that only happens on transitions. We need it to run once at game
        start so the title scene starts its music, spawns ships, etc.
        Idempotent and safe to call multiple times (each scene's on_enter
        is expected to be re-entrant on first call only).
        """
        try:
            with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
                _f.write(
                    f"_trigger_initial_on_enter: "
                    f"current_state={self.scenes.current_state}, "
                    f"overlay_stack={self.scenes.overlay_stack}\n"
                )
        except Exception:
            pass
        if (self.scenes.current_state in self.scenes.scenes
                and not self.scenes.overlay_stack):
            scene = self.scenes.scenes[self.scenes.current_state]
            if scene is not None:
                try:
                    with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
                        _f.write(f"  calling on_enter on {type(scene).__name__}\n")
                except Exception:
                    pass
                scene.on_enter()

    # ------------------------------------------------------------------
    # BLOQUE 58.46: session score carry-over
    # ------------------------------------------------------------------
    def _set_session_score(self, score: int) -> None:
        """Update the session score (called by GameplayScene.on_exit)."""
        self.session_score = score

    def _get_session_score(self) -> int:
        """Read the current session score (called by BossFightScene / ActClearedScene)."""
        return self.session_score

    def _present(self) -> None:
        """Scale the internal 320x480 surface to the display and present."""
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
        # BLOQUE 58.46: pass session_score callbacks so the score carries
        # over between gameplay, boss, and act_cleared scenes.
        self.scenes.register_scene(
            GameState.GAMEPLAY,
            GameplayScene(transition_to, audio=self.audio,
                          set_session_score=self._set_session_score),
        )
        # BLOQUE 58.23: pass the shared audio engine to BOSS_INTRO and
        # SUB_BOSS_INTRO. The previous versions did `AudioEngine()` in
        # on_enter, which re-initialized pygame.mixer and re-baked all
        # SFX + BGM (~1.2s freeze) right when the wave cleared.
        self.scenes.register_scene(GameState.BOSS_INTRO, BossIntroScene(transition_to, audio=self.audio))
        self.scenes.register_scene(
            GameState.BOSS_FIGHT,
            BossFightScene(transition_to, act=1, audio=self.audio,
                           get_session_score=self._get_session_score,
                           set_session_score=self._set_session_score),
        )
        self.scenes.register_scene(
            GameState.ACT_CLEARED,
            ActClearedScene(transition_to,
                            get_session_score=self._get_session_score,
                            set_session_score=self._set_session_score),
        )
        self.scenes.register_scene(
            GameState.GAME_OVER,
            GameOverScene(transition_to,
                          get_session_score=self._get_session_score,
                          set_session_score=self._set_session_score),
        )
        self.scenes.register_scene(GameState.VICTORY, VictoryScene(transition_to))
        self.scenes.register_scene(GameState.CREDITS, CreditsScene(transition_to))
        # BLOQUE 50: sub-boss mid-wave warning (yellow)
        self.scenes.register_scene(GameState.SUB_BOSS_INTRO, SubBossIntroScene(transition_to, audio=self.audio))
        self.scenes.register_scene(GameState.PAUSE, PauseScene(transition_to))

    def run(self) -> int:
        """Main loop with fixed-timestep accumulator (120 FPS)."""
        # BLOQUE 58.51: explicitly trigger on_enter for the initial scene
        # (TITLE). SceneManager.__init__ sets current_state=TITLE but
        # never calls on_enter — that only happens on transitions. Without
        # this, the title scene runs draw() (with lazy ship spawn in
        # update()) but on_enter's side effects (init parallax, spawn
        # ships, START MUSIC) never run. Symptom: no music, ships appear
        # only via the update() fallback, and the title feels broken.
        try:
            with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
                _f.write(f"Game.run() entered, current_state={self.scenes.current_state}\n")
        except Exception:
            pass
        if (self.scenes.current_state in self.scenes.scenes
                and not self.scenes.overlay_stack):
            scene = self.scenes.scenes[self.scenes.current_state]
            if scene is not None:
                try:
                    with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
                        _f.write(f"  calling on_enter on {type(scene).__name__}\n")
                except Exception:
                    pass
                scene.on_enter()
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
