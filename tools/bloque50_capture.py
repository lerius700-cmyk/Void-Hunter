"""BLOQUE 50: visual frames for diffuse aura + sub-boss + warning signs.

Captures:
  - polish_25_diffuse_aura: diffuse energy aura (no static ring)
  - polish_26_sub_boss: SUB_BOSS in flight (yellow dart, frenetic wobble)
  - polish_27_boss_intro_red: BossIntroScene red alarm
  - polish_28_sub_boss_intro_yellow: SubBossIntroScene yellow warning
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_INVULN"] = "1"
os.environ["VOID_HUNTER_EASY"] = "1"
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
from src.core.game import Game
from src.core.scene_manager import GameState
from src.core.settings import INTERNAL_W, INTERNAL_H
from src.entities.enemies.enemy import EnemyKind

print("=" * 60)
print("BLOQUE 50: diffuse aura + sub-boss + warning signs")
print("=" * 60)

game = Game()

# ---- Frame 1: Diffuse aura (L3 charge) ----
print("\n--- Frame 1: Diffuse aura (L3 charge) ---")
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game_scene = game.scenes.scenes[GameState.GAMEPLAY]
game_scene.on_enter()
rt = game_scene._rt
p = rt._player
p.invuln_frames = 999999

# Position player at center
p.x = INTERNAL_W * 0.30
p.y = INTERNAL_H * 0.65

# L3 charge
p._enter_charge()
p.charge_time = 1.5
p.input_fire = True
rt._laser_active = True
rt._laser_end_x = INTERNAL_W * 0.50
rt._laser_end_y = -50

# Update for a moment so particles accumulate and are visible mid-flight
for _ in range(int(0.5 * 60)):
    rt.update(1.0 / 60)
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
game_scene.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * 4, INTERNAL_H * 4))
out1 = Path("tools/playtest_out/polish_25_diffuse_aura.png")
pygame.image.save(scaled, str(out1))
print(f"Saved: {out1}")

# ---- Frame 2: SUB_BOSS in flight ----
print("\n--- Frame 2: SUB_BOSS in flight ---")
# Reset and start fresh
game.scenes.transition_to(GameState.GAMEPLAY)
game_scene = game.scenes.scenes[GameState.GAMEPLAY]
game_scene.on_enter()
rt = game_scene._rt
p = rt._player
p.invuln_frames = 999999
p.x = INTERNAL_W * 0.50
p.y = INTERNAL_H * 0.75

# Spawn a SUB_BOSS with some score
sb = rt._enemies.spawn(EnemyKind.SUB_BOSS, INTERNAL_W * 0.30, 60.0)
if sb is not None:
    # Make it look like it's in mid-frenetic motion
    sb.hp = sb.max_hp
    sb.x = INTERNAL_W * 0.30 + 8
    sb.y = 50.0
    sb.sine_t = 0.5
    sb.sine_origin_x = sb.x

# Update briefly so it has age for animation
for _ in range(int(0.3 * 60)):
    rt.update(1.0 / 60)

surf2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
game_scene.draw(surf2)
scaled2 = pygame.transform.scale(surf2, (INTERNAL_W * 4, INTERNAL_H * 4))
out2 = Path("tools/playtest_out/polish_26_sub_boss.png")
pygame.image.save(scaled2, str(out2))
print(f"Saved: {out2}")

# ---- Frame 3: BossIntroScene (red alarm) ----
print("\n--- Frame 3: BossIntroScene red alarm ---")
boss_intro = game.scenes.scenes[GameState.BOSS_INTRO]
boss_intro._boss_name = "VOID OVERLORD"
# Update to ~1.5s (mid-animation)
for _ in range(int(1.5 * 60)):
    boss_intro.update(1.0 / 60)
surf3 = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_intro.draw(surf3)
scaled3 = pygame.transform.scale(surf3, (INTERNAL_W * 4, INTERNAL_H * 4))
out3 = Path("tools/playtest_out/polish_27_boss_intro_red.png")
pygame.image.save(scaled3, str(out3))
print(f"Saved: {out3}")

# ---- Frame 4: SubBossIntroScene (yellow warning) ----
print("\n--- Frame 4: SubBossIntroScene yellow warning ---")
sub_boss_intro = game.scenes.scenes[GameState.SUB_BOSS_INTRO]
# Update to ~1.0s (mid-animation)
for _ in range(int(1.0 * 60)):
    sub_boss_intro.update(1.0 / 60)
surf4 = pygame.Surface((INTERNAL_W, INTERNAL_H))
sub_boss_intro.draw(surf4)
scaled4 = pygame.transform.scale(surf4, (INTERNAL_W * 4, INTERNAL_H * 4))
out4 = Path("tools/playtest_out/polish_28_sub_boss_intro_yellow.png")
pygame.image.save(scaled4, str(out4))
print(f"Saved: {out4}")

print("\nDone.")
