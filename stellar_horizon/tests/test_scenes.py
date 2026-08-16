# stellar_horizon/tests/test_scenes.py
import pytest
import pygame

from stellar_horizon.core.scene_manager import Scene, SceneManager, SceneName


class CountingScene(Scene):
    def __init__(self, name):
        self.name = name
        self.entered = 0
        self.exited = 0
        self.updates = 0
        self.draws = 0
        self.next = None

    def on_enter(self):
        self.entered += 1

    def on_exit(self):
        self.exited += 1

    def update(self, dt, events):
        self.updates += 1

    def draw(self, surface):
        self.draws += 1

    def next_scene(self):
        return self.next


def test_scene_name_constants():
    assert SceneName.TITLE == "title"
    assert SceneName.GAMEPLAY == "gameplay"
    assert SceneName.BOSS_FIGHT == "boss_fight"
    assert SceneName.ACT_CLEARED == "act_cleared"
    assert SceneName.GAME_OVER == "game_over"


def test_scene_manager_starts_at_title():
    title = CountingScene(SceneName.TITLE)
    sm = SceneManager(title)
    assert sm.current_state == SceneName.TITLE


def test_scene_manager_calls_on_enter_on_start():
    title = CountingScene(SceneName.TITLE)
    SceneManager(title)
    assert title.entered == 1


def test_scene_manager_update_calls_scene_update():
    title = CountingScene(SceneName.TITLE)
    sm = SceneManager(title)
    sm.update(0.1, [])
    assert title.updates == 1


def test_scene_manager_draw_calls_scene_draw():
    title = CountingScene(SceneName.TITLE)
    sm = SceneManager(title)
    sm.draw(pygame.Surface((10, 10)))
    assert title.draws == 1


def test_scene_manager_transitions_when_next_scene_set():
    title = CountingScene(SceneName.TITLE)
    gameplay = CountingScene(SceneName.GAMEPLAY)
    title.next = gameplay
    sm = SceneManager(title)
    sm.update(0.1, [])
    assert sm.current_state == SceneName.GAMEPLAY
    assert title.exited == 1
    assert gameplay.entered == 1


def test_scene_manager_explicit_transition_to():
    title = CountingScene(SceneName.TITLE)
    gameplay = CountingScene(SceneName.GAMEPLAY)
    sm = SceneManager(title)
    sm.transition_to(gameplay)
    assert sm.current_state == SceneName.GAMEPLAY
    assert title.exited == 1
