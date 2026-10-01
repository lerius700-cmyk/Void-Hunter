"""BLOQUE 72 T6: GameplayRuntime initializes 4 empty weapon slots.

Per spec (docs/superpowers/specs/2026-09-09-asteroid-hit-and-powerup-system-design.md)
the player carries 4 fixed weapon slots (A/S/D/F) keyed to weapon_ids
(thick/laser/flame/double). All start empty; pickup powerups fill them
in subsequent tasks (T7-T8).
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
pygame.init()

import pytest

from src.ui.gameplay_runtime import GameplayRuntime


@pytest.fixture
def runtime() -> GameplayRuntime:
    return GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)


def test_runtime_has_4_weapon_slots(runtime: GameplayRuntime) -> None:
    assert hasattr(runtime, "_weapon_slots")
    assert isinstance(runtime._weapon_slots, list)
    assert len(runtime._weapon_slots) == 4


def test_slots_initially_empty(runtime: GameplayRuntime) -> None:
    for s in runtime._weapon_slots:
        assert s.ammo == 0
        assert s.is_empty is True


def test_slot_letters_are_asdf(runtime: GameplayRuntime) -> None:
    letters = [s.letter for s in runtime._weapon_slots]
    assert letters == ["A", "S", "D", "F"]


def test_slot_weapon_ids(runtime: GameplayRuntime) -> None:
    ids = [s.weapon_id for s in runtime._weapon_slots]
    assert ids == ["thick", "laser", "flame", "double"]


def test_active_idx_starts_at_zero(runtime: GameplayRuntime) -> None:
    assert hasattr(runtime, "_weapon_active_idx")
    assert runtime._weapon_active_idx == 0


def test_pop_anim_init(runtime: GameplayRuntime) -> None:
    """BLOQUE 72 T6: HUD pickup pop animation dict starts at 0.0 for all 4 letters."""
    assert hasattr(runtime, "_weapon_pop_anim")
    assert runtime._weapon_pop_anim == {"A": 0.0, "S": 0.0, "D": 0.0, "F": 0.0}
