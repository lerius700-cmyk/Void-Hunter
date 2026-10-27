"""BLOQUE 74: the manifest must describe the assets that actually exist.

The manifest is the spec of an animated set. If it drifts from the assets
on disk, the auditor measures the wrong thing and the runtime draws from a
stale table. This test is the drift alarm.
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

from src.anim.manifest import ManifestError, load_set


@pytest.fixture(scope="module")
def display():
    """Dummy display: `convert_alpha()` needs a video mode to read sprites."""
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    yield


@pytest.fixture(scope="module")
def goliath():
    return load_set("goliath")


def test_manifest_loads(goliath):
    assert goliath.name == "GOLIATH"
    assert goliath.canvas == (96, 80)
    assert goliath.anchor == (48, 40)
    assert goliath.sided == "right"


def test_every_clip_directory_exists(goliath):
    for clip in goliath.clips.values():
        assert (goliath.path / clip.dir).is_dir(), clip.id


def test_frame_count_matches_manifest(goliath):
    for clip in goliath.clips.values():
        pngs = sorted((goliath.path / clip.dir).glob("frame_*.png"))
        assert len(pngs) == clip.frames, (
            f"{clip.id}: {len(pngs)} PNGs on disk, manifest says {clip.frames}"
        )


def test_every_frame_has_the_declared_canvas(goliath, display):
    import pygame

    for clip in goliath.clips.values():
        for png in sorted((goliath.path / clip.dir).glob("frame_*.png")):
            surf = pygame.image.load(str(png)).convert_alpha()
            assert surf.get_size() == goliath.canvas, f"{png}: {surf.get_size()}"


def test_expected_clips_and_parts_exist(goliath):
    assert set(goliath.clips) == {
        "phase1_idle", "phase2_idle", "javelin", "laser", "purple_bullet", "death",
    }
    part_ids = {p.id for p in goliath.parts}
    assert {"body", "shield_plate", "eye", "fx_eye_beam"} <= part_ids


def test_death_clip_is_one_shot(goliath):
    assert goliath.clip("death").loop is False
    assert goliath.clip("phase1_idle").loop is True


def test_shield_constants_were_moved_verbatim(goliath):
    """BLOQUE 67 user-approved values. The manifest moves them, it does not
    retune them."""
    shield = goliath.part("shield_plate")
    assert shield.offset == (0, 3)
    assert shield.scale == (0.78, 1.0)


def test_unknown_set_raises():
    with pytest.raises(ManifestError):
        load_set("no_existe")
