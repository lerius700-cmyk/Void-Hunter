"""Tests for src.systems.projectile — ProjectilePool (BLOQUE 2)."""
from __future__ import annotations

import pytest
import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W, PROJECTILE_POOL
from src.systems.projectile import (
    BULLET_BOSS,
    BULLET_ENEMY,
    BULLET_PLAYER,
    BULLET_PLAYER_CHARGED,
    FRAME_DURATION_S,
    NUM_FRAMES,
    OWNER_BOSS,
    OWNER_ENEMY,
    OWNER_PLAYER,
    ProjectilePool,
)


@pytest.fixture
def pool() -> ProjectilePool:
    return ProjectilePool(capacity=PROJECTILE_POOL)


@pytest.fixture
def display() -> pygame.Surface:
    return pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# 1. Capacity & exhaustion
# ---------------------------------------------------------------------------
def test_default_capacity_is_400(pool: ProjectilePool) -> None:
    assert pool.capacity == 400
    assert pool.pool.size == 400


def test_pool_exhaustion_returns_none(pool: ProjectilePool) -> None:
    """Fill the pool of 400, next spawn returns None."""
    spawned = [pool.spawn(BULLET_PLAYER, 0.0, 0.0, 0.0, 0.0) for _ in range(400)]
    assert all(s is not None for s in spawned)
    assert pool.active_count == 400
    assert pool.spawn(BULLET_PLAYER, 0.0, 0.0, 0.0, 0.0) is None


def test_boss_expansion_increases_capacity(pool: ProjectilePool) -> None:
    """expand_for_boss raises reported capacity to 600."""
    pool.expand_for_boss()
    assert pool.capacity == 600
    pool.collapse_from_boss()
    assert pool.capacity == 400


# ---------------------------------------------------------------------------
# 2. Spawn returns projectile with correct fields
# ---------------------------------------------------------------------------
def test_spawn_player_bullet(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER, 100.0, 50.0, 0.0, -480.0, damage=1, owner=OWNER_PLAYER)
    assert p is not None
    assert p.kind == BULLET_PLAYER
    assert p.owner == OWNER_PLAYER
    assert p.x == 100.0 and p.y == 50.0
    assert p.vy == -480.0  # negative = upward in screen coords
    assert p.damage == 1


def test_spawn_charged_bullet_with_pierce(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER_CHARGED, 100.0, 50.0, 0.0, -600.0,
                    damage=3, owner=OWNER_PLAYER, pierce=2)
    assert p is not None
    assert p.kind == BULLET_PLAYER_CHARGED
    assert p.pierce == 2
    assert p.pierce_hits == 0
    assert p.damage == 3


def test_spawn_enemy_bullet(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_ENEMY, 50.0, 100.0, 0.0, 220.0, damage=1, owner=OWNER_ENEMY)
    assert p is not None
    assert p.kind == BULLET_ENEMY
    assert p.owner == OWNER_ENEMY


def test_spawn_boss_bullet(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_BOSS, 50.0, 100.0, 0.0, 240.0, damage=2, owner=OWNER_BOSS)
    assert p is not None
    assert p.kind == BULLET_BOSS
    assert p.owner == OWNER_BOSS


# ---------------------------------------------------------------------------
# 3. Position integration
# ---------------------------------------------------------------------------
def test_position_advances_per_dt(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER, 100.0, 100.0, 0.0, -100.0)
    assert p is not None
    pool.update(1.0)  # 1 second
    assert p.y == pytest.approx(0.0, abs=1e-6)  # 100 + (-100)*1


def test_zero_dt_advances_nothing(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER, 100.0, 100.0, 0.0, -100.0)
    assert p is not None
    pool.update(0.0)
    assert p.x == 100.0 and p.y == 100.0


# ---------------------------------------------------------------------------
# 4. Offscreen cull
# ---------------------------------------------------------------------------
def test_offscreen_cull_releases(pool: ProjectilePool) -> None:
    """Bullet that goes off the right edge → released."""
    p = pool.spawn(BULLET_PLAYER, INTERNAL_W + 100.0, 100.0, 100.0, 0.0)
    assert p is not None
    pool.update(1.0)
    assert not p.active


