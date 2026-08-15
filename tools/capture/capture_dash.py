"""BLOQUE 58.7aa: capture a screenshot during a DASH to verify the
after-image trail is drawn correctly (8 ghosts fading behind the player).
"""
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
    # Put the player in the middle of the screen in DASH state, with
    # some afterimages already populated
    rt._player.x = 160.0
    rt._player.y = 240.0
    rt._player.state = PlayerState.DASH
    # Manually populate 8 afterimages behind the player
    rt._player.afterimage.clear()
    for i in range(8):
        rt._player.afterimage.append(
            (160.0 - i * 6, 240.0 + i * 2, i * 0.015)
        )
    # Render
    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    rt.draw(surf)
    out = ROOT / "tools" / "playtest_out" / "dash_v1.28.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(out))
    print(f"Saved {out}")
    print(f"afterimage count: {len(rt._player.afterimage)}")


if __name__ == "__main__":
    capture()
