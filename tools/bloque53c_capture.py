"""BLOQUE 53c: visual frames of the new HP bar + gold ring pickup."""
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
print("BLOQUE 53c: HP bar (Mega Man / Star Fox) + gold ring HUD")
print("=" * 60)

game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game_scene = game.scenes.scenes[GameState.GAMEPLAY]
game_scene.on_enter()
rt = game_scene._rt
p = rt._player
p.invuln_frames = 999999
p.x = INTERNAL_W * 0.30
p.y = INTERNAL_H * 0.65

# ---- Frame 1: HP at full (30/30) ----
print("\n--- Frame 1: HP at full ---")
# Update a few frames for HUD animation
for _ in range(int(0.3 * 60)):
    rt.update(1.0 / 60)
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
game_scene.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * 4, INTERNAL_H * 4))
out1 = Path("tools/playtest_out/polish_38_hp_full.png")
pygame.image.save(scaled, str(out1))
print(f"Saved: {out1}")

# ---- Frame 2: HP at 60% (18/30) with 1 gold ring collected ----
print("\n--- Frame 2: HP at 60% + 1 gold ring ---")
p.hp = 18
p.gold_rings = 1
for _ in range(int(0.2 * 60)):
    rt.update(1.0 / 60)
surf2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
game_scene.draw(surf2)
scaled2 = pygame.transform.scale(surf2, (INTERNAL_W * 4, INTERNAL_H * 4))
out2 = Path("tools/playtest_out/polish_39_hp_60_percent_1_ring.png")
pygame.image.save(scaled2, str(out2))
print(f"Saved: {out2}")

# ---- Frame 3: HP doubled after 3 rings (60/60) + tech upgrade HP_BOOST_10 ----
print("\n--- Frame 3: HP doubled (60/60) + 1 tech upgrade ---")
p.hp = 60
p.hp_max = 60
p.hp_doubled = True
p.add_tech_upgrade("HP_BOOST_10")  # adds +6
p.hp = p.hp_max  # refill
for _ in range(int(0.2 * 60)):
    rt.update(1.0 / 60)
surf3 = pygame.Surface((INTERNAL_W, INTERNAL_H))
game_scene.draw(surf3)
scaled3 = pygame.transform.scale(surf3, (INTERNAL_W * 4, INTERNAL_H * 4))
out3 = Path("tools/playtest_out/polish_40_hp_doubled_with_tech.png")
pygame.image.save(scaled3, str(out3))
print(f"Saved: {out3}")

print("\nDone.")
