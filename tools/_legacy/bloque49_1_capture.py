"""BLOQUE 49.1: visual frame of LOCAL energy aura around player.

Aura is now concentrated around the ship (radius 16-20px), not from
screen edges. Particles spawn in a ring around player, flow inward,
short life (0.25s) so they look "absorbed".
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

print("=" * 60)
print("BLOQUE 49.1: local energy aura around player")
print("=" * 60)

game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game_scene = game.scenes.scenes[GameState.GAMEPLAY]
game_scene.on_enter()
rt = game_scene._rt
p = rt._player
p.invuln_frames = 999999

# Position the player a bit off-center
p.x = INTERNAL_W * 0.30
p.y = INTERNAL_H * 0.65

# ---- Frame 1: L1 charge (light aura) ----
print("\n--- Frame 1: L1 charge (light local aura) ---")
p._enter_charge()
p.charge_time = 0.10  # L1
p.input_fire = True
# Keep updating for a bit so the aura ring is visible
for _ in range(int(0.5 * 60)):
    rt.update(1.0 / 60)
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
game_scene.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * 4, INTERNAL_H * 4))
out1 = Path("tools/playtest_out/polish_23_local_aura_l1.png")
pygame.image.save(scaled, str(out1))
print(f"Saved: {out1}")

# ---- Frame 2: L3 charge (bright aura + active laser) ----
print("\n--- Frame 2: L3 charge (bright local aura + laser) ---")
p.charge_time = 1.5  # well into L3 laser
rt._laser_active = True
rt._laser_end_x = INTERNAL_W * 0.50
rt._laser_end_y = -50
# Update a few more frames so particles accumulate around the ship
for _ in range(int(0.4 * 60)):
    rt.update(1.0 / 60)
surf2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
game_scene.draw(surf2)
scaled2 = pygame.transform.scale(surf2, (INTERNAL_W * 4, INTERNAL_H * 4))
out2 = Path("tools/playtest_out/polish_24_local_aura_l3.png")
pygame.image.save(scaled2, str(out2))
print(f"Saved: {out2}")

print("\nDone.")
