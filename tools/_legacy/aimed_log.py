"""Aimed log test: simulates mouse aiming at enemies."""
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
print("VOID HUNTER 10-SECOND AIMED TEST")
print("=" * 60)
game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()
rt = game.scenes.scenes[GameState.GAMEPLAY]._rt
rt._read_input = lambda: None  # skip keyboard/mouse

print(f"  Level 1 mode: {rt._is_level1_mode()}")
print(f"  Pending spawns: {len(rt._pending_wave_spawns)}")

# Simulate: aim at enemies + fire
target_frames = 120 * 10
last_kills = 0
for f in range(target_frames):
    game_time = f / 120.0
    # Mouse aiming: find nearest enemy
    nearest_x = None
    nearest_y = None
    for e in rt._enemies.pool:
        if e.active and e.state.name != "DEAD":
            nearest_x = e.x
            nearest_y = e.y
            break
    if nearest_x is not None:
        # Set mouse position to enemy
        rt._mouse_x = nearest_x
        rt._mouse_y = nearest_y
    # Always fire
    rt._player.input_fire = True
    # Update
    rt._update_nose_angle()
    rt._player.update(1.0 / 120.0)
    rt._handle_firing(0.0)
    rt._bullets.update(1.0 / 120.0)
    rt._update_enemies(1.0 / 120.0)
    rt._handle_collisions()
    rt._spawn_pending(1.0 / 120.0)
    rt._update_wave_state(1.0 / 120.0)
    # Log every 2s
    if f % 240 == 0 and f > 0:
        kills = rt._wave_mgr.current.kills
        nk = kills - last_kills
        last_kills = kills
        live = sum(1 for e in rt._enemies.pool if e.active)
        bullets = sum(1 for b in rt._bullets.pool if b.active and b.owner == 0)
        print(f"  t={game_time:.1f}s hp={rt._player.hp} lives={rt._player.lives} "
              f"enemies={live} bullets={bullets} "
              f"kills={kills} (+{nk}) score={rt._scoring.score}")

print(f"\nFinal: state={game.scenes.current_state} "
      f"kills={rt._wave_mgr.current.kills} score={rt._scoring.score}")
print(f"  Player: hp={rt._player.hp} lives={rt._player.lives}")
print("=" * 60)
