"""BLOQUE 28: Focused boss-kill test.

Skips directly to the boss fight and tries to kill GOLIATH.
Tests if the boss is actually killable with smart play.
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
from src.systems.projectile import OWNER_BOSS, OWNER_ENEMY, OWNER_PLAYER

print("[boss test] starting focused boss fight")
game = Game()
# Skip directly to boss fight via gameplay
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.transition_to(GameState.BOSS_INTRO)
game.scenes.transition_to(GameState.BOSS_FIGHT)
game.scenes.scenes[GameState.BOSS_FIGHT].on_enter()
rt = game.scenes.scenes[GameState.BOSS_FIGHT]._rt
rt._read_input = lambda: None

target_frames = 120 * 90  # 90s
last_dash = -10.0
last_bomb = -10.0
kills = 0
last_boss_hp = rt._boss.hp if rt._boss else 0

for f in range(target_frames):
    game_time = f / 120.0
    rt._player.input_fire = True

    # Track boss HP to see if we're damaging it
    if rt._boss and rt._boss.active:
        if rt._boss.hp < last_boss_hp:
            damage = last_boss_hp - rt._boss.hp
            if f % 60 == 0:
                print(f"  t={game_time:.1f}s boss_hp={rt._boss.hp}/{rt._boss.max_hp} "
                      f"player_hp={rt._player.hp} lives={rt._player.lives}")
        last_boss_hp = rt._boss.hp

    # Aim at boss
    if rt._boss and rt._boss.active:
        if rt._boss.x < rt._player.x - 8:
            rt._player.input_left = True
            rt._player.input_right = False
        elif rt._boss.x > rt._player.x + 8:
            rt._player.input_left = False
            rt._player.input_right = True
        else:
            rt._player.input_left = False
            rt._player.input_right = False

    # Aggressive dash in boss fight — but only when REALLY imminent
    if game_time - last_dash >= 0.6:
        px, py = rt._player.x, rt._player.y
        for p in rt._bullets.pool:
            if not p.active or p.owner not in (OWNER_ENEMY, OWNER_BOSS):
                continue
            fut_x = p.x + p.vx * 0.15  # only 0.15s lookahead
            fut_y = p.y + p.vy * 0.15
            if abs(fut_x - px) < 10 and abs(fut_y - py) < 10:
                rt._player.input_dash = True
                last_dash = game_time
                break

    # Aggressive bomb in boss fight
    if rt._player.bombs > 0 and game_time - last_bomb >= 1.5 and rt._player.hp <= 2:
        rt._player.input_bomb = True
        rt._player.wants_to_bomb = True
        last_bomb = game_time

    rt.update(1.0 / 120.0)

    # Check boss death
    if rt._boss is None or not rt._boss.active:
        print(f"  BOSS KILLED at t={game_time:.1f}s!")
        print(f"    state={game.scenes.current_state} "
              f"player_hp={rt._player.hp} lives={rt._player.lives} "
              f"is_dead={rt._player.is_dead} boss_killed={getattr(rt, '_boss_killed_this_frame', 'N/A')}")
        # Force another frame to see if GAME_OVER transition overrides
        rt.update(1.0 / 120.0)
        print(f"  After extra frame: state={game.scenes.current_state}")
        kills = 1
        break

    if rt._player.is_dead and rt._player.lives < 0:
        print(f"  Player died at t={game_time:.1f}s")
        break

if kills == 1:
    print("[boss test] SUCCESS — GOLIATH killed")
    # Verify scene transitioned to ACT_CLEARED
    if game.scenes.current_state == GameState.ACT_CLEARED:
        print("[boss test] PASS — transitioned to ACT_CLEARED after boss kill")
    else:
        print(f"[boss test] NOTE — state after kill: {game.scenes.current_state}")
        # Debug: why is player dead?
        print(f"  player.is_dead={rt._player.is_dead} hp={rt._player.hp} lives={rt._player.lives}")
else:
    if rt._boss and rt._boss.active:
        print(f"[boss test] FAIL — boss still alive at t={game_time:.1f}s "
              f"with {rt._boss.hp}/{rt._boss.max_hp} HP")
    else:
        print(f"[boss test] FAIL — bot died before killing boss")
