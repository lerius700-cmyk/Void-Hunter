"""BLOQUE 66.6: final visual verification.

Render each GOLIATH animation state at the runtime's actual world scale
(twice as wide as internal — same as default window), with the boss
mid-charge (8 hits so the shield is showing), and produce a strip showing
the boss area only. The user can compare this against the earlier
"NO_BP" strip to confirm javelin and similar poses no longer look
"cortado".
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.ui.gameplay_runtime import GameplayRuntime
from src.entities.enemies.boss import BOSS_CONFIGS

out_dir = ROOT / "tools" / "playtest_out"
ANIMS = ["phase1_idle", "javelin", "laser", "purple_bullet"]

for anim in ANIMS:
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    rt._boss_entry_t = 2.0
    rt._boss_shield_hits = 8
    b = rt._boss
    cfg = BOSS_CONFIGS[b.id]
    b.x = cfg.anchor_x
    b.y = cfg.anchor_y
    b.move_t = 0.0
    b.hp = b.max_hp
    b.phase = 1
    b.animation_state = anim
    for i in range(10):
        b.animation_frame = i
        b.animation_timer = 0.0
        surf = pygame.Surface((320, 480))
        surf.fill((8, 8, 20))
        rt.draw(surf)
        cropped = surf.subsurface(pygame.Rect(40, 0, 240, 200))
        pygame.image.save(
            cropped,
            str(out_dir / f"final_{anim}_f{i:02d}.png"),
        )
    print(f"final {anim}: 10 frames captured")
