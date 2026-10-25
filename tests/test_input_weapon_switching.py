"""BLOQUE 73 Fase C: input remap for weapon slot system.

Three input paths to wire up:
  1. MOUSEWHEEL: cycle ``_weapon_active_idx`` (UP = next, DOWN = prev, wrap).
  2. Keys 1/2/3/4: direct slot selection (A/S/D/F).
  3. RMB held: consume ammo from active slot at fire rate (10/sec default).
     Sets ``_weapon_fire_request = True`` while firing (consumed by Fase B
     fire functions to spawn bullets).

RMB OLD behavior (rapid fire L1) is replaced: RMB now fires the active
weapon instead. LMB still does charge shot as before.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
pygame.init()

import pytest

from src.ui.gameplay_runtime import GameplayRuntime
from src.entities.asteroid import PowerupKind


@pytest.fixture
def runtime() -> GameplayRuntime:
    return GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)


# ---------------------------------------------------------------------------
# 1. Wheel cycling
# ---------------------------------------------------------------------------
def test_wheel_up_cycles_to_next_slot(runtime: GameplayRuntime) -> None:
    """MOUSEWHEEL up increments active_idx (with wrap-around)."""
    assert runtime._weapon_active_idx == 0  # starts at A
    runtime._cycle_weapon_slot(+1)
    assert runtime._weapon_active_idx == 1  # S
    runtime._cycle_weapon_slot(+1)
    assert runtime._weapon_active_idx == 2  # D
    runtime._cycle_weapon_slot(+1)
    assert runtime._weapon_active_idx == 3  # F


def test_wheel_down_cycles_to_prev_slot(runtime: GameplayRuntime) -> None:
    """MOUSEWHEEL down decrements active_idx (with wrap-around)."""
    # From 0 going down wraps to 3
    runtime._cycle_weapon_slot(-1)
    assert runtime._weapon_active_idx == 3
    runtime._cycle_weapon_slot(-1)
    assert runtime._weapon_active_idx == 2


def test_wheel_wraps_around_at_end(runtime: GameplayRuntime) -> None:
    """From slot 3, wheel up wraps to slot 0."""
    runtime._weapon_active_idx = 3
    runtime._cycle_weapon_slot(+1)
    assert runtime._weapon_active_idx == 0


def test_wheel_does_not_change_when_no_slots(runtime: GameplayRuntime) -> None:
    """Defensive: if slots list is somehow empty, cycle is a no-op."""
    runtime._weapon_slots = []
    runtime._cycle_weapon_slot(+1)
    assert runtime._weapon_active_idx == 0  # unchanged


# ---------------------------------------------------------------------------
# 2. Keys 1/2/3/4 direct selection
# ---------------------------------------------------------------------------
def test_key_1_selects_slot_a(runtime: GameplayRuntime) -> None:
    runtime._select_weapon_slot(0)
    assert runtime._weapon_active_idx == 0


def test_key_2_selects_slot_s(runtime: GameplayRuntime) -> None:
    runtime._weapon_active_idx = 0  # start elsewhere
    runtime._select_weapon_slot(1)
    assert runtime._weapon_active_idx == 1


def test_key_3_selects_slot_d(runtime: GameplayRuntime) -> None:
    runtime._select_weapon_slot(2)
    assert runtime._weapon_active_idx == 2


def test_key_4_selects_slot_f(runtime: GameplayRuntime) -> None:
    runtime._select_weapon_slot(3)
    assert runtime._weapon_active_idx == 3


def test_select_with_invalid_index_clamps_or_ignores(runtime: GameplayRuntime) -> None:
    """Selecting an out-of-range index is a safe no-op (ignores bad input)."""
    runtime._weapon_active_idx = 2
    runtime._select_weapon_slot(99)
    assert runtime._weapon_active_idx == 2  # unchanged
    runtime._select_weapon_slot(-1)
    assert runtime._weapon_active_idx == 2  # unchanged


# ---------------------------------------------------------------------------
# 3. RMB weapon fire
# ---------------------------------------------------------------------------
def test_rmb_fire_consumes_ammo_from_active_slot(runtime: GameplayRuntime) -> None:
    """RMB held with non-empty active slot: ammo decreases by 1."""
    runtime._apply_asteroid_powerup(PowerupKind.THICK)  # fills slot A (idx=0)
    assert runtime._weapon_slots[0].ammo == 30
    assert runtime._fire_active_weapon() is True
    assert runtime._weapon_slots[0].ammo == 29


def test_rmb_fire_with_empty_slot_returns_false(runtime: GameplayRuntime) -> None:
    """RMB held with empty active slot: no-op, returns False, no ammo change."""
    assert runtime._weapon_slots[0].is_empty
    assert runtime._fire_active_weapon() is False
    assert runtime._weapon_slots[0].ammo == 0


def test_rmb_fire_sets_fire_request_flag(runtime: GameplayRuntime) -> None:
    """While firing, _weapon_fire_request = True (consumed by Fase B)."""
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._weapon_fire_request = False
    runtime._fire_active_weapon()
    assert runtime._weapon_fire_request is True


def test_rmb_fire_respects_cooldown(runtime: GameplayRuntime) -> None:
    """After firing, _weapon_fire_cooldown must be set so rapid calls don't fire.

    BLOQUE 73 Fase B: each weapon has its own cooldown now (THICK 0.20s,
    LASER 0.10s, FLAME 0.07s, DOUBLE 0.125s). The single WEAPON_FIRE_COOLDOWN_S
    constant is no longer the source of truth — the per-weapon fire
    function sets it. We just verify that the cooldown is > 0 after a
    successful fire, which is sufficient to gate re-fire.
    """
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._fire_active_weapon()
    assert runtime._weapon_slots[0].ammo == 29
    assert runtime._weapon_fire_cooldown > 0.0  # any positive value blocks re-fire


def test_rmb_fire_consumes_from_correct_slot(runtime: GameplayRuntime) -> None:
    """RMB fires the ACTIVE slot, not the first non-empty one."""
    # Fill THICK (slot A=0) and LASER (slot S=1). Active=S.
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._apply_asteroid_powerup(PowerupKind.LASER)
    runtime._weapon_active_idx = 1  # LASER (slot S)
    runtime._fire_active_weapon()
    # LASER ammo went 30 -> 29; THICK ammo still 30.
    assert runtime._weapon_slots[0].ammo == 30  # THICK unchanged
    assert runtime._weapon_slots[1].ammo == 29  # LASER consumed


def test_fire_cooldown_decays_in_update(runtime: GameplayRuntime) -> None:
    """``_weapon_fire_cooldown`` decrements each frame (in update tick)."""
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._fire_active_weapon()
    assert runtime._weapon_fire_cooldown > 0.0
    initial_cd = runtime._weapon_fire_cooldown
    runtime.update(0.05)  # tick
    assert runtime._weapon_fire_cooldown < initial_cd
