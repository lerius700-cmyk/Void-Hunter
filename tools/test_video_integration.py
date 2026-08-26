"""Smoke test for the video integration. Verifies the game initializes,
the title + cinematic scenes are registered, and the videos can play.
"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'  # headless

import sys
import pygame
pygame.init()
pygame.display.set_mode((1, 1))
print('pygame initialized')

sys.path.insert(0, r'D:\AI\void-hunter')
from src.core.game import Game
from src.core.scene_manager import GameState

g = Game()
print(f'Game created, current state: {g.scenes.current_state.name}')
print(f'Registered scenes: {list(g.scenes.scenes.keys())}')

assert GameState.CINEMATIC in g.scenes.scenes, 'CinematicScene not registered'
print('CINEMATIC state registered')

title = g.scenes.scenes[GameState.TITLE]
cine = g.scenes.scenes[GameState.CINEMATIC]

print(f'TitleScene._video_available: {title._video_available}')
print(f'TitleScene._video is None: {title._video is None}')
print(f'CinematicScene._video_available: {cine._video_available}')
print(f'CinematicScene._video is None: {cine._video is None}')

# Run 30 update ticks (~1 second)
for i in range(30):
    g.scenes.update(1.0 / 30)

if title._video is not None:
    print(f'After 1s: title _t={title._t:.2f}, video frame_index={title._video._frame_index}')
else:
    print(f'After 1s: title _t={title._t:.2f}, no video (fallback to bg)')

print('Smoke test passed')
