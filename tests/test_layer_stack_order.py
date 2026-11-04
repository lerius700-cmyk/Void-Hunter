"""BLOQUE 75 Fase 2: the layer order is DATA, not code.

The order the frame used to be drawn in is now a list of layers with a
`z`. This test pins it: a layer moved by accident changes the frame, and
the golden frames would catch the pixels -- but only if the ids and their
order are pinned here too.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXPECTED = (
    "ambient_dust",
    "player_damage_flash",
    "powerups",
    "enemies",
    "asteroids_and_powerups",
    "leader_glows",
    "boss",
    "boss_spears",
    "shield_laser",
    "shockwaves",
    "bomb_bursts",
    "bullets",
    "missiles",
    "tron_trail",
    "player_afterimage",
    "player",
    "continuous_laser",
    "reticle",
    "bomb_flash",
    "particles",
    "score_popups",
    "wave_indicator",
    "play_area_frame",
    "hud",
    "pattern_banner",
    "screen_flash",
    "charge_release_flash",
    "pickup_flash",
    "level_up_flash",
    "speed_lines",
)


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def test_the_layer_order_is_pinned(display):
    from src.ui.gameplay_layers import build_layers
    from src.ui.gameplay_runtime import GameplayRuntime

    runtime = GameplayRuntime(lambda *a, **k: None, is_boss=False, act=1, audio=None)
    stack = build_layers(runtime)
    assert tuple(layer.id for layer in stack.layers) == EXPECTED
    assert tuple(layer.z for layer in stack.layers) == tuple(range(len(EXPECTED)))


def test_every_layer_calls_a_method_that_exists(display):
    """A renamed runtime method must break here, not silently."""
    from src.ui.gameplay_layers import LAYER_BODIES
    from src.ui.gameplay_runtime import GameplayRuntime

    runtime = GameplayRuntime(lambda *a, **k: None, is_boss=False, act=1, audio=None)
    for method_name in LAYER_BODIES:
        assert hasattr(runtime, method_name), method_name


def test_every_helper_arity_matches_the_factory(display):
    """The layer body must pass what the helper actually takes.

    The runtime's draw helpers are a MIX: some take `(target)` and some
    take `(target, ox, oy)`. The factory has one call form per helper, so
    a helper whose signature changes must break HERE -- otherwise the
    layer raises TypeError in the middle of a frame (or, worse, silently
    draws with the wrong arguments).
    """
    from src.ui.gameplay_layers import LAYER_ARITY, LAYER_BODIES
    from src.ui.gameplay_runtime import GameplayRuntime

    runtime = GameplayRuntime(lambda *a, **k: None, is_boss=False, act=1, audio=None)
    assert len(LAYER_ARITY) == len(LAYER_BODIES)
    for method_name, arity in zip(LAYER_BODIES, LAYER_ARITY):
        method = getattr(runtime, method_name)
        params = inspect.signature(method).parameters
        # `self` is bound out, so what is left is what the layer passes.
        assert len(params) == arity, (method_name, tuple(params))
