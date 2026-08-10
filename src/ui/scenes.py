"""Concrete scenes for the 9 game states (BLOQUE 14).

All fonts are sized for the 240x360 internal surface (the screen is
scaled 4x to 960x1440 by Game._present). 240px width is the hard cap.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional
import math

import pygame

from src.core.scene_manager import GameState, Scene
from src.utils.palette import PALETTE


# Type alias for scene constructor
TransitionFn = Callable[[GameState], None]

if TYPE_CHECKING:
    from src.audio.synth import AudioEngine


def _center_blit(
    target: pygame.Surface,
    text_surface: pygame.Surface,
    y: int,
) -> None:
    """Blit a surface centered horizontally at the given y on target."""
    x = target.get_width() // 2 - text_surface.get_width() // 2
    target.blit(text_surface, (x, y))


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap text to fit max_width, breaking on spaces or at hard char limits."""
    if font.size(text)[0] <= max_width:
        return [text]
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            # Hard-break words longer than max_width
            while font.size(word)[0] > max_width and len(word) > 1:
                # Binary search largest prefix that fits
                lo, hi = 1, len(word)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if font.size(word[:mid])[0] <= max_width:
                        lo = mid
                    else:
                        hi = mid - 1
                lines.append(word[:lo])
                word = word[lo:]
            current = word
    if current:
        lines.append(current)
    return lines


