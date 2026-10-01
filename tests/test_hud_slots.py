"""BLOQUE 72 T9: HUD draws 4 weapon slots (empty/filled/selected/pop).

Renders the weapon slot inventory in the bottom-center of the playfield:
  - 4 boxes 12x12 px, horizontal layout, 4 px spacing
  - Empty slot: dark bg (30, 20, 30)
  - Filled slot: weapon color (orange/green/red-orange/cyan per weapon_id)
  - Selected slot (active_idx): white outline 2 px
  - Pop animation: scale 1.0 -> 1.4 -> 1.0 over 0.2s after pickup
  - Selection pulse: +/-5% scale at 0.5 Hz
  - Letter A/S/D/F drawn centered in filled slots
  - Ammo count drawn below the slot
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
pygame.init()

import pytest

from src.ui.hud import HUD
from src.entities.weapon_slot import WeaponSlot


@pytest.fixture
def hud() -> HUD:
    return HUD()


def test_hud_has_draw_weapon_slots_method(hud: HUD) -> None:
    """BLOQUE 72 T9: HUD exposes a private method for slot rendering."""
    assert hasattr(hud, "_draw_weapon_slots")


def test_draw_weapon_slots_empty_does_not_raise(hud: HUD) -> None:
    """Drawing 4 empty slots must not raise (no ammo, no pop, idx=0)."""
    target = pygame.Surface((320, 480))
    slots = [
        WeaponSlot("A", "thick",  0, 100),
        WeaponSlot("S", "laser",  0, 200),
        WeaponSlot("D", "flame",  0,  50),
        WeaponSlot("F", "double", 0, 150),
    ]
    hud._draw_weapon_slots(target, slots, active_idx=0, t=0.0, pop_anim={})


def test_draw_weapon_slots_filled_does_not_raise(hud: HUD) -> None:
    """Drawing filled slots with mid-pop animation must not raise."""
    target = pygame.Surface((320, 480))
    slots = [
        WeaponSlot("A", "thick",  50, 100),
        WeaponSlot("S", "laser",  100, 200),
        WeaponSlot("D", "flame",  0,   50),
        WeaponSlot("F", "double", 75, 150),
    ]
    hud._draw_weapon_slots(
        target, slots, active_idx=1, t=1.23, pop_anim={"A": 0.1, "S": 0.0},
    )


def test_draw_weapon_slots_changes_pixels(hud: HUD) -> None:
    """Filled slot must visibly differ from empty slot in the slot region."""
    target_empty = pygame.Surface((320, 480))
    target_filled = pygame.Surface((320, 480))
    slots_empty = [
        WeaponSlot("A", "thick",  0, 100),
        WeaponSlot("S", "laser",  0, 200),
        WeaponSlot("D", "flame",  0,  50),
        WeaponSlot("F", "double", 0, 150),
    ]
    slots_filled = [
        WeaponSlot("A", "thick",  50, 100),
        WeaponSlot("S", "laser",  0, 200),
        WeaponSlot("D", "flame",  0,  50),
        WeaponSlot("F", "double", 0, 150),
    ]
    hud._draw_weapon_slots(target_empty, slots_empty, 0, 0.0, {})
    hud._draw_weapon_slots(target_filled, slots_filled, 0, 0.0, {})

    # The 4 slots are drawn at bottom-center. Slot 0 (A) starts at x ~= 146
    # in INTERNAL_W=320 layout. The slot extends from y=466 (bottom of slot)
    # down. Check the interior of the first filled slot for the orange color.
    differ = False
    for x in range(140, 180):
        for y in range(440, 470):
            if target_empty.get_at((x, y)) != target_filled.get_at((x, y)):
                differ = True
                break
        if differ:
            break
    assert differ, "Filled slot should produce different pixels than empty"
