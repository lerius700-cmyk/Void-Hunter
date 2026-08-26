"""Tests for src.core.scene_manager + game state machine (BLOQUE 14)."""
from __future__ import annotations

import pytest

from src.core.scene_manager import (
    GameState,
    Scene,
    SceneManager,
    StateError,
    VALID_TRANSITIONS,
)


@pytest.fixture
def sm() -> SceneManager:
    return SceneManager()


class _MockScene(Scene):
    def __init__(self) -> None:
        self.entered = False
        self.exited = False
        self.updates = 0
        self.draws = 0

    def on_enter(self) -> None:
        self.entered = True

    def update(self, dt: float) -> None:
        self.updates += 1

    def draw(self, target) -> None:
        self.draws += 1

    def on_exit(self) -> None:
        self.exited = True


# ---------------------------------------------------------------------------
# 1. 10 states (9 main + PAUSE overlay)
# ---------------------------------------------------------------------------
def test_ten_states_total() -> None:
    """BLOQUE 58.59: 12 states now (added CINEMATIC for the ship zoom video)."""
    assert len(GameState) == 12


def test_valid_transitions_table_populated() -> None:
    """BLOQUE 58.59: 12 states have transition entries; PAUSE is overlay-only."""
    assert len(VALID_TRANSITIONS) == 12
    # Spot check
    assert GameState.TITLE in VALID_TRANSITIONS
    assert GameState.CINEMATIC in VALID_TRANSITIONS
    assert GameState.GAMEPLAY in VALID_TRANSITIONS
    assert GameState.BOSS_FIGHT in VALID_TRANSITIONS


# ---------------------------------------------------------------------------
# 2. Register + transition
# ---------------------------------------------------------------------------
def test_register_scene(sm: SceneManager) -> None:
    scene = _MockScene()
    sm.register_scene(GameState.TITLE, scene)
    assert sm.scenes[GameState.TITLE] is scene


def test_transition_calls_on_exit_and_on_enter(sm: SceneManager) -> None:
    title = _MockScene()
    intro = _MockScene()
    sm.register_scene(GameState.TITLE, title)
    sm.register_scene(GameState.ACT_INTRO, intro)
    # Initial state is TITLE; we need to call on_enter manually for the initial.
    title.on_enter()
    sm.transition_to(GameState.ACT_INTRO)
    assert title.exited is True
    assert intro.entered is True


def test_invalid_transition_raises(sm: SceneManager) -> None:
    title = _MockScene()
    sm.register_scene(GameState.TITLE, title)
    title.on_enter()
    # TITLE -> BOSS_FIGHT is invalid
    with pytest.raises(StateError):
        sm.transition_to(GameState.BOSS_FIGHT)


def test_valid_transition_path(sm: SceneManager) -> None:
    """TITLE -> ACT_INTRO -> GAMEPLAY -> BOSS_INTRO -> BOSS_FIGHT."""
    sm.register_scene(GameState.TITLE, _MockScene())
    sm.register_scene(GameState.ACT_INTRO, _MockScene())
    sm.register_scene(GameState.GAMEPLAY, _MockScene())
    sm.register_scene(GameState.BOSS_INTRO, _MockScene())
    sm.register_scene(GameState.BOSS_FIGHT, _MockScene())
    sm.scenes[GameState.TITLE].on_enter()
    sm.transition_to(GameState.ACT_INTRO)
    assert sm.current_state == GameState.ACT_INTRO
    sm.transition_to(GameState.GAMEPLAY)
    sm.transition_to(GameState.BOSS_INTRO)
    sm.transition_to(GameState.BOSS_FIGHT)
    assert sm.current_state == GameState.BOSS_FIGHT


# ---------------------------------------------------------------------------
# 3. Overlay (PAUSE)
# ---------------------------------------------------------------------------
def test_push_overlay(sm: SceneManager) -> None:
    scene = _MockScene()
    sm.push_overlay(scene)
    assert sm.is_overlay_active() is True
    assert scene.entered is True


def test_pop_overlay(sm: SceneManager) -> None:
    scene = _MockScene()
    sm.push_overlay(scene)
    popped = sm.pop_overlay()
    assert popped is scene
    assert scene.exited is True
    assert not sm.is_overlay_active()


def test_pop_overlay_when_empty(sm: SceneManager) -> None:
    assert sm.pop_overlay() is None


def test_update_routes_to_overlay_first(sm: SceneManager) -> None:
    base = _MockScene()
    overlay = _MockScene()
    sm.register_scene(GameState.GAMEPLAY, base)
    sm.push_overlay(overlay)
    sm.update(0.016)
    # Overlay gets update, not base
    assert overlay.updates == 1
    assert base.updates == 0


def test_draw_composites_overlay_on_top(sm: SceneManager) -> None:
    base = _MockScene()
    overlay = _MockScene()
    sm.register_scene(GameState.TITLE, _MockScene())
    sm.register_scene(GameState.GAMEPLAY, base)
    sm.scenes[GameState.TITLE].on_enter()
    sm.transition_to(GameState.ACT_INTRO)
    sm.transition_to(GameState.GAMEPLAY)
    sm.push_overlay(overlay)
    sm.draw(None)
    assert base.draws == 1
    assert overlay.draws == 1


# ---------------------------------------------------------------------------
# 4. Reset
# ---------------------------------------------------------------------------
def test_reset_returns_to_title(sm: SceneManager) -> None:
    sm.register_scene(GameState.TITLE, _MockScene())
    sm.scenes[GameState.TITLE].on_enter()
    sm.transition_to(GameState.ACT_INTRO)
    sm.reset()
    assert sm.current_state == GameState.TITLE


def test_reset_clears_overlays(sm: SceneManager) -> None:
    overlay = _MockScene()
    sm.push_overlay(overlay)
    sm.reset()
    assert not sm.is_overlay_active()
    assert overlay.exited is True


# ---------------------------------------------------------------------------
# 5. Specific transitions from spec
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("from_state,to_state", [
    (GameState.TITLE, GameState.ACT_INTRO),
    (GameState.ACT_INTRO, GameState.GAMEPLAY),
    (GameState.GAMEPLAY, GameState.BOSS_INTRO),
    (GameState.BOSS_INTRO, GameState.BOSS_FIGHT),
    (GameState.BOSS_FIGHT, GameState.ACT_CLEARED),
    (GameState.ACT_CLEARED, GameState.ACT_INTRO),
    (GameState.ACT_CLEARED, GameState.VICTORY),
    (GameState.GAME_OVER, GameState.TITLE),
    (GameState.VICTORY, GameState.CREDITS),
    (GameState.CREDITS, GameState.TITLE),
])
def test_spec_transitions_are_valid(from_state: GameState, to_state: GameState) -> None:
    """GDD §13: the spec transition table."""
    assert to_state in VALID_TRANSITIONS[from_state]


# ---------------------------------------------------------------------------
# 6. Same-state transition is no-op
# ---------------------------------------------------------------------------
def test_same_state_transition_is_noop(sm: SceneManager) -> None:
    title = _MockScene()
    sm.register_scene(GameState.TITLE, title)
    sm.scenes[GameState.TITLE].on_enter()
    sm.transition_to(GameState.TITLE)
    assert sm.current_state == GameState.TITLE
    # on_exit should NOT have been called
    assert title.exited is False
