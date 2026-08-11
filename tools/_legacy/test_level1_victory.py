"""BLOQUE 29: Test level 1 victory condition.

Force kills to 50 quickly and verify boss intro triggers.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("VOID_HUNTER_EASY", "1")
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
from src.core.game import Game
from src.core.scene_manager import GameState

print("[level1 victory test] starting")
game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()
rt = game.scenes.scenes[GameState.GAMEPLAY]._rt
rt._read_input = lambda: None

# Force kills to 50 to trigger victory
print("  forcing 50 kills to trigger boss intro...")
rt._wave_mgr.current.kills = 50
# Run 1 update to let wave state check fire
rt._player.input_fire = True
rt.update(1.0 / 120.0)
print(f"  State after 50 kills: {game.scenes.current_state}")
assert game.scenes.current_state == GameState.BOSS_INTRO, \
    f"Expected BOSS_INTRO, got {game.scenes.current_state}"

# Reset and test 5 min timeout
print("\n  resetting, testing 5 min timeout...")
game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()
rt = game.scenes.scenes[GameState.GAMEPLAY]._rt
rt._read_input = lambda: None

# Force elapsed time to 300+
rt._wave_mgr.current.elapsed_s = 305.0
rt._player.input_fire = True
rt.update(1.0 / 120.0)
print(f"  State after 5 min: {game.scenes.current_state}")
assert game.scenes.current_state == GameState.BOSS_INTRO, \
    f"Expected BOSS_INTRO, got {game.scenes.current_state}"

print("\n[level1 victory test] PASS — both win conditions work")
