"""BLOQUE 52: visual frames of GOLIATH's spear throw mechanic.

Captures:
  - polish_32_goliath_winding: spear being pulled back for the throw
  - polish_33_goliath_spear_flight: the main spear serpentining in flight
  - polish_34_goliath_spear_split: 3 fragments spreading in cone after split
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
from src.entities.boss_spear import BossSpear

print("=" * 60)
print("BLOQUE 52: GOLIATH spear throw + serpentine + split")
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

# ---- Frame 1: winding (spear pulled back) ----
print("\n--- Frame 1: GOLIATH winding spear ---")
rt._start_goliath_spear_throw()
# Advance to ~80% of the wind-up
for _ in range(int(0.24 * 60)):
    rt.update(1.0 / 60)
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * 4, INTERNAL_H * 4))
out1 = Path("tools/playtest_out/polish_32_goliath_winding.png")
pygame.image.save(scaled, str(out1))
print(f"Saved: {out1}")

# ---- Frame 2: main spear in flight (serpentine) ----
print("\n--- Frame 2: GOLIATH spear serpentining in flight ---")
# Wait for the wind-up to complete and spear to spawn
for _ in range(int(0.15 * 60)):
    rt.update(1.0 / 60)
# Spear should be in "thrown" state and moving
print(f"  Boss spears in flight: {len(rt._boss_spears)}")
print(f"  Phase: {rt._boss_spear_phase}")
# Advance more to let the spear move and serpentine
for _ in range(int(0.8 * 60)):
    rt.update(1.0 / 60)
surf2 = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf2)
scaled2 = pygame.transform.scale(surf2, (INTERNAL_W * 4, INTERNAL_H * 4))
out2 = Path("tools/playtest_out/polish_33_goliath_spear_flight.png")
pygame.image.save(scaled2, str(out2))
print(f"Saved: {out2}")

# ---- Frame 3: 3 fragments after split ----
print("\n--- Frame 3: GOLIATH spear fragments in cone ---")
# Force a split scenario: set main spear to 1 HP, spawn a bullet, hit
# Reset: clear spears, spawn a fresh one
rt._boss_spears.clear()
rt._boss_spear_phase = "thrown"  # don't re-spawn
# Manually create a main spear ready to be killed
from src.entities.boss_spear import BossSpear
main = BossSpear(
    active=True, kind="main", is_main=True,
    x=INTERNAL_W / 2, y=200, base_vx=0.0, base_vy=1.0,
    perp_vx=1.0, perp_vy=0.0,
    speed=160.0, wave_amp=15.0, wave_freq_hz=1.5,
    wave_amp_growth=8.0, hp=1, max_hp=3, damage=2, life=2.0, max_life=2.0,
)
rt._boss_spears.append(main)
# Spawn a player bullet right on the spear
from src.systems.projectile import BULLET_PLAYER, OWNER_PLAYER
bullet = rt._bullets.spawn(
    BULLET_PLAYER, INTERNAL_W / 2, 200, 0.0, -480.0,
    damage=1, owner=OWNER_PLAYER,
)
# Directly call collision handler (the bullet would be moved by
# _bullets.update() before the regular collision pass, so we
# bypass that and just trigger the hit)
if bullet is not None:
    rt._handle_spear_collisions(rt._player.hitbox)
# After kill, 3 fragments should be flying in a cone
print(f"  Boss spears after split: {len(rt._boss_spears)}")
for sp in rt._boss_spears:
    print(f"    kind={sp.kind} pos=({sp.x:.0f}, {sp.y:.0f})")
# Advance a bit to see the cone spread
for _ in range(int(0.3 * 60)):
    rt.update(1.0 / 60)
surf3 = pygame.Surface((INTERNAL_W, INTERNAL_H))
boss_scene.draw(surf3)
scaled3 = pygame.transform.scale(surf3, (INTERNAL_W * 4, INTERNAL_H * 4))
out3 = Path("tools/playtest_out/polish_34_goliath_spear_split.png")
pygame.image.save(scaled3, str(out3))
print(f"Saved: {out3}")

print("\nDone.")
