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
import pytest

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


# A whole synthetic SET whose clip id and clip DIRECTORY are different
# names. Every shipped manifest declares `id = dir`, so a regression that
# used the id for the PNG path (or the directory for the anchor key)
# would pass every other test in the suite. This fixture is the one place
# where the two genuinely differ.
SYNTHETIC_MANIFEST = """
[meta]
name    = "SYNTHETIC"
version = 1
canvas  = [96, 80]
anchor  = [48, 40]

[[clips]]
id     = "javelin"
dir    = "javelin_frames"
frames = 1
fps    = 10
loop   = true

[[parts]]
id    = "body"
draw  = "frames"
pivot = "centroid"
z     = 0
"""

# The anchor table of that set: keyed by the clip ID ("javelin"), not by
# the clip directory ("javelin_frames").
SYNTHETIC_SET_ANCHORS = """
[meta]
generated_by = "test"

[[anchors]]
clip = "javelin"
frame = 0
body_dx = 10
body_dy = 0
eye = [51, 19]
eye_source = "measured"
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "measured"
"""

# A table that claims a measurement it does not carry.
CORRUPT_ANCHORS = """
[meta]
generated_by = "test"

[[anchors]]
clip = "javelin"
frame = 0
body_dx = -3
body_dy = 2
eye_source = "measured"
shield = [60.5, 40.5, 8.5, 10.5]
shield_source = "measured"
"""


def _write_synthetic_set(root: Path) -> Path:
    """Write a set whose clip id and clip directory differ, and return it."""
    set_dir = root / "synthetic"
    frames_dir = set_dir / "javelin_frames"
    frames_dir.mkdir(parents=True)
    (set_dir / "manifest.toml").write_text(SYNTHETIC_MANIFEST, encoding="utf-8")
    (set_dir / "anchors.toml").write_text(SYNTHETIC_SET_ANCHORS, encoding="utf-8")
    # The body sits at (30, 30) 16x20, so its alpha centroid is (37.5,
    # 39.5) and the registration correction is +10 / 0 -- the same
    # arithmetic the auditor does.
    surf = pygame.Surface((96, 80), pygame.SRCALPHA)
    surf.fill((200, 100, 50, 255), pygame.Rect(30, 30, 16, 20))
    pygame.image.save(surf, str(frames_dir / "frame_00.png"))
    return set_dir


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


def test_an_unresolved_plate_keeps_the_canonical_oval(tmp_path):
    """BLOQUE 74: no credible position -> the CANONICAL oval.

    The policy changed in BLOQUE 74. The oval used to disappear when the
    plate could not be resolved, which deleted the shield's hitbox and
    left the laser with no origin. Now the frame keeps the canonical
    ellipse -- the manifest's radii at the canonical centre -- and it must
    not land on the origin either.
    """
    from src.anim.manifest import load_set
    from src.anim.parts import (
        CANONICAL_PLATE_CENTRE,
        draw_part,
        shield_ellipse_rect,
    )

    anchors = _load_synthetic(tmp_path)
    anim_set = load_set("goliath")
    part = anim_set.part("shield_plate")
    anchor = anchors.get("javelin", 1)
    assert anchor is not None and anchor.shield is None

    rect = shield_ellipse_rect(part, anchor, (120, 180), anim_set.canvas)
    assert rect is not None
    assert rect.centerx != 0 and rect.centery != 0
    expected_x = (
        120 - 96 // 2 + anchor.body_dx + CANONICAL_PLATE_CENTRE[0] + part.offset[0]
    )
    expected_y = (
        180 - 80 // 2 + anchor.body_dy + CANONICAL_PLATE_CENTRE[1] + part.offset[1]
    )
    assert abs(rect.centerx - expected_x) <= 1
    assert abs(rect.centery - expected_y) <= 1
    _r, rx, ry = part.radii
    assert rect.width == max(2, int(round(rx * part.scale[0]))) * 2
    assert rect.height == max(2, int(round(ry * part.scale[1]))) * 2

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    draw_part(target, part, None, anchor, (120, 180), anim_set.canvas)
    assert target.get_bounding_rect().width == 0, "the oval must stay invisible"


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


# --------------------------------------------------------------------------
# the clip id and the clip directory are two different names
# --------------------------------------------------------------------------


def test_the_anchor_table_is_keyed_by_the_clip_id(tmp_path):
    """The ID keys the table; the DIRECTORY names the PNG.

    Every shipped manifest declares `id = dir`, so only a set where the
    two differ can tell the two apart.
    """
    from src.anim.anchors import load_anchors
    from src.anim.manifest import load_set

    set_dir = _write_synthetic_set(tmp_path)
    anim_set = load_set("synthetic", root=tmp_path)
    clip = anim_set.clip("javelin")
    assert clip.id == "javelin"
    assert clip.dir == "javelin_frames"

    anchors = load_anchors(set_dir / "anchors.toml")
    assert anchors.get("javelin", 0) is not None, "the id does not key the table"
    assert anchors.get("javelin_frames", 0) is None, "the directory keys the table"


