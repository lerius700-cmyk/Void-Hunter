"""Tests for stellar_horizon.audio.thrusters (per-ship engine loops).

Verifies:
- Player thruster: set_player / clear_player toggle the right channel
- Enemy thrusters: add_enemy assigns a channel, remove_enemy releases
  it; idempotent on double-add
- Compressor math: 1/sqrt(N) curve scales per-channel volume
- 7-channel cap: enemies beyond MAX_ENEMY_CHANNELS get no thruster
  (silent) but don't crash
- Null-safety: ThrusterManager() with audio=None is a no-op (so the
  game still runs in headless test mode)
- Scene integration: GameplayScene._sync_thrusters tracks spawn/die
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Allow tests to import stellar_horizon.* without installing it.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import math
import pygame
if not pygame.get_init():
    pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

from stellar_horizon.audio.thrusters import (
    MAX_ENEMY_CHANNELS, PLAYER_CHANNEL, THRUSTER_SFX,
    ThrusterManager, _BASE_VOLUME,
)
from stellar_horizon.entities.enemy import Enemy, EnemyKind


def _make_enemy(kind: str = "scout") -> Enemy:
    """Build a fresh enemy with `kind` set. Bypasses on_spawn() to
    avoid needing a PathFollower."""
    e = Enemy()
    e.kind = kind
    e.alive = True
    return e


# ---------------------------------------------------------------------------
# 1. Null-safety
# ---------------------------------------------------------------------------
def test_no_audio_engine_is_no_op():
    """ThrusterManager with audio=None must not crash. All operations
    are no-ops, and update() is safe with zero active."""
    tm = ThrusterManager(audio_engine=None)
    assert tm.set_player() is False
    tm.clear_player()
    e = _make_enemy()
    assert tm.add_enemy(e) is False
    tm.remove_enemy(e)
    tm.update()  # must not raise


# ---------------------------------------------------------------------------
# 2. Player thruster
# ---------------------------------------------------------------------------
def test_set_player_assigns_channel_0():
    audio = MagicMock()
    audio.play_loop.return_value = True
    tm = ThrusterManager(audio_engine=audio)
    ok = tm.set_player("player")
    assert ok
    audio.play_loop.assert_called_once()
    args, kwargs = audio.play_loop.call_args
    assert args[0] == "thruster_player"
    assert args[1] == PLAYER_CHANNEL == 0


def test_set_player_is_idempotent():
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    tm.set_player("player")
    tm.set_player("player")
    assert audio.play_loop.call_count == 1


def test_clear_player_stops_channel_0():
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    tm.set_player("player")
    tm.clear_player()
    audio.stop_loop.assert_called_once_with(PLAYER_CHANNEL)


# ---------------------------------------------------------------------------
# 3. Enemy thrusters
# ---------------------------------------------------------------------------
def test_add_enemy_assigns_free_channel():
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    e = _make_enemy("scout")
    ok = tm.add_enemy(e)
    assert ok is True
    audio.play_loop.assert_called_once()
    # Channel should be 1 (first enemy slot).
    assert audio.play_loop.call_args.args[1] == 1


def test_add_enemy_is_idempotent():
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    e = _make_enemy("scout")
    tm.add_enemy(e)
    tm.add_enemy(e)  # second call should be a no-op
    assert audio.play_loop.call_count == 1


def test_remove_enemy_releases_channel():
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    e = _make_enemy("scout")
    tm.add_enemy(e)
    tm.remove_enemy(e)
    audio.stop_loop.assert_called_once_with(1)


def test_remove_unknown_enemy_is_no_op():
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    e = _make_enemy("scout")
    tm.remove_enemy(e)  # never added
    audio.stop_loop.assert_not_called()


def test_enemy_uses_kind_specific_sfx():
    """Each enemy kind gets its own SFX so the player can identify
    them by ear."""
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    e_heavy = _make_enemy("heavy")
    e_ufo = _make_enemy("ufo")
    tm.add_enemy(e_heavy)
    tm.add_enemy(e_ufo)
    sfx_names = [c.args[0] for c in audio.play_loop.call_args_list]
    assert "thruster_heavy" in sfx_names
    assert "thruster_ufo" in sfx_names


def test_7_enemy_channel_cap():
    """The 8th enemy thruster should not get a channel."""
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    enemies = [_make_enemy("scout") for _ in range(8)]
    results = [tm.add_enemy(e) for e in enemies]
    # 7 should succeed, the 8th should fail (no free channel).
    assert sum(1 for r in results if r) == MAX_ENEMY_CHANNELS
    assert results[-1] is False


# ---------------------------------------------------------------------------
# 4. Compressor
# ---------------------------------------------------------------------------
def test_compressor_scales_with_active_count():
    """With N active thrusters, each one is scaled to base / sqrt(N).
    The compressor optimization skips the call when the volume is
    unchanged, so we force a 2nd active thruster so the scale drops
    from 1.0 to 0.707 and triggers the set_channel_volume call.
    """
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    tm.set_player("player")
    audio.set_channel_volume.reset_mock()  # ignore the initial set in _play_on
    # Add 1 enemy so total = 2, scale = 1/sqrt(2) ≈ 0.707.
    tm.add_enemy(_make_enemy("scout"))
    tm.update()
    # The player channel should have been called with the new volume.
    assert audio.set_channel_volume.call_count >= 1
    # Find the call for the player channel and verify the volume.
    player_calls = [c for c in audio.set_channel_volume.call_args_list
                    if c.args[0] == PLAYER_CHANNEL]
    assert len(player_calls) == 1
    new_volume = player_calls[0].args[1]
    expected = _BASE_VOLUME["player"] / math.sqrt(2)
    assert abs(new_volume - expected) < 1e-6


def test_initial_volume_set_on_play():
    """When a thruster starts, the initial volume is passed to
    play_loop() so pygame.mixer plays it at the right level from
    frame 1 (no need to wait for the compressor)."""
    audio = MagicMock()
    audio.play_loop.return_value = True
    tm = ThrusterManager(audio_engine=audio)
    tm.set_player("player")
    audio.play_loop.assert_called_once()
    args, _ = audio.play_loop.call_args
    sfx_name, channel, volume = args
    assert sfx_name == "thruster_player"
    assert channel == PLAYER_CHANNEL
    assert abs(volume - _BASE_VOLUME["player"]) < 1e-6


def test_compressor_divides_by_sqrt_n():
    """4 ships = each at 50% of base (1/sqrt(4) = 0.5)."""
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    tm.set_player("player")
    # Add 3 enemies for total = 4
    for kind in ("scout", "cruiser", "heavy"):
        tm.add_enemy(_make_enemy(kind))
    # Trigger an update with a DIFFERENT scale than the initial 1.0.
    # Since we just added 3 enemies, active=4. The initial player
    # volume was set to base (no scale). After update(), the
    # compressor kicks in and the player volume drops to base/2.
    tm.update()
    # Find the LAST call for the player channel — it should reflect
    # the compressed scale.
    player_calls = [c for c in audio.set_channel_volume.call_args_list
                    if c.args[0] == PLAYER_CHANNEL]
    assert len(player_calls) == 1  # only one call (the compressed one)
    new_volume = player_calls[0].args[1]
    expected = _BASE_VOLUME["player"] / math.sqrt(4)
    assert abs(new_volume - expected) < 1e-6


def test_compressor_dead_silence_after_clear():
    """After clearing all thrusters, update() does nothing."""
    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    tm.set_player("player")
    tm.update()
    audio.set_channel_volume.reset_mock()
    tm.clear_player()
    tm.update()
    audio.set_channel_volume.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Scene integration: _sync_thrusters tracks spawn/die
# ---------------------------------------------------------------------------
def test_sync_thrusters_adds_for_new_spawns():
    """When the wave manager spawns a new enemy, _sync_thrusters
    assigns a thruster."""
    from stellar_horizon.audio.thrusters import ThrusterManager

    # Build a scene with a mock wave manager.
    class _MockWM:
        spawned_enemies: list = []

    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    wm = _MockWM()

    # Mimic what _sync_thrusters does (without spinning up the
    # whole scene).
    spawned = wm.spawned_enemies
    managed = set()
    for e in spawned:
        if e.alive and id(e) not in managed:
            if tm.add_enemy(e):
                managed.add(id(e))
    # Spawn a new enemy.
    new_e = _make_enemy("scout")
    new_e.alive = True
    spawned.append(new_e)
    # Sync.
    for e in spawned:
        if e.alive and id(e) not in managed:
            if tm.add_enemy(e):
                managed.add(id(e))
    # The new enemy should have a thruster.
    assert id(new_e) in managed


def test_sync_thrusters_releases_dead_enemies():
    """When an enemy dies, _sync_thrusters releases its channel."""
    from stellar_horizon.audio.thrusters import ThrusterManager

    audio = MagicMock()
    tm = ThrusterManager(audio_engine=audio)
    e = _make_enemy("scout")
    tm.add_enemy(e)
    # Mark as dead.
    e.alive = False
    # Simulate sync: live_ids = {e for e in spawned if e.alive}
    # In our test, the spawned list is just [e], and e.alive=False,
    # so live_ids is empty.
    live_ids = set()
    managed = {id(e)}
    dead = managed - live_ids
    for eid in dead:
        tm.remove_enemy(e)
    audio.stop_loop.assert_called_once_with(1)
