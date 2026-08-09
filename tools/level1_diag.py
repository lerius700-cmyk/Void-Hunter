"""Diagnostic: print player position + state every second, no other input."""
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
from src.core.settings import INTERNAL_H, INTERNAL_W

print("=" * 60)
print("VOID HUNTER — POSITION DIAGNOSTIC")
print("=" * 60)

game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()
rt = game.scenes.scenes[GameState.GAMEPLAY]._rt

NO_INPUT = lambda: None

# Press right for 0.5s, then left for 0.5s, alternating
strafing_dir = 1
strafing_timer = 0.0
p = rt._player

for f in range(120 * 5):  # 5 sec
    game_time = f / 120.0
    rt._read_input = NO_INPUT

    if game.scenes.current_state != GameState.GAMEPLAY:
        break

    strafing_timer += 1.0 / 120.0
    if strafing_timer > 0.5:
        strafing_timer = 0.0
        strafing_dir *= -1
        # Also try setting vx
        p.vx = 78.0 if strafing_dir > 0 else -78.0

    p.input_left = (strafing_dir < 0)
    p.input_right = (strafing_dir > 0)
    p.input_up = False
    p.input_down = False
    p.input_fire = False

    rt.update(1.0 / 120.0)

    if f % 12 == 0:
        print(f"  t={game_time:4.2f}s pos=({p.x:6.1f},{p.y:6.1f}) vx={p.vx:6.1f} state={p.state.name} "
              f"dir=({p.input_left},{p.input_right}) vx_set={p.vx}")

print("=" * 60)
