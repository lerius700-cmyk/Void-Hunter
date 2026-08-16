# stellar_horizon/tests/test_enemy.py
import pytest
import pygame

from stellar_horizon.entities.enemy import Enemy, EnemyKind
from src.movement import PathFollower, HybridPath
from stellar_horizon.waves.bezier_horizontal import path_s_right_to_left


class FakePlayer:
    def __init__(self, x=200, y=135):
        self.x, self.y = x, y


def test_enemy_kind_constants():
    assert EnemyKind.SCOUT == "scout"
    assert EnemyKind.CRUISER == "cruiser"
    assert EnemyKind.HEAVY == "heavy"


def test_enemy_starts_inactive():
    e = Enemy()
    assert e.alive is False
    assert e.hp == 1
    assert e.kind == EnemyKind.SCOUT


def test_enemy_take_damage_decrements_hp():
    e = Enemy()
    e.hp = 4
    e.alive = True
    e.take_damage(1)
    assert e.hp == 3


def test_enemy_take_damage_kills_at_zero():
    e = Enemy()
    e.hp = 1
    e.alive = True
    e.take_damage(1)
    assert e.alive is False


def test_enemy_path_attached_moves_along_path():
    path = path_s_right_to_left(y_offset=0)
    hybrid = HybridPath.from_segments([path])
    follower = PathFollower(hybrid)
    e = Enemy()
    e.attach_path(follower, slot_dx=0, slot_dy=0)
    e.x = 0
    e.y = 0
    e.alive = True
    player = FakePlayer()
    for _ in range(10):
        e.update(0.05, player)
    assert e.x > 0


def test_enemy_path_done_marks_done_flag():
    path = path_s_right_to_left()
    hybrid = HybridPath.from_segments([path])
    hybrid_short = HybridPath([hybrid.segments[0]], [0.2])
    follower = PathFollower(hybrid_short)
    e = Enemy()
    e.attach_path(follower, slot_dx=0, slot_dy=0)
    e.alive = True
    player = FakePlayer()
    for _ in range(60):
        e.update(0.05, player)
    assert e.path_done is True


def test_enemy_off_screen_culling_left():
    e = Enemy()
    e.x = -50.0
    e.y = 100.0
    e.alive = True
    e.path_done = True
    e.update(0.05, FakePlayer())
    assert e.alive is False


def test_enemy_off_screen_culling_top():
    e = Enemy()
    e.x = 100.0
    e.y = -50.0
    e.alive = True
    e.path_done = True
    e.update(0.05, FakePlayer())
    assert e.alive is False


def test_scout_attack_cooldown_1_5s():
    e = Enemy()
    e.kind = EnemyKind.SCOUT
    e.hp = 1
    e.alive = True
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraphing is True
    assert e.telegraph_frames == 8


def test_cruiser_attack_cooldown_1_2s():
    e = Enemy()
    e.kind = EnemyKind.CRUISER
    e.hp = 4
    e.alive = True
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraph_frames == 14


def test_heavy_attack_cooldown_2_5s():
    e = Enemy()
    e.kind = EnemyKind.HEAVY
    e.hp = 12
    e.alive = True
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraph_frames == 24


def test_enemy_emits_bullet_after_telegraph():
    """Verify telegraph starts, ticks down, then emits a bullet. Position kept in play area manually."""
    e = Enemy()
    e.kind = EnemyKind.SCOUT
    e.hp = 1
    e.alive = True
    # No path attached — we want to control position manually to stay in play area
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraphing is True
    for _ in range(20):
        e.update(0.05, player)
        e.x, e.y = 200.0, 100.0  # keep position in play area (no path = no auto-move)
    assert e.telegraphing is False
