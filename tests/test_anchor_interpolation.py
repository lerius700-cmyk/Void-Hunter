"""BLOQUE 74: a missing measurement must be reconstructed, not defaulted.

Seven of GOLIATH's frames have an implausible shield ellipse (the plate is
missing from the art or the arm is measured instead). A constant fallback
would pin the oval to a fixed point while the arm moves. Interpolating
from the frames around it keeps the oval on the arm.

The READER has to keep two things apart:

  * a feature the generator could not measure is written as a ZERO
    PLACEHOLDER, and only its `*_source` field tells that apart from a
    feature genuinely measured at the origin;
  * an unresolved feature must stay None -- the eye laser must not be
    launched from the corner of the canvas, and the oval must not be
    drawn at the corner of the screen.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.measure import interpolate  # noqa: E402

# A synthetic anchor table: the shipped assets have ZERO unresolved
# features (53 measured / 7 interpolated shields, 59 / 1 eyes), so the
# unresolved path is exercised here instead.
SYNTHETIC_ANCHORS = """
[meta]
generated_by = "test"

[[anchors]]
clip = "javelin"
frame = 0
body_dx = -3
body_dy = 2
eye = [51, 19]
eye_source = "measured"
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "measured"

[[anchors]]
clip = "javelin"
frame = 1
body_dx = -3
body_dy = 2
eye = [0, 0]
eye_source = "missing"
shield = [0.0, 0.0, 0.0, 0.0]
shield_source = "out_of_range"

[[anchors]]
clip = "javelin"
frame = 2
body_dx = -3
body_dy = 2
eye = [0, 0]
eye_source = "measured"
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "measured"
"""


def _load_synthetic(tmp_path: Path):
    from src.anim.anchors import load_anchors

    path = tmp_path / "anchors.toml"
    path.write_text(SYNTHETIC_ANCHORS, encoding="utf-8")
    return load_anchors(path)


# --------------------------------------------------------------------------
# the interpolation itself
# --------------------------------------------------------------------------


def test_interpolates_a_gap():
    # measured 10, missing, measured 12 -> the middle is 11
    assert interpolate([10.0, None, 12.0], 1) == 11.0


def test_keeps_a_measured_value():
    assert interpolate([10.0, 11.0, 12.0], 1) == 11.0


def test_returns_none_without_neighbours():
    """No measured value anywhere: there is nothing to interpolate from."""
    assert interpolate([None, None, None], 1) is None


def test_falls_back_to_the_only_neighbour():
    """One side only: the missing tangent collapses onto that side.

    The first frame of a clip has no left neighbour. Falling back to the
    right one keeps it resolvable, which is what the auditor needs to
    reconstruct a plate the art forgot.
    """
    assert interpolate([None, None, 12.0], 0) == 12.0
    assert interpolate([12.0, None, None], 2) == 12.0


def test_interpolates_at_the_edges():
    # the first frame is missing: use the next two
    value = interpolate([None, 10.0, 12.0], 0)
    assert value is not None
    assert 10.0 <= value <= 12.0


# --------------------------------------------------------------------------
# the reader
# --------------------------------------------------------------------------


def test_goliath_has_no_unresolved_plates():
    """After the repair, every frame resolves its plate."""
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    unresolved = [
        f"{clip}/{frame:02d}"
        for (clip, frame), entry in anchors.entries.items()
        if entry.shield_source in ("missing", "out_of_range")
    ]
    assert not unresolved, "unresolved plates: " + ", ".join(unresolved)


def test_the_shipped_set_reconstructs_what_it_could_not_measure():
    """The interpolated frames are RECONSTRUCTED, not defaulted.

    death/frame_09 is a heap of wreckage with no eye left to find: its eye
    comes from death/frame_08 while its plate is measured in that very
    frame. javelin/frame_03 is the other way round: the plate was painted
    on the wrong side, so the plate is interpolated while the eye is
    measured.
    """
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")

    wreck = anchors.get("death", 9)
    assert wreck is not None
    assert wreck.eye_source == "interpolated"
    assert wreck.eye is not None
    assert wreck.shield_source == "measured"
    assert wreck.shield is not None

    javelin = anchors.get("javelin", 3)
    assert javelin is not None
    assert javelin.shield_source == "interpolated"
    assert javelin.shield is not None
    assert javelin.eye_source == "measured"
    assert javelin.eye is not None


def test_every_frame_of_the_shipped_set_is_resolved():
    """60 frames, 60 resolved plates, 60 resolved eyes."""
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    assert len(anchors.entries) == sum(c.frames for c in anim_set.clips.values())
    for (clip, frame), entry in anchors.entries.items():
        assert entry.shield is not None, f"{clip}/{frame:02d} has no plate"
        assert entry.eye is not None, f"{clip}/{frame:02d} has no eye"


def test_an_unresolved_feature_stays_none(tmp_path):
    """The zero placeholder is NOT a position.

    The generator writes `eye = [0, 0]` for an eye it could not find.
    Reading that as a real position would launch the laser from the
    corner of the canvas.
    """
    anchors = _load_synthetic(tmp_path)

    unresolved = anchors.get("javelin", 1)
    assert unresolved is not None
    assert unresolved.eye is None
    assert unresolved.eye_source == "missing"
    assert unresolved.shield is None
    assert unresolved.shield_source == "out_of_range"


def test_a_measured_feature_at_the_origin_is_not_none(tmp_path):
    """The SOURCE is what tells "measured at (0, 0)" from "not measured"."""
    anchors = _load_synthetic(tmp_path)

    measured = anchors.get("javelin", 2)
    assert measured is not None
    assert measured.eye == (0, 0)
    assert measured.eye_source == "measured"
    assert measured.shield == (60.5, 40.5, 8.5, 10.5)
    assert measured.shield_source == "measured"


def test_the_anchor_table_is_keyed_by_clip_id(tmp_path):
    """The clip id is the key; the clip DIRECTORY names the PNG."""
    anchors = _load_synthetic(tmp_path)
    assert ("javelin", 0) in anchors.entries
    assert anchors.get("javelin", 99) is None


# --------------------------------------------------------------------------
# the compositor
# --------------------------------------------------------------------------


def test_the_compositor_finds_the_frame_png():
    """The PNG lives in the clip's DIRECTORY, inside the set."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    surf = player.surface("javelin", 3)
    assert surf is not None, "the frame PNG was not found"
    assert surf.get_size() == anim_set.canvas


