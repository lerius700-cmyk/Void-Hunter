"""BLOQUE 58.7x: tests for ultra-neon propulsion + visible sub-boss spawn."""
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


def test_propulsion_trail_has_six_particles_per_engine() -> None:
    """BLOQUE 58.7x: trail emits 6 particles per engine (was 4)."""
    rt = _make_runtime()
    # Get the source of _emit_propulsion_trail and count emits
    import inspect
    src = inspect.getsource(rt._emit_propulsion_trail)
    # Count P_SPARK and P_GLOW and P_SMOKE emit calls
    spark_count = src.count("P_SPARK,")
    glow_count = src.count("P_GLOW,")
    smoke_count = src.count("P_SMOKE,")
    assert spark_count >= 2, f"expected >= 2 P_SPARK emits, got {spark_count}"
    assert glow_count >= 3, f"expected >= 3 P_GLOW emits, got {glow_count}"
    assert smoke_count >= 1, f"expected >= 1 P_SMOKE emit, got {smoke_count}"


def test_propulsion_trail_uses_neon_electric_palette() -> None:
    """BLOQUE 58.7x: trail uses the ultra-neon electric blue palette."""
    rt = _make_runtime()
    import inspect
    src = inspect.getsource(rt._emit_propulsion_trail)
    # Must include the white plasma core color
    assert "(220, 250, 255)" in src, "missing white-hot plasma core color"
    # Must include the electric blue color
    assert "(60, 180, 255)" in src, "missing electric blue color"
    # Must include the cyan-white halo
    assert "(140, 230, 255)" in src, "missing cyan-white halo color"
    # Must include the violet edge
    assert "(130, 80, 255)" in src, "missing violet edge color"
    # Must include the deep navy smoke
    assert "(30, 90, 220)" in src, "missing deep navy smoke color"


def test_sub_boss_spawns_fully_inside_playfield() -> None:
    """BLOQUE 58.7x: sub-boss spawns at y=20 (fully inside playfield)."""
    from src.entities.enemies.enemy import EnemyKind
    rt = _make_runtime()
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    rt.on_enter()
    rt.update(1.0 / 60.0)
    sub = None
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            sub = e
            break
    assert sub is not None, "sub-boss not spawned"
    # The body is 14 tall, centered on the spawn y. To be fully inside,
    # spawn_y - 7 must be >= 0, so spawn_y >= 7.
    assert sub.y >= 7, f"sub-boss spawn y too high: {sub.y} (body would clip)"
    assert sub.y < 50, f"sub-boss spawn y too low: {sub.y}"


def test_sub_boss_spawn_emits_flash_and_particles() -> None:
    """BLOQUE 58.7x: spawning a sub-boss creates a shockwave + particles
    + screen flash so the dart is impossible to miss."""
    from src.entities.enemies.enemy import EnemyKind
    from src.core.settings import INTERNAL_W
    rt = _make_runtime()
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    rt.on_enter()
    # Snapshot counts before
    pre_shockwaves = len(rt._shockwaves)
    pre_particles = rt._particles.active_count
    rt.update(1.0 / 60.0)
    # After spawn, there should be MORE shockwaves, particles, and a
    # positive screen flash
    assert len(rt._shockwaves) > pre_shockwaves, (
        "sub-boss spawn did not add a shockwave"
    )
    assert rt._particles.active_count > pre_particles, (
        "sub-boss spawn did not emit spawn particles"
    )
    assert rt._screen_flash > 0.0, (
        "sub-boss spawn did not trigger screen flash"
    )


def test_sub_boss_intro_duration_is_long() -> None:
    """BLOQUE 58.7x: SUB_BOSS_INTRO lasts 5.0s for reaction time."""
    from src.ui.scenes import SubBossIntroScene
    scene = SubBossIntroScene(transition_to=_noop_transition)
    assert scene._duration >= 4.5, (
        f"SUB_BOSS_INTRO too short: {scene._duration}s (want >= 4.5s)"
    )
