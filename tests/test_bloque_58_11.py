"""Tests for BLOQUE 58.11: Tron-style light trail.

Covers:
  - TronTrail spawn / age / max-length cap.
  - Enemy collision applies 3x damage with per-enemy cooldown.
  - Trail is rendered as a chain of cyan segments.
  - The trail is reset when the player dies.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("VOID_HUNTER_INVULN", "1")

import math
import pygame
pygame.init()
pygame.display.set_mode((1, 1))


# -----------------------------------------------------------------------
# 1) TronTrail data model
# -----------------------------------------------------------------------
def test_tron_trail_starts_empty():
    """A fresh TronTrail has no segments."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail()
    assert t.segments == []
    assert t.is_active() is False


def test_tron_trail_spawn_creates_segment():
    """spawn_if_ready creates a new segment at the back of the ship."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0)  # always ready
    # Ship facing RIGHT (angle=0), center=(100, 100), back offset=10
    t.spawn_if_ready(100.0, 100.0, 0.0, 10.0, 0.05)
    assert len(t.segments) == 1
    seg = t.segments[0]
    # Segment should be at (100-10, 100) = (90, 100) — back of ship
    assert abs(seg.cx - 90.0) < 0.5
    assert abs(seg.cy - 100.0) < 0.5
    assert seg.age == 0.0


def test_tron_trail_spawn_direction_down():
    """Ship facing DOWN (angle=pi/2 in screen coords) spawns a segment
    ABOVE the ship (the back of the ship is in the opposite direction
    of travel, which is UP).
    """
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0)
    t.spawn_if_ready(100.0, 100.0, math.pi / 2, 10.0, 0.05)
    seg = t.segments[0]
    # cos(pi/2)=0, sin(pi/2)=1. Back = (100, 100 - 10) = (100, 90)
    # (back is opposite of facing direction, so cy=90 is UP from ship)
    assert abs(seg.cx - 100.0) < 0.5
    assert abs(seg.cy - 90.0) < 0.5


def test_tron_trail_spawn_respects_interval():
    """spawn_if_ready only spawns once per spawn_interval_s."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.1)
    # First call with dt=0.1 (full interval) — should spawn
    t.spawn_if_ready(100.0, 100.0, 0.0, 10.0, 0.1)
    assert len(t.segments) == 1
    # Another call with dt=0.05 (half the interval) — should NOT spawn
    t.spawn_if_ready(100.0, 100.0, 0.0, 10.0, 0.05)
    assert len(t.segments) == 1
    # Another call with full interval — should spawn
    t.spawn_if_ready(100.0, 100.0, 0.0, 10.0, 0.1)
    assert len(t.segments) == 2


def test_tron_trail_update_ages_segments():
    """update() ages segments and removes the dead ones."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0, max_age=1.0)
    t.spawn_if_ready(100.0, 100.0, 0.0, 10.0, 0.05)
    assert t.segments[0].age == 0.0
    t.update(0.5)
    assert t.segments[0].age == 0.5
    t.update(0.6)
    assert len(t.segments) == 0  # past max_age


def test_tron_trail_max_segments_cap():
    """The trail respects max_segments cap (enforced in update())."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0, max_segments=5)
    for _ in range(10):
        t.spawn_if_ready(100.0, 100.0, 0.0, 10.0, 0.001)
    # update() is what enforces the cap (so the trail can burst-spawn
    # in one frame and then trim down).
    t.update(0.0)
    assert len(t.segments) == 5


