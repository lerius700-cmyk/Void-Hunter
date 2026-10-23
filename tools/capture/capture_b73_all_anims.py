"""BLOQUE 73.3: capture every frame of every GOLIATH animation at 4x, so we
can confirm the restored BLOQUE 65 frames actually animate and that the
javelin poses read as complete bodies (not the "cortado" silhouette the
user reported at the start of the session).
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

out = ROOT / "tools" / "playtest_out"
ANIMS = ["phase1_idle", "phase2_idle", "javelin", "laser", "purple_bullet", "death"]

rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
rt.on_enter()
rt._boss_entry_t = 2.0
rt._boss_shield_hits = 8  # mid-charge so the shield is visible in-frame
b = rt._boss
cfg = BOSS_CONFIGS[b.id]
b.x = cfg.anchor_x
b.y = cfg.anchor_y
b.move_t = 0.0
b.hp = b.max_hp
b.phase = 1

ZOOM = 4
CW, CH = 120 * ZOOM, 110 * ZOOM   # crop region scaled
PAD = 6 * ZOOM
CROP_X, CROP_Y, CROP_W, CROP_H = 80, 8, 120, 110

for anim in ANIMS:
    b.animation_state = anim
    b.animation_timer = 0.0
    frames = []
    for i in range(10):
        b.animation_frame = i
        surf = pygame.Surface((320, 480))
        surf.fill((8, 8, 20))
        rt.draw(surf)
        crop = surf.subsurface(pygame.Rect(CROP_X, CROP_Y, CROP_W, CROP_H))
        frames.append(pygame.transform.scale(crop, (CW, CH)))
    canvas = pygame.Surface((CW * 10 + PAD * 11, CH + PAD * 2))
    canvas.fill((20, 20, 30))
    for i, fr in enumerate(frames):
        canvas.blit(fr, (PAD + i * (CW + PAD), PAD))
    path = out / f"b73_{anim}_10f.png"
    pygame.image.save(canvas, str(path))
    print(f"wrote {path.name}")