"""BLOQUE 72 T8: _apply_asteroid_powerup fills weapon slots + pop anim trigger.

When a MINE-ASTEROID drops a powerup of kind THICK/LASER/FLAME/DOUBLE
(BLOQUE 72 T7 expanded the enum), the player picks it up via
``_player_pickup_powerups`` which calls ``_apply_asteroid_powerup(kind)``.

NOTE: the method is named ``_apply_asteroid_powerup`` (not
``_apply_powerup``) to avoid being silently overridden by the
ring-system ``_apply_powerup`` defined later in the same class
(gameplay_runtime.py:3679+). Python rebinds the name on each def.

This test file verifies that:
  1. Each of the 4 weapon kinds fills the corresponding slot (A/S/D/F).
  2. Re-pickup stacks ammo (capped at max_ammo).
  3. The HUD pop-up animation timer is triggered on pickup.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
pygame.init()

import pytest

from src.ui.gameplay_runtime import GameplayRuntime
from src.entities.asteroid import PowerupKind
from src.core.settings import WEAPON_PICKUP_AMMO


@pytest.fixture
def runtime() -> GameplayRuntime:
    return GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)


def test_apply_thick_fills_slot_a(runtime: GameplayRuntime) -> None:
    """THICK maps to slot 0 (letter A, weapon_id 'thick')."""
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    assert runtime._weapon_slots[0].ammo == WEAPON_PICKUP_AMMO
    assert runtime._weapon_slots[0].letter == "A"
    assert not runtime._weapon_slots[0].is_empty


def test_apply_laser_fills_slot_s(runtime: GameplayRuntime) -> None:
    """LASER maps to slot 1 (letter S)."""
    runtime._apply_asteroid_powerup(PowerupKind.LASER)
    assert runtime._weapon_slots[1].ammo == WEAPON_PICKUP_AMMO


def test_apply_flame_fills_slot_d(runtime: GameplayRuntime) -> None:
    """FLAME maps to slot 2 (letter D)."""
    runtime._apply_asteroid_powerup(PowerupKind.FLAME)
    assert runtime._weapon_slots[2].ammo == WEAPON_PICKUP_AMMO


def test_apply_double_fills_slot_f(runtime: GameplayRuntime) -> None:
    """DOUBLE maps to slot 3 (letter F)."""
    runtime._apply_asteroid_powerup(PowerupKind.DOUBLE)
    assert runtime._weapon_slots[3].ammo == WEAPON_PICKUP_AMMO


def test_repickup_stacks(runtime: GameplayRuntime) -> None:
    """Re-pickup of the same weapon kind stacks ammo (under cap)."""
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    assert runtime._weapon_slots[0].ammo == WEAPON_PICKUP_AMMO * 2


def test_repickup_caps_at_max(runtime: GameplayRuntime) -> None:
    """Re-pickup clamps ammo at max_ammo; excess is silently dropped."""
    runtime._weapon_slots[0].ammo = 90  # THICK max is 100
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    assert runtime._weapon_slots[0].ammo == 100


def test_apply_triggers_pop_anim(runtime: GameplayRuntime) -> None:
    """HUD pop animation timer is set on the slot's letter key."""
    runtime._apply_asteroid_powerup(PowerupKind.LASER)
    assert runtime._weapon_pop_anim["S"] > 0.0
