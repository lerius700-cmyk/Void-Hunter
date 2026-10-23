"""BLOQUE 66.6: capture javelin runtime WITHOUT backplate, save alongside
the WITH-backplate capture, so we can do a true before/after diff.
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
from src.ui.scenes import _goliath_backplate_cache

out_dir = ROOT / "tools" / "playtest_out"


def capture(anim: str, backplate_enabled: bool) -> None:
    if not backplate_enabled:
        # Force the runtime to "skip" the backplate by nulling the cache.
        _goliath_backplate_cache = None
        # Mark as "loaded" with None so the helper returns None.
        from src.ui import scenes as sc
        sc._goliath_backplate_cache = None
        sc._goliath_backplate_loaded = True
    else:
        # Reset and reload from disk.
        from src.ui import scenes as sc
        sc._goliath_backplate_cache = None
        sc._goliath_backplate_loaded = False
        sc._load_goliath_backplate()

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
    suffix = "WITH_bp" if backplate_enabled else "NO_bp"
    for i in range(10):
        b.animation_frame = i
        b.animation_timer = 0.0
        surf = pygame.Surface((320, 480))
        surf.fill((8, 8, 20))
        rt.draw(surf)
        # Crop to the boss area for clarity.
        cropped = surf.subsurface(pygame.Rect(40, 0, 240, 200))
        pygame.image.save(cropped, str(out_dir / f"goliath_{anim}_f{i:02d}_{suffix}.png"))
    print(f"captured {anim} {suffix}")


if __name__ == "__main__":
    capture("javelin", backplate_enabled=False)
    capture("javelin", backplate_enabled=True)
    capture("phase1_idle", backplate_enabled=False)
    capture("phase1_idle", backplate_enabled=True)
