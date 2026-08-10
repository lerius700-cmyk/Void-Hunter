"""Game state machine — 9 states with scene stack (BLOQUE 14).

Per GDD §13:
  TITLE → ACT_INTRO → GAMEPLAY → BOSS_INTRO → BOSS_FIGHT
  → ACT_CLEARED → GAME_OVER → VICTORY → CREDITS

Each state has its own Scene. SceneManager keeps a stack for overlay
scenes (PAUSE over GAMEPLAY). Transitions validate against a table.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable, Optional

import pygame


class GameState(Enum):
    TITLE = "title"
    ACT_INTRO = "act_intro"
    GAMEPLAY = "gameplay"
    BOSS_INTRO = "boss_intro"
    BOSS_FIGHT = "boss_fight"
    ACT_CLEARED = "act_cleared"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    CREDITS = "credits"
    # BLOQUE 50: mid-wave sub-boss intro scene (yellow WARNING)
    SUB_BOSS_INTRO = "sub_boss_intro"
    # Overlay state (not in main sequence, pushed onto stack)
    PAUSE = "pause"


# Valid transitions: from_state -> set of allowed to_states
VALID_TRANSITIONS: dict[GameState, set[GameState]] = {
    GameState.TITLE: {GameState.ACT_INTRO, GameState.CREDITS},
    GameState.ACT_INTRO: {GameState.GAMEPLAY, GameState.TITLE},
    GameState.GAMEPLAY: {
        GameState.BOSS_INTRO,
        GameState.SUB_BOSS_INTRO,  # BLOQUE 50
        GameState.ACT_CLEARED,
        GameState.GAME_OVER,
        GameState.PAUSE,
    },
    GameState.BOSS_INTRO: {GameState.BOSS_FIGHT, GameState.GAMEPLAY},
    GameState.BOSS_FIGHT: {GameState.ACT_CLEARED, GameState.GAME_OVER, GameState.PAUSE},
    GameState.ACT_CLEARED: {GameState.ACT_INTRO, GameState.VICTORY, GameState.TITLE},
    GameState.GAME_OVER: {GameState.TITLE, GameState.CREDITS},
    GameState.VICTORY: {GameState.CREDITS, GameState.TITLE},
    GameState.CREDITS: {GameState.TITLE},
    GameState.SUB_BOSS_INTRO: {GameState.GAMEPLAY},  # BLOQUE 50: back to gameplay with sub-boss
    GameState.PAUSE: {GameState.GAMEPLAY, GameState.BOSS_FIGHT, GameState.TITLE},
}


class StateError(Exception):
    """Raised on invalid state transition."""


class Scene:
    """Base class for scenes. Subclass and override on_enter/update/draw/on_exit."""

    def on_enter(self) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, target: pygame.Surface) -> None:
        pass

    def on_exit(self) -> None:
        pass


class SceneManager:
    """Manages current scene + overlay stack + state transitions."""

    def __init__(self) -> None:
        self.current_state: GameState = GameState.TITLE
        self.scenes: dict[GameState, Scene] = {}
        self.overlay_stack: list[Scene] = []
        self._previous_state: Optional[GameState] = None
        self._on_state_change: Optional[Callable[[GameState, GameState], None]] = None

    def register_scene(self, state: GameState, scene: Scene) -> None:
        """Register a scene for a state. Must be called before transition_into."""
        self.scenes[state] = scene

    def transition_to(self, new_state: GameState) -> None:
        """Transition to a new state. Validates against the transition table."""
        if new_state == self.current_state:
            return
        if new_state not in VALID_TRANSITIONS.get(self.current_state, set()):
            # Special case: PAUSE is a push, not a transition.
            if new_state == GameState.PAUSE:
                self.push_overlay(self.scenes.get(new_state))
                return
            raise StateError(
                f"invalid transition: {self.current_state.value} -> {new_state.value}"
            )
        # Exit current scene
        if self.current_state in self.scenes:
            self.scenes[self.current_state].on_exit()
        # Update state
        self._previous_state = self.current_state
        self.current_state = new_state
        # Enter new scene
        if new_state in self.scenes:
            self.scenes[new_state].on_enter()
        # Notify
        if self._on_state_change is not None:
            self._on_state_change(self._previous_state, new_state)

    def push_overlay(self, scene: Optional[Scene]) -> None:
        """Push a scene onto the overlay stack (e.g. PAUSE)."""
        if scene is None:
            return
        self.overlay_stack.append(scene)
        scene.on_enter()

    def pop_overlay(self) -> Optional[Scene]:
        """Pop the top overlay. Returns it."""
        if not self.overlay_stack:
            return None
        scene = self.overlay_stack.pop()
        scene.on_exit()
        return scene

    def update(self, dt: float) -> None:
        # Top overlay gets input first; underlying scene runs underneath
        if self.overlay_stack:
            self.overlay_stack[-1].update(dt)
        elif self.current_state in self.scenes:
            self.scenes[self.current_state].update(dt)

    def draw(self, target: pygame.Surface) -> None:
        if self.current_state in self.scenes:
            self.scenes[self.current_state].draw(target)
        for overlay in self.overlay_stack:
            overlay.draw(target)

    def is_overlay_active(self) -> bool:
        return len(self.overlay_stack) > 0

    def reset(self) -> None:
        """Full reset: clear overlays, return to TITLE."""
        while self.overlay_stack:
            self.pop_overlay()
        if self.current_state in self.scenes:
            self.scenes[self.current_state].on_exit()
        self.current_state = GameState.TITLE
        if GameState.TITLE in self.scenes:
            self.scenes[GameState.TITLE].on_enter()
