"""BLOQUE 47: capture a visual frame showing the new features.
- Aim reticle (yellow crosshair)
- Player banking (Arwing with roll)
- SQUADRON formation (5 enemies in leader+followers choreography)
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_INVULN"] = "1"
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
from src.core.game import Game
from src.core.scene_manager import GameState
from src.systems.wave_manager import parse_formation, spawn_formation, Spawn
from src.entities.enemies.enemy import EnemyKind
from src.core.settings import INTERNAL_W, INTERNAL_H

print("=" * 60)
print("BLOQUE 47: visual frame capture")
print("=" * 60)

# Build the game
game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
scene = game.scenes.scenes[GameState.GAMEPLAY]
rt = scene._rt  # GameplayRuntime is wrapped by GameplayScene
# Skip the auto-start
rt._wave_spawn_timer = 0.0

# Manually populate wave 2 as a SQUADRON
formation = parse_formation({
    "formation_type": "squadron",
    "enemy_type": "SCOUT",
    "count": 5,
    "spacing_px": 24,
    "entry_axis": "top",
    "pattern_speed": 50,
    "telegraph_frames": 30,
})
spawns = spawn_formation(formation)
# Spawn each enemy with the squadron fields tagged
for i, sp in enumerate(spawns):
    e = rt._enemies.spawn(EnemyKind.SCOUT, sp.x, sp.y)
    if e is not None:
        e.squadron_id = 100  # fixed id for the visual
        e.squadron_origin_x = float(sp.x)
        e.squadron_time_offset = float(sp.time_offset_s)
        e.squadron_age = 0.0
        if sp.time_offset_s > 0.0:
            e.squadron_age = -sp.time_offset_s

# Move the player to mid-screen
rt._player.x = INTERNAL_W / 2
rt._player.y = INTERNAL_H * 0.75
# Set mouse position (offset from player to show banking)
rt._mouse_x = INTERNAL_W * 0.65
rt._mouse_y = INTERNAL_H * 0.40
# Set player tilt to show banking
rt._player.input_left = True
# Run a few frames to advance the squadron
import math
for frame in range(45):  # ~0.75s
    game.scenes.update(1.0 / 60)
    # Apply tilt to player
    if rt._player.input_left and rt._player.vx < -10:
        pass  # tilt is computed in update

# Force the mouse position so the reticle shows up in the captured frame
# (headless dummy SDL returns (0,0) from pygame.mouse.get_pos, but we want
# to see the reticle in the visual frame)
rt._mouse_x = INTERNAL_W * 0.65
rt._mouse_y = INTERNAL_H * 0.40
# Force player tilt to show banking
rt._player.input_left = True
for _ in range(8):
    rt._player.update(1.0 / 60)

# Capture frame
print(f"Enemies alive: {rt._enemies.active_count}")
for e in rt._enemies.pool:
    if e.active:
        print(f"  Enemy pos=({e.x:.1f}, {e.y:.1f}) squadron_id={e.squadron_id} offset={e.squadron_time_offset:.1f}")

# Render to a 4x scale and save
scale = 4
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
game.scenes.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * scale, INTERNAL_H * scale))
out_path = Path("tools/playtest_out/polish_19_squadron.png")
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(scaled, str(out_path))
print(f"Saved frame to {out_path}")
print(f"Size: {scaled.get_size()}")
