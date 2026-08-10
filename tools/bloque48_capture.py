"""BLOQUE 48: visual frame of the chained wave system.

Shows the level 1 mode with 4 waves of enemies entering in sequence.
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
from src.core.settings import INTERNAL_W, INTERNAL_H, INTERNAL_W, INTERNAL_H  # noqa: F401

print("=" * 60)
print("BLOQUE 48: chained wave system visual frame")
print("=" * 60)

game = Game()
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
scene = game.scenes.scenes[GameState.GAMEPLAY]
scene.on_enter()
rt = scene._rt
p = rt._player
p.invuln_frames = 999999

# Run a few frames to spawn wave 0 enemies
for f in range(int(8 * 120)):  # 8s
    rt.update(1.0 / 120)

print(f"After 8s: {rt._enemies.active_count} enemies, current_wave={rt._level1_chain.current_wave_idx}")

# Move player to mid-screen
rt._player.x = INTERNAL_W / 2
rt._player.y = INTERNAL_H * 0.75
# Set mouse position
rt._mouse_x = INTERNAL_W * 0.5
rt._mouse_y = INTERNAL_H * 0.30

# Capture frame
scale = 4
surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
game.scenes.draw(surf)
scaled = pygame.transform.scale(surf, (INTERNAL_W * scale, INTERNAL_H * scale))
out_path = Path("tools/playtest_out/polish_20_chained_waves.png")
out_path.parent.mkdir(parents=True, exist_ok=True)
pygame.image.save(scaled, str(out_path))
print(f"Saved frame to {out_path}")
