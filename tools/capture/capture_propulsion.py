"""BLOQUE 58.7x: capture a screenshot of the new ultra-neon propulsion trail."""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))


def _noop(_state):
    pass


def capture():
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.player.player import PlayerState
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    # Set player to PROPULSION state, in the middle of the screen
    rt._player.state = PlayerState.PROPULSION
    rt._player.x = 160.0
    rt._player.y = 350.0
    # Disable mouse aim so the player doesn't auto-aim
    # Emit a long stream of propulsion particles over many frames
    # (we reset the timer each time so the trail is dense for the snapshot)
    # The player moves UP (y decreases) so the trail extends downward,
    # like in real gameplay when the player is flying forward.
    for i in range(40):
        rt._player.propulsion_trail_timer = 1.0  # force above interval
        rt._player.y -= 8  # move up each frame
        rt._emit_propulsion_trail(1.0 / 60.0)
    # Render
    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    rt.draw(surf)
    out = ROOT / "tools" / "playtest_out" / "propulsion_v1.26.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(out))
    print(f"Saved {out}")
    # Count non-black pixels in the trail area
    non_black = 0
    for dy in range(0, 100):
        for dx in range(100, 220):
            r, g, b, *_ = surf.get_at((dx, 350 + dy))
            if r > 30 or g > 30 or b > 30:
                non_black += 1
    print(f"{non_black} non-black pixels in 120x100 trail area")


if __name__ == "__main__":
    capture()
