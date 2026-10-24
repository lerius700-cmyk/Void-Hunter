"""BLOQUE 67: capture del escudo de GOLIATH con la rampa de carga nueva
(rojo al primer impacto -> naranja -> ambar -> blanco caliente) y el
laser grueso naranja.

5 paneles de carga + 1 panel con el laser disparado.
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

STATES = ((0, "0 hits  cold"), (1, "1 hit  RED"), (5, "5 hits  orange"),
          (12, "12 hits  amber"), (20, "20 hits  white hot"))

panels = []
for hits, label in STATES:
    rt._boss_shield_hits = hits
    rt._boss_shield_laser_t = 0.0
    surf = pygame.Surface((320, 480))
    surf.fill((8, 8, 20))
    rt.draw(surf)
    panels.append((surf.subsurface(pygame.Rect(60, 0, 200, 160)), label))

# Panel del laser: 20 hits y el laser disparandose.
rt._boss_shield_hits = 20
rt._boss_shield_laser_t = 0.8
surf = pygame.Surface((320, 480))
surf.fill((8, 8, 20))
rt.draw(surf)
panels.append((surf.subsurface(pygame.Rect(60, 0, 200, 300)), "LASER naranja"))

ZOOM = 3
cw, chh = 200 * ZOOM, 160 * ZOOM
pad = 10 * ZOOM
laser_h = 300 * ZOOM
n = len(panels)
canvas = pygame.Surface((cw * n + pad * (n + 1), laser_h + pad * 2 + 30))
canvas.fill((24, 24, 34))
for i, (panel, label) in enumerate(panels):
    big = pygame.transform.scale(panel, (cw, panel.get_height() * ZOOM))
    canvas.blit(big, (pad + i * (cw + pad), pad))
    font = pygame.font.Font(None, 22)
    txt = font.render(label, True, (230, 230, 240))
    canvas.blit(txt, (pad + i * (cw + pad) + 6, laser_h + pad + 6))

pygame.image.save(canvas, str(out / "goliath_shield_charge_bloque67.png"))
print(f"wrote {out / 'goliath_shield_charge_bloque67.png'}")
for hits, label in STATES:
    print(f"  {label}")
print("  LASER naranja (grueso)")
