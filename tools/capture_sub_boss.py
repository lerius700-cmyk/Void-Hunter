"""BLOQUE 58.7x: capture a screenshot of the sub-boss after spawn.

Runs the game in headless mode, ticks the runtime to the sub-boss
spawn state, and saves a PNG of the playfield showing the sub-boss.
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
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    # Jump to the sub-boss resume state
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    rt.on_enter()
    # Spawn the sub-boss
    rt.update(1.0 / 60.0)
    # Tick a few frames so the sub-boss moves into the screen and the
    # spawn flash particles spread out
    for _ in range(8):
        rt.update(1.0 / 60.0)
    # Render to a 320x480 surface
    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    rt.draw(surf)
    out = ROOT / "tools" / "playtest_out" / "sub_boss_v1.26.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(out))
    print(f"Saved {out}")
    # Count non-black pixels in the sub-boss area
    from src.entities.enemies.enemy import EnemyKind
    sub = None
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            sub = e
            break
    if sub:
        sx, sy = int(sub.x), int(sub.y)
        non_black = 0
        for dy in range(-25, 25):
            for dx in range(-25, 25):
                px, py = sx + dx, sy + dy
                if 0 <= px < 320 and 0 <= py < 480:
                    r, g, b, *_ = surf.get_at((px, py))
                    if r > 30 or g > 30 or b > 30:
                        non_black += 1
        print(f"sub-boss at ({sx}, {sy}); {non_black} non-black pixels in 50x50 box")
    # Also check particle density (spawn flash)
    particles = rt._particles.active_count
    print(f"particles alive: {particles}")
    print(f"screen_flash: {rt._screen_flash}")
    print(f"shockwaves: {len(rt._shockwaves)}")


if __name__ == "__main__":
    capture()
