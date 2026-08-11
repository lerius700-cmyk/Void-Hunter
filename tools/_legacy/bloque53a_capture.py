"""BLOQUE 53a: visual frames of GOLIATH shield charge + laser."""
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
from src.systems.projectile import BULLET_PLAYER, OWNER_PLAYER

print("=" * 60)
print("BLOQUE 53a: GOLIATH shield charge + charged laser")
print("=" * 60)

game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.transition_to(GameState.BOSS_INTRO)
game.scenes.transition_to(GameState.BOSS_FIGHT)
boss_scene = game.scenes.scenes[GameState.BOSS_FIGHT]
boss_scene.on_enter()
rt = boss_scene._rt
if rt._boss is not None:
    rt._boss.phase = 1
    rt._boss.hp = rt._boss.max_hp
    rt._boss.x = INTERNAL_W / 2
    rt._boss.y = 100.0
    rt._boss_entry_t = 2.0
rt._player.x = INTERNAL_W / 2
rt._player.y = INTERNAL_H - 80

# ---- Frame 1: shield at ~50% charge ----
print("\n--- Frame 1: shield at ~50% charge ---")
rt._boss_shield_hits = 10
# Tick a frame so visuals update
rt.update(1.0 / 60)
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * 4, INTERNAL_H * 4))
out1 = Path("tools/playtest_out/polish_35_shield_half.png")
pygame.image.save(scaled, str(out1))
print(f"Saved: {out1}")

# ---- Frame 2: shield at 100% charge (just before laser) ----
print("\n--- Frame 2: shield at full charge (about to fire laser) ---")
rt._boss_shield_hits = 20
# Don't trigger laser yet — render the full-charge shield
rt.update(1.0 / 60)
surf2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf2)
scaled2 = pygame.transform.scale(surf2, (INTERNAL_W * 4, INTERNAL_H * 4))
out2 = Path("tools/playtest_out/polish_36_shield_full.png")
pygame.image.save(scaled2, str(out2))
print(f"Saved: {out2}")

# ---- Frame 3: laser firing (0.5s into the 1s) ----
print("\n--- Frame 3: charged laser firing ---")
# Trigger the laser manually
rt._start_shield_laser()
# Move player into the beam
rt._player.x = INTERNAL_W / 2 - 30
rt._player.y = INTERNAL_H / 2
# Tick a few frames for the laser to be visible
for _ in range(int(0.4 * 60)):
    rt.update(1.0 / 60)
surf3 = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf3)
scaled3 = pygame.transform.scale(surf3, (INTERNAL_W * 4, INTERNAL_H * 4))
out3 = Path("tools/playtest_out/polish_37_shield_laser.png")
pygame.image.save(scaled3, str(out3))
print(f"Saved: {out3}")

print("\nDone.")
