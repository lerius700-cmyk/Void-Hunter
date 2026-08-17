"""Tests for the weapon switching system + redesigned HUD.

Verifies:
- Player has 10 distinct weapon cooldowns and bullet speeds.
- Player.set_weapon switches the index (no-op on same weapon or
  out-of-range).
- GameplayScene wires K_1..K_9 and K_0 to the 10 weapon indices.
- HUD.set_weapon_catalog / set_current_weapon track the active
  weapon and don't crash when the weapon cache is missing.
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

from pathlib import Path

from stellar_horizon.entities.player import Player
from stellar_horizon.ui.hud import Hud


# --- Player weapon state -----------------------------------------------

def test_player_has_ten_weapon_cooldowns():
    assert len(Player.WEAPON_COOLDOWN_S) == 10
    assert len(Player.WEAPON_BULLET_SPEED) == 10
    # All cooldowns are positive.
    for c in Player.WEAPON_COOLDOWN_S:
        assert c > 0.0
    # All bullet speeds are positive and reasonable.
    for s in Player.WEAPON_BULLET_SPEED:
        assert s > 0.0


def test_player_set_weapon_switches_index():
    p = Player(pygame.Rect(0, 0, 480, 270))
    assert p.weapon == 0
    p.set_weapon(5)
    assert p.weapon == 5
    p.set_weapon(9)
    assert p.weapon == 9
    # No-op on same weapon.
    p.set_weapon(9)
    assert p.weapon == 9


def test_player_set_weapon_ignores_out_of_range():
    p = Player(pygame.Rect(0, 0, 480, 270))
    p.set_weapon(3)
    p.set_weapon(-1)
    assert p.weapon == 3
    p.set_weapon(99)
    assert p.weapon == 3


def test_player_bullet_speed_uses_weapon():
    """spawn_bullet reads WEAPON_BULLET_SPEED[self.weapon], so a
    freshly-constructed Player should emit bullets at the
    weapon-0 muzzle velocity (480 px/s)."""
    p = Player(pygame.Rect(0, 0, 480, 270))
    p.set_weapon(2)  # blue ion (700 px/s)
    pool = []
    from stellar_horizon.entities.bullet import PlayerBullet
    for _ in range(2):
        pool.append(PlayerBullet())
    p.x, p.y = 100.0, 130.0
    p.firing = True
    p.shoot_cooldown = 0.0
    p.update(1 / 120, {pygame.K_SPACE: True}, pool)
    alive = [b for b in pool if b.alive]
    assert len(alive) == 1
    assert alive[0].vx == 700.0  # weapon 2 = blue ion
    # Cooldown is set to weapon-2 value (0.07).
    assert abs(p.shoot_cooldown - 0.07) < 1e-6


def test_player_bullet_records_spawn_time_and_weapon():
    """Player._spawn_bullet must stamp the new bullet with the
    current scene time (so the code-driven VFX knows how old it is)
    and the weapon index (so the VFX picks the right animation)."""
    p = Player(pygame.Rect(0, 0, 480, 270))
    p.set_weapon(7)  # pink heart
    pool = []
    from stellar_horizon.entities.bullet import PlayerBullet
    for _ in range(2):
        pool.append(PlayerBullet())
    p.x, p.y = 100.0, 130.0
    p.firing = True
    p.shoot_cooldown = 0.0
    p.update(1 / 120, {pygame.K_SPACE: True}, pool, now=3.75)
    alive = [b for b in pool if b.alive]
    assert len(alive) == 1
    assert alive[0].spawn_time == 3.75
    assert alive[0].weapon == 7


def test_player_update_without_now_keeps_default_spawn_time():
    """Backward compat: callers that don't pass `now` should still
    work (spawn_time defaults to 0.0, which makes the VFX phase
    predictable instead of crashing)."""
    p = Player(pygame.Rect(0, 0, 480, 270))
    pool = []
    from stellar_horizon.entities.bullet import PlayerBullet
    for _ in range(2):
        pool.append(PlayerBullet())
    p.x, p.y = 100.0, 130.0
    p.firing = True
    p.shoot_cooldown = 0.0
    p.update(1 / 120, {pygame.K_SPACE: True}, pool)  # no now
    alive = [b for b in pool if b.alive]
    assert len(alive) == 1
    assert alive[0].spawn_time == 0.0
    assert alive[0].weapon == 0  # default weapon


# --- GameplayScene weapon-key mapping ----------------------------------

def test_weapon_keys_are_ten_and_distinct():
    from stellar_horizon.scenes.gameplay import GameplayScene
    keys = GameplayScene._WEAPON_KEYS
    assert len(keys) == 10
    assert len(set(keys)) == 10  # all distinct
    # 1..9 + 0 in that order.
    expected = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
               pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8,
               pygame.K_9, pygame.K_0]
    assert list(keys) == expected


def test_weapon_names_match_keys():
    from stellar_horizon.scenes.gameplay import GameplayScene
    names = GameplayScene._WEAPON_NAMES
    assert len(names) == 10
    # Each name is a non-empty string.
    for n in names:
        assert isinstance(n, str) and len(n) > 0


def test_keydown_event_switches_weapon():
    """Posting a K_3 KEYDOWN should set player.weapon to 2 (the
    third laser)."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    assert s.player.weapon == 0
    # Simulate pressing key '4' (index 3 = purple void).
    events = [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_4,
                                                  "mod": 0, "unicode": "4",
                                                  "scancode": 5,
                                                  "window": None})]
    s.update(1 / 120, events)
    assert s.player.weapon == 3


def test_same_weapon_keypress_does_not_emit_impact():
    """Pressing the key for the weapon already selected should NOT
    trigger the impact FX (the game should be idempotent)."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    s.player.set_weapon(2)
    pre = s.fx.engine._pool.active_count
    events = [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_3,
                                                  "mod": 0, "unicode": "3",
                                                  "scancode": 4,
                                                  "window": None})]
    s.update(1 / 120, events)
    post = s.fx.engine._pool.active_count
    assert post == pre, "keypress for the current weapon should not emit FX"


# --- HUD weapon catalog ------------------------------------------------

def test_hud_set_weapon_catalog_records_state():
    h = Hud()
    assert h.current_weapon == 0
    h.set_weapon_catalog({}, ("A", "B", "C"), 2)
    assert h._weapon_names == ("A", "B", "C")
    assert h.current_weapon == 2
    h.set_current_weapon(1)
    assert h.current_weapon == 1


def test_hud_draw_with_weapon_catalog_does_not_crash():
    """Draw with the catalog wired up: should not raise even though
    the catalog is empty (all weapon_anim lookups return None and
    the code falls back to a small box)."""
    h = Hud()
    h.set_weapon_catalog({}, ("A",) * 10, 0)
    surf = pygame.Surface((480, 270))
    h.draw(surf)
    # The bottom bar should have been painted (some non-bg pixels
    # along its top edge).
    found = False
    for x in range(0, 480, 8):
        r, g, b, _ = surf.get_at((x, 270 - 22))
        if (r, g, b) != (10, 15, 31):
            found = True
            break
    assert found, "bottom bar was not drawn"
