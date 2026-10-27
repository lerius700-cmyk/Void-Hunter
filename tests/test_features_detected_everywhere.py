"""BLOQUE 74: every required feature must be resolved in every frame.

A feature is "resolved" when the auditor measured it, or when the repair
interpolated it from the frames around it. The guard fails when a frame
still has an unresolved feature -- that is the case where the runtime would
fall back to a constant and the shield would stop tracking the arm.
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
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline.audit import audit_set  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def display():
    """pygame needs a video mode before convert_alpha() works."""
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def test_every_frame_resolves_the_shield_plate():
    anim_set = load_set("goliath")
    _, measurements = audit_set(anim_set)
    unresolved = [
        f"{m.clip}/frame_{m.frame:02d}"
        for m in measurements
        if m.shield is None
    ]
    assert not unresolved, (
        "the shield plate is unresolved in these frames -- they need "
        "interpolation or repair: " + ", ".join(unresolved)
    )


def test_every_frame_resolves_the_eye():
    anim_set = load_set("goliath")
    _, measurements = audit_set(anim_set)
    missing = [
        f"{m.clip}/frame_{m.frame:02d}"
        for m in measurements
        if m.eye is None
    ]
    assert not missing, "eye anchor not found in: " + ", ".join(missing)


def test_every_frame_has_a_body_offset():
    anim_set = load_set("goliath")
    _, measurements = audit_set(anim_set)
    assert len(measurements) == sum(c.frames for c in anim_set.clips.values())
    assert all(isinstance(m.body_dx, int) for m in measurements)


def test_the_report_still_documents_the_art_problem():
    """The interpolation fixes the measurement, not the art.

    The findings must keep reporting the frames whose plate is missing
    from the drawing, otherwise the report lies about the source art.
    """
    anim_set = load_set("goliath")
    findings, _ = audit_set(anim_set)
    reported = {f"{f.clip}/frame_{f.frame:02d}" for f in findings}
    assert "javelin/frame_04" in reported
    assert "laser/frame_05" in reported
    assert "purple_bullet/frame_08" in reported
