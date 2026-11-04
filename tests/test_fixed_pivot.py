"""BLOQUE 75 Fase 2: a `fixed` pivot means "do not apply the correction".

`pivot = "fixed"` is what the enemy sets declare: the sprite is blitted
CENTRED on the entity, exactly as the runtime does today. The measured
registration is recorded in the anchors table, but applying it would move
the ship up to 3.7 px off its hitbox -- and the golden frames would catch
it.

The last test goes through the PUBLIC path (`parts.draw_part`) and looks
at where the pixels landed: the two above call the PRIVATE helper, so on
their own they could not see a public path that ignored the pivot.
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

from src.anim import parts
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
    # The base is the CANVAS half-size (32 // 2 == 16) plus the measured
    # registration correction: 100 - 16 + 3, 100 - 16 - 2.
    assert (x, y) == (87, 82)


def test_a_fixed_pivot_does_not_apply_the_correction():
    part = _part("fixed")
    x, y = _base((100, 100), (32, 32), _anchor(3, -2), part)
    # Centred on the entity: 100 - 16, 100 - 16. The correction is
    # recorded, not applied.
    assert (x, y) == (84, 84)


def test_the_public_path_draws_a_fixed_part_centred(display):
    """The PUBLIC path must honour the pivot: the pixels, not the helper.

    The two tests above call the PRIVATE `_base()`. A mutation that made
    `draw_part` ignore the pivot -- the pre-Task-5 arithmetic -- would
    leave them green, so this test renders through the public entry point
    and looks at where the pixels actually landed.
    """
    part = _part("fixed")
    target = pygame.Surface((128, 128), pygame.SRCALPHA)
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    surf.fill((255, 0, 0, 255))
    anchor = _anchor(3, -2)
    parts.draw_part(target, part, surf, anchor, (100, 100), (32, 32))
    drawn = target.get_bounding_rect()
    # The surface is blitted at the origin minus the CANVAS half-size
    # (32 // 2 == 16): 100 - 16, 100 - 16. The measured correction is
    # NOT applied -- the part is centred.
    assert drawn.topleft == (84, 84)
    # And explicitly NOT where the centroid arithmetic would put it:
    # 100 - 16 + 3, 100 - 16 - 2.
    assert drawn.topleft != (87, 82)
