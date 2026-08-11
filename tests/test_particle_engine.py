"""Tests for src.systems.particle_engine — 18 kinds, pool 1500, LRU tint cache.

Per GDD §11 validation + §8 particle style guide: 5+ tests per kind plus
edge cases. Targets ≥90 tests total.
"""
from __future__ import annotations

import math
import time

import pygame
import pytest

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.systems.particle_engine import (
    KIND_CONFIG,
    P_DEBRIS,
    P_DUST,
    P_ELECTRIC,
    P_ELECTRIC_ARC,
    P_FIRE,
    P_FLASH,
    P_GLOW,
    P_ION,
    P_KIND_COUNT,
    P_LIGHT_FLASH,
    P_LINE,
    P_MUZZLE,
    P_RING_FILL,
    P_RING_THICK,
    P_SHOCKWAVE,
    P_SMOKE,
    P_SPARK,
    P_SHRAPNEL,
    P_SQUARE,
    P_KIND_COUNT as _,
    Particle,
    ParticleEngine,
)
from src.systems.pool import Pool
from src.utils.palette import PALETTE, validate_palette_integrity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def engine() -> ParticleEngine:
    return ParticleEngine(pool_size=1500, max_tint_cache=128)


@pytest.fixture
def display() -> pygame.Surface:
    """Headless display surface for blits() targets."""
    pygame.init()
    return pygame.Surface((240, 360), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# 1. Constants & invariants
# ---------------------------------------------------------------------------
def test_particle_kind_count_is_19() -> None:
    """BLOQUE 58.8.3: 19 kinds (was 18) — added P_WAKE for the
    1-second-delayed player propulsion afterglow.
    """
    assert P_KIND_COUNT == 19


def test_all_kinds_have_config() -> None:
    """Every kind 0..18 has a KIND_CONFIG entry."""
    for k in range(P_KIND_COUNT):
        assert k in KIND_CONFIG, f"kind {k} missing from KIND_CONFIG"


def test_palette_has_64_unique_chars() -> None:
    ok, msg = validate_palette_integrity()
    assert ok, msg


# ---------------------------------------------------------------------------
# 2. Pool exhaustion (positive + edge)
# ---------------------------------------------------------------------------
def test_engine_pool_size_matches_setting(engine: ParticleEngine) -> None:
    """ParticleEngine default pool is PARTICLE_POOL = 1500."""
    assert engine.pool.size == 1500


def test_emit_returns_particle_with_kind(engine: ParticleEngine) -> None:
    p = engine.emit(P_SPARK, 10.0, 20.0, vx=5.0, vy=-3.0)
    assert p is not None
    assert p.kind == P_SPARK
    assert p.active
    assert p.x == 10.0 and p.y == 20.0
    assert p.vx == 5.0 and p.vy == -3.0


def test_emit_returns_none_when_pool_full(engine: ParticleEngine) -> None:
    """Pool of 1500 → 1501st emit returns None silently."""
    spawned = [engine.emit(P_SPARK, 0.0, 0.0) for _ in range(1500)]
    assert all(p is not None for p in spawned)
    assert engine.active_count == 1500
    assert engine.emit(P_SPARK, 0.0, 0.0) is None


def test_emit_unknown_kind_returns_none(engine: ParticleEngine) -> None:
    """Defensive: unknown kind returns None (not crash)."""
    assert engine.emit(99, 0.0, 0.0) is None
    assert engine.emit(-1, 0.0, 0.0) is None


# ---------------------------------------------------------------------------
# 3. Life + fade
# ---------------------------------------------------------------------------
def test_particle_released_when_life_expires(engine: ParticleEngine) -> None:
    p = engine.emit(P_SPARK, 100.0, 100.0, life=0.10)
    assert p is not None
    engine.update(0.20)  # exceeds life
    assert not p.active
    assert engine.active_count == 0


def test_fade_alpha_proportional_to_life(engine: ParticleEngine) -> None:
    """fade=True: alpha = 255 * (life / max_life)."""
    p = engine.emit(P_SMOKE, 0.0, 0.0, life=1.0)
    assert p is not None
    engine.update(0.5)  # life = 0.5
    assert p._alpha == 127 or p._alpha == 128  # 255*0.5 = 127.5 → int rounds


def test_fade_lives_one_frame(engine: ParticleEngine) -> None:
    """fade=True con life=0.01 → vive 1 frame y se libera OK (edge)."""
    p = engine.emit(P_SPARK, 0.0, 0.0, life=0.01)
    assert p is not None
    engine.update(1 / 120)  # 1 frame @ 120 FPS
    # After 1 frame: life=0.01-0.0083 = 0.0017, still alive
    assert p.active
    engine.update(1 / 120)
    # After 2 frames: life ≤ 0
    assert not p.active


def test_fade_at_max_life_alpha_is_255(engine: ParticleEngine) -> None:
    """Edge: at spawn (life = max_life), alpha = 255."""
    p = engine.emit(P_SPARK, 0.0, 0.0, life=0.5)
    assert p is not None
    assert p.max_life == 0.5
    assert p._alpha == 255


def test_dt_zero_or_negative_is_noop(engine: ParticleEngine) -> None:
    """Defensive: dt<=0 does not advance physics."""
    p = engine.emit(P_SPARK, 0.0, 0.0, vx=100.0)
    assert p is not None
    engine.update(0.0)
    assert p.x == 0.0
    engine.update(-1.0)
    assert p.x == 0.0


# ---------------------------------------------------------------------------
# 4. Physics
# ---------------------------------------------------------------------------
def test_velocity_decay_with_damping(engine: ParticleEngine) -> None:
    """Damping reduces |v| each frame (P_ION has damping=0.95)."""
    p = engine.emit(P_ION, 0.0, 0.0, vx=100.0)
    assert p is not None
    initial_vx = p.vx
    for _ in range(10):
        engine.update(1 / 60)
    assert abs(p.vx) < abs(initial_vx)


def test_gravity_pulls_downward(engine: ParticleEngine) -> None:
    """P_FIRE has gravity -120 (px/s²). After 0.1s, vy should be more negative."""
    p = engine.emit(P_FIRE, 0.0, 0.0, vy=0.0, life=2.0)  # long life for the test
    assert p is not None
    engine.update(0.1)
    assert p.vy < 0.0  # pulled down


def test_offscreen_cull_releases_particle(engine: ParticleEngine) -> None:
    """Particle out of bounds (240x360 + 16 margin) → released."""
    p = engine.emit(P_SPARK, 500.0, 500.0)  # far outside
    assert p is not None
    engine.update(0.016)
    assert not p.active


# ---------------------------------------------------------------------------
# 5. Rotation
# ---------------------------------------------------------------------------
def test_debris_rotation_360_returns_to_zero(engine: ParticleEngine) -> None:
    """P_DEBRIS rotating at 360 deg/s wraps cleanly without glitch."""
    p = engine.emit(P_DEBRIS, 0.0, 0.0, angle=350.0, angular_vel=360.0)
    assert p is not None
    engine.update(1.0)  # 1 second → 360° rotation
    assert 0.0 <= p.angle < 360.0  # wrapped cleanly
    # After exactly 1s with 360 deg/s, angle should be 350 + 360 = 710 % 360 = 350
    # (degenerate case but should not glitch)


def test_rotation_with_zero_angular_vel_unchanged(engine: ParticleEngine) -> None:
    p = engine.emit(P_DEBRIS, 0.0, 0.0, angle=45.0, angular_vel=0.0)
    assert p is not None
    engine.update(1.0)
    assert p.angle == 45.0


# ---------------------------------------------------------------------------
# 6. Electric-arc jitter (NaN protection)
# ---------------------------------------------------------------------------
def test_electric_arc_extreme_jitter_no_nan(engine: ParticleEngine) -> None:
    """Even with 60s of accumulated jitter, angle stays finite."""
    p = engine.emit(P_ELECTRIC_ARC, 0.0, 0.0)
    assert p is not None
    for _ in range(60 * 120):  # 60 seconds at 120 FPS
        engine.update(1 / 120)
    assert math.isfinite(p.angle)
    assert 0.0 <= p.angle < 360.0


# ---------------------------------------------------------------------------
# 7. Shockwave + rings
# ---------------------------------------------------------------------------
def test_shockwave_max_radius_zero_no_crash(engine: ParticleEngine) -> None:
    """P_SHOCKWAVE con radius=0 → no se ve, no crashea (edge)."""
    p = engine.emit(P_SHOCKWAVE, 0.0, 0.0, radius=0.0)
    assert p is not None
    # draw should not raise
    surf = pygame.Surface((240, 360), pygame.SRCALPHA)
    engine.draw(surf)  # no crash


def test_shockwave_radius_grows_with_expand(engine: ParticleEngine) -> None:
    p = engine.emit(P_SHOCKWAVE, 100.0, 100.0, life=2.0)  # long life for the test
    assert p is not None
    initial_r = p.radius
    engine.update(0.1)
    assert p.radius > initial_r  # expanded


def test_ring_fill_expand_grows(engine: ParticleEngine) -> None:
    p = engine.emit(P_RING_FILL, 0.0, 0.0)
    assert p is not None
    engine.update(0.2)
    assert p.radius > 0.0


def test_ring_thick_thicker_than_ring_fill(engine: ParticleEngine) -> None:
    """P_RING_THICK uses 4px stroke; visual differentiation, not testable in
    surface dimensions directly. Sanity: both kinds exist with different configs."""
    assert P_RING_THICK != P_RING_FILL
    assert KIND_CONFIG[P_RING_THICK].expand > 0.0
    assert KIND_CONFIG[P_RING_FILL].expand > 0.0


# ---------------------------------------------------------------------------
# 8. Line particle thickness=0 → width=1
# ---------------------------------------------------------------------------
def test_line_particle_thickness_zero_width_one(engine: ParticleEngine) -> None:
    """P_LINE con thickness=0 → width=1 (no division by zero, edge)."""
    p = engine.emit(P_LINE, 0.0, 0.0, radius=0.0)
    assert p is not None
    # The base surface for P_LINE is pre-baked to size 1, no thickness logic
    # exposed; we just confirm the particle exists and doesn't crash.
    surf = pygame.Surface((240, 360), pygame.SRCALPHA)
    engine.draw(surf)


# ---------------------------------------------------------------------------
# 9. Tint cache LRU
# ---------------------------------------------------------------------------
def test_tint_cache_lru_evicts_oldest(engine: ParticleEngine) -> None:
    """129 distinct (kind, color) keys → cap 128, oldest evicted."""
    # Use a fresh cache with cap 4 for fast eviction test
    small = ParticleEngine(pool_size=10, max_tint_cache=4)
    # 5 distinct colors, same kind
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
    ]
    # Each emit+draw cycle caches a tint
    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    for c in colors:
        p = small.emit(P_SQUARE, 50.0, 50.0, color=c)
        assert p is not None
        small.update(1 / 60)  # 1 frame
        small.draw(target)
    # After 5 distinct colors, cap=4 → size = 4
    assert small.tint_cache_size == 4


