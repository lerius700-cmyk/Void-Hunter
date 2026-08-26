"""BLOQUE 58.60: Gallery scene tests.

Validates the in-game gallery (sprite sheets + videos) accessible
from the title screen via S / V hotkeys.
"""
from __future__ import annotations
import pygame
import pytest


@pytest.fixture(scope="module", autouse=True)
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_gallery_sprite_scene_instantiates():
    from src.ui.gallery_scene import GallerySpriteScene
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GallerySpriteScene(t)
    assert scene._current == 0
    assert scene.SHIP_COUNT == 5


def test_gallery_video_scene_instantiates():
    from src.ui.gallery_scene import GalleryVideoScene
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GalleryVideoScene(t)
    assert scene._current == 0
    assert len(scene.VIDEO_SUB_DIRS) == 2


def test_gallery_sprite_right_arrow_cycles():
    from src.ui.gallery_scene import GallerySpriteScene
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GallerySpriteScene(t)
    scene.on_enter()
    assert scene._current == 0
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert scene._current == 1
    # Wrap around at 4 -> 0
    scene._current = 4
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert scene._current == 0


def test_gallery_sprite_left_arrow_cycles():
    from src.ui.gallery_scene import GallerySpriteScene
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GallerySpriteScene(t)
    scene.on_enter()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    # 0 - 1 = -1, mod 5 = 4
    assert scene._current == 4


def test_gallery_sprite_number_key_jumps():
    from src.ui.gallery_scene import GallerySpriteScene
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GallerySpriteScene(t)
    scene.on_enter()
    for i, key in enumerate([
        pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
    ]):
        event = pygame.event.Event(pygame.KEYDOWN, key=key)
        pygame.event.post(event)
        pygame.event.pump()
        scene.update(1.0 / 30)
        assert scene._current == i, f"key {key} should select ship {i}"


def test_gallery_sprite_esc_returns_to_title():
    from src.ui.gallery_scene import GallerySpriteScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GallerySpriteScene(t)
    scene.on_enter()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert GameState.TITLE in transitions


def test_gallery_sprite_tab_jumps_to_video():
    from src.ui.gallery_scene import GallerySpriteScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GallerySpriteScene(t)
    scene.on_enter()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert GameState.GALLERY_VIDEO in transitions


def test_gallery_sprite_draw_doesnt_crash():
    from src.ui.gallery_scene import GallerySpriteScene
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GallerySpriteScene(t)
    scene.on_enter()
    target = pygame.Surface((240, 360))
    scene.draw(target)


def test_gallery_video_esc_returns_to_title():
    from src.ui.gallery_scene import GalleryVideoScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GalleryVideoScene(t)
    scene.on_enter()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert GameState.TITLE in transitions


def test_gallery_video_right_arrow_switches():
    from src.ui.gallery_scene import GalleryVideoScene
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GalleryVideoScene(t)
    scene.on_enter()
    assert scene._current == 0
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert scene._current == 1


def test_gallery_video_tab_jumps_to_sprite():
    from src.ui.gallery_scene import GalleryVideoScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GalleryVideoScene(t)
    scene.on_enter()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert GameState.GALLERY_SPRITE in transitions


def test_gallery_video_draw_doesnt_crash():
    from src.ui.gallery_scene import GalleryVideoScene
    transitions: list = []
    def t(state): transitions.append(state)
    scene = GalleryVideoScene(t)
    scene.on_enter()
    target = pygame.Surface((240, 360))
    scene.draw(target)


def test_title_scene_s_key_opens_sprite_gallery():
    from src.ui.scenes import TitleScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def t(state): transitions.append(state)
    scene = TitleScene(t)
    scene.on_enter()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert GameState.GALLERY_SPRITE in transitions


def test_title_scene_v_key_opens_video_gallery():
    from src.ui.scenes import TitleScene
    from src.core.scene_manager import GameState
    transitions: list = []
    def t(state): transitions.append(state)
    scene = TitleScene(t)
    scene.on_enter()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v)
    pygame.event.post(event)
    pygame.event.pump()
    scene.update(1.0 / 30)
    assert GameState.GALLERY_VIDEO in transitions
