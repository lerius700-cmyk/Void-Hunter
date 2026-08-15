"""BLOQUE 58.7x: end-to-end test for the sub-boss spawn + render flow.

Verifies that:
1. The sub-boss is spawned after SUB_BOSS_INTRO returns to GAMEPLAY
2. The sub-boss is positioned visibly (y >= 0)
3. The sub-boss is drawn to the screen surface (not transparent)
4. The sub-boss is alive for several frames
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


def _noop_transition(_state):
    pass


def _make_runtime():
    from src.ui.gameplay_runtime import GameplayRuntime
    rt = GameplayRuntime(transition_to=_noop_transition, is_boss=False, act=1)
    rt.on_enter()
    return rt


def test_sub_boss_spawns_at_visible_y():
    """Sub-boss should spawn at y=0 (top edge) so it's visible."""
    from src.entities.enemies.enemy import EnemyKind
    rt = _make_runtime()
    # Mark chain as pending sub-boss (post-O2 state)
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    # Resume from sub-boss intro
    rt.on_enter()
    # Tick once to spawn
    rt.update(1.0 / 60.0)
    # Find the sub-boss
    sub = None
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            sub = e
            break
    assert sub is not None, "sub-boss not spawned"
    assert sub.y >= 0, f"sub-boss spawned off-screen: y={sub.y}"
    assert sub.y < 50, f"sub-boss spawned too far from top: y={sub.y}"


def test_sub_boss_visible_after_ticks():
    """Sub-boss should be visible (drawn) for several frames after spawn."""
    from src.entities.enemies.enemy import EnemyKind
    rt = _make_runtime()
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    rt.on_enter()
    # Tick several frames
    for _ in range(10):
        rt.update(1.0 / 60.0)
    # Find the sub-boss
    sub = None
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            sub = e
            break
    assert sub is not None, "sub-boss not alive after 10 frames"
    # Sub-boss should be moving down
    assert sub.y > 0, f"sub-boss not moving: y={sub.y}"
    assert sub.y < 200, f"sub-boss too far down: y={sub.y}"


def test_sub_boss_drawn_to_screen():
    """Sub-boss should actually appear when drawn to a screen surface."""
    from src.entities.enemies.enemy import EnemyKind
    rt = _make_runtime()
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    rt.on_enter()
    # Tick to spawn and move it into the screen
    for _ in range(30):
        rt.update(1.0 / 60.0)
    # Find the sub-boss
    sub = None
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            sub = e
            break
    assert sub is not None, "sub-boss not spawned"
    # Draw the runtime to a 320x480 surface
    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    rt.draw(surf)
    # Sample the area around the sub-boss position
    sx, sy = int(sub.x), int(sub.y)
    # Count non-black pixels in a 40x40 box around the sub-boss
    non_black = 0
    for dy in range(-20, 20):
        for dx in range(-20, 20):
            px, py = sx + dx, sy + dy
            if 0 <= px < 320 and 0 <= py < 480:
                r, g, b, *_ = surf.get_at((px, py))
                if r > 30 or g > 30 or b > 30:
                    non_black += 1
    assert non_black > 10, (
        f"sub-boss area is mostly black ({non_black} non-black pixels); "
        f"sub-boss at ({sx}, {sy}) is invisible"
    )


def test_sub_boss_dispatch_does_not_loop():
    """After sub-boss is alive, the SUB_BOSS_INTRO transition should not re-fire."""
    rt = _make_runtime()
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    rt.on_enter()
    transitions = []
    real_transition = rt._transition_to
    def capture(state):
        transitions.append(state)
    rt._transition_to = capture
    # Tick several frames
    for _ in range(10):
        rt.update(1.0 / 60.0)
    rt._transition_to = real_transition
    # No transitions to SUB_BOSS_INTRO should have happened
    from src.core.scene_manager import GameState
    sub_boss_intros = [s for s in transitions if s == GameState.SUB_BOSS_INTRO]
    assert len(sub_boss_intros) == 0, (
        f"SUB_BOSS_INTRO re-fired {len(sub_boss_intros)} times after resume"
    )
