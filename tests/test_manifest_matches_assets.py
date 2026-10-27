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

from src.anim.manifest import DetectRule, ManifestError, WarmRule, load_set


@pytest.fixture(scope="module")
def display():
    """pygame needs a video mode before convert_alpha() works."""
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
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
    assert shield.radii == (11.0, 11.0, 17.0)


def test_shield_rule_declares_the_warm_fallback(goliath):
    rule = goliath.part("shield_plate").detect
    assert rule is not None
    assert rule.warm_fallback is not None
    assert rule.warm_fallback.r_min == 235
    assert rule.warm_fallback.b_max == 140
    assert rule.warm_fallback.g_min == 130
    assert rule.warm_fallback.r_minus_b_min == 190


def test_warm_rule_matches_the_whole_beam_and_keeps_the_plate_highlight():
    """The beam is a gradient: exact RGB triples do not cover it.

    (220,180,80) is the plate's own face highlight and must NOT be
    discarded, or the plate stops being measurable.
    """
    rule = WarmRule(r_min=235, b_max=140, g_min=130, r_minus_b_min=190)
    assert rule.matches(255, 220, 80) is True
    assert rule.matches(240, 200, 120) is True
    assert rule.matches(255, 140, 60) is True
    assert rule.matches(255, 80, 40) is True
    assert rule.matches(220, 180, 80) is False


def test_unknown_set_raises():
    with pytest.raises(ManifestError):
        load_set("no_existe")


# ---------------------------------------------------------------------------
# The ManifestError contract: a malformed manifest must fail LOUDLY and with
# the manifest's own error type, never with a bare IndexError/KeyError.
# ---------------------------------------------------------------------------
def test_unknown_detect_method_raises():
    """A misspelled method must not flow into the auditor unchallenged."""
    with pytest.raises(ManifestError):
        DetectRule.from_dict({"method": "shapeh"})


def test_unknown_detect_side_raises():
    with pytest.raises(ManifestError):
        DetectRule.from_dict({"method": "shape", "side": "middle"})


def test_bad_pair_arity_raises_manifest_error():
    """`band = [28]` used to raise a bare IndexError."""
    with pytest.raises(ManifestError):
        DetectRule.from_dict({"method": "shape", "band": [28]})


def test_unknown_clip_and_part_raise():
    set_ = load_set("goliath")
    with pytest.raises(ManifestError):
        set_.clip("no_such_clip")
    with pytest.raises(ManifestError):
        set_.part("no_such_part")
