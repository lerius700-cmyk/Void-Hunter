"""Thruster sound manager: per-ship engine loops with dynamic compression.

Why this module exists
----------------------
The game has 6 enemy kinds + 1 player. Each ship has its own
engine sound so the player can tell what they're fighting by ear
(scout whine vs cruiser hum vs kamikaze scream). The naive
approach — play each engine at full volume and stack them — turns
into a wall of noise when a wave has 10+ enemies on screen.

This module:
  1. Reserves 8 dedicated mixer channels (0 = player, 1-7 = enemies).
  2. Assigns a channel to each ship on spawn, releases on death.
  3. Applies a sqrt(N) compressor each frame: with N active
     thrusters, each one is scaled to 1/sqrt(N). The result is that
     1 ship = full volume, 4 ships = 50% each, 9 ships = 33% each.
     Total perceived volume stays roughly constant as the wave
     scales up.
  4. Uses different SFX names per kind (from SFX_CATALOG in
     src/audio/synth.py) so the player can identify ships by ear.

API
---
    tm = ThrusterManager(audio_engine)
    tm.set_player(player)              # permanent channel
    tm.add_enemy(enemy)                # assigns a channel
    tm.remove_enemy(enemy)             # stops the channel
    tm.update()                       # apply compressor each frame
"""
from __future__ import annotations

import math
from typing import Optional


# Per-kind SFX name. The SFX must exist in SFX_CATALOG.
# Player is treated specially (always-on channel 0).
THRUSTER_SFX = {
    "player":   "thruster_player",
    "scout":    "thruster_scout",
    "cruiser":  "thruster_cruiser",
    "heavy":    "thruster_heavy",
    "bomber":   "thruster_bomber",
    "ufo":      "thruster_ufo",
    "kamikaze": "thruster_kamikaze",
}

# Base volume per ship (before compression). Player is the quietest
# baseline; heavies/bombers are a bit louder so they read through.
_BASE_VOLUME = {
    "player":   0.45,
    "scout":    0.32,
    "cruiser":  0.34,
    "heavy":    0.42,
    "bomber":   0.38,
    "ufo":      0.32,
    "kamikaze": 0.40,
}

# Cap on simultaneous enemy thrusters (we reserve 7 channels for
# enemies on top of the 1 player channel).
MAX_ENEMY_CHANNELS = 7
PLAYER_CHANNEL = 0
ENEMY_CHANNELS_START = 1  # channels 1..7 are for enemies


class ThrusterManager:
    """Per-ship engine loops with dynamic compression.

    Null-safe: if `audio_engine` is missing or the mixer is down,
    all operations become no-ops. This lets the game run in
    headless test environments without pygame.mixer.

    The enemy dict keys are the enemy OBJECTS (not id()), so the
    dict keeps a strong reference. Without this, short-lived
    enemies in tests (or any caller that doesn't hold a ref) would
    be GC'd and the id() could be reused, silently breaking the
    channel map.
    """

    def __init__(self, audio_engine=None) -> None:
        self._audio = audio_engine
        # enemy_object -> channel_id (1..7). Strong reference via
        # the key keeps the enemy alive while it has a thruster.
        self._enemy_channels: dict = {}
        # Per-channel current volume (so we can apply compressor
        # without restarting the loop).
        self._channel_volumes: dict[int, float] = {}
        self._player_kind: Optional[str] = None
        self._active: int = 0  # total active thrusters (player + enemies)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_player(self, kind: str = "player") -> bool:
        """Start the player thruster loop on channel 0.

        Idempotent: calling twice with the same kind is a no-op.
        """
        if self._player_kind == kind:
            return True
        self._player_kind = kind
        sfx_name = THRUSTER_SFX.get(kind, THRUSTER_SFX["player"])
        base = _BASE_VOLUME.get(kind, 0.40)
        ok = self._play_on(PLAYER_CHANNEL, sfx_name, base)
        if ok:
            self._active += 1
        return ok

    def clear_player(self) -> None:
        """Stop the player thruster (e.g. on game over)."""
        if self._player_kind is None:
            return
        self._stop_on(PLAYER_CHANNEL)
        self._player_kind = None
        self._active = max(0, self._active - 1)

    def add_enemy(self, enemy) -> bool:
        """Assign a free channel to the enemy and start the loop.

        If all 7 enemy channels are busy, the enemy is silent (the
        player still gets the visual but no extra thruster audio).
        Returns True if a channel was assigned, False otherwise.

        The enemy object is stored as the dict key, so the manager
        holds a strong reference until `remove_enemy` is called.
        """
        # Re-use channel if the enemy already has one (idempotent).
        if enemy in self._enemy_channels:
            return True
        # Find a free channel
        used = set(self._enemy_channels.values())
        for slot in range(MAX_ENEMY_CHANNELS):
            channel = ENEMY_CHANNELS_START + slot
            if channel not in used:
                sfx_name = THRUSTER_SFX.get(enemy.kind, THRUSTER_SFX["scout"])
                base = _BASE_VOLUME.get(enemy.kind, 0.32)
                if self._play_on(channel, sfx_name, base):
                    self._enemy_channels[enemy] = channel
                    self._active += 1
                    return True
                return False
        return False  # no free channel

    def remove_enemy(self, enemy) -> None:
        """Stop the enemy's thruster and release its channel."""
        channel = self._enemy_channels.pop(enemy, None)
        if channel is not None:
            self._stop_on(channel)
            self._active = max(0, self._active - 1)

    def update(self) -> None:
        """Apply the dynamic compressor to all active thrusters.

        Call once per frame. The curve is:
            volume_scale = 1.0 / sqrt(active_count)
        so 1 ship = 100%, 4 ships = 50% each, 9 ships = 33% each.
        """
        if self._active <= 0:
            return
        scale = 1.0 / math.sqrt(self._active)
        # Player
        if self._player_kind is not None:
            base = _BASE_VOLUME.get(self._player_kind, 0.40)
            self._apply_volume(PLAYER_CHANNEL, base * scale)
        # Enemies — dict key IS the enemy object, so we can read
        # the kind without a separate reverse map.
        for enemy, channel in self._enemy_channels.items():
            base = _BASE_VOLUME.get(enemy.kind, 0.32)
            self._apply_volume(channel, base * scale)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _play_on(self, channel: int, sfx_name: str, base_volume: float) -> bool:
        if self._audio is None:
            return False
        ok = self._audio.play_loop(sfx_name, channel, base_volume)
        if ok:
            self._channel_volumes[channel] = base_volume
        return ok

    def _stop_on(self, channel: int) -> None:
        if self._audio is None:
            return
        self._audio.stop_loop(channel)
        self._channel_volumes.pop(channel, None)

    def _apply_volume(self, channel: int, volume: float) -> None:
        if self._audio is None:
            return
        # Only call set_channel_volume if the value actually
        # changed by a meaningful amount (pygame calls aren't free).
        prev = self._channel_volumes.get(channel, -1.0)
        if abs(prev - volume) < 0.005:
            return
        self._audio.set_channel_volume(channel, volume)
        self._channel_volumes[channel] = volume
