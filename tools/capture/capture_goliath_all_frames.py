"""BLOQUE 66.6: capture GOLIATH rendering every frame of every animation
into one strip per anim, at 4x zoom. The bug we're hunting is
"GOLIATH looks cortado in some animations (like javelin)" — a runtime
visual problem, not a source-PNG problem, so we need to see what the
runtime actually paints.
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
out_dir.mkdir(parents=True, exist_ok=True)

ANIMS = ["phase1_idle", "javelin", "laser", "purple_bullet"]

# Build per-frame captures
for anim in ANIMS:
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    rt._boss_entry_t = 2.0
    rt._boss_shield_hits = 8  # mid-charge so shield is visible
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
        pygame.image.save(surf, str(out_dir / f"goliath_runtime_{anim}_f{i:02d}.png"))
    print(f"captured {anim}: 10 frames")
