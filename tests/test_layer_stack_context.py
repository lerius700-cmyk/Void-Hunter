"""BLOQUE 75 Fase 2: the frame engine.

The engine is generic: it knows about layers, an order and a context, and
NOTHING about the game. That boundary is what keeps the mypy gate clean
(L6): `src/render/` must not import `src/ui/` or `src/entities/`.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.render.layer import DrawContext, Layer, LayerStack


@pytest.fixture(scope="module")
def display():
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _ctx(**kwargs) -> DrawContext:
    base = {
        "target": pygame.Surface((320, 480)),
        "origin": (160.0, 240.0),
        "scale": 1.0,
        "time": 0.0,
        "shake": (0, 0),
        "size": (320, 480),
    }
    base.update(kwargs)
    return DrawContext(**base)


def test_the_stack_renders_in_z_order(display):
    calls: list[str] = []
    stack = LayerStack(
        [
            Layer(id="second", z=5, draw=lambda t, c: calls.append("second")),
            Layer(id="first", z=1, draw=lambda t, c: calls.append("first")),
        ]
    )
    stack.render(_ctx())
    assert calls == ["first", "second"]


def test_the_stack_is_stable_for_equal_z(display):
    calls: list[str] = []
    stack = LayerStack(
        [
            Layer(id="a", z=1, draw=lambda t, c: calls.append("a")),
            Layer(id="b", z=1, draw=lambda t, c: calls.append("b")),
        ]
    )
    stack.render(_ctx())
    assert calls == ["a", "b"]


def test_the_context_keeps_the_internal_resolution(display):
    ctx = _ctx()
    assert ctx.size == (320, 480)
    assert ctx.scale == 1.0


def test_with_origin_moves_the_origin_without_mutating_the_original(display):
    ctx = _ctx()
    moved = ctx.with_origin(10.0, 20.0)
    assert moved.origin == (10.0, 20.0)
    assert ctx.origin == (160.0, 240.0)
    assert moved.shake == ctx.shake
    assert moved.target is ctx.target


def test_at_adds_the_shake_once(display):
    ctx = _ctx(shake=(3, -4))
    assert ctx.at(10.0, 20.0) == (13, 16)


def test_the_render_package_does_not_import_the_game(display):
    """L6: `src/render/` must not depend on `src/ui/` or `src/entities/`."""
    source = (ROOT / "src" / "render" / "layer.py").read_text(encoding="utf-8")
    for forbidden in ("src.ui", "src.entities", "src.anim"):
        assert forbidden not in source, f"{forbidden} must not be imported by src/render/"
