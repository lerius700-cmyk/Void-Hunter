"""Scene state machine."""
from __future__ import annotations

import pygame


class SceneName:
    TITLE = "title"
    GAMEPLAY = "gameplay"
    BOSS_FIGHT = "boss_fight"
    ACT_CLEARED = "act_cleared"
    GAME_OVER = "game_over"


class Scene:
    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...
    def update(self, dt: float, events: list[pygame.event.Event]) -> None: ...
    def draw(self, surface: pygame.Surface) -> None: ...
    def next_scene(self) -> "Scene | None": ...


class SceneManager:
    def __init__(self, initial_scene: Scene) -> None:
        self.current: Scene = initial_scene
        self.current_state: str = initial_scene.name
        self.current.on_enter()

    def update(self, dt: float, events: list[pygame.event.Event]) -> None:
        self.current.update(dt, events)
        nxt = self.current.next_scene()
        if nxt is not None:
            self.transition_to(nxt)

    def draw(self, surface: pygame.Surface) -> None:
        self.current.draw(surface)

    def transition_to(self, scene: Scene) -> None:
        self.current.on_exit()
        self.current = scene
        self.current_state = scene.name
        self.current.on_enter()