class TitleScene(Scene):
    """TITLE — main menu, void logo, 'PRESS ENTER TO START'."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        # BLOQUE 46: auto-start after 3s if user hasn't pressed anything
        # (fix for "user doesn't realize they need to press Enter")
        self._auto_start_s: float = 3.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.ACT_INTRO)
            elif event.key == pygame.K_c:
                self._transition_to(GameState.CREDITS)
        # Auto-start if user idle
        if self._t >= self._auto_start_s:
            self._transition_to(GameState.ACT_INTRO)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        # Title — 32px sized to fit "VOID HUNTER" in 240px
        font = pygame.font.Font(None, 32)
        title = font.render("VOID HUNTER", True, (220, 220, 255))
        _center_blit(target, title, 100)
        # Subtitle
        font2 = pygame.font.Font(None, 14)
        sub = font2.render("PRESS ENTER TO START", True, (180, 180, 200))
        # Blink
        if int(self._t * 2) % 2 == 0:
            _center_blit(target, sub, 200)
        # BLOQUE 46: auto-start countdown
        if self._t < self._auto_start_s:
            remaining = int(self._auto_start_s - self._t) + 1
            auto = font2.render(f"AUTO-START IN {remaining}s", True, (140, 140, 160))
            _center_blit(target, auto, 220)
        else:
            auto = font2.render("STARTING...", True, (180, 220, 180))
            _center_blit(target, auto, 220)
        # Credits hint
        sub2 = font2.render("C: CREDITS", True, (120, 120, 140))
        _center_blit(target, sub2, 230)


class ActIntroScene(Scene):
    """ACT_INTRO — 'ACT N' title + boss portrait placeholder."""

    def __init__(self, transition_to: TransitionFn, act: int = 1) -> None:
        self._transition_to = transition_to
        self._act = act
        self._t: float = 0.0
        self._duration: float = 4.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.GAMEPLAY)
        if self._t >= self._duration:
            self._transition_to(GameState.GAMEPLAY)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        font = pygame.font.Font(None, 40)
        text = font.render(f"ACT {self._act}", True, (255, 220, 100))
        _center_blit(target, text, 120)
        # Boss name — 18px fits "GOLIATH AWAITS" comfortably
        font2 = pygame.font.Font(None, 18)
        boss_names = {1: "GOLIATH AWAITS", 2: "HYDRA EMERGES", 3: "PHANTOM & NEMESIS"}
        sub = font2.render(boss_names.get(self._act, ""), True, (220, 80, 80))
        _center_blit(target, sub, 200)


class GameplayScene(Scene):
    """GAMEPLAY — main action scene. Delegates to GameplayRuntime.

    Runtime handles: bullets, enemies, waves, score, particles, HUD,
    boss transitions, collisions, hitstop, shake, slowmo.
    """

    def __init__(self, transition_to: "TransitionFn", act: int = 1,
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._act = act
        from src.ui.gameplay_runtime import GameplayRuntime
        self._rt = GameplayRuntime(transition_to, is_boss=False, act=act, audio=audio)

    def on_enter(self) -> None:
        self._rt.on_enter()

    def on_exit(self) -> None:
        self._rt.on_exit()

    def update(self, dt: float) -> None:
        self._rt.update(dt)

    def draw(self, target: pygame.Surface) -> None:
        self._rt.draw(target)


class BossIntroScene(Scene):
    """BOSS_INTRO — boss warning, 4-6s animated intro.

    Phases (5s total):
      0.0 - 0.3s : White flash burst, then dark red
      0.3 - 1.5s : WARNING text slides in from left/right
      1.5 - 3.5s : Boss portrait slides down from top
      3.5 - 4.5s : Pulsing red, boss locked in
      4.5 - 5.0s : Transition to fight
    """

    def __init__(self, transition_to: TransitionFn, boss_name: str = "BOSS") -> None:
        self._transition_to = transition_to
        self._boss_name = boss_name
        self._t: float = 0.0
        self._duration: float = 4.5  # slightly shorter with animation

    def on_enter(self) -> None:
        self._t = 0.0
        # Try to play boss warning SFX
        try:
            from src.audio.synth import AudioEngine
            audio = AudioEngine()
            audio.play_sfx("boss_warning", volume=0.9)
        except Exception:
            pass

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.BOSS_FIGHT)
        if self._t >= self._duration:
            self._transition_to(GameState.BOSS_FIGHT)

    def draw(self, target: pygame.Surface) -> None:
        w, h = target.get_size()
        # Phase 1: white flash burst (first 0.3s)
        if self._t < 0.3:
            target.fill((255, 255, 255))
            return
        # Background: pulsing dark red (gets more intense)
        pulse = 0.5 + 0.5 * math.sin(self._t * 6.0)
        bg_r = int(40 + pulse * 30)
        bg_g = int(0 + pulse * 5)
        bg_b = int(0)
        target.fill((bg_r, bg_g, bg_b))
        # Phase 2: WARNING text (slides in from left+right, settles center)
        # Use larger font for impact
        font = pygame.font.Font(None, 24)
        # Slide: text appears 0.3-1.5s
        text_alpha = min(1.0, max(0.0, (self._t - 0.3) / 0.3))
        warning_text = f"WARNING: {self._boss_name}"
        # Truncate if too long for 240px
        if font.size(warning_text)[0] > 220:
            # Try shorter format
            warning_text = self._boss_name
            if font.size(f"!! {warning_text} !!")[0] > 220:
                warning_text = warning_text[:10]
        warn_surf = font.render(warning_text, True, (255, 220, 100))
        warn_surf.set_alpha(int(255 * text_alpha))
        # Add a glow
        glow_surf = font.render(warning_text, True, (255, 100, 60))
        glow_surf.set_alpha(int(80 * text_alpha))
        for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            target.blit(glow_surf,
                        (w // 2 - warn_surf.get_width() // 2 + ox,
                         80 - warn_surf.get_height() // 2 + oy))
        target.blit(warn_surf,
                    (w // 2 - warn_surf.get_width() // 2,
                     80 - warn_surf.get_height() // 2))
        # Phase 3: Boss portrait slides down from top (1.5s+)
        if self._t > 1.0:
            # Boss rectangle (gray, with eye detail)
            boss_size = 32
            # Slide in: y starts at -boss_size, settles at 160
            target_y = 160
            start_y = -boss_size
            t_slide = min(1.0, (self._t - 1.0) / 0.8)
            t_eased = 1.0 - (1.0 - t_slide) ** 3  # ease-out
            boss_y = int(start_y + (target_y - start_y) * t_eased)
            boss_x = w // 2
            # Glow under boss
            glow_size = boss_size + 12
            glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            pygame.draw.rect(glow, (200, 100, 100, 60 + int(60 * pulse)),
                             (0, 0, glow_size, glow_size), border_radius=4)
            target.blit(glow, (boss_x - glow_size // 2, boss_y - glow_size // 2))
            # Boss body
            boss_rect = pygame.Rect(boss_x - boss_size // 2, boss_y - boss_size // 2 // 2,
                                    boss_size, boss_size // 2)
            pygame.draw.rect(target, (200, 100, 100), boss_rect)
            # Boss eye (white)
            eye_w = 12
            eye_h = 3
            pygame.draw.rect(target, (255, 255, 255),
                             (boss_x - eye_w // 2, boss_y - eye_h // 2, eye_w, eye_h))
            # Phase border (red, glowing)
            border_color = (255, 80, 80) if pulse > 0.5 else (200, 60, 60)
            pygame.draw.rect(target, border_color, boss_rect, 1)
        # Bottom: "INCOMING HOSTILE" subtitle (blinking)
        font2 = pygame.font.Font(None, 12)
        sub = font2.render("INCOMING HOSTILE", True, (255, 100, 100))
        if int(self._t * 2) % 2 == 0 and self._t > 0.5:
            _center_blit(target, sub, 230)
        # Progress bar (fills over duration)
        bar_w = 200
        bar_h = 4
        bar_x = (w - bar_w) // 2
        bar_y = 320
        pygame.draw.rect(target, (60, 20, 20), (bar_x, bar_y, bar_w, bar_h), 1)
        progress = min(1.0, self._t / self._duration)
        pygame.draw.rect(target, (255, 100, 100),
                         (bar_x + 1, bar_y + 1, int(bar_w * progress) - 2, bar_h - 2))
        # "PRESS ENTER TO SKIP" hint
        if self._t > 1.0:
            font3 = pygame.font.Font(None, 10)
            hint = font3.render("PRESS ENTER TO SKIP", True, (180, 180, 180))
            _center_blit(target, hint, 340)
            _center_blit(target, sub, 200)


class BossFightScene(Scene):
    """BOSS_FIGHT — boss arena. Delegates to GameplayRuntime in boss mode."""

    def __init__(self, transition_to: "TransitionFn", act: int = 1,
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._act = act
        from src.ui.gameplay_runtime import GameplayRuntime
        self._rt = GameplayRuntime(transition_to, is_boss=True, act=act, audio=audio)

    def on_enter(self) -> None:
        self._rt.on_enter()

    def on_exit(self) -> None:
        self._rt.on_exit()

    def update(self, dt: float) -> None:
        # ESC to pause; otherwise full runtime
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.PAUSE)
        self._rt.update(dt)

    def draw(self, target: pygame.Surface) -> None:
        self._rt.draw(target)


class ActClearedScene(Scene):
    """ACT_CLEARED — act boss defeated, +25000 pts, act transition."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 4.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.ACT_INTRO)
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.ACT_INTRO)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        # 28px fits "ACT CLEARED!" (12 chars) in 240px
        font = pygame.font.Font(None, 28)
        text = font.render("ACT CLEARED!", True, (255, 220, 100))
        _center_blit(target, text, 100)
        font2 = pygame.font.Font(None, 18)
        sub = font2.render("+25000 PTS", True, (255, 180, 40))
        _center_blit(target, sub, 200)