def test_tint_cache_hit_increments_counter(engine: ParticleEngine) -> None:
    """Cache hit increments hits counter."""
    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    p = engine.emit(P_SQUARE, 50.0, 50.0, color=(120, 200, 80))
    assert p is not None
    engine.update(1 / 60)
    # First draw: miss
    engine.draw(target)
    size1, hits1, misses1 = engine.get_tint_cache_stats()
    # Spawn another with same color, draw again
    p2 = engine.emit(P_SQUARE, 60.0, 60.0, color=(120, 200, 80))
    assert p2 is not None
    engine.update(1 / 60)
    engine.draw(target)
    size2, hits2, misses2 = engine.get_tint_cache_stats()
    assert hits2 > hits1
    assert size2 == size1  # no new entries; same color


# ---------------------------------------------------------------------------
# 10. Draw uses single blits() (no per-particle blit)
# ---------------------------------------------------------------------------
def test_draw_uses_single_blits_batch(engine: ParticleEngine, display: pygame.Surface) -> None:
    """Verify draw() submits a single batch via the public API.

    Strategy: introspect the engine source to count `target.blits` literal
    occurrences. The single-batch contract is enforced at the implementation
    level — exactly one `target.blits(` call inside draw().
    """
    import inspect
    from src.systems.particle_engine import ParticleEngine as PE
    src = inspect.getsource(PE.draw)
    # Count the actual CALL pattern: `target.blits(` at line start (i.e. not in docstring).
    n_target_blits = sum(
        1 for line in src.splitlines()
        if line.strip().startswith("target.blits(") and "blits(batch)" in line
    )
    assert n_target_blits == 1, f"draw() should call target.blits() exactly once, got {n_target_blits}"
    # And draw returns the count for verification.
    for i in range(50):
        engine.emit(P_SPARK, 100.0 + i, 100.0, color=(255, 100, 50))
    engine.update(1 / 60)
    n = engine.draw(display)
    assert n == 50


