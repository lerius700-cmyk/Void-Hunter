"""BLOQUE 71: MINE-ASTEROID hit_timer and flash in 4 states."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest
from unittest.mock import patch

from src.entities.enemies.enemy import (
    Enemy,
    EnemyKind,
    MINE_ASTEROID_CLOSED,
    MINE_ASTEROID_OPEN1,
    MINE_ASTEROID_OPEN2,
    MINE_ASTEROID_OPEN3,
)
from src.core.settings import HIT_FLASH_DURATION_S


def _make_mine(state: str = MINE_ASTEROID_CLOSED) -> Enemy:
    """Build a MINE-ASTEROID enemy directly. State machine uses string values
    ("closed" | "open1" | "open2" | "open3") per BLOQUE 65/71.

    Note: the Enemy dataclass default for ``active`` is False, but the
    hit() and update() methods short-circuit when ``active`` is False.
    We set both ``active`` and ``alive`` so the test exercises the
    full hit/update path. ``state`` (EnemyState enum) is set to IDLE
    to bypass the DEAD short-circuit in update().
    """
    from src.entities.enemies.enemy import EnemyState
    e = Enemy.__new__(Enemy)
    e.kind = EnemyKind.MINE_ASTEROID
    e.x = 160.0
    e.y = 240.0
    e.vx = 0.0
    e.vy = 30.0
    e.active = True
    e.alive = True
    e.state = EnemyState.IDLE
    e.hp = 3
    e.mine_state = state
    e.mine_state_t = 0.0
    e.mine_fire_cooldown = 1.0
    e.mine_variant = 0
    e.on_fire = False
    e.on_death = False
    e.hit_timer = 0.0
    return e


def test_mine_closed_hit_sets_flash_no_damage():
    e = _make_mine(MINE_ASTEROID_CLOSED)
    e.hp = 3
    result = e.hit(damage=1)
    assert result is False
    assert e.hit_timer == HIT_FLASH_DURATION_S
    assert e.hp == 3  # no damage taken
    assert e.mine_state == MINE_ASTEROID_CLOSED  # no state change


def test_mine_open1_hit_sets_flash_no_damage():
    e = _make_mine(MINE_ASTEROID_OPEN1)
    e.hp = 3
    e.hit(damage=1)
    assert e.hit_timer == HIT_FLASH_DURATION_S
    assert e.hp == 3


def test_mine_open2_hit_sets_flash_no_damage():
    e = _make_mine(MINE_ASTEROID_OPEN2)
    e.hp = 3
    e.hit(damage=1)
    assert e.hit_timer == HIT_FLASH_DURATION_S
    assert e.hp == 3


def test_mine_open3_hit_sets_flash_decrements_hp():
    e = _make_mine(MINE_ASTEROID_OPEN3)
    e.hp = 3
    e.hit(damage=1)
    assert e.hit_timer == HIT_FLASH_DURATION_S
    assert e.hp == 2


def test_mine_open3_destroyed_at_zero_hp():
    e = _make_mine(MINE_ASTEROID_OPEN3)
    e.hp = 1
    result = e.hit(damage=1)
    assert result is True
    assert e.hp == 0
    assert e.alive is False


def test_mine_hit_timer_decrements_in_update():
    e = _make_mine(MINE_ASTEROID_CLOSED)
    e.hit()
    initial = e.hit_timer
    e.update(0.05, player_x=160.0, player_y=400.0)
    assert e.hit_timer == pytest.approx(initial - 0.05)
