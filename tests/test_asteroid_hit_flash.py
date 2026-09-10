"""BLOQUE 71: Asteroid hit_timer and flash render."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from src.entities.asteroid import Asteroid, draw_asteroid_with_hit_flash
from src.core.settings import HIT_FLASH_DURATION_S


def _make_asteroid() -> Asteroid:
    return Asteroid(x=160, y=240, radius=24, variant=0, scale=1.0)


def test_asteroid_hit_sets_hit_timer():
    ast = _make_asteroid()
    assert ast.hit_timer == 0.0
    result = ast.hit(damage=1)
    assert result is False
    assert ast.hit_timer == HIT_FLASH_DURATION_S


def test_asteroid_hit_timer_decrements():
    ast = _make_asteroid()
    ast.hit()
    initial = ast.hit_timer
    ast.update(dt=0.05)
    assert ast.hit_timer == pytest.approx(initial - 0.05)


def test_asteroid_hit_timer_reaches_zero():
    ast = _make_asteroid()
    ast.hit()
    ast.update(dt=HIT_FLASH_DURATION_S + 0.01)
    assert ast.hit_timer == 0.0


def test_asteroid_indestructible_always_returns_false():
    ast = _make_asteroid()
    for _ in range(5):
        assert ast.hit(damage=99) is False
    assert ast.active is True  # still alive


def test_draw_asteroid_with_hit_flash_does_not_crash():
    pygame.init()
    # dummy driver requires a display set_mode before pygame.image.load
    # (the brief's "no crash even if sprite missing" note assumes fallback;
    #  in this env the sprite exists, so we need a display for image.load)
    pygame.display.set_mode((320, 480))
    target = pygame.Surface((320, 480))
    ast = _make_asteroid()
    ast.hit()
    # Should not raise even if sprite is missing
    draw_asteroid_with_hit_flash(target, ast)
    pygame.quit()
