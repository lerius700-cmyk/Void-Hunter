"""Quick 5-second diagnostic - what happens in the first 5s of play."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
from src.core.game import Game
from src.core.scene_manager import GameState
from src.systems.projectile import OWNER_PLAYER

game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()
rt = game.scenes.scenes[GameState.GAMEPLAY]._rt
# Skip _read_input
rt._read_input = lambda: None

print(f"Start: hp={rt._player.hp} lives={rt._player.lives}")
print(f"Weight: wave_idx={rt._wave_idx} pending_spawns={len(rt._pending_wave_spawns)}")

# 5 seconds of stationary firing
for f in range(120 * 5):
    rt._player.input_fire = True
    rt._player.input_left = False
    rt._player.input_right = False
    rt.update(1.0 / 120.0)
    if f % 60 == 0:  # every 0.5s
        bullets = sum(1 for b in rt._bullets.pool if b.active and b.owner == OWNER_PLAYER)
        enemies = sum(1 for e in rt._enemies.pool if e.active)
        print(f"  t={f/120:.1f}s hp={rt._player.hp} lives={rt._player.lives} "
              f"player_bullets={bullets} enemies={enemies} "
              f"score={rt._scoring.score} kills={rt._scoring.kills} "
              f"wave_kills={rt._wave_mgr.current.kills}")

bullets = sum(1 for b in rt._bullets.pool if b.active and b.owner == OWNER_PLAYER)
enemies = sum(1 for e in rt._enemies.pool if e.active)
print(f"\nFinal 5s: hp={rt._player.hp} lives={rt._player.lives} is_dead={rt._player.is_dead}")
print(f"Active player bullets: {bullets}")
print(f"Active enemies: {enemies}")
print(f"Score: {rt._scoring.score} Kills: {rt._scoring.kills}")
print(f"Wave: {rt._wave_idx} kills this wave: {rt._wave_mgr.current.kills}/{rt._wave_mgr.scripts[rt._wave_idx]['kill_target']}")
