"""BLOQUE 73.2: capture GOLIATH's shield in 3 charge states (0 / 12 / 19
hits) so the user can confirm the oval is mounted on the shield plate and
recolours iron -> mid blue -> cyan-white.
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

rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
rt.on_enter()
rt._boss_entry_t = 2.0
b = rt._boss
cfg = BOSS_CONFIGS[b.id]
b.x = cfg.anchor_x
b.y = cfg.anchor_y
b.move_t = 0.0
b.hp = b.max_hp
b.phase = 1
b.animation_state = "phase1_idle"
b.animation_frame = 0
b.animation_timer = 0.0

# 3 charge states side by side: 0 hits, 12 hits, 19 hits (near full).
panels = []
for hits, label in ((0, "gray"), (12, "mid"), (19, "cyan")):
    rt._boss_shield_hits = hits
    surf = pygame.Surface((320, 480))
    surf.fill((8, 8, 20))
    rt.draw(surf)
    crop = surf.subsurface(pygame.Rect(60, 0, 200, 160))
    panels.append((crop, label))

# Stitch horizontally with generous padding.
ZOOM = 3
cw, chh = 200 * ZOOM, 160 * ZOOM
pad = 10 * ZOOM
canvas = pygame.Surface((cw * 3 + pad * 4, chh + pad * 2))
canvas.fill((24, 24, 34))
for i, (panel, _label) in enumerate(panels):
    big = pygame.transform.scale(panel, (cw, chh))
    canvas.blit(big, (pad + i * (cw + pad), pad))
pygame.image.save(canvas, str(out / "goliath_shield_3states_bloque73.png"))
print(f"wrote {out / 'goliath_shield_3states_bloque73.png'}")
print("  panel 1 = 0 hits (iron)")
print("  panel 2 = 12 hits (mid blue)")
print("  panel 3 = 19 hits (bright cyan-white)")