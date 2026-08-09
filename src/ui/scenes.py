"""Concrete scenes for the 9 game states (BLOQUE 14).

All fonts are sized for the 240x360 internal surface (the screen is
scaled 4x to 960x1440 by Game._present). 240px width is the hard cap.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

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

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.ACT_INTRO)
            elif event.key == pygame.K_c:
                self._transition_to(GameState.CREDITS)

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
    """BOSS_INTRO — boss warning, 4-6s animated intro."""

    def __init__(self, transition_to: TransitionFn, boss_name: str = "BOSS") -> None:
        self._transition_to = transition_to
        self._boss_name = boss_name
        self._t: float = 0.0
        self._duration: float = 5.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.BOSS_FIGHT)
        if self._t >= self._duration:
            self._transition_to(GameState.BOSS_FIGHT)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((40, 0, 0))
        # Warning — 18px to fit "WARNING: <boss_name>" in 240px
        font = pygame.font.Font(None, 18)
        text = font.render(f"WARNING: {self._boss_name}", True, (255, 220, 100))
        _center_blit(target, text, 140)
        # Subtitle (blinking)
        font2 = pygame.font.Font(None, 12)
        if int(self._t * 2) % 2 == 0:
            sub = font2.render("INCOMING HOSTILE", True, (255, 100, 100))
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
