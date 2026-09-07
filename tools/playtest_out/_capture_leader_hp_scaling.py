"""Capture visual proof of the leader HP scaling (BLOQUE 58.next item #3).

Renders a V_FORMATION at wave 1 (3 hits = 90 HP leader) and wave 10
(5 hits = 150 HP leader) side-by-side, with a mini HP bar overlay on
the leader so the difference is obvious to the eye.
"""
import os
import sys
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import random
import pygame

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.entities.enemies.enemy import EnemyPool
from src.systems.wave_patterns.runtime import spawn_pattern_wave, _KIND_HP
from src.systems.wave_patterns.v_formation import VFormationPattern


def render_with_leader_hp_bar(wave_idx: int) -> pygame.Surface:
    """Render a V_FORMATION at the given wave_idx with a HP bar on the leader."""
    pool = EnemyPool(capacity=16)
    result = VFormationPattern().generate(random.Random(42), level=3)
    spawn_pattern_wave(pool, result, current_wave_idx=wave_idx)
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    surf.fill((0, 0, 0))
    # V_FORMATION spawns at y=-20 (leader) to y=-64 (outer wings) — all
    # off-surface. Apply a y_offset to bring the formation into the
    # playfield for visual capture.
    y_offset = 100
    for e in pool.pool:
        if not e.active:
            continue
        # Ship dot (yellow if leader, white otherwise)
        color = (255, 220, 80) if e.is_leader else (180, 180, 200)
        ship_y = int(e.y) + y_offset
        pygame.draw.circle(surf, color, (int(e.x), ship_y), 6)
        # HP bar above leader
        if e.is_leader:
            max_hp = _KIND_HP["SCOUT"] * 5  # always show as 5-cell bar
            filled = int((e.hp / max_hp) * 30)
            bar_y = ship_y - 16
            pygame.draw.rect(surf, (60, 60, 60), (int(e.x) - 15, bar_y, 30, 4))
            pygame.draw.rect(surf, (80, 220, 120), (int(e.x) - 15, bar_y, filled, 4))
    return surf


def main() -> int:
    pygame.init()
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(exist_ok=True)
    surf_w1 = render_with_leader_hp_bar(0)
    surf_w10 = render_with_leader_hp_bar(9)
    panel_w, panel_h = INTERNAL_W, INTERNAL_H
    label_h = 30
    mosaic = pygame.Surface((panel_w * 2, panel_h + label_h))
    mosaic.fill((20, 20, 20))
    font = pygame.font.SysFont("Consolas", 16, bold=True)
    # Border + panel wave 1
    pygame.draw.rect(mosaic, (60, 60, 60), (0, label_h, panel_w, panel_h), 2)
    mosaic.blit(surf_w1, (0, label_h))
    mosaic.blit(font.render("WAVE 1 — 3 hits (90 HP)", True, (255, 255, 255)), (4, 6))
    # Border + panel wave 10
    pygame.draw.rect(mosaic, (60, 60, 60), (panel_w, label_h, panel_w, panel_h), 2)
    mosaic.blit(surf_w10, (panel_w, label_h))
    mosaic.blit(font.render("WAVE 10 — 5 hits (150 HP)", True, (255, 255, 255)), (panel_w + 4, 6))
    out_path = out_dir / "leader_hp_wave1_vs_wave10.png"
    pygame.image.save(mosaic, str(out_path))
    print(f"saved -> {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
