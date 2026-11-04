"""BLOQUE 75: the layered frame engine.

Three objects:

  * `DrawContext` -- WHERE and WHEN a layer draws: the target surface, the
    world point at the target's centre, the uniform scale, the scene clock,
    the screen shake and the target size. The internal resolution is fixed
    at 320x480; the window scaling happens in `Game._present()`, never
    here.
  * `Layer` -- ONE draw operation: an id, a `z` (the global order) and the
    draw body. The body is the drawing code that already exists.
  * `LayerStack` -- the ordered set of layers that compose one frame.

This module is generic on purpose: it imports stdlib and pygame and
NOTHING from the game. That keeps the mypy gate over `src/anim/` clean
(L6) and makes the engine reusable by another scene later.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Sequence

import pygame


@dataclass(frozen=True)
class DrawContext:
    """Everything a layer needs to know about WHERE and WHEN it draws."""

    target: pygame.Surface
    origin: tuple[float, float]
    scale: float
    time: float
    shake: tuple[int, int]
    size: tuple[int, int]

    def with_origin(self, x: float, y: float) -> "DrawContext":
        """A copy whose origin is another world point.

        The procedural fallback draws into a scratch surface centred on the
        entity: the scratch is 64x64 (player), 48x48 (enemy) or 64x64
        (sub-boss), and the current code computes
        `offset = scratch_size // 2 - entity_pos` per entity
        (gameplay_runtime.py:5351-5353). `with_origin` replaces that
        arithmetic: the layer asks for a context centred on the entity and
        the scratch draw becomes ordinary code.
        """
        return replace(self, origin=(x, y))

    def at(self, x: float, y: float) -> tuple[int, int]:
        """A screen-space position plus the shake.

        The origin and the scale are NOT applied here: the caller owns
        that mapping. The shake IS applied here, and only here -- the old
        code passed `(target, shx, shy)` to every draw call.

        The position is truncated toward zero (`int()`), NOT floored:
        `at(-0.5, 0.5)` with a shake of `(3, -4)` gives `(3, -4)`.
        """
        return (int(x) + self.shake[0], int(y) + self.shake[1])


@dataclass(frozen=True)
class Layer:
    """One draw operation of the frame."""

    id: str
    z: int
    draw: Callable[[pygame.Surface, DrawContext], None]


class LayerStack:
    """The ordered set of layers that compose one frame.

    The stack owns the ORDER and nothing else: it never draws a layer
    itself, never mutates a layer and never reorders at runtime. The order
    is fixed at build time and asserted by `tests/test_layer_stack_order.py`.
    """

    def __init__(self, layers: Sequence[Layer]) -> None:
        self._layers = tuple(sorted(layers, key=lambda layer: layer.z))

    @property
    def layers(self) -> tuple[Layer, ...]:
        return self._layers

    def render(self, ctx: DrawContext) -> None:
        for layer in self._layers:
            layer.draw(ctx.target, ctx)
