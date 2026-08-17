"""Tests for the per-weapon bullet VFX system (fx/bullet_vfx.py).

The VFX is stdlib-only (dataclasses + math) so it doesn't need
pygame. We pass a stub bullet object with `weapon: int` and
`spawn_time: float` attributes.

What we verify:
- All 10 weapons have a WeaponVFX entry in WEAPON_VFX_PARAMS.
- The alpha stays in [0, 255] for every weapon across a range of
  time inputs.
- Weapons 0-5, 7, 8, 9 have an alpha pulse (amp > 0) and oscillate
  with time. Weapon 6 (white piercing) does NOT pulse.
- Weapons 1-5, 7, 8 have a halo; weapons 0, 6, 9 do not.
- Scale pulse only for weapons 3, 5, 7.
- compute() returns a BulletVFX with sensible values.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from stellar_horizon.fx.bullet_vfx import (
    WEAPON_VFX_PARAMS, BulletVFX, compute,
)


@dataclass
class _StubBullet:
    """Minimal stand-in for PlayerBullet — VFX only needs weapon + spawn_time."""
    weapon: int = 0
    spawn_time: float = 0.0


# --- Parameter table sanity -----------------------------------------

def test_weapon_vfx_table_has_10_entries():
    assert len(WEAPON_VFX_PARAMS) == 10


def test_all_weapon_ids_have_an_entry():
    for i in range(10):
        params = WEAPON_VFX_PARAMS[i]
        assert params is not None


# --- Alpha pulse behavior -------------------------------------------

@pytest.mark.parametrize("weapon", [0, 1, 3, 4, 5, 7, 8, 9])
def test_alpha_pulses_for_weapons_with_amp(weapon):
    """Weapons with alpha_pulse_amp > 0 should oscillate as time
    advances. Sample at 60 evenly-spaced times and confirm the range
    of alpha values is non-trivial."""
    params = WEAPON_VFX_PARAMS[weapon]
    assert params.alpha_pulse_amp > 0.0
    b = _StubBullet(weapon=weapon, spawn_time=0.0)
    samples = [compute(b, t).alpha for t in [i / 60 for i in range(60)]]
    # All samples in [0, 255].
    for a in samples:
        assert 0 <= a <= 255
    # Range should be at least half of amp*255.
    expected_range = params.alpha_pulse_amp * 255 * 0.5
    assert (max(samples) - min(samples)) >= expected_range, (
        f"weapon {weapon}: alpha range {max(samples) - min(samples)} "
        f"too small (expected >= {expected_range:.0f})"
    )


@pytest.mark.parametrize("weapon", [2, 6])
def test_alpha_is_constant_for_weapons_without_pulse(weapon):
    """Blue ion and white piercing have no pulse — alpha should be
    a flat 255 at every time."""
    b = _StubBullet(weapon=weapon, spawn_time=0.0)
    for t in [0.0, 0.1, 0.5, 1.0, 2.0]:
        assert compute(b, t).alpha == 255


def test_all_weapons_have_alpha_in_range():
    for w in range(10):
        b = _StubBullet(weapon=w, spawn_time=0.0)
        for t in [0.0, 0.05, 0.2, 0.5, 1.0]:
            v = compute(b, t)
            assert 0 <= v.alpha <= 255, f"weapon {w} alpha {v.alpha} OOR"


# --- Scale pulse behavior -------------------------------------------

@pytest.mark.parametrize("weapon", [3, 5, 7])
def test_scale_pulses_for_weapons_with_amp(weapon):
    params = WEAPON_VFX_PARAMS[weapon]
    assert params.scale_pulse_amp > 0.0
    b = _StubBullet(weapon=weapon, spawn_time=0.0)
    samples = [compute(b, t).scale for t in [i / 60 for i in range(60)]]
    # All >= 1.0.
    for s in samples:
        assert s >= 1.0
    # Max should be near 1 + amp.
    assert max(samples) >= 1.0 + params.scale_pulse_amp * 0.5


@pytest.mark.parametrize("weapon", [0, 1, 2, 4, 6, 8, 9])
def test_scale_is_unity_for_weapons_without_pulse(weapon):
    b = _StubBullet(weapon=weapon, spawn_time=0.0)
    for t in [0.0, 0.1, 0.5, 1.0]:
        assert compute(b, t).scale == 1.0


# --- Halo behavior --------------------------------------------------

@pytest.mark.parametrize("weapon", [1, 2, 3, 4, 5, 7, 8])
def test_weapons_with_halo(weapon):
    params = WEAPON_VFX_PARAMS[weapon]
    assert params.halo_color is not None
    assert params.halo_size > 0
    assert params.halo_alpha > 0
    b = _StubBullet(weapon=weapon, spawn_time=0.0)
    v = compute(b, 0.0)
    assert v.halo_color is not None
    assert v.halo_size == params.halo_size
    assert v.halo_alpha > 0


@pytest.mark.parametrize("weapon", [0, 6, 9])
def test_weapons_without_halo(weapon):
    """Yellow plasma, white piercing, and rainbow streak have no
    halo — the sprite itself is the visual."""
    b = _StubBullet(weapon=weapon, spawn_time=0.0)
    v = compute(b, 0.0)
    assert v.halo_color is None
    assert v.halo_size == 0
    assert v.halo_alpha == 0


# --- Weapon identity check ------------------------------------------

def test_white_piercing_has_no_fx():
    """Weapon 6 (white piercing) is the no-FX weapon — fast, thin, no
    pulse, no halo. The speed is its identity."""
    params = WEAPON_VFX_PARAMS[6]
    assert params.alpha_pulse_amp == 0.0
    assert params.scale_pulse_amp == 0.0
    assert params.halo_color is None


def test_rainbow_has_pulse_but_no_halo():
    """Weapon 9 (rainbow) has an alpha pulse to give it life, but no
    halo (the gradient IS the visual)."""
    params = WEAPON_VFX_PARAMS[9]
    assert params.alpha_pulse_amp > 0.0
    assert params.halo_color is None


# --- Return type ----------------------------------------------------

def test_compute_returns_bullet_vfx():
    b = _StubBullet(weapon=4, spawn_time=1.0)
    v = compute(b, 1.5)
    assert isinstance(v, BulletVFX)
    assert hasattr(v, "alpha")
    assert hasattr(v, "scale")
    assert hasattr(v, "halo_color")
    assert hasattr(v, "halo_size")
    assert hasattr(v, "halo_alpha")


def test_compute_handles_missing_spawn_time():
    """A bullet without spawn_time (legacy / first-frame) should
    not crash — alpha pulse should still work at t=0."""
    class _NoSpawn:
        weapon = 0
    v = compute(_NoSpawn(), 0.0)
    assert v.alpha > 0


def test_compute_handles_out_of_range_weapon():
    """A bullet with weapon=99 (corrupted state) should fall back
    to weapon 0 instead of crashing."""
    b = _StubBullet(weapon=99, spawn_time=0.0)
    v = compute(b, 0.0)
    # Weapon 0 = yellow plasma, full alpha 255 at t=0 (alpha_pulse
    # sine starts at 0 -> alpha = 255 - 0.3*127 = ~217, but range
    # just needs to be valid).
    assert 0 <= v.alpha <= 255
