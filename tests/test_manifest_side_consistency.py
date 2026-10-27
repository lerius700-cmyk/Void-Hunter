"""BLOQUE 74: the plate must be on the side the manifest declares.

BLOQUE 73.4 shipped GOLIATH with two frames where the character is drawn
turned around: the shield plate sits at probe column 27.4 and 33.1 instead
of the 40.8-59.6 band every healthy frame stays inside. The SHAPE rule
cannot see this --
it finds the arm at the right of the band and measures a plausible ellipse
that is not the plate. The PROBE can: a cheap colour signature used only
to answer "which side is the plate on?".

A frame counts as turned around when the probe column is on the opposite
side of the canvas centre AND it strays more than `side_tolerance` from
the clip's median probe column. Both conditions are needed: death/frame_02
is legitimately at column 40.7 because the boss is collapsing.

This test FAILS until Task 5 mirrors javelin/frame_03 and
purple_bullet/frame_06.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import load_set
from src.anim.measure import color_centroid


@pytest.fixture(scope="module")
def goliath():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    return load_set("goliath")


def probe_columns(goliath, clip):
    """probe column per frame of a clip."""
    import pygame

    rule = goliath.part("shield_plate").detect
    assert rule is not None and rule.probe is not None
    out = []
    for i in range(clip.frames):
        png = goliath.path / clip.dir / f"frame_{i:02d}.png"
        surf = pygame.image.load(str(png)).convert_alpha()
        found = color_centroid(surf, rule.probe, warm=rule.warm_fallback)
        out.append(found[0] if found else None)
    return out


def test_every_clip_detects_the_plate(goliath):
    for clip in goliath.clips.values():
        cols = probe_columns(goliath, clip)
        missing = [i for i, c in enumerate(cols) if c is None]
        assert not missing, f"{clip.id}: no plate detected in frames {missing}"


def test_plate_is_on_the_declared_side(goliath):
    rule = goliath.part("shield_plate").detect
    assert rule is not None and rule.side == "right"
    centre = goliath.anchor[0]
    offenders = []
    for clip in goliath.clips.values():
        cols = probe_columns(goliath, clip)
        good = sorted(c for c in cols if c is not None)
        median = good[len(good) // 2]
        for i, col in enumerate(cols):
            if col is None:
                continue
            wrong_side = col <= centre if rule.side == "right" else col >= centre
            stray = abs(col - median) > clip.side_tolerance
            if wrong_side and stray:
                offenders.append(
                    f"{clip.id}/frame_{i:02d} (probe col {col:.1f}, median {median:.1f})"
                )
    assert not offenders, "plate on the wrong side: " + ", ".join(offenders)
