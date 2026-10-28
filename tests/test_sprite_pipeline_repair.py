"""BLOQUE 74: the repair pass must be deterministic and idempotent.

Mirroring is the repair for a turned-around character. It must flip the
sprite inside its own canvas (not move it), and it must leave every other
frame byte-identical.

The flip itself is an INVOLUTION -- mirroring twice restores the original
pixels. What is idempotent is the repair PASS: it only acts on a
LADO_EQUIVOCADO finding, and once the frame has been mirrored the next
audit finds none, so a second `--fix` changes nothing.

The re-pad and the auditor must agree on the THRESHOLD: the repair targets
CORTADO_MARGIN, the very threshold the auditor flags below, so a frame the
auditor flags is a frame the repair can reach.
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
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set  # noqa: E402
from src.anim.measure import (  # noqa: E402
    CORTADO_MARGIN,
    silhouette_bbox,
    silhouette_margins,
)
from sprite_pipeline.audit import Finding, audit_set  # noqa: E402
from sprite_pipeline.repair import (  # noqa: E402
    mirror_frame,
    repair_set,
    repad_frame,
)

# The synthetic-set builder lives with the auditor's own tests: the
# manifest it writes declares the parts the auditor measures (the shield
# plate and the eye), and there is exactly ONE copy of that manifest.
from tests.test_sprite_pipeline_audit import build_set  # noqa: E402

W, H = 96, 80
TRANSPARENT = (0, 0, 0, 0)
BODY = (160, 110, 50, 255)


def _surface(pixels: dict[tuple[int, int], tuple]) -> pygame.Surface:
    surf = pygame.Surface((W, H), pygame.SRCALPHA, 32)
    surf.fill(TRANSPARENT)
    for (x, y), colour in pixels.items():
        surf.set_at((x, y), colour)
    return surf


def _rect(x0: int, y0: int, x1: int, y1: int) -> dict[tuple[int, int], tuple]:
    """Pixels of a filled rectangle, `x1`/`y1` exclusive."""
    return {
        (x, y): BODY
        for y in range(y0, y1)
        for x in range(x0, x1)
    }


def _margins(surf: pygame.Surface) -> tuple[int, int, int, int]:
    """The four margins of the silhouette, as the auditor measures them."""
    bbox = silhouette_bbox(surf)
    assert bbox is not None, "the surface has no silhouette"
    left, top, right, bottom = bbox
    w, h = surf.get_size()
    return (left, top, w - right, h - bottom)


def _tight_pixels() -> dict[tuple[int, int], tuple]:
    """A silhouette with the margins (0, 1).

    It touches the LEFT edge and is 1 px from the TOP edge, and it keeps
    4 px of slack on the right: the tightest frame a translation can still
    give the auditor's margin to.
    """
    return _rect(0, 1, W - 4, 40)


def _synthetic_set(
    tmp_path: Path, pixels: dict[tuple[int, int], tuple], clip_dir: str = "idle"
):
    """A one-frame set on disk, loaded through the real manifest loader.

    The clip's ID is always "idle"; `clip_dir` is the DIRECTORY the frames
    live in, so a set that separates the two can be built.
    """
    set_dir = tmp_path / "synthetic"
    frames_dir = set_dir / clip_dir
    frames_dir.mkdir(parents=True)
    pygame.image.save(_surface(pixels), str(frames_dir / "frame_00.png"))
    (set_dir / "manifest.toml").write_text(
        f"""[meta]
name = "SYNTHETIC"
version = 1
canvas = [96, 80]
anchor = [48, 40]
sided = "right"

[[clips]]
id = "idle"
dir = "{clip_dir}"
frames = 1
fps = 10
loop = true