def test_the_compositor_puts_the_body_on_the_anchor():
    """The character's centre of mass lands on the world anchor."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set
    from src.anim.measure import alpha_centroid

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(target, "javelin", 3, origin=(120, 180))

    centroid = alpha_centroid(target)
    assert centroid is not None, "nothing was drawn"
    assert abs(centroid[0] - 120) <= 1.0
    assert abs(centroid[1] - 180) <= 1.0


def test_the_oval_geometry_follows_the_anchor():
    """The oval sits on the plate, with the manifest's nudge and scale."""
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set
    from src.anim.parts import shield_ellipse_rect

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    part = anim_set.part("shield_plate")
    anchor = anchors.get("javelin", 3)
    assert anchor is not None and anchor.shield is not None

    rect = shield_ellipse_rect(part, anchor, origin=(120, 180), canvas=anim_set.canvas)
    assert rect is not None

    cx, cy, rx, ry = anchor.shield
    # The same arithmetic the shipped runtime does (src/ui/
    # gameplay_runtime.py::_goliath_shield_ellipse).
    expected_x = 120 - 96 // 2 + anchor.body_dx + round(cx) + part.offset[0]
    expected_y = 180 - 80 // 2 + anchor.body_dy + round(cy) + part.offset[1]
    assert abs(rect.centerx - expected_x) <= 1
    assert abs(rect.centery - expected_y) <= 1
    assert rect.width == max(2, int(round(rx * part.scale[0]))) * 2
    assert rect.height == max(2, int(round(ry * part.scale[1]))) * 2


def test_an_unresolved_plate_draws_no_oval(tmp_path):
    """No credible position -> no oval. It must not land on the origin."""
    from src.anim.manifest import load_set
    from src.anim.parts import draw_part, shield_ellipse_rect

    anchors = _load_synthetic(tmp_path)
    anim_set = load_set("goliath")
    part = anim_set.part("shield_plate")
    anchor = anchors.get("javelin", 1)
    assert anchor is not None and anchor.shield is None

    assert (
        shield_ellipse_rect(part, anchor, (120, 180), anim_set.canvas) is None
    )

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    draw_part(target, part, None, anchor, (120, 180), anim_set.canvas)
    assert target.get_bounding_rect().width == 0


def test_the_clip_follows_the_manifest_fps():
    """The timing comes from the manifest, not from a hardcoded constant."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    assert anim_set.clip("javelin").fps == 10
    assert player.state("javelin", 0.0).frame == 0
    assert player.state("javelin", 0.1).frame == 1
    assert player.state("javelin", 0.25).frame == 2
    # a looping clip wraps around
    assert player.state("javelin", 1.05).frame == 0
    # a one-shot clip holds on its last frame
    assert player.state("death", 99.0).frame == 9
