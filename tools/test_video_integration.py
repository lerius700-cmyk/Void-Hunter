"""Focused smoke test for the video integration.

Verifies what BLOQUE 58.59 added (VideoPlayer + CinematicScene + new
CINEMATIC state) without going through Game() which has unrelated
pre-existing issues with ParallaxBackground in gameplay_runtime.
"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import sys
import pygame
pygame.init()
pygame.display.set_mode((1, 1))
print('pygame initialized')

sys.path.insert(0, r'D:\AI\void-hunter')

# Test 1: imports work
print('Test 1: imports')
from src.core.scene_manager import GameState, SceneManager
from src.ui.scenes import TitleScene, CinematicScene, _build_video_player
from src.ui.video_player import VideoPlayer
print('  All imports OK')

# Test 2: GameState has CINEMATIC
print('Test 2: GameState.CINEMATIC exists')
assert GameState.CINEMATIC in GameState
assert GameState.CINEMATIC.value == 'cinematic'
print('  OK')

# Test 3: TitleScene has video player when assets present
print('Test 3: TitleScene video integration')
transitions: list = []
def t(state): transitions.append(state)
title = TitleScene(t)
title.on_enter()
assert title._video is not None, 'TitleScene should have video when assets present'
print(f'  Video: {title._video is not None}, available: {title._video_available}')
print(f'  After on_enter: frame_index = {title._video._frame_index}')

# Test 4: TitleScene keypress transitions to CINEMATIC
print('Test 4: TitleScene keypress -> CINEMATIC')
event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
pygame.event.post(event)
pygame.event.pump()
title.update(1.0 / 30)
assert GameState.CINEMATIC in transitions, f'Expected CINEMATIC in {transitions}'
print('  OK')

# Test 5: CinematicScene plays the zoom video
print('Test 5: CinematicScene video integration')
cine = CinematicScene(t)
cine.on_enter()
assert cine._video is not None
print(f'  Video: {cine._video is not None}, is_playing: {cine._video.is_playing()}')

# Test 6: CinematicScene updates the video
print('Test 6: CinematicScene update advances video')
cine.update(1.0 / 30)  # 1 frame
print(f'  After 1 frame: frame_index = {cine._video._frame_index}')
assert cine._video._frame_index == 1
print('  OK')

# Test 7: CinematicScene ESC skips to ACT_INTRO
print('Test 7: CinematicScene ESC skip')
event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
pygame.event.post(event)
pygame.event.pump()
cine.update(1.0 / 30)
assert GameState.ACT_INTRO in transitions
print('  OK')

print()
print('All 7 video integration tests passed.')
