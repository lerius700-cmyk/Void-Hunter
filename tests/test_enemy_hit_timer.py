"""BLOQUE 71.2: hit_timer must decrement for ALL enemy kinds, not just MINE.

The bug: ``hit_timer`` was only decremented inside the MINE_ASTEROID
branch of ``Enemy.update()``. Non-MINE enemies (SCOUT, CRUISER, HEAVY) had
the flash set by ``Enemy.hit()`` but never decremented, so they stayed
permanently "blancuscas" (white overlay 70%) for the rest of the run.

This test pins the contract: ``hit_timer`` decrements toward 0 for any
enemy kind that has it > 0.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

from src.entities.enemies.enemy import Enemy, EnemyKind
from src.core.settings import HIT_FLASH_DURATION_S


def _make_enemy(kind: EnemyKind) -> Enemy:
    """Bypasses dataclass __init__ and sets the bare minimum to test update()."""
    e = Enemy.__new__(Enemy)
    e.active = True
    e.state = 1  # any non-DEAD state
    e.kind = kind
    e.x = 160.0
    e.y = 240.0
    e.vx = 0.0
    e.vy = 30.0
    e.hp = 10
    e.hit_timer = 0.0
    e.mine_hit_flash_timer = 0.0
    # Required by update() for non-MINE branches:
    e.animation_timer = 0.0
    e.animation_frame = 0
    e.animation_state = "idle"
    e.path_follower = None
    e.sine_t = 0.0
    e.homing_target = None
    e.spawn_timer = 0.0
    e.fire_cd = 0.0
    e.on_fire = False
    e.is_leader = False
    return e


def test_hit_timer_decrements_for_scout():
    e = _make_enemy(EnemyKind.SCOUT)
    e.hit_timer = HIT_FLASH_DURATION_S  # simulate a hit
    e.update(dt=0.05, player_x=0.0, player_y=0.0)
    assert e.hit_timer < HIT_FLASH_DURATION_S, (
        f"BUG: SCOUT hit_timer did not decrement "
        f"({e.hit_timer} after update)"
    )
    assert e.hit_timer == pytest.approx(HIT_FLASH_DURATION_S - 0.05)


def test_hit_timer_decrements_for_cruiser():
    e = _make_enemy(EnemyKind.CRUISER)
    e.hit_timer = HIT_FLASH_DURATION_S
    e.update(dt=0.05, player_x=0.0, player_y=0.0)
    assert e.hit_timer == pytest.approx(HIT_FLASH_DURATION_S - 0.05)


def test_hit_timer_decrements_for_heavy():
    e = _make_enemy(EnemyKind.HEAVY)
    e.hit_timer = HIT_FLASH_DURATION_S
    e.update(dt=0.05, player_x=0.0, player_y=0.0)
    assert e.hit_timer == pytest.approx(HIT_FLASH_DURATION_S - 0.05)


def test_hit_timer_reaches_zero_after_enough_ticks():
    e = _make_enemy(EnemyKind.SCOUT)
    e.hit_timer = HIT_FLASH_DURATION_S
    # Tick for longer than the flash duration.
    for _ in range(20):  # 20 * 0.05 = 1.0s, way past 0.15s
        e.update(dt=0.05, player_x=0.0, player_y=0.0)
    assert e.hit_timer == 0.0, f"hit_timer should clamp at 0, got {e.hit_timer}"


def test_hit_timer_unchanged_when_zero():
    """Sanity: if hit_timer is 0, update() should not touch it."""
    e = _make_enemy(EnemyKind.SCOUT)
    e.hit_timer = 0.0
    e.update(dt=0.05, player_x=0.0, player_y=0.0)
    assert e.hit_timer == 0.0


def test_hit_timer_still_decrements_for_mine_asteroid():
    """Regression guard: the MINE branch's decrement must keep working."""
    e = _make_enemy(EnemyKind.MINE_ASTEROID)
    e.mine_state = "closed"
    e.mine_state_t = 0.0
    e.mine_fire_cooldown = 1.0
    e.mine_variant = 0
    e.mine_hit_flash_timer = 0.0
    e.hit_timer = HIT_FLASH_DURATION_S
    e.update(dt=0.05, player_x=0.0, player_y=0.0)
    assert e.hit_timer == pytest.approx(HIT_FLASH_DURATION_S - 0.05)