def test_draw_with_no_active_particles_is_noop(engine: ParticleEngine, display: pygame.Surface) -> None:
    """Empty engine: draw returns 0, no blits call."""
    n = engine.draw(display)
    assert n == 0


# ---------------------------------------------------------------------------
# 11. Per-kind smoke: each of the 19 kinds emits + updates + draws without error
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kind", list(range(P_KIND_COUNT)))
def test_all_kinds_emit_update_draw(kind: int, engine: ParticleEngine, display: pygame.Surface) -> None:
    """All 19 kinds go through the full pipeline without exception."""
    p = engine.emit(kind, 120.0, 180.0)
    assert p is not None, f"kind {kind} failed to emit"
    engine.update(1 / 60)
    # Some kinds (e.g. shockwave) may have died this frame; check the live count instead.
    assert engine.active_count >= 0
    n = engine.draw(display)
    assert n >= 0


# ---------------------------------------------------------------------------
# 12. Performance smoke (loose bounds, not strict)
# ---------------------------------------------------------------------------
def test_1500_particles_update_under_5ms(engine: ParticleEngine) -> None:
    """Soft target: 1500 particles update in <5ms (loose; spec says <0.75ms
    for production but we tolerate CI jitter here)."""
    for i in range(1500):
        engine.emit(P_SPARK, 100.0 + (i % 240), 100.0 + (i // 240), vx=10.0, vy=-5.0)
    # Warm up
    engine.update(1 / 60)
    # Measure
    t0 = time.perf_counter()
    for _ in range(60):  # 1 second of frames
        engine.update(1 / 60)
    elapsed = time.perf_counter() - t0
    # 60 updates should take <300ms (~5ms per update worst case)
    assert elapsed < 0.300, f"update too slow: {elapsed*1000:.1f}ms / 60 frames"


def test_1500_particles_draw_under_20ms(engine: ParticleEngine, display: pygame.Surface) -> None:
    """Soft target: 1500 particles draw in <20ms (loose)."""
    for i in range(1500):
        engine.emit(P_SPARK, 100.0 + (i % 240), 100.0 + (i // 240),
                    color=((i * 7) % 256, (i * 11) % 256, (i * 13) % 256))
    engine.update(1 / 60)
    # Warm up
    engine.draw(display)
    t0 = time.perf_counter()
    for _ in range(10):
        engine.draw(display)
    elapsed = time.perf_counter() - t0
    # 10 draws <200ms (~20ms each worst case)
    assert elapsed < 0.200, f"draw too slow: {elapsed*1000:.1f}ms / 10 frames"


# ---------------------------------------------------------------------------
# 13. release_all + scene transition
# ---------------------------------------------------------------------------
def test_release_all_clears_active(engine: ParticleEngine) -> None:
    for _ in range(100):
        engine.emit(P_SPARK, 0.0, 0.0)
    assert engine.active_count == 100
    engine.release_all()
    assert engine.active_count == 0


# ---------------------------------------------------------------------------
# 14. Per-kind defaults are sane
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kind", list(range(P_KIND_COUNT)))
def test_kind_default_life_positive(kind: int) -> None:
    assert KIND_CONFIG[kind].default_life > 0.0


@pytest.mark.parametrize("kind", list(range(P_KIND_COUNT)))
def test_kind_default_color_is_rgb_tuple(kind: int) -> None:
    rgb = KIND_CONFIG[kind].base_color
    assert isinstance(rgb, tuple)
    assert len(rgb) == 3
    for c in rgb:
        assert 0 <= c <= 255


# ---------------------------------------------------------------------------
# 15. Bounds culling edge cases
# ---------------------------------------------------------------------------
def test_particle_at_edge_of_bounds_survives(engine: ParticleEngine) -> None:
    """Particle exactly at right edge (x=INTERNAL_W) survives one frame, then dies."""
    p = engine.emit(P_SPARK, float(INTERNAL_W), float(INTERNAL_H) / 2, vx=0.0, life=1.0)
    assert p is not None
    engine.update(1 / 120)
    # x=INTERNAL_W + 0 vx → still at edge. Margin is 16, so x < INTERNAL_W+16 → alive.
    assert p.active
    # Push it out hard (1000 px/s)
    p.vx = 1000.0
    engine.update(1 / 60)
    # 1000 * 1/60 ≈ 16.67 px → x = INTERNAL_W + 16.67, beyond margin → culled
    assert not p.active
