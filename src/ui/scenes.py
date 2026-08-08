"""Concrete scenes for the 9 game states (BLOQUE 14)."""
from __future__ import annotations

from typing import Callable, Optional

import pygame

from src.core.scene_manager import GameState, Scene
from src.utils.palette import PALETTE


# Type alias for scene constructor
TransitionFn = Callable[[GameState], None]


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
        # Title text
        font = pygame.font.Font(None, 64)
        title = font.render("VOID HUNTER", True, (220, 220, 255))
        target.blit(title, (target.get_width() // 2 - title.get_width() // 2, 100))
        # Subtitle
        font2 = pygame.font.Font(None, 24)
        sub = font2.render("PRESS ENTER TO START", True, (180, 180, 200))
        # Blink
        if int(self._t * 2) % 2 == 0:
            target.blit(sub, (target.get_width() // 2 - sub.get_width() // 2, 220))
        # Credits hint
        sub2 = font2.render("C: CREDITS", True, (120, 120, 140))
        target.blit(sub2, (target.get_width() // 2 - sub2.get_width() // 2, 260))


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
        font = pygame.font.Font(None, 56)
        text = font.render(f"ACT {self._act}", True, (255, 220, 100))
        target.blit(text, (target.get_width() // 2 - text.get_width() // 2, 120))
        # Boss name
        font2 = pygame.font.Font(None, 28)
        boss_names = {1: "GOLIATH AWAITS", 2: "HYDRA EMERGES", 3: "PHANTOM & NEMESIS"}
        sub = font2.render(boss_names.get(self._act, ""), True, (220, 80, 80))
        target.blit(sub, (target.get_width() // 2 - sub.get_width() // 2, 200))


class GameplayScene(Scene):
    """GAMEPLAY — main action scene. Wires up pools + systems + player.

    For BLOQUE 14, this is a stub that draws the player and ticks the
    fixed timestep. Full integration (enemies, waves, scoring) lands
    in BLOQUE 16.
    """

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        from src.entities.player import Player
        from src.systems.parallax import ParallaxBackground
        self._player = Player()
        self._bg = ParallaxBackground(rng_seed=42)
        self._t: float = 0.0

    def on_enter(self) -> None:
        self._player.reset()
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        # Input
        keys = pygame.key.get_pressed()
        self._player.input_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        self._player.input_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_j:
                self._player.input_fire = True
            elif event.key == pygame.K_k:
                self._player.input_dash = True
            elif event.key == pygame.K_l:
                self._player.input_bomb = True
            elif event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.PAUSE)
        # Update systems
        self._player.update(dt)
        self._bg.update(dt)
        # Reset one-shot inputs
        self._player.input_fire = False
        self._player.input_dash = False
        self._player.input_bomb = False

    def draw(self, target: pygame.Surface) -> None:
        # Background
        self._bg.draw(target)
        # Player
        surf = pygame.Surface((18, 16), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (220, 240, 255), [(9, 0), (0, 16), (18, 16)])
        pygame.draw.polygon(surf, (255, 100, 100), [(9, 4), (4, 14), (14, 14)])
        # Apply tilt
        rotated = pygame.transform.rotate(surf, -self._player.current_tilt)
        rect = rotated.get_rect(center=(int(self._player.x), int(self._player.y)))
        target.blit(rotated, rect)


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
        # Warning
        font = pygame.font.Font(None, 64)
        text = font.render(f"WARNING: {self._boss_name}", True, (255, 220, 100))
        target.blit(text, (target.get_width() // 2 - text.get_width() // 2, 140))


class BossFightScene(Scene):
    """BOSS_FIGHT — boss arena. Stub for BLOQUE 14; full integration later."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to

    def update(self, dt: float) -> None:
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.PAUSE)
            elif event.key == pygame.K_RETURN:
                self._transition_to(GameState.ACT_CLEARED)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((20, 0, 0))
        font = pygame.font.Font(None, 32)
        text = font.render("BOSS FIGHT (stub — full integration in BLOQUE 16)", True, (255, 100, 100))
        target.blit(text, (target.get_width() // 2 - text.get_width() // 2, 100))


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
        font = pygame.font.Font(None, 64)
        text = font.render("ACT CLEARED!", True, (255, 220, 100))
        target.blit(text, (target.get_width() // 2 - text.get_width() // 2, 100))
        font2 = pygame.font.Font(None, 28)
        sub = font2.render("+25000 PTS", True, (255, 180, 40))
        target.blit(sub, (target.get_width() // 2 - sub.get_width() // 2, 200))


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
        font = pygame.font.Font(None, 72)
        text = font.render("GAME OVER", True, (255, 60, 40))
        target.blit(text, (target.get_width() // 2 - text.get_width() // 2, 140))


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
        font = pygame.font.Font(None, 80)
        text = font.render("VICTORY!", True, (255, 220, 100))
        target.blit(text, (target.get_width() // 2 - text.get_width() // 2, 140))


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
        font = pygame.font.Font(None, 36)
        lines = [
            "VOID HUNTER",
            "",
            "A shmup by Lerius",
            "",
            "Built on Pygame 2.6 + Python 3.11",
            "120 FPS lock",
            "Zero external deps (numpy/scipy prohibited)",
            "",
            "Thanks to: Cave, Touhou, Ikaruga, DoDonPachi,",
            "Gradius, R-Type, Metal Slug, Devil May Cry",
            "",
            f"Run time: {int(self._t)}s",
            "",
            "PRESS ENTER TO RETURN TO TITLE",
        ]
        for i, line in enumerate(lines):
            text = font.render(line, True, (200, 200, 220))
            target.blit(text, (target.get_width() // 2 - text.get_width() // 2, 60 + i * 40))


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
        font = pygame.font.Font(None, 64)
        text = font.render("PAUSED", True, (255, 255, 255))
        target.blit(text, (target.get_width() // 2 - text.get_width() // 2, 140))
        font2 = pygame.font.Font(None, 24)
        sub = font2.render("ESC to resume", True, (200, 200, 200))
        target.blit(sub, (target.get_width() // 2 - sub.get_width() // 2, 220))

