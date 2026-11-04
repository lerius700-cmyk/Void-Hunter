"""BLOQUE 75 Fase 2: a `fixed` pivot means "do not apply the correction".

`pivot = "fixed"` is what the enemy sets declare: the sprite is blitted
CENTRED on the entity, exactly as the runtime does today. The measured
registration is recorded in the anchors table, but applying it would move
the ship up to 3.7 px off its hitbox -- and the golden frames would catch
it.
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

from src.anim.anchors import FrameAnchor
from src.anim.parts import _base
from src.anim.manifest import Part


@pytest.fixture(scope="module")
def display():
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _anchor(dx: int, dy: int) -> FrameAnchor:
    return FrameAnchor(
        body_dx=dx,
        body_dy=dy,
        eye=None,
        eye_source="missing",
        shield=None,
        shield_source="missing",
    )


def _part(pivot: str) -> Part:
    """A body part with the given pivot.

    `Part` declares no defaults for the fields this test does not care
    about (offset, scale, radii, detect, on_missing), so they are spelled
    out ONCE here instead of at every call site.
    """
    return Part(
        id="body",
        draw="frames",
        pivot=pivot,
        z=0,
        offset=(0, 0),
        scale=(1.0, 1.0),
        radii=None,
        detect=None,
        on_missing="fallback",
    )


def test_a_centroid_pivot_applies_the_correction():
    part = _part("centroid")
    x, y = _base((100, 100), (32, 32), _anchor(3, -2), part)
    # The base is the CANVAS half-size (32 // 2 == 16), plus the measured
    # registration correction.
    assert (x, y) == (100 - 16 + 3, 100 - 16 - 2)


def test_a_fixed_pivot_does_not_apply_the_correction():
    part = _part("fixed")
    x, y = _base((100, 100), (32, 32), _anchor(3, -2), part)
    # Centred on the entity: the correction is recorded, not applied.
    assert (x, y) == (100 - 16, 100 - 16)
