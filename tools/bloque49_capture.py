"""BLOQUE 49: visual frame of charge aura + orange laser sparks."""
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
from src.entities.player.player import PlayerState

print("=" * 60)
print("BLOQUE 49: title screen + charge aura + laser sparks")
print("=" * 60)

game = Game()

# ---- Frame 1: title screen ----
print("\n--- Frame 1: Title screen ---")
game.scenes.transition_to(GameState.TITLE)
title_scene = game.scenes.scenes[GameState.TITLE]
# Run a few updates to show the blink
for _ in range(60):
    title_scene.update(1.0 / 60)
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
title_scene.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * 4, INTERNAL_H * 4))
out1 = Path("tools/playtest_out/polish_21_title.png")
pygame.image.save(scaled, str(out1))
print(f"Saved: {out1}")

# ---- Frame 2: gameplay with charge aura ----
print("\n--- Frame 2: gameplay with charge aura ---")
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game_scene = game.scenes.scenes[GameState.GAMEPLAY]
game_scene.on_enter()
rt = game_scene._rt
p = rt._player
p.invuln_frames = 999999

# Force charge state
p._enter_charge()  # enter CHARGE state
p.charge_time = 1.0  # well into charge (will reach L3 = laser)
p.input_fire = True
p.input_left = True  # for tilt

# Set mouse position
rt._mouse_x = INTERNAL_W * 0.55
rt._mouse_y = INTERNAL_H * 0.40

# Spawn an enemy in front of the player
rt._enemies_spawned_total = 0
from src.entities.enemies.enemy import EnemyKind
e = rt._enemies.spawn(EnemyKind.SCOUT, INTERNAL_W * 0.55, INTERNAL_H * 0.25)
if e is not None:
    e.hp = 1

# Run a few frames to accumulate particles
for _ in range(int(1.0 * 60)):  # 1 second
    rt.update(1.0 / 60)
# Force the laser to be active
rt._laser_active = True
rt._laser_end_x = INTERNAL_W * 0.55
rt._laser_end_y = -50  # off-screen above

# Another short update to render
for _ in range(30):
    rt.update(1.0 / 60)

surf2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
game_scene.draw(surf2)
scaled2 = pygame.transform.scale(surf2, (INTERNAL_W * 4, INTERNAL_H * 4))
out2 = Path("tools/playtest_out/polish_22_charge_aura.png")
pygame.image.save(scaled2, str(out2))
print(f"Saved: {out2}")

print("\nDone.")
