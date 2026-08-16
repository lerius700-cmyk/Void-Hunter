# stellar_horizon/tests/test_player.py
import pygame
import pytest

from stellar_horizon.entities.player import Player
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


@pytest.fixture
def screen_rect():
    return pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H)


@pytest.fixture
def no_keys():
    return {k: False for k in (
        pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
        pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
        pygame.K_SPACE,
    )}


def test_player_starts_at_left_center(screen_rect):
    p = Player(screen_rect)
    assert p.x == 40.0
    assert p.y == screen_rect.centery


def test_player_has_3_lives(screen_rect):
    p = Player(screen_rect)
    assert p.lives == 3
    assert p.alive is True


def test_player_move_right(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_d: True}
    p.update(0.1, keys, [])
    assert p.x > 40.0
    assert p.vy == 0.0


def test_player_move_up_with_w(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_w: True}
    p.update(0.1, keys, [])
    assert p.y < screen_rect.centery


def test_player_move_with_arrows(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_LEFT: True}
    p.update(0.1, keys, [])
    assert p.x < 40.0


def test_player_bounds_x(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_d: True}
    for _ in range(600):
        p.update(1 / 120, keys, [])
    assert p.x <= 472


def test_player_bounds_y(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_w: True}
    for _ in range(600):
        p.update(1 / 120, keys, [])
    assert p.y >= 16


def test_player_take_hit_decrements_lives(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    assert p.lives == 2


def test_player_take_hit_sets_iframes(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    assert p.invulnerable_frames > 0


def test_player_take_hit_kills_when_no_lives(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    p.invulnerable_frames = 0  # reset iframes between hits (in real gameplay 3 hits can't happen within 30f)
    p.take_hit()
    p.invulnerable_frames = 0
    p.take_hit()
    assert p.lives == 0
    assert p.alive is False


def test_player_iframes_prevent_double_hit(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    p.take_hit()
    assert p.lives == 2


def test_player_shoot_cooldown_decreases(screen_rect, no_keys):
    p = Player(screen_rect)
    p.shoot_cooldown = 0.5
    p.update(0.1, no_keys, [])
    assert p.shoot_cooldown == pytest.approx(0.4)
