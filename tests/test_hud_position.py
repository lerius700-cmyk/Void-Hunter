"""BLOQUE 58.7ab: test that the HUD is at the BOTTOM of the screen.

User feedback: the HUD at the top was covering the sub-boss that
spawns at y=20. The HUD must be at the BOTTOM so it does not block
incoming ships or the sub-boss.
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


def test_hud_appears_at_bottom() -> None:
    """The HUD must render in the BOTTOM half of the playfield so it
    does not cover ships spawning from the top. This test checks
    the HUD source code directly: the draw() method must START at
    the bottom (y = INTERNAL_H - height) instead of the top (y = 0).
    """
    import inspect
    from src.ui.hud import HUD
    src = inspect.getsource(HUD.draw)
    # The old (top) position: y = HUD_MARGIN at the start
    # The new (bottom) position: y = INTERNAL_H - left_col_h
    assert "y = INTERNAL_H - left_col_h" in src, (
        "HUD.draw() still starts at the top. Expected "
        "'y = INTERNAL_H - left_col_h' to anchor the HUD to the bottom."
    )
    # And the score is at the bottom
    import inspect as _i
    score_src = _i.getsource(HUD._draw_score)
    assert "INTERNAL_H - SCORE_FONT_SIZE" in score_src, (
        "Score is not at the bottom. Expected "
        "'INTERNAL_H - SCORE_FONT_SIZE' in _draw_score."
    )


def test_sub_boss_visible_with_hud_at_bottom() -> None:
    """Sub-boss spawned at y=20 should now be VISIBLE (not covered by
    HUD which is now at the bottom).
    """
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.enemies.enemy import EnemyKind
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    # Initialize the chain via on_enter (must be first)
    rt.on_enter()
    # Now set the chain to post-O2 state
    assert rt._level1_chain is not None, "level1 chain not initialized"
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    # Re-enter to apply the resume-from-sub-boss path
    rt.on_enter()
    rt.update(1.0 / 60.0)
    for _ in range(5):
        rt.update(1.0 / 60.0)
    sub = None
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            sub = e
            break
    assert sub is not None, "sub-boss not spawned"
    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    rt.draw(surf)
    # Count non-black pixels in the sub-boss area
    sx, sy = int(sub.x), int(sub.y)
    non_black = 0
    for dy in range(-15, 15):
        for dx in range(-15, 15):
            px, py = sx + dx, sy + dy
            if 0 <= px < 320 and 0 <= py < 480:
                r, g, b, *_ = surf.get_at((px, py))
                if r > 30 or g > 30 or b > 30:
                    non_black += 1
    assert non_black > 20, (
        f"sub-boss at ({sx}, {sy}) is mostly invisible: "
        f"only {non_black} non-black pixels in 30x30 box"
    )
