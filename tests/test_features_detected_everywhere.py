"""BLOQUE 74: every required feature must be resolved in every frame.

A feature is "resolved" when the auditor measured it, or when the repair
interpolated it from the frames around it. The guard fails when a frame
still has an unresolved feature -- that is the case where the runtime would
fall back to a constant and the shield would stop tracking the arm.

Resolution is not the same as measurement. Every feature also carries its
PROVENANCE (`measured` / `interpolated` / `missing` / `out_of_range`), and
the two features of a frame are resolved INDEPENDENTLY: an interpolated eye
does not make an interpolated shield. The coverage guard above cannot see
the difference -- a reconstructed eye satisfies `m.eye is not None` -- so
the provenance is asserted here.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from collections import Counter
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline.audit import audit_set  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def display():
    """pygame needs a video mode before convert_alpha() works."""
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.fixture(scope="module")
def goliath():
    return load_set("goliath")


@pytest.fixture(scope="module")
def audit(display, goliath):
    """The auditor's verdict on the 60 shipped frames, measured ONCE."""
    return audit_set(goliath)


def test_every_frame_resolves_the_shield_plate(audit):
    _, measurements = audit
    unresolved = [
        f"{m.clip}/frame_{m.frame:02d}"
        for m in measurements
        if m.shield is None
    ]
    assert not unresolved, (
        "the shield plate is unresolved in these frames -- they need "
        "interpolation or repair: " + ", ".join(unresolved)
    )


def test_every_frame_resolves_the_eye(audit):
    _, measurements = audit
    missing = [
        f"{m.clip}/frame_{m.frame:02d}"
        for m in measurements
        if m.eye is None
    ]
    assert not missing, "eye anchor not found in: " + ", ".join(missing)


def test_every_frame_has_a_body_offset(audit, goliath):
    """The registration correction stays a plausible offset.

    `body_dx` / `body_dy` move the sprite so that its visual centre of
    mass lands on the anchor. The shipped frames need -16..+20 px
    horizontally and -12..+5 px vertically; a bigger jump would mean the
    centroid is broken, not that the art changed.
    """
    _, measurements = audit
    assert len(measurements) == sum(c.frames for c in goliath.clips.values())
    assert all(
        abs(m.body_dx) <= 32 and abs(m.body_dy) <= 32 for m in measurements
    ), [
        f"{m.clip}/frame_{m.frame:02d} body offset {m.body_dx},{m.body_dy}"
        for m in measurements
        if abs(m.body_dx) > 32 or abs(m.body_dy) > 32
    ]
    # The correction is a real measurement, not a constant zero.
    assert any(m.body_dx != 0 or m.body_dy != 0 for m in measurements)


def test_every_feature_says_where_it_came_from(audit):
    """Every feature carries its provenance, and nothing is unresolved.

    `measured` = the detector found it in this frame. `interpolated` = it
    was reconstructed from the frames around it. `missing` and
    `out_of_range` mean UNRESOLVED -- the guards above would have failed
    on those.

    BLOQUE 77: the counts MOVED, and that is the point. They were
    53/7 (shields) and are now 58/2. The seven frames that could not be
    measured were the ones whose ART IS AUTHORED SHIFTED inside its
    canvas: the rule has absolute columns, the plate fell outside the
    window, and the ellipse was reconstructed from the neighbours -- onto
    the boss's belly. Measuring on the REGISTERED sprite (the art as it
    will be drawn) fixed five of them.
    """
    _, measurements = audit
    shield_sources = Counter(m.shield_source for m in measurements)
    eye_sources = Counter(m.eye_source for m in measurements)
    assert shield_sources == {"measured": 58, "interpolated": 2}, dict(
        shield_sources
    )
    assert eye_sources == {"measured": 59, "interpolated": 1}, dict(eye_sources)


def test_the_eye_and_the_shield_are_resolved_independently(audit):
    """One feature can be reconstructed while the other is measured.

    death/frame_09 has no eye left to find -- by the last frame of the
    death clip the boss is a heap of wreckage -- so its eye is
    interpolated from death/frame_08 while its shield is measured in that
    very frame. laser/frame_04 is the other way round: the baked beam
    crosses the plate, so the shield is interpolated while the eye is
    measured.

    BLOQUE 77: the example used to be javelin/frame_03, and it is not
    any more -- that frame is MEASURED now, because its art is authored
    shifted and the measurement happens on the registered sprite.
    """
    _, measurements = audit
    by_frame = {(m.clip, m.frame): m for m in measurements}

    wreck = by_frame[("death", 9)]
    assert wreck.eye_source == "interpolated"
    assert wreck.shield_source == "measured"

    beam = by_frame[("laser", 4)]
    assert beam.shield_source == "interpolated"
    assert beam.eye_source == "measured"


def test_the_report_still_documents_the_art_problem(audit):
    """The interpolation fixes the measurement, not the art.

    The findings must keep reporting the frames whose plate is missing
    from the drawing, otherwise the report lies about the source art.

    BLOQUE 77: the three frames are now the ones the CONTRACT names --
    the two where the baked beam crosses the plate, and the one where
    the boss is collapsing and the two detectors disagree. The five
    frames that USED to be reported are no longer: they were not an art
    problem, they were a measurement that did not know the sprite can
    be authored shifted.
    """
    findings, _ = audit
    reported = {f"{f.clip}/frame_{f.frame:02d}" for f in findings}
    assert "laser/frame_04" in reported
    assert "laser/frame_05" in reported
    assert "death/frame_02" in reported
