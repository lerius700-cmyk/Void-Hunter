"""Tests for the new enemy types (BOMBER, UFO, KAMIKAZE) added in the
sprite-expansion + level-improve pass.

Verifies:
- All 6 kinds are registered in EnemyKind
- BOMBER drops bombs with the _bomb flag
- UFO's path_done → sinuous oscillation keeps y in a reasonable band
- KAMIKAZE homes toward the player when path_done
- WaveManager builds enemies of every kind without error
- _ENEMY_SPRITE_CYCLE covers every new kind
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import pygame
if not pygame.get_init():
    pygame.init()
if not pygame.font.get_init():
    pygame.font.init()

import math
from pathlib import Path

from stellar_horizon.entities.enemy import Enemy, EnemyKind, _TYPE_PARAMS
from stellar_horizon.scenes.gameplay import _ENEMY_SPRITE_CYCLE
from stellar_horizon.waves.bezier_horizontal import path_s_right_to_left
from stellar_horizon.waves.wave_manager import _build_enemies


class _FakePlayer:
    """Minimal stand-in for the player used by Enemy.update()."""
    x = 50.0
    y = 130.0


def _make_enemy(kind: str) -> Enemy:
    e = Enemy()
    e.kind = kind
    e.on_spawn()
    return e


# --- EnemyKind coverage ------------------------------------------------

def test_all_six_kinds_registered():
    expected = {"scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze"}
    actual = {k for k in vars(EnemyKind).values() if isinstance(k, str)}
    assert expected.issubset(actual), f"missing: {expected - actual}"


def test_type_params_cover_all_kinds():
    for kind in ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze"):
        assert kind in _TYPE_PARAMS, f"no _TYPE_PARAMS entry for {kind}"


def test_sprite_cycle_covers_all_kinds():
    for kind in ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze"):
        assert kind in _ENEMY_SPRITE_CYCLE, f"no sprite cycle for {kind}"
        assert len(_ENEMY_SPRITE_CYCLE[kind]) >= 2, (
            f"{kind} should have at least 2 sprite variants"
        )


# --- BOMBER behavior ----------------------------------------------------

def test_bomber_drops_bomb_with_flag():
    e = _make_enemy("bomber")
    # Place on-screen and tick enough for bomb_timer to expire.
    e.x, e.y = 300.0, 100.0
    e.bomb_timer = 0.0  # force immediate drop
    player = _FakePlayer()
    bullets = e.update(1 / 120, player)
    assert len(bullets) == 1
    assert bullets[0]._bomb is True
    # Bomb's vertical velocity should be downward (positive vy).
    assert bullets[0].vy > 0


def test_bomber_horizontal_velocity_low():
    """Bombs drop mostly straight down — vx should be much smaller than vy."""
    e = _make_enemy("bomber")
    e.x, e.y = 300.0, 100.0
    e.bomb_timer = 0.0
    bullets = e.update(1 / 120, _FakePlayer())
    b = bullets[0]
    assert abs(b.vx) < abs(b.vy)


def test_bomber_does_not_fire_normal_bullets():
    """Bomber should only drop bombs, never a regular telegraph shot."""
    e = _make_enemy("bomber")
    e.x, e.y = 300.0, 100.0
    # Tick many frames; collect all bullets and assert none lack _bomb.
    player = _FakePlayer()
    all_bullets = []
    for _ in range(240):  # 2s
        all_bullets.extend(e.update(1 / 120, player))
        if not e.alive:
            break
    for b in all_bullets:
        assert b._bomb is True, "bomber produced a non-bomb bullet"


# --- UFO behavior -------------------------------------------------------

def test_ufo_sinuous_oscillates_after_entry():
    e = _make_enemy("ufo")
    e.x, e.y = 300.0, 130.0
    e.path_done = True
    e.ufo_base_y = 130.0
    base_y = e.y
    # Tick 2 seconds; y should oscillate around base_y.
    ys = []
    for _ in range(240):
        e.update(1 / 120, _FakePlayer())
        ys.append(e.y)
    min_y, max_y = min(ys), max(ys)
    assert min_y < base_y, f"UFO never dipped below base: min={min_y}"
    assert max_y > base_y, f"UFO never rose above base: max={max_y}"
    # Amplitude should be the +/-35 px we wired in.
    assert (max_y - min_y) > 30, f"UFO swing too small: {max_y - min_y}px"


def test_ufo_leftward_drift_after_entry():
    e = _make_enemy("ufo")
    e.x, e.y = 300.0, 130.0
    e.path_done = True
    e.ufo_base_y = 130.0
    start_x = e.x
    for _ in range(120):  # 1 second
        e.update(1 / 120, _FakePlayer())
    assert e.x < start_x, "UFO should drift left after entry path is done"


# --- KAMIKAZE behavior --------------------------------------------------

def test_kamikaze_homes_toward_player():
    e = _make_enemy("kamikaze")
    e.x, e.y = 350.0, 50.0
    e.path_done = True  # skip the entry path; go straight to homing
    player = _FakePlayer()
    player.x, player.y = 50.0, 200.0  # player is below-left
    # Tick 0.5s; velocity should point toward the player.
    for _ in range(60):
        e.update(1 / 120, player)
    # After a few frames, vx and vy should both be negative (toward player).
    assert e.vx < 0, f"kamikaze vx should be negative: {e.vx}"
    assert e.vy > 0, f"kamikaze vy should be positive (downward toward player): {e.vy}"


def test_kamikaze_deals_2_contact_damage():
    e = _make_enemy("kamikaze")
    assert e.contact_damage == 2


def test_others_deal_1_contact_damage():
    for kind in ("scout", "cruiser", "heavy", "bomber", "ufo"):
        e = _make_enemy(kind)
        assert e.contact_damage == 1, f"{kind} should deal 1 contact damage"


# --- WaveManager integration -------------------------------------------

def test_wave_manager_builds_all_kinds():
    """WaveManager._build_enemies must accept the new kinds via _KIND_MAP."""
    from stellar_horizon.waves.wave_manager import _KIND_MAP
    for kind in ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze"):
        spawn = {
            "formation": "v_pointing_left",
            "formation_count": 3,
            "enemy_kind": kind,
            "path": "s_right_to_left",
        }
        enemies = _build_enemies(spawn, sprite_picker=lambda k: f"enemy_{k}")
        assert len(enemies) == 3
        for e in enemies:
            assert e.alive
            assert e.sprite_name  # sprite was assigned