[[parts]]
id = "body"
draw = "frames"
pivot = "centroid"
z = 0
""",
        encoding="utf-8",
    )
    return load_set("synthetic", root=tmp_path)


# ---------------------------------------------------------------------------
# The mirror primitive.
# ---------------------------------------------------------------------------
def test_mirror_flips_the_pixels(tmp_path):
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    surf.set_at((10, 10), (255, 0, 0, 255))
    pygame.image.save(surf, str(path))

    assert mirror_frame(path) is True

    after = pygame.image.load(str(path)).convert_alpha()
    assert after.get_at((85, 10)) == (255, 0, 0, 255)
    assert after.get_at((10, 10))[3] == 0


def test_mirror_is_an_involution(tmp_path):
    """Mirroring twice restores the original pixels.

    The flip is its own inverse -- that is a property of the primitive, not
    a bug. What is idempotent is the REPAIR PASS: it only acts on a
    LADO_EQUIVOCADO finding, and once the frame has been mirrored the next
    audit finds none, so the second run does nothing.
    """
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    surf.set_at((10, 10), (255, 0, 0, 255))
    pygame.image.save(surf, str(path))

    mirror_frame(path)
    once = pygame.image.load(str(path)).convert_alpha()
    mirror_frame(path)
    twice = pygame.image.load(str(path)).convert_alpha()

    assert once.get_at((85, 10)) == (255, 0, 0, 255)
    assert twice.get_at((10, 10)) == (255, 0, 0, 255)
    assert twice.get_at((85, 10))[3] == 0


def test_mirror_keeps_the_canvas_size(tmp_path):
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    pygame.image.save(surf, str(path))

    mirror_frame(path)
    after = pygame.image.load(str(path)).convert_alpha()
    assert after.get_size() == (96, 80)


# ---------------------------------------------------------------------------
# The re-pad primitive.
#
# The shipped GOLIATH frames are NOT cut off, so the CORTADO repair is never
# exercised by the real assets: without a synthetic frame here, a repair that
# is inert could stay inert forever.
# ---------------------------------------------------------------------------
def test_repad_gives_the_silhouette_a_margin_on_every_side(tmp_path):
    """A sprite touching the LEFT edge is moved inward.

    The canvas keeps its size and the sprite keeps its size: it is MOVED
    inside its own canvas, never scaled.
    """
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(0, 30, 41, 50)), str(path))

    assert repad_frame(path, min_margin=3) is True

    after = pygame.image.load(str(path)).convert_alpha()
    assert after.get_size() == (W, H)

    left, top, right, bottom = _margins(after)
    assert left >= 3, f"left margin {left}"
    assert top >= 3, f"top margin {top}"
    assert right >= 3, f"right margin {right}"
    assert bottom >= 3, f"bottom margin {bottom}"

    # The silhouette itself is unchanged: same size, same pixel count. The
    # repair moves the art, it does not redraw it.
    bbox = silhouette_bbox(after)
    assert bbox is not None
    assert (bbox[2] - bbox[0], bbox[3] - bbox[1]) == (41, 20)
    assert sum(after.get_at((x, y))[3] != 0 for y in range(H) for x in range(W)) == (
        41 * 20
    )


def test_repad_also_fixes_a_silhouette_on_the_right_edge(tmp_path):
    """The shift may go LEFT: a sprite touching the right edge moves left."""
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(55, 30, 96, 50)), str(path))

    assert repad_frame(path, min_margin=3) is True

    after = pygame.image.load(str(path)).convert_alpha()
    left, top, right, bottom = _margins(after)
    assert left >= 3, f"left margin {left}"
    assert top >= 3, f"top margin {top}"
    assert right >= 3, f"right margin {right}"
    assert bottom >= 3, f"bottom margin {bottom}"
    assert after.get_size() == (W, H)


def test_repad_fixes_a_silhouette_that_touches_the_bottom_edge(tmp_path):
    """The vertical axis is handled like the horizontal one."""
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(20, 60, 50, 80)), str(path))

    assert repad_frame(path, min_margin=3) is True

    after = pygame.image.load(str(path)).convert_alpha()
    left, top, right, bottom = _margins(after)
    assert left >= 3, f"left margin {left}"
    assert top >= 3, f"top margin {top}"
    assert right >= 3, f"right margin {right}"
    assert bottom >= 3, f"bottom margin {bottom}"


def test_repad_leaves_a_healthy_frame_alone(tmp_path):
    """A frame that already has the margin is not rewritten."""
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(20, 30, 60, 50)), str(path))
    before = path.read_bytes()

    assert repad_frame(path, min_margin=3) is False
    assert path.read_bytes() == before


def test_repad_reports_failure_when_no_shift_can_help(tmp_path):
    """A silhouette that spans the whole canvas cannot be re-padded.

    No translation gives it a margin on both sides, so the repair must say
    it did nothing instead of claiming a success it cannot deliver.
    """
    path = tmp_path / "frame_00.png"
    pygame.image.save(_surface(_rect(0, 0, W, H)), str(path))
    before = path.read_bytes()

    assert repad_frame(path, min_margin=3) is False
    assert path.read_bytes() == before


# ---------------------------------------------------------------------------
# The repair PASS: dry by default, and honest about what it did.
# ---------------------------------------------------------------------------
def test_repair_set_is_dry_by_default(tmp_path):
    """Without apply=True the pass reports what it WOULD do and writes
    nothing."""
    anim_set = _synthetic_set(tmp_path, _rect(20, 30, 60, 50))
    frame = anim_set.path / "idle" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "LADO_EQUIVOCADO", "probe col 10.0")],
    )

    assert actions == ["would mirror idle/frame_00"]
    assert frame.read_bytes() == before


def test_repair_set_applies_when_asked(tmp_path):
    anim_set = _synthetic_set(tmp_path, _rect(20, 30, 60, 50))
    frame = anim_set.path / "idle" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "LADO_EQUIVOCADO", "probe col 10.0")],
        apply=True,
    )

    assert actions == ["mirrored idle/frame_00"]
    assert frame.read_bytes() != before


def test_repair_set_dry_and_applied_words_differ(tmp_path):
    """A dry run and a real run never print the same line."""
    anim_set = _synthetic_set(tmp_path, _rect(20, 30, 60, 50))
    findings = [Finding("idle", 0, "LADO_EQUIVOCADO", "probe col 10.0")]

    dry = repair_set(anim_set, findings)
    applied = repair_set(anim_set, findings, apply=True)

    assert dry != applied
    assert all(a.startswith("would ") for a in dry)
    assert all(not a.startswith("would ") for a in applied)


def test_repair_set_reports_only_what_it_actually_did(tmp_path):
    """A repair that could not be performed is NOT reported.

    The frame's silhouette spans the whole canvas, so the re-pad cannot
    succeed. The pass must return an empty list instead of claiming a
    repair it did not make.
    """
    anim_set = _synthetic_set(tmp_path, _rect(0, 0, W, H))
    frame = anim_set.path / "idle" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "CORTADO", "silhouette margins L0 T0 R0 B0")],
        apply=True,
    )

    assert actions == []
    assert frame.read_bytes() == before


def test_repair_set_reports_a_re_pad_that_worked(tmp_path):
    anim_set = _synthetic_set(tmp_path, _rect(0, 30, 41, 50))
    frame = anim_set.path / "idle" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "CORTADO", "silhouette margins L0 T30 R55 B30")],
        apply=True,
    )

    assert actions == ["re-padded idle/frame_00"]
    assert frame.read_bytes() != before


# ---------------------------------------------------------------------------
# The re-pad and the auditor must agree on the threshold.
#
# The repair used to target a margin of 3 while the auditor flagged below
# 2. A frame with only 4 px of slack could not reach the repair's target,
# so it stayed flagged FOREVER: `run.py --fix` exited 1 on a set that can
# never be repaired. ONE threshold (CORTADO_MARGIN) closes the gap.
# ---------------------------------------------------------------------------
def test_a_frame_with_margins_0_and_1_is_repaired_and_stops_being_CORTADO(tmp_path):
    """The tightest repairable frame: margins (0, 1).

    The auditor flags it CORTADO, the re-pad moves it inward, and the
    auditor accepts the result: the finding is GONE.
    """
    build_set(tmp_path, [_tight_pixels()])
    anim_set = load_set("synthetic", root=tmp_path)
    frame = anim_set.path / "idle" / "frame_00.png"

    findings, _ = audit_set(anim_set)
    cortado = [f for f in findings if f.state == "CORTADO"]
    assert cortado, "the tight frame must be flagged CORTADO"
    assert "L0 T1" in cortado[0].detail, cortado[0].detail

    actions = repair_set(anim_set, cortado, apply=True)
    assert actions == ["re-padded idle/frame_00"]

    # The repaired frame is not flagged any more.
    findings_after, _ = audit_set(anim_set)
    assert not [f for f in findings_after if f.state == "CORTADO"], [
        f.detail for f in findings_after
    ]

    after = pygame.image.load(str(frame)).convert_alpha()
    margins = silhouette_margins(after)
    assert margins is not None
    assert min(margins) >= CORTADO_MARGIN, margins


def test_the_re_pad_targets_the_threshold_the_auditor_applies(tmp_path):
    """ONE threshold: the repair's default IS the auditor's threshold.

    A stricter target than the auditor's would leave frames the auditor
    flags unrepaired; a looser one would move art that does not need to
    move. The repair must target exactly CORTADO_MARGIN.
    """
    path = tmp_path / "frame_00.png"
    # A silhouette whose margins are exactly (2, 2): the auditor accepts
    # it, so the repair must NOT touch it.
    pygame.image.save(_surface(_rect(2, 2, W - 2, H - 2)), str(path))
    before = path.read_bytes()

    assert repad_frame(path) is False
    assert path.read_bytes() == before

    # One pixel too close on the left: the auditor flags it and the
    # repair (with its default margin) fixes it. The silhouette keeps 4 px
    # of slack in total, so a translation CAN give it the margin.
    pygame.image.save(_surface(_rect(1, 2, W - 3, H - 2)), str(path))
    assert repad_frame(path) is True

    after = pygame.image.load(str(path)).convert_alpha()
    margins = silhouette_margins(after)
    assert margins is not None
    assert min(margins) >= CORTADO_MARGIN, margins


# ---------------------------------------------------------------------------
# The frame is looked up through the manifest's `clip.dir`, never through
# the clip id. The two are allowed to differ.
# ---------------------------------------------------------------------------
def test_the_repair_resolves_the_directory_from_the_manifest(tmp_path):
    """A finding names the clip by ID; the frames live in `clip.dir`.

    Every clip of the shipped GOLIATH manifest declares `dir` equal to its
    `id`, so the two are the same string there. A set that separates them
    must still be repaired in the right place -- the directory comes from
    the manifest, never from the id.
    """
    anim_set = _synthetic_set(tmp_path, _rect(20, 30, 60, 50), clip_dir="frames")
    frame = anim_set.path / "frames" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "LADO_EQUIVOCADO", "probe col 10.0")],
        apply=True,
    )

    assert actions == ["mirrored frames/frame_00"]
    assert frame.read_bytes() != before


def test_the_repair_resolves_the_directory_of_a_re_pad_from_the_manifest(tmp_path):
    """The re-pad resolves its frame through the manifest too."""
    anim_set = _synthetic_set(tmp_path, _rect(0, 30, 41, 50), clip_dir="frames")
    frame = anim_set.path / "frames" / "frame_00.png"
    before = frame.read_bytes()

    actions = repair_set(
        anim_set,
        [Finding("idle", 0, "CORTADO", "silhouette margins L0 T30 R55 B30")],
        apply=True,
    )

    assert actions == ["re-padded frames/frame_00"]
    assert frame.read_bytes() != before