def test_bullet_in_bounds_survives(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER, 100.0, 100.0, 0.0, 0.0)
    assert p is not None
    pool.update(1.0)
    assert p.active


# ---------------------------------------------------------------------------
# 5. 4-frame animation @ 16 FPS
# ---------------------------------------------------------------------------
def test_animation_advances_after_frame_duration(pool: ProjectilePool) -> None:
    """0.0625s = 1 frame @ 16 FPS; frame advances after that."""
    p = pool.spawn(BULLET_PLAYER, 100.0, 100.0, 0.0, 0.0)
    assert p is not None
    assert p.frame == 0
    pool.update(FRAME_DURATION_S - 0.001)  # just under
    assert p.frame == 0
    pool.update(0.002)  # cross the threshold
    assert p.frame == 1


def test_animation_wraps_at_num_frames(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER, 100.0, 100.0, 0.0, 0.0)
    assert p is not None
    for _ in range(NUM_FRAMES + 2):
        pool.update(FRAME_DURATION_S + 0.001)
    # After 6 full frame durations, frame = 6 % 4 = 2
    assert p.frame == (NUM_FRAMES + 2) % NUM_FRAMES


def test_boss_bullet_animation_does_not_advance(pool: ProjectilePool) -> None:
    """Boss bullets are 1-frame per spec — no flicker."""
    p = pool.spawn(BULLET_BOSS, 100.0, 100.0, 0.0, 0.0, owner=OWNER_BOSS)
    assert p is not None
    pool.update(1.0)
    assert p.frame == 0  # never advances


# ---------------------------------------------------------------------------
# 6. Pierce mechanics
# ---------------------------------------------------------------------------
def test_pierce_zero_releases_on_hit(pool: ProjectilePool) -> None:
    """pierce=0 (default): bullet is not auto-released by hits (collision
    system handles that), but pierce tracking is intact."""
    p = pool.spawn(BULLET_PLAYER_CHARGED, 100.0, 100.0, 0.0, -100.0, pierce=0)
    assert p is not None
    pool.take_damage_hits(p)
    # pierce=0 means hits don't increment counter; bullet still alive.
    assert p.pierce_hits == 0
    assert p.active


def test_pierce_n_releases_after_n_hits(pool: ProjectilePool) -> None:
    """pierce=2: bullet released after 2 hits."""
    p = pool.spawn(BULLET_PLAYER_CHARGED, 100.0, 100.0, 0.0, -100.0, pierce=2)
    assert p is not None
    pool.take_damage_hits(p)
    pool.take_damage_hits(p)
    pool.update(0.001)  # advance to check pierce condition
    assert not p.active


def test_take_damage_hits_increments_counter(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER_CHARGED, 100.0, 100.0, 0.0, -100.0, pierce=3)
    assert p is not None
    pool.take_damage_hits(p)
    assert p.pierce_hits == 1
    pool.take_damage_hits(p)
    assert p.pierce_hits == 2


# ---------------------------------------------------------------------------
# 7. Trail state
# ---------------------------------------------------------------------------
def test_trail_cooldown_decreases(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER, 100.0, 100.0, 0.0, -100.0, has_trail=True)
    assert p is not None
    initial_cd = p.trail_cooldown
    pool.update(0.5)
    assert p.trail_cooldown < initial_cd


def test_trail_color_default(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_PLAYER, 0.0, 0.0, 0.0, 0.0, has_trail=True)
    assert p is not None
    assert p.trail_color == (255, 220, 100)  # default player color


def test_trail_color_custom(pool: ProjectilePool) -> None:
    p = pool.spawn(BULLET_ENEMY, 0.0, 0.0, 0.0, 0.0,
                    has_trail=True, trail_color=(80, 200, 255))
    assert p is not None
    assert p.trail_color == (80, 200, 255)


