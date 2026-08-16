# stellar_horizon/tests/test_hud.py
import pytest
import pygame

from stellar_horizon.ui.hud import Hud
from stellar_horizon.entities.player import Player
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


@pytest.fixture
def hud():
    return Hud()


@pytest.fixture
def screen():
    return pygame.Surface((INTERNAL_W, INTERNAL_H))


def test_hud_initial_state(hud):
    assert hud.score == 0
    assert hud.wave_n == 0
    assert hud.wave_total == 0


def test_hud_set_score(hud):
    hud.set_score(12345)
    assert hud.score == 12345


def test_hud_set_wave(hud):
    hud.set_wave(2, 4)
    assert hud.wave_n == 2
    assert hud.wave_total == 4


def test_hud_format_score(hud, screen):
    hud.set_score(12345)
    hud.set_wave(2, 4)
    hud.set_enemies_remaining(8, 15)
    hud.draw(screen)


def test_hud_with_player(hud, screen):
    p = Player(pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H))
    hud.set_player(p)
    hud.draw(screen)


def test_hud_with_boss(hud, screen):
    from stellar_horizon.entities.boss import Boss
    boss = Boss()
    hud.set_boss(boss)
    hud.draw(screen)


def test_hud_lives_display(hud, screen):
    p = Player(pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H))
    p.lives = 2
    hud.set_player(p)
    hud.draw(screen)
