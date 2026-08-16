# stellar_horizon/tests/test_fx.py
import pytest
import pygame

from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.fx.screen_shake import ScreenShake


def test_fx_layer_constructs():
    fx = FxLayer()
    assert fx is not None


def test_fx_layer_emit_sparks():
    fx = FxLayer()
    fx.emit_sparks(100, 100, count=5)
    assert fx.engine.active_count > 0


def test_fx_layer_emit_explosion():
    fx = FxLayer()
    fx.emit_explosion(200, 100, scale=1.0)
    assert fx.engine.active_count > 0


def test_fx_layer_update_and_draw():
    fx = FxLayer()
    fx.emit_sparks(100, 100, count=3)
    fx.update(0.1)
    surf = pygame.Surface((480, 270))
    fx.draw(surf)


def test_screen_shake_starts_at_zero():
    s = ScreenShake()
    assert s.offset() == (0.0, 0.0)


def test_screen_shake_add_trauma_produces_offset():
    s = ScreenShake()
    s.add_trauma(1.0)
    s.update(0.016)
    ox, oy = s.offset()
    assert abs(ox) > 0 or abs(oy) > 0


def test_screen_shake_decays():
    s = ScreenShake()
    s.add_trauma(1.0)
    s.update(0.016)
    for _ in range(600):
        s.update(1 / 120)
    assert s.trauma == pytest.approx(0.0, abs=0.01)