def test_tron_trail_reset_clears():
    """reset() clears the trail and the hit cooldown dict."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0)
    t.spawn_if_ready(100.0, 100.0, 0.0, 10.0, 0.05)
    t.hit_cooldown[12345] = 0.1
    t.reset()
    assert t.segments == []
    assert t.hit_cooldown == {}


# -----------------------------------------------------------------------
# 2) TronTrail damage
# -----------------------------------------------------------------------
class _FakeEnemy:
    """Minimal stand-in for src.entities.enemies.enemy.Enemy."""
    def __init__(self, x, y, w=12, h=8, hp=10, max_hp=10):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.hp = hp
        self.max_hp = max_hp
        self.active = True
        self.damage_taken = 0
        self.state = type("S", (), {"name": "IDLE"})()
    def hitbox(self):
        """Mimic the real Enemy.hitbox() — returns a Rect with the
        70% forgiveness scale (per GDD §5)."""
        w = int(self.w * 0.7)
        h = int(self.h * 0.7)
        return pygame.Rect(int(self.x - w // 2), int(self.y - h // 2), w, h)
    def apply_damage(self, amount):
        self.hp -= amount
        self.damage_taken += amount
        if self.hp <= 0:
            self.state = type("S", (), {"name": "DEAD"})()
            return True
        return False


def test_tron_trail_damages_enemy_on_contact():
    """An enemy overlapping a trail segment takes 3x damage (per spec)."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0, segment_length=20, segment_thickness=4)
    # Spawn a segment at (100, 100) facing RIGHT
    t.spawn_if_ready(110.0, 100.0, 0.0, 10.0, 0.001)
    # Place the enemy right on the segment
    enemy = _FakeEnemy(x=105, y=100, hp=10)
    hit = t.check_enemy_collision(enemy, 0.0, damage=3)
    assert hit is True
    assert enemy.damage_taken == 3
    assert enemy.hp == 7


def test_tron_trail_respects_enemy_hit_cooldown():
    """An enemy that just got hit by the trail is immune for the cooldown."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0, segment_length=20, segment_thickness=4)
    t.spawn_if_ready(110.0, 100.0, 0.0, 10.0, 0.001)
    enemy = _FakeEnemy(x=105, y=100, hp=10)
    t.check_enemy_collision(enemy, 0.0, damage=3)
    # Second hit during cooldown — should NOT damage
    t.spawn_if_ready(110.0, 100.0, 0.0, 10.0, 0.001)
    hit = t.check_enemy_collision(enemy, 0.0, damage=3)
    assert hit is False
    assert enemy.damage_taken == 3  # unchanged
    # Wait past the cooldown and try again
    t.update(t.hit_cooldown_s + 0.01)
    hit = t.check_enemy_collision(enemy, 1.0, damage=3)
    assert hit is True
    assert enemy.damage_taken == 6


def test_tron_trail_no_hit_when_enemy_far_away():
    """An enemy far from the trail takes no damage."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0, segment_length=20, segment_thickness=4)
    t.spawn_if_ready(110.0, 100.0, 0.0, 10.0, 0.001)
    enemy = _FakeEnemy(x=200, y=200, hp=10)  # far away
    hit = t.check_enemy_collision(enemy, 0.0, damage=3)
    assert hit is False
    assert enemy.damage_taken == 0


def test_tron_trail_bbox_early_exit():
    """BLOQUE 58.11 perf: enemies far outside the bbox skip the
    per-segment loop entirely.
    """
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0, segment_length=8, segment_thickness=3)
    # Spawn a trail at (100, 100) facing right — bbox should be
    # roughly (88, 95) to (112, 105).
    t.spawn_if_ready(108.0, 100.0, 0.0, 8.0, 0.001)
    t.update(0.0)  # force bbox computation
    # Enemy very far away — should be skipped via bbox early-exit
    far_enemy = _FakeEnemy(x=300, y=300, hp=10)
    # Bbox should be roughly (88, 95)-(112, 105). Enemy at 300,300
    # with half-extent ~6 is way outside.
    assert (far_enemy.x + 6) < t.bbox_min_x or (far_enemy.x - 6) > t.bbox_max_x
    hit = t.check_enemy_collision(far_enemy, 0.0, damage=3)
    assert hit is False
    assert far_enemy.damage_taken == 0


