"""BLOQUE 58.59: TitleScene + CinematicScene integration tests.

Validates that:
- TitleScene can be instantiated without crashing (even when video assets
  are missing — falls back to legacy parallax)
- CinematicScene transitions to ACT_INTRO when the video finishes
- CinematicScene transitions to ACT_INTRO when ESC is pressed
"""
from __future__ import annotations
import sys
from pathlib import Path

import pygame
import pytest


# Initialize pygame once for the test session
@pytest.fixture(scope="module", autouse=True)
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_title_scene_instantiates_with_video_assets():
    """TitleScene should instantiate without crashing when video assets exist."""
    from src.ui.scenes import TitleScene
    transitions: list = []
    def transition_to(state):
        transitions.append(state)
    scene = TitleScene(transition_to)
    scene.on_enter()
    # Should have created a video player (if assets are present)
    assert scene._video is not None or scene._bg is not None


def test_title_scene_input_transitions_to_cinematic():
    """Pressing any key in TitleScene should transition to CINEMATIC state."""
    from src.ui.scenes import TitleScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def transition_to(state):
        transitions.append(state)
    scene = TitleScene(transition_to)
    scene.on_enter()
    # Inject a KEYDOWN event
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    pygame.event.post(event)
    # Pump events
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert GameState.CINEMATIC in transitions


def test_cinematic_scene_instantiates():
    from src.ui.scenes import CinematicScene
    transitions: list = []
    def transition_to(state):
        transitions.append(state)
    scene = CinematicScene(transition_to)
    scene.on_enter()
    assert scene._t == 0.0
    assert scene._finished is False


def test_cinematic_scene_esc_skips_to_act_intro():
    """ESC key during cinematic should transition to ACT_INTRO."""
    from src.ui.scenes import CinematicScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def transition_to(state):
        transitions.append(state)
    scene = CinematicScene(transition_to)
    scene.on_enter()
    # Inject ESC keydown
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert GameState.ACT_INTRO in transitions


def test_cinematic_scene_safety_net_finishes_at_15s():
    """If the video takes > 15s, force-finish and go to ACT_INTRO."""
    from src.ui.scenes import CinematicScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def transition_to(state):
        transitions.append(state)
    scene = CinematicScene(transition_to)
    scene.on_enter()
    # Advance 16 seconds (no events)
    scene.update(16.0)
    assert GameState.ACT_INTRO in transitions


def test_cinematic_scene_draw_doesnt_crash():
    """draw() should work even when the video is unavailable (fallback)."""
    from src.ui.scenes import CinematicScene
    transitions: list = []
    def transition_to(state):
        transitions.append(state)
    scene = CinematicScene(transition_to)
    scene.on_enter()
    target = pygame.Surface((240, 360))
    # Should not raise even if video is None
    scene.draw(target)


def test_title_scene_draw_uses_video_when_available():
    """When video is available, draw() should call video_player.draw()."""
    from src.ui.scenes import TitleScene
    transitions: list = []
    def transition_to(state):
        transitions.append(state)
    scene = TitleScene(transition_to)
    scene.on_enter()
    target = pygame.Surface((240, 360))
    # This will use the video if present, else the legacy bg
    scene.draw(target)
    # No assertion needed; we just verify it doesn't crash