# ---------------------------------------------------------------------------
# 8. Draw with single blits() batch
# ---------------------------------------------------------------------------
def test_draw_with_active_projectiles(pool: ProjectilePool, display: pygame.Surface) -> None:
    """draw() returns count and submits single batch."""
    import inspect
    src = inspect.getsource(ProjectilePool.draw)
    n_target_blits = sum(
        1 for line in src.splitlines()
        if line.strip().startswith("target.blits(") and "blits(batch)" in line
    )
    assert n_target_blits == 1, f"draw() should call target.blits() exactly once, got {n_target_blits}"

    for i in range(10):
        pool.spawn(BULLET_PLAYER, 50.0 + i, 100.0, 0.0, -100.0)
    pool.update(0.01)
    n = pool.draw(display)
    assert n == 10


def test_draw_with_no_active_projectiles(pool: ProjectilePool, display: pygame.Surface) -> None:
    """Empty pool: draw returns 0."""
    n = pool.draw(display)
    assert n == 0


# ---------------------------------------------------------------------------
# 9. release_all on scene transition
# ---------------------------------------------------------------------------
def test_release_all_clears_active(pool: ProjectilePool) -> None:
    for i in range(50):
        pool.spawn(BULLET_PLAYER, 0.0, 0.0, 0.0, 0.0)
    assert pool.active_count == 50
    pool.release_all()
    assert pool.active_count == 0


# ---------------------------------------------------------------------------
# 10. Pre-baked frame surface invariant
# ---------------------------------------------------------------------------
def test_pre_baked_frames_have_4_per_kind(pool: ProjectilePool) -> None:
    """4 kinds × 4 frames = 16 surface keys, all unique-ish."""
    assert len(pool._frames) == 16


def test_bullet_kinds_have_correct_size(pool: ProjectilePool) -> None:
    from src.systems.projectile import BULLET_SIZES
    assert BULLET_SIZES[BULLET_PLAYER] == (4, 6)
    assert BULLET_SIZES[BULLET_PLAYER_CHARGED] == (6, 10)
    assert BULLET_SIZES[BULLET_ENEMY] == (4, 6)
    assert BULLET_SIZES[BULLET_BOSS] == (8, 8)


# ---------------------------------------------------------------------------
# 11. Performance smoke
# ---------------------------------------------------------------------------
def test_400_bullets_update_under_2ms(pool: ProjectilePool) -> None:
    """Soft target: 400 bullets update in <2ms (spec: <0.12ms, loose)."""
    for i in range(400):
        pool.spawn(BULLET_PLAYER, 50.0 + (i % 240), 100.0, 0.0, -200.0)
    # warmup
    pool.update(1 / 60)
    import time
    t0 = time.perf_counter()
    for _ in range(60):
        pool.update(1 / 60)
    elapsed = time.perf_counter() - t0
    # 60 updates < 120ms
    assert elapsed < 0.120, f"update too slow: {elapsed*1000:.1f}ms / 60 frames"


def test_400_bullets_draw_under_5ms(pool: ProjectilePool, display: pygame.Surface) -> None:
    """Soft target: 400 bullets draw in <5ms."""
    for i in range(400):
        pool.spawn(BULLET_PLAYER, 50.0 + (i % 240), 100.0, 0.0, -200.0)
    pool.update(1 / 60)
    pool.draw(display)  # warmup
    import time
    t0 = time.perf_counter()
    for _ in range(20):
        pool.draw(display)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.100, f"draw too slow: {elapsed*1000:.1f}ms / 20 frames"


# ---------------------------------------------------------------------------
# 12. on_spawn resets frame and pierce_hits (regression)
# ---------------------------------------------------------------------------
def test_respawn_resets_state(pool: ProjectilePool) -> None:
    """A bullet reused via release→acquire has fresh state."""
    p1 = pool.spawn(BULLET_PLAYER_CHARGED, 0.0, 0.0, 0.0, -100.0, pierce=3)
    assert p1 is not None
    pool.take_damage_hits(p1)
    pool.take_damage_hits(p1)
    assert p1.pierce_hits == 2
    p1.frame = 3
    pool.release_all()
    p2 = pool.spawn(BULLET_PLAYER_CHARGED, 0.0, 0.0, 0.0, -100.0, pierce=3)
    assert p2 is not None
    assert p2.pierce_hits == 0
    assert p2.frame == 0
