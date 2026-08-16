"""Capture a screenshot of Stellar Horizon gameplay with the new sprites.

Renders the gameplay scene to an internal 480x270 surface, upscales 4x
to 1920x1080, and saves to tools/playtest_out/sprites_preview.png so
the user can see how the 16-bit pixel-art sprites look in-game without
having to launch the game interactively.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import sys
from pathlib import Path

ROOT = Path("D:/AI/void-hunter")
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene

midi = MidiPlayer()
scene = GameplayScene(
    midi_player=midi,
    wave_json=Path("stellar_horizon/waves/waves_act1.json"),
    assets_dir=Path("stellar_horizon/assets"),
)
scene.on_enter()

# Tick a few frames so wave manager spawns the first wave of enemies.
for _ in range(int(2.0 * 120)):  # 2 seconds at 120 fps
    scene.update(1 / 120, [])

# Render to the internal surface, upscale 4x to 1920x1080, save.
internal = pygame.Surface((480, 270))
scene.draw(internal)
scaled = pygame.transform.scale(internal, (1920, 1080))

out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "sprites_preview.png"
pygame.image.save(scaled, str(out_path))
print(f"Saved: {out_path}")
