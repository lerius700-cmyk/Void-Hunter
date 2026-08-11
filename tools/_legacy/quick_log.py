"""Quick log test: runs the game 8 seconds with auto-input and logs events."""
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
print("VOID HUNTER 8-SECOND LOG TEST")
print("=" * 60)
game = Game()
print(f"  Initial state: {game.scenes.current_state}")
print(f"  Display: {game.screen.get_size()}")
print(f"  Internal: {game.internal.get_size()}")

# Force into gameplay
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()
rt = game.scenes.scenes[GameState.GAMEPLAY]._rt
print(f"  After transitions: {game.scenes.current_state}")
print(f"  Wave idx: {rt._wave_idx}, pending spawns: {len(rt._pending_wave_spawns)}")
print(f"  Player: pos=({rt._player.x:.0f},{rt._player.y:.0f}) hp={rt._player.hp} lives={rt._player.lives}")

# Simulate 8 seconds of play with auto-input
last_state = game.scenes.current_state
target_frames = 120 * 8
for f in range(target_frames):
    game_time = f / 120.0
    # Auto-input: always fire + slight movement
    rt._player.input_fire = True
    # Move toward center
    if rt._player.x < INTERNAL_W / 2:
        rt._player.input_right = True
    elif rt._player.x > INTERNAL_W / 2:
        rt._player.input_left = True
    rt.update(1.0 / 120.0)
    # Log every 2 seconds
    if f % 240 == 0 and f > 0:
        live = sum(1 for e in rt._enemies.pool if e.active)
        bullets = sum(1 for b in rt._bullets.pool if b.active)
        print(f"  t={game_time:.1f}s state={game.scenes.current_state} "
              f"enemies={live} bullets={bullets} "
              f"hp={rt._player.hp} lives={rt._player.lives} "
              f"kills={rt._wave_mgr.current.kills} "
              f"score={rt._scoring.score}")

# Final state
print(f"\nFinal: state={game.scenes.current_state} "
      f"kills={rt._wave_mgr.current.kills} score={rt._scoring.score}")
print(f"  Player: hp={rt._player.hp} lives={rt._player.lives}")
print("=" * 60)
