"""BLOQUE 73 Fase B: per-weapon fire functions hooked into RMB consume.

Each weapon pickup (THICK/LASER/FLAME/DOUBLE) spawns a different bullet
pattern when RMB fires:
  - THICK: 1 large slow bullet, high damage (slow fire rate 5/sec).
  - LASER: 1 fast bullet per tick, pierce (medium fire rate 10/sec).
  - FLAME: 3-bullet fan spread (high fire rate 15/sec).
  - DOUBLE: 2 parallel bullets side-by-side (medium fire rate 8/sec).

The existing BULLET_PLAYER kind is reused; per-weapon identity comes
from the spawn pattern + speed/damage. Phase B+ can replace with
distinct BULLET_* kinds + procedural sprites.

Fire rate is differentiated per weapon via a ``_weapon_fire_cooldown``
override. Cooldown now sets itself based on the active weapon's id.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
pygame.init()

import pytest

from src.ui.gameplay_runtime import GameplayRuntime
from src.entities.asteroid import PowerupKind
from src.systems.projectile import BULLET_PLAYER, OWNER_PLAYER


@pytest.fixture
def runtime() -> GameplayRuntime:
    return GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)


def _bullet_count(rt: GameplayRuntime) -> int:
    """Count active player-owned bullets in the pool."""
    return sum(
        1 for b in rt._bullets.pool if b.active and b.owner == OWNER_PLAYER
    )


# ---------------------------------------------------------------------------
# Cooldown per weapon
# ---------------------------------------------------------------------------
def test_thick_fire_cooldown_is_slow(runtime: GameplayRuntime) -> None:
    """THICK weapon: 0.20s cooldown (5 shots/sec)."""
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._fire_active_weapon()
    assert runtime._weapon_fire_cooldown == pytest.approx(0.20, abs=1e-6)


def test_laser_fire_cooldown_is_medium(runtime: GameplayRuntime) -> None:
    """LASER weapon: 0.10s cooldown (10 shots/sec)."""
    runtime._apply_asteroid_powerup(PowerupKind.LASER)
    runtime._fire_active_weapon()
    assert runtime._weapon_fire_cooldown == pytest.approx(0.10, abs=1e-6)


def test_flame_fire_cooldown_is_fast(runtime: GameplayRuntime) -> None:
    """FLAME weapon: 0.07s cooldown (~14 shots/sec)."""
    runtime._apply_asteroid_powerup(PowerupKind.FLAME)
    runtime._fire_active_weapon()
    assert runtime._weapon_fire_cooldown == pytest.approx(0.07, abs=1e-6)


def test_double_fire_cooldown_is_medium(runtime: GameplayRuntime) -> None:
    """DOUBLE weapon: 0.125s cooldown (8 shots/sec)."""
    runtime._apply_asteroid_powerup(PowerupKind.DOUBLE)
    runtime._fire_active_weapon()
    assert runtime._weapon_fire_cooldown == pytest.approx(0.125, abs=1e-6)


# ---------------------------------------------------------------------------
# Bullet spawn per weapon
# ---------------------------------------------------------------------------
def test_thick_fire_spawns_one_bullet(runtime: GameplayRuntime) -> None:
    """THICK: 1 single big bullet per fire."""
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    initial = _bullet_count(runtime)
    runtime._fire_active_weapon()
    assert _bullet_count(runtime) == initial + 1


def test_laser_fire_spawns_one_pierce_bullet(runtime: GameplayRuntime) -> None:
    """LASER: 1 fast bullet per fire (pierce for cutting through enemies)."""
    runtime._apply_asteroid_powerup(PowerupKind.LASER)
    initial = _bullet_count(runtime)
    runtime._fire_active_weapon()
    assert _bullet_count(runtime) == initial + 1
    # Check that the new bullet has pierce > 0
    new_bullets = [
        b for b in runtime._bullets.pool
        if b.active and b.owner == OWNER_PLAYER
    ]
    assert any(b.pierce > 0 for b in new_bullets)


def test_flame_fire_spawns_fan_three_bullets(runtime: GameplayRuntime) -> None:
    """FLAME: 3-bullet fan spread per fire."""
    runtime._apply_asteroid_powerup(PowerupKind.FLAME)
    initial = _bullet_count(runtime)
    runtime._fire_active_weapon()
    assert _bullet_count(runtime) == initial + 3


def test_double_fire_spawns_two_parallel_bullets(runtime: GameplayRuntime) -> None:
    """DOUBLE: 2 bullets side-by-side per fire."""
    runtime._apply_asteroid_powerup(PowerupKind.DOUBLE)
    initial = _bullet_count(runtime)
    runtime._fire_active_weapon()
    assert _bullet_count(runtime) == initial + 2


# ---------------------------------------------------------------------------
# Cooldown prevents spam
# ---------------------------------------------------------------------------
def test_fire_cooldown_blocks_rapid_calls(runtime: GameplayRuntime) -> None:
    """After firing, cooldown must prevent immediate re-fire."""
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    initial = _bullet_count(runtime)
    runtime._fire_active_weapon()
    after_first = _bullet_count(runtime)
    runtime._fire_active_weapon()  # should be blocked by cooldown
    assert _bullet_count(runtime) == after_first, "cooldown did not block re-fire"


def test_fire_cooldown_decays(runtime: GameplayRuntime) -> None:
    """Cooldown decays in update tick (re-enables fire)."""
    # Re-init pygame if a previous test closed the video subsystem.
    # update() calls pygame.key.get_pressed() in _read_input which fails
    # if pygame.display was quit by an earlier test in the suite.
    if not pygame.display.get_init():
        pygame.init()
        pygame.display.set_mode((320, 480))
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._fire_active_weapon()
    initial_cd = runtime._weapon_fire_cooldown
    assert initial_cd > 0.0
    runtime.update(0.30)  # longer than THICK cooldown (0.20s)
    assert runtime._weapon_fire_cooldown == 0.0


# ---------------------------------------------------------------------------
# Integration: RMB tick in _read_input
# ---------------------------------------------------------------------------
def test_weapon_id_drives_fire_pattern(runtime: GameplayRuntime) -> None:
    """Different weapon_ids produce different bullet counts (THICK=1, FLAME=3)."""
    # THICK = 1 bullet
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._weapon_fire_cooldown = 0.0  # reset
    runtime._fire_active_weapon()
    thick_count = _bullet_count(runtime)

    # Switch to FLAME
    runtime._apply_asteroid_powerup(PowerupKind.FLAME)
    runtime._select_weapon_slot(2)  # FLAME slot idx
    runtime._weapon_fire_cooldown = 0.0
    runtime._fire_active_weapon()
    flame_count = _bullet_count(runtime)

    # FLAME adds 3 bullets (one fire). THICK added 1. So flame_count - thick_count = 3
    assert flame_count - thick_count == 3
