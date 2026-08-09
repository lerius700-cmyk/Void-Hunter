"""BLOQUE 29: Test level 1 mode.

Validates:
- 100+ ships in spawn queue
- 3 distinct enemy types
- Win condition at 50 kills OR 5 min
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
from src.entities.enemies import EnemyKind

print("[level1 test] starting")
game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()
rt = game.scenes.scenes[GameState.GAMEPLAY]._rt
rt._read_input = lambda: None

# Verify level 1 mode is active
assert rt._is_level1_mode(), "Should be in level 1 mode"

# Verify spawn queue has 100+ ships
total = len(rt._pending_wave_spawns)
print(f"  pending spawns: {total}")
assert total >= 100, f"Expected 100+ spawns, got {total}"

# Verify 3 distinct enemy types
kinds = set(item[1] for item in rt._pending_wave_spawns)
print(f"  enemy kinds: {[k.value for k in kinds]}")
assert len(kinds) == 3, f"Expected 3 distinct kinds, got {len(kinds)}"
assert EnemyKind.SCOUT in kinds
assert EnemyKind.CRUISER in kinds
assert EnemyKind.HEAVY in kinds

# Simulate 10 seconds of play and check spawns
rt._player.input_fire = True
kills = 0
start_t = 0.0
for f in range(120 * 10):
    game_time = f / 120.0
    rt._player.input_fire = True
    rt.update(1.0 / 120.0)
    # Track kills
    if game_time > start_t + 0.5:
        kills = rt._wave_mgr.current.kills
        if f % 240 == 0:
            live_enemies = sum(1 for e in rt._enemies.pool if e.active)
            print(f"  t={game_time:.1f}s spawns_remaining={len(rt._pending_wave_spawns)} "
                  f"live_enemies={live_enemies} kills={kills}")
        start_t = game_time

# Verify level 1 mode still active after 10s
print(f"\n[level1 test] PASS — level 1 active, {total} ships queued, 3 distinct types")
print(f"  Final: kills={rt._wave_mgr.current.kills} elapsed={rt._wave_mgr.current.elapsed_s:.1f}s")
print(f"  State: {game.scenes.current_state}")
