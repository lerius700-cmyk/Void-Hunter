"""BLOQUE 31: Level 1 completion bot — final realistic version.

Strategy:
- Always aim at nearest enemy (or boss during boss fight).
- During level 1: L1 fire (input_fire=True), strafing in MOVE state.
- During boss fight: short CHARGE bursts to fire L3 beam (8 dmg), with brief
  release cycles for movement.
- Bomb when overwhelmed or HP low.
- Dash when very close bullet.

Why this should work:
- Level 1 transitions to BOSS_INTRO after 300s OR 50 kills.
- With L1 fire + strafe + aim, 30+ kills in 300s should be possible.
- Boss GOLIATH (400 HP) takes ~50 L3 beam hits = ~4s of beam time.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("VOID_HUNTER_EASY", "1")
# Set VOID_HUNTER_INVULN=1 to make the bot unkillable (testing only)
INVULN = os.environ.get("VOID_HUNTER_INVULN", "0") == "1"
import sys
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
from src.core.game import Game
from src.core.scene_manager import GameState
from src.core.settings import INTERNAL_H, INTERNAL_W
from src.systems.projectile import OWNER_BOSS, OWNER_ENEMY, OWNER_PLAYER

print("=" * 64)
print("VOID HUNTER — LEVEL 1 COMPLETION BOT (BLOQUE 31)")
print("=" * 64)

game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()

NO_INPUT = lambda: None

target_frames = 120 * 600  # up to 10 min
phase = "level"
prev_state = None
last_dash = -10.0
last_bomb = -10.0
strafing_dir = 1
strafing_timer = 0.0
last_log_kills = 0
prev_hp = 3
prev_lives = 9

# Boss fight: cycle charge (1.5s) → release (0.2s)
boss_hold_t = 1.5
boss_release_t = 0.2
boss_cycle = boss_hold_t + boss_release_t

for f in range(target_frames):
    game_time = f / 120.0
    state = game.scenes.current_state

    if state != prev_state:
        print(f"  [t={game_time:6.1f}s] state -> {state}")
        prev_state = state

    if state == GameState.ACT_CLEARED:
        print(f"  [t={game_time:6.1f}s] *** LEVEL 1 CLEARED! ***")
        break
    if state == GameState.VICTORY:
        print(f"  [t={game_time:6.1f}s] *** FULL VICTORY! ***")
        break
    if state == GameState.GAME_OVER:
        print(f"  [t={game_time:6.1f}s] GAME OVER")
        break

    if state == GameState.BOSS_INTRO:
        scene = game.scenes.scenes.get(GameState.BOSS_INTRO)
        if scene is not None:
            scene.update(1.0 / 120.0)
        continue

    if state == GameState.GAMEPLAY:
        rt = game.scenes.scenes[GameState.GAMEPLAY]._rt
        phase = "level"
    elif state == GameState.BOSS_FIGHT:
        rt = game.scenes.scenes[GameState.BOSS_FIGHT]._rt
        phase = "boss"
    else:
        scene = game.scenes.scenes.get(state)
        if scene is not None:
            scene.update(1.0 / 120.0)
        continue

    rt._read_input = NO_INPUT
    p = rt._player
    if INVULN:
        p.invuln_frames = 999999

    if p.is_dead:
        rt.update(1.0 / 120.0)
        continue

    # ---- Target ----
    best = None
    if phase == "boss" and rt._boss is not None and rt._boss.active:
        best = rt._boss
    else:
        best_d = 9999.0
        for e in rt._enemies.pool:
            if e.active and getattr(e, "state", None) is not None and e.state.name != "DEAD":
                d = abs(e.x - p.x) + abs(e.y - p.y) * 0.3
                if d < best_d:
                    best_d = d
                    best = e
    if best is not None:
        rt._mouse_x = best.x
        rt._mouse_y = best.y

    # ---- Threat ----
    danger_bullets = 0
    closest_dist = 9999.0
    closest_bullet_vx = 0.0
    closest_bullet_vy = 0.0
    for bullet in rt._bullets.pool:
        if not bullet.active or bullet.owner not in (OWNER_ENEMY, OWNER_BOSS):
            continue
        fut_x = bullet.x + bullet.vx * 0.18
        fut_y = bullet.y + bullet.vy * 0.18
        d = math.hypot(fut_x - p.x, fut_y - p.y)
        if d < closest_dist:
            closest_dist = d
            closest_bullet_vx = bullet.vx
            closest_bullet_vy = bullet.vy
        if d < 30.0:
            danger_bullets += 1

    # ---- Fire mode ----
    if phase == "boss":
        # Boss fight: hold 1.5s (L3 beam), release 0.2s for movement
        cycle_pos = game_time % boss_cycle
        if cycle_pos < boss_hold_t and p.hp > 1:
            rt._mouse_held = True
            rt._player.input_fire = True
        else:
            rt._mouse_held = False
            rt._player.input_fire = False
    else:
        # Level: always fire L1 — keeps input_fire=True so SHOOT↔MOVE cycle
        # allows movement while firing. The player will be in MOVE state
        # because input_left/right is set.
        rt._mouse_held = False
        rt._player.input_fire = True

    # ---- Vertical positioning ----
    rt._player.input_up = False
    rt._player.input_down = False
    target_y = 320.0 if phase == "boss" else 280.0
    if p.y < target_y - 5:
        rt._player.input_down = True
    elif p.y > target_y + 5:
        rt._player.input_up = True

    # ---- Strafing ----
    strafing_timer += 1.0 / 120.0
    if strafing_timer > 0.40:
        strafing_timer = 0.0
        strafing_dir *= -1
        rt._player.vx = -78.0 if strafing_dir < 0 else 78.0
    rt._player.input_left = (strafing_dir < 0)
    rt._player.input_right = (strafing_dir > 0)

    # ---- Dash ----
    if game_time - last_dash > 0.30 and closest_dist < 9.0:
        bx, by = closest_bullet_vx, closest_bullet_vy
        blen = math.hypot(bx, by)
        if blen > 0.01:
            nx, ny = -by / blen, bx / blen
            if nx > 0:
                rt._player.input_left = True
                rt._player.input_right = False
            else:
                rt._player.input_left = False
                rt._player.input_right = True
        rt._player.input_dash = True
        last_dash = game_time

    # ---- Bomb ----
    if p.bombs > 0 and game_time - last_bomb > 2.0:
        if p.hp <= 2 or danger_bullets >= 5:
            rt._player.input_bomb = True
            last_bomb = game_time

    rt.update(1.0 / 120.0)

    # ---- HP diagnostics ----
    if p.hp < prev_hp:
        phb_check = pygame.Rect(int(p.x) - 12, int(p.y) - 12, 24, 24)
        for e in rt._enemies.pool:
            if not e.active or e.state.name == "DEAD":
                continue
            eh = e.hitbox()
            if eh.colliderect(phb_check):
                print(f"  [t={game_time:5.2f}s] HIT by {e.kind.name} (player @({p.x:.0f},{p.y:.0f})) hp {prev_hp}->{p.hp}")
                break
        else:
            print(f"  [t={game_time:5.2f}s] HIT by bullet (player @({p.x:.0f},{p.y:.0f})) hp {prev_hp}->{p.hp}")
    prev_hp = p.hp
    if p.lives != prev_lives:
        print(f"  [t={game_time:5.2f}s] LIVES {prev_lives}->{p.lives}")
        prev_lives = p.lives

    if f % 600 == 0 and f > 0:
        kills = rt._wave_mgr.current.kills if hasattr(rt, "_wave_mgr") and rt._wave_mgr.current else 0
        nk = kills - last_log_kills
        last_log_kills = kills
        live_enemies = sum(1 for e in rt._enemies.pool if e.active)
        boss_hp = rt._boss.hp if rt._boss and rt._boss.active else 0
        print(f"  [t={game_time:5.0f}s] phase={phase:9s} hp={p.hp} lives={p.lives} "
              f"kills={kills:3d} (+{nk:2d}) score={rt._scoring.score:6d} "
              f"enemies={live_enemies:2d} bombs={p.bombs} boss_hp={boss_hp}")

print("=" * 64)
final_state = game.scenes.current_state
print(f"Final state: {final_state}")
if final_state == GameState.ACT_CLEARED:
    print("RESULT: Level 1 cleared successfully!")
elif final_state == GameState.VICTORY:
    print("RESULT: Full game victory!")
elif final_state == GameState.GAME_OVER:
    print("RESULT: Bot died. Try again or lower difficulty.")
else:
    print("RESULT: Bot timed out without reaching ACT_CLEARED.")
print("=" * 64)
