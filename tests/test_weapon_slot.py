"""BLOQUE 72: WeaponSlot dataclass — fill, cap, stack, empty."""
from __future__ import annotations

import pytest

from src.entities.weapon_slot import WeaponSlot


def test_init_empty_slot():
    s = WeaponSlot(letter="A", weapon_id="thick", ammo=0, max_ammo=100)
    assert s.is_empty is True
    assert s.ammo == 0


def test_add_ammo_to_empty_fills_to_pickup():
    s = WeaponSlot("A", "thick", 0, 100)
    s.add_ammo(30)
    assert s.ammo == 30
    assert s.is_empty is False


def test_add_ammo_stacks_under_cap():
    s = WeaponSlot("A", "thick", 50, 100)
    s.add_ammo(30)
    assert s.ammo == 80


def test_add_ammo_caps_at_max():
    s = WeaponSlot("A", "thick", 80, 100)
    s.add_ammo(50)  # would be 130, cap at 100
    assert s.ammo == 100


def test_add_ammo_exact_cap_no_overflow():
    s = WeaponSlot("A", "thick", 50, 100)
    s.add_ammo(50)
    assert s.ammo == 100


def test_add_ammo_drops_excess_silently():
    """Spec: pickup that exceeds max drops excess (no storage)."""
    s = WeaponSlot("A", "thick", 95, 100)
    s.add_ammo(30)  # would be 125, cap at 100
    assert s.ammo == 100  # 25 excess dropped


def test_consume_ammo():
    s = WeaponSlot("A", "thick", 50, 100)
    s.consume(5)
    assert s.ammo == 45


def test_consume_more_than_ammo_returns_zero():
    s = WeaponSlot("A", "thick", 3, 100)
    s.consume(10)
    assert s.ammo == 0
    assert s.is_empty is True