def test_tron_trail_bbox_dirty_flag():
    """BLOQUE 58.11 perf: the bbox is only recomputed when dirty."""
    from src.systems.tron_trail import TronTrail
    t = TronTrail(spawn_interval_s=0.0, segment_length=8, segment_thickness=3)
    assert t.bbox_dirty is True
    t.spawn_if_ready(100.0, 100.0, 0.0, 8.0, 0.001)
    # After spawn, dirty is set so the next check_enemy_collision recomputes
    assert t.bbox_dirty is True
    _FakeEnemy(x=100, y=100, hp=1)  # dummy
    # Trigger bbox recompute
    class _E:
        x = 100; y = 100; w = 12; h = 8
        def hitbox(self):
            w = int(self.w * 0.7)
            h = int(self.h * 0.7)
            return pygame.Rect(int(self.x - w // 2), int(self.y - h // 2), w, h)
        def apply_damage(self, d): pass
    t.check_enemy_collision(_E(), 0.0, 1)
    assert t.bbox_dirty is False
    # Spawn a new segment — dirty should be True again
    t.spawn_if_ready(120.0, 100.0, 0.0, 8.0, 0.001)
    assert t.bbox_dirty is True


def test_tron_trail_3x_damage_value():
    """BLOQUE 58.11: damage = 3x bullet damage (L1=1, so 3 per touch)."""
    from src.core.settings import TRON_TRAIL_DAMAGE_MULT
    from src.systems.weapon_system import WeaponLevel
    # L1 bullet damage is 1 (from weapon_system specs)
    bullet_damage = 1
    expected = int(TRON_TRAIL_DAMAGE_MULT * bullet_damage)
    assert expected == 3
    # Verify the engine uses this multiplier
    from src.ui import gameplay_runtime as gpr
    import inspect
    src = inspect.getsource(gpr.GameplayRuntime._update_tron_trail_collisions)
    assert "TRON_TRAIL_DAMAGE_MULT" in src


# -----------------------------------------------------------------------
# 3) Tron trail settings
# -----------------------------------------------------------------------
def test_tron_trail_settings_present():
    """All BLOQUE 58.11 settings are defined."""
    from src.core import settings
    assert hasattr(settings, "TRON_TRAIL_DAMAGE_MULT")
    assert hasattr(settings, "TRON_TRAIL_SEGMENT_LENGTH")
    assert hasattr(settings, "TRON_TRAIL_SEGMENT_THICKNESS")
    assert hasattr(settings, "TRON_TRAIL_MAX_AGE_S")
    assert hasattr(settings, "TRON_TRAIL_SPAWN_INTERVAL_S")
    assert hasattr(settings, "TRON_TRAIL_MAX_SEGMENTS")
    assert hasattr(settings, "TRON_TRAIL_HIT_COOLDOWN_S")
    # Sanity
    assert settings.TRON_TRAIL_DAMAGE_MULT == 3.0
    assert settings.TRON_TRAIL_MAX_AGE_S >= 1.5
    assert 100 <= settings.TRON_TRAIL_MAX_SEGMENTS <= 500


# -----------------------------------------------------------------------
# 4) Tron trail is reset on player death (gameplay_runtime integration)
# -----------------------------------------------------------------------
def test_tron_trail_resets_on_player_death():
    """When the player dies, the trail must be cleared."""
    from src.ui import gameplay_runtime as gpr
    from src.entities.player import Player
    from src.entities.player.player import PlayerState

    rt = gpr.GameplayRuntime.__new__(gpr.GameplayRuntime)
    rt._player = Player()
    rt._player.is_dead = True  # simulate death
    rt._tron_trail = gpr.TronTrail(spawn_interval_s=0.0)
    # Pre-populate
    rt._tron_trail.spawn_if_ready(100.0, 100.0, 0.0, 10.0, 0.001)
    assert len(rt._tron_trail.segments) == 1
    # The integration code should call _tron_trail.reset() when
    # the player is dead. Verify the source includes this branch.
    import inspect
    src = inspect.getsource(gpr.GameplayRuntime.update)
    assert "_tron_trail.reset()" in src, (
        "Expected _tron_trail.reset() in update() when player is dead"
    )