class GameOverScene(Scene):
    """GAME_OVER — 0 lives, end of run."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 5.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.TITLE)
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.TITLE)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((40, 0, 0))
        # 32px fits "GAME OVER" (9 chars) in 240px
        font = pygame.font.Font(None, 32)
        text = font.render("GAME OVER", True, (255, 60, 40))
        _center_blit(target, text, 140)


class VictoryScene(Scene):
    """VICTORY — final boss defeated, runs after NEMESIS dies."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 6.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.CREDITS)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((40, 30, 0))
        # 40px fits "VICTORY!" (8 chars) in 240px
        font = pygame.font.Font(None, 40)
        text = font.render("VICTORY!", True, (255, 220, 100))
        _center_blit(target, text, 140)


class CreditsScene(Scene):
    """CREDITS — final roll, "PRESS ENTER FOR TITLE"."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.TITLE)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        # Title (small)
        title_font = pygame.font.Font(None, 20)
        title = title_font.render("VOID HUNTER", True, (255, 220, 100))
        _center_blit(target, title, 30)
        # Body — wrap to fit 240px
        body_font = pygame.font.Font(None, 12)
        body_lines = [
            "A shmup by Lerius",
            "",
            "Built on Pygame 2.6 + Python 3.11",
            "120 FPS lock",
            "Zero external deps",
            "(numpy/scipy prohibited)",
            "",
            "Thanks to: Cave, Touhou, Ikaruga,",
            "DoDonPachi, Gradius, R-Type,",
            "Metal Slug, Devil May Cry",
            "",
            f"Run time: {int(self._t)}s",
            "",
            "PRESS ENTER FOR TITLE",
        ]
        y = 70
        for line in body_lines:
            text = body_font.render(line, True, (200, 200, 220))
            _center_blit(target, text, y)
            y += 16


class PauseScene(Scene):
    """PAUSE overlay — dim screen, 'PAUSED' text, ESC to resume."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to

    def update(self, dt: float) -> None:
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.GAMEPLAY)  # will pop overlay

    def draw(self, target: pygame.Surface) -> None:
        # Dim overlay
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 128))
        target.blit(dim, (0, 0))
        # 48px fits "PAUSED" (6 chars) in 240px
        font = pygame.font.Font(None, 48)
        text = font.render("PAUSED", True, (255, 255, 255))
        _center_blit(target, text, 140)
        font2 = pygame.font.Font(None, 14)
        sub = font2.render("ESC to resume", True, (200, 200, 200))
        _center_blit(target, sub, 220)
