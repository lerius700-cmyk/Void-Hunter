"""BLOQUE 51: visual frames of the redesigned GOLIATH boss.

Captures:
  - polish_29_goliath_phase1: GOLIATH at full HP (phase 1)
  - polish_30_goliath_phase2: GOLIATH in phase 2 (armor cracked, eyes brighter)
  - polish_31_goliath_hit: GOLIATH with hit flash
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
from src.entities.enemies.boss import BossId

print("=" * 60)
print("BLOQUE 51: GOLIATH biblical giant warrior")
print("=" * 60)

game = Game()

# ---- Frame 1: GOLIATH phase 1 (full HP) ----
print("\n--- Frame 1: GOLIATH phase 1 ---")
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.transition_to(GameState.BOSS_INTRO)
game.scenes.transition_to(GameState.BOSS_FIGHT)
boss_scene = game.scenes.scenes[GameState.BOSS_FIGHT]
boss_scene.on_enter()
rt = boss_scene._rt
# Make sure boss is at anchor (no entry animation overlay)
if rt._boss is not None:
    rt._boss.phase = 1
    rt._boss.hp = rt._boss.max_hp
    rt._boss.x = INTERNAL_W / 2
    rt._boss.y = 100.0
    rt._boss_entry_t = 2.0  # past the entry animation
# Update so animations have a moment to advance
for _ in range(int(0.3 * 60)):
    rt.update(1.0 / 60)
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * 4, INTERNAL_H * 4))
out1 = Path("tools/playtest_out/polish_29_goliath_phase1.png")
pygame.image.save(scaled, str(out1))
print(f"Saved: {out1}")

# ---- Frame 2: GOLIATH phase 2 (HP below 66%) ----
print("\n--- Frame 2: GOLIATH phase 2 (armor cracked) ---")
if rt._boss is not None:
    rt._boss.phase = 2
    rt._boss.hp = int(rt._boss.max_hp * 0.5)  # 50% HP
for _ in range(int(0.3 * 60)):
    rt.update(1.0 / 60)
surf2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf2)
scaled2 = pygame.transform.scale(surf2, (INTERNAL_W * 4, INTERNAL_H * 4))
out2 = Path("tools/playtest_out/polish_30_goliath_phase2.png")
pygame.image.save(scaled2, str(out2))
print(f"Saved: {out2}")

# ---- Frame 3: GOLIATH hit (white flash) ----
print("\n--- Frame 3: GOLIOTH hit (white flash) ---")
if rt._boss is not None:
    rt._boss.phase = 1
    rt._boss.hp = rt._boss.max_hp
    # Trigger a flash
    rt._boss_flash[id(rt._boss)] = 0.10
rt.update(1.0 / 60)  # one frame
surf3 = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf3)
scaled3 = pygame.transform.scale(surf3, (INTERNAL_W * 4, INTERNAL_H * 4))
out3 = Path("tools/playtest_out/polish_31_goliath_hit.png")
pygame.image.save(scaled3, str(out3))
print(f"Saved: {out3}")

print("\nDone.")
