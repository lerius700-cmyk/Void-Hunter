"""Worker verification script: actually run the game and count spawns.

Per the parent's instructions, this script:
1. Initializes pygame + the GameplayRuntime in headless mode
2. Wraps spawn_obstacle to log every call
3. Runs the game for N seconds of game time
4. Prints the actual mine vs asteroid ratio
5. Prints the first-N-spawns breakdown

Run from the project root with the venv Python:
    .venv\Scripts\python.exe tools\verify_spawn_ratio.py
"""
from __future__ import annotations

import os
import sys
import time

# Force headless rendering so we don't need a display
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame
pygame.init()
# A real display surface is required even in dummy mode for some operations
pygame.display.set_mode((320, 480))

# ------------------------------------------------------------------
# Wrap spawn_obstacle BEFORE the game instantiates it, so we count
# every spawn decision the game makes.
# ------------------------------------------------------------------
import src.entities.enemies.enemy as enemy_mod
_orig_spawn_obstacle = enemy_mod.spawn_obstacle

spawn_log: list[str] = []  # "mine" or "asteroid"
call_count = {"n": 0}


def _wrapped_spawn_obstacle(rng):
    call_count["n"] += 1
    kind, payload = _orig_spawn_obstacle(rng)
    spawn_log.append(kind)
    return kind, payload


enemy_mod.spawn_obstacle = _wrapped_spawn_obstacle

# Also wrap _update_asteroids_and_powerups so we know when the game
# tried to spawn but was capped at 8 active asteroids.
_orig_update = None
cap_log: list[int] = []


def _wrap_caps(runtime):
    """No-op now; we don't need to wrap update since spawn_obstacle wrap
    already captures every spawn decision. Kept as a placeholder for
    future cap-stats if needed.
    """
    pass


# ------------------------------------------------------------------
# Instantiate the game
# ------------------------------------------------------------------
def noop_transition(*args, **kwargs):
    pass


print("[verify] importing GameplayRuntime...")
from src.ui.gameplay_runtime import GameplayRuntime

print("[verify] creating GameplayRuntime (act=1, is_boss=False)...")
t0 = time.perf_counter()
game = GameplayRuntime(transition_to=noop_transition, is_boss=False, act=1)
print(f"[verify] init took {time.perf_counter() - t0:.2f}s")

# Trigger on_enter to populate level1 chain (needed for sub_boss_pending)
print("[verify] calling on_enter() to populate level1 wave chain...")
game.on_enter()

_wrap_caps(game)

# Print RNG seed info
print(f"[verify] asteroid RNG seed: 0x{game._asteroid_rng.randint(0, 0xFFFFFFFF):08X} (after 1 sample)")

# ------------------------------------------------------------------
# Run 60 seconds of game time
# ------------------------------------------------------------------
TICK = 1.0 / 60.0
DURATION_S = 60.0
TOTAL_TICKS = int(DURATION_S * 60)

# Reset RNG so we start at the same state as a fresh game launch
import random as _r
game._asteroid_rng = _r.Random(0xA57E2012)
spawn_log.clear()

print(f"[verify] running {DURATION_S:.0f}s @ {TICK*1000:.1f}ms/tick ({TOTAL_TICKS} ticks)...")
t0 = time.perf_counter()
for i in range(TOTAL_TICKS):
    game.update(TICK)
    # Don't actually draw (saves time)
elapsed = time.perf_counter() - t0
print(f"[verify] sim took {elapsed:.2f}s real ({elapsed/DURATION_S*100:.0f}% of game time)")

# ------------------------------------------------------------------
# Report
# ------------------------------------------------------------------
mine_count = sum(1 for k in spawn_log if k == "mine_asteroid")
ast_count = sum(1 for k in spawn_log if k == "asteroid")
total = len(spawn_log)

print()
print("=" * 60)
print(f"ACTUAL SPAWN RATIO OVER {DURATION_S:.0f}s ({total} spawns)")
print("=" * 60)
print(f"  mines:    {mine_count:5d}  ({mine_count/max(1,total)*100:5.1f}%)")
print(f"  asteroids:{ast_count:5d}  ({ast_count/max(1,total)*100:5.1f}%)")
print(f"  total:    {total:5d}")
print()
print("First 20 spawns (in order):")
for i, k in enumerate(spawn_log[:20]):
    print(f"  {i+1:2d}. {k}")
print()
# Check if the first 3 are all mines (the parent's "bad luck" hypothesis)
if total >= 3:
    first3 = spawn_log[:3]
    if all(k == "mine_asteroid" for k in first3):
        print("!! FIRST 3 SPAWNS ARE ALL MINES !!")
    else:
        print(f"OK: first 3 spawns = {first3} (not all mines)")

# Count active at end
active_mines = sum(
    1 for e in game._enemies.pool
    if e is not None and getattr(e, "kind", None) == enemy_mod.EnemyKind.MINE_ASTEROID
    and e.state != enemy_mod.EnemyState.DEAD
)
active_asteroids = sum(1 for a in game._asteroids if a.active)
print()
print(f"ACTIVE on screen at end of sim:")
print(f"  mines:    {active_mines}")
print(f"  asteroids:{active_asteroids}")

# Also: how many mines actually OPENED (reached open3) during the sim?
opened_mines = sum(
    1 for e in game._enemies.pool
    if e is not None and getattr(e, "kind", None) == enemy_mod.EnemyKind.MINE_ASTEROID
    and getattr(e, "mine_state", "closed") != "closed"
)
print(f"  mines that opened (reached OPENING_Y_THRESHOLD): {opened_mines}")

print()
print("=" * 60)
print("VERDICT")
print("=" * 60)
if total == 0:
    print("BUG: zero spawns in 60s — spawn loop never fired")
elif mine_count / max(1, total) > 0.50:
    print(f"BUG CONFIRMED: {mine_count/max(1,total)*100:.0f}% mines (expected 25%)")
elif all(k == "mine_asteroid" for k in spawn_log[:3]):
    print(f"CODE OK (ratio {mine_count/max(1,total)*100:.0f}%) but first 3 spawns are all mines")
    print("User perception of '100% mines' is a SEED BIAS artifact")
else:
    print(f"CODE OK: {mine_count/max(1,total)*100:.0f}% mines / {ast_count/max(1,total)*100:.0f}% asteroids")
