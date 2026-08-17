"""Capture a screenshot of the gameplay with mountains + dust + thrusters.

Renders 1.5 seconds of wave 1 to a 1920x1080 PNG so the user can
review the new scenery without launching the game interactively.
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


def main():
    out_dir = ROOT / "tools" / "playtest_out"
    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()

    # Simulate the player moving forward (right) and thrusting so
    # the thruster trail is visible. The mountains and dust scroll
    # automatically.
    s.player.x, s.player.y = 80.0, 150.0
    s.player.thrusting = True
    # Tick enough to get a representative frame: 1.5s of game time.
    for _ in range(int(1.5 * 120)):
        s._keys = {pygame.K_d: True, pygame.K_RIGHT: True}
        s.player.firing = True
        s.update(1 / 120, [])

    internal = pygame.Surface((480, 270))
    s.draw(internal)
    scaled = pygame.transform.scale(internal, (1920, 1080))
    out_path = out_dir / "scenery_preview.png"
    out_dir.mkdir(parents=True, exist_ok=True)
    pygame.image.save(scaled, str(out_path))
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