def test_the_png_is_named_by_the_clip_directory(tmp_path):
    """The PNG lives in the clip's DIRECTORY, not in a folder named after
    the id."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    set_dir = _write_synthetic_set(tmp_path)
    anim_set = load_set("synthetic", root=tmp_path)
    anchors = load_anchors(set_dir / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    surf = player.surface("javelin", 0)
    assert surf is not None, "the frame PNG was not found in the clip directory"
    assert surf.get_size() == anim_set.canvas


def test_the_compositor_uses_the_id_for_the_anchor_and_the_dir_for_the_png(tmp_path):
    """The two names are used for the two different things."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set
    from src.anim.measure import alpha_centroid

    set_dir = _write_synthetic_set(tmp_path)
    anim_set = load_set("synthetic", root=tmp_path)
    anchors = load_anchors(set_dir / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(target, "javelin", 0, origin=(120, 180))

    centroid = alpha_centroid(target)
    assert centroid is not None, "the body was not drawn: the anchor was not found"
    assert abs(centroid[0] - 120) <= 1.0
    assert abs(centroid[1] - 180) <= 1.0


# --------------------------------------------------------------------------
# the frame boundary
# --------------------------------------------------------------------------


def test_a_frame_boundary_is_not_lost_to_float_error():
    """0.3 s at 10 fps is frame 3, not frame 2.

    0.3 * 10 is 2.9999999999999996 in binary floating point, so the
    division used to land on the previous frame.
    """
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    assert player.state("javelin", 0.3).frame == 3
    assert player.state("javelin", 0.6).frame == 6
    assert player.state("javelin", 0.7).frame == 7


def test_the_epsilon_does_not_move_a_mid_interval_frame():
    """The epsilon rescues an exact boundary and nothing else."""
    from src.anim.anchors import load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    player = ClipPlayer(anim_set, anchors)

    assert player.state("javelin", 0.29).frame == 2
    assert player.state("javelin", 0.31).frame == 3
    assert player.state("javelin", 0.89).frame == 8


# --------------------------------------------------------------------------
# a hole in the table
# --------------------------------------------------------------------------


def test_a_frame_missing_from_the_table_still_draws_its_body():
    """A hole in the table must not make the boss blink out.

    The registration correction is unknown for a frame that is not in the
    table, so the body degrades to a plain centred blit.
    """
    from src.anim.anchors import AnchorSet, load_anchors
    from src.anim.clip import ClipPlayer
    from src.anim.manifest import load_set
    from src.anim.measure import alpha_centroid

    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    original = anchors.get("javelin", 3)
    assert original is not None

    trimmed = AnchorSet(
        entries={
            key: value
            for key, value in anchors.entries.items()
            if key != ("javelin", 3)
        }
    )
    player = ClipPlayer(anim_set, trimmed)

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(target, "javelin", 3, origin=(120, 180))

    centroid = alpha_centroid(target)
    assert centroid is not None, "the body vanished with its anchor"
    # No correction: the body lands where the canvas puts it.
    assert abs(centroid[0] - (120 - original.body_dx)) <= 1.0
    assert abs(centroid[1] - (180 - original.body_dy)) <= 1.0


# --------------------------------------------------------------------------
# a corrupt table
# --------------------------------------------------------------------------


def test_a_table_that_claims_a_measurement_it_does_not_carry_fails_loudly(tmp_path):
    """A source of "measured" with no value is corruption, not a position.

    Reading it as (0, 0) would fire the eye laser from the corner of the
    canvas.
    """
    from src.anim.anchors import AnchorError, load_anchors

    path = tmp_path / "anchors.toml"
    path.write_text(CORRUPT_ANCHORS, encoding="utf-8")
    with pytest.raises(AnchorError):
        load_anchors(path)


def test_an_unresolved_entry_may_omit_its_value(tmp_path):
    """An unresolved feature carries no value, and that is not corruption."""
    from src.anim.anchors import load_anchors

    path = tmp_path / "anchors.toml"
    path.write_text(
        CORRUPT_ANCHORS.replace(
            'eye_source = "measured"', 'eye_source = "missing"'
        ),
        encoding="utf-8",
    )
    anchors = load_anchors(path)
    entry = anchors.get("javelin", 0)
    assert entry is not None
    assert entry.eye is None
    assert entry.eye_source == "missing"

