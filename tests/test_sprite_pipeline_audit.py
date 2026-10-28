"""BLOQUE 74: the auditor's own classification must be covered.

The auditor is the gate that stops a broken set from entering the repo.
If the auditor itself is wrong, it silently blesses broken art. These
tests feed it synthetic frames, one per state, and assert the verdict.

All SEVEN states are covered here: COLAPSADO, CORTADO, LADO_EQUIVOCADO,
FIRMA_AMBIGUA, AUSENTE, FUERA_DE_RANGO and ESCALADO.

Synthetic frames are built in a temporary directory with a temporary
manifest, so nothing here touches the shipped assets.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json
import subprocess
import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline.audit import FAIL_STATES, audit_set  # noqa: E402

W, H = 96, 80
TRANSPARENT = (0, 0, 0, 0)
BRASS = (200, 170, 60)
BODY = (160, 110, 50)


def write_frame(path: Path, pixels: dict[tuple[int, int], tuple]) -> None:
    surf = pygame.Surface((W, H), pygame.SRCALPHA, 32)
    surf.fill(TRANSPARENT)
    for (x, y), colour in pixels.items():
        surf.set_at((x, y), colour)
    pygame.image.save(surf, str(path))


def build_set(tmp_path: Path, frames: list[dict[tuple[int, int], tuple]]) -> None:
    """Write a one-clip set into `tmp_path`."""
    set_dir = tmp_path / "synthetic"
    clip_dir = set_dir / "idle"
    clip_dir.mkdir(parents=True)
    for i, pixels in enumerate(frames):
        write_frame(clip_dir / f"frame_{i:02d}.png", pixels)

    manifest = """[meta]
name = "SYNTHETIC"
version = 1
canvas = [96, 80]
anchor = [48, 40]
sided = "right"

[[clips]]
id = "idle"
dir = "idle"
frames = {n}
fps = 10
loop = true
scale_tolerance = 0.15
# The tolerance the synthetic cases are tuned for. The shipped GOLIATH
# manifest uses 14.0; here 10.0 keeps every case off the edge of its
# threshold (the LADO case is 15 px away, so it clears it by 5 px and
# not by 1).
side_tolerance = 10.0

[[parts]]
id = "body"
draw = "frames"
pivot = "centroid"
z = 0

[[parts]]
id = "shield_plate"
draw = "ellipse"
pivot = "detect"
z = 1
offset = [0, 3]
scale = [0.78, 1.0]
radii = [11, 11, 17]
detect = {{ method = "shape", band = [28, 54], side = "right", min_col = 50, ranges = {{ rx = [6.5, 11.0], ry = [9.0, 13.0] }}, warm_fallback = {{ r_min = 235, b_max = 140, g_min = 130, r_minus_b_min = 190 }}, probe = {{ method = "color", r_min = 185, g_min = 145, b_max = 130, r_minus_b_min = 70 }} }}
on_missing = "interpolate"

[[parts]]
id = "eye"
draw = "point"
pivot = "detect"
z = 2
detect = {{ method = "color", head_band = [0, 30], col_range = [24, 70], r_min = 170, rg_min = 70 }}
on_missing = "interpolate"
"""
    (set_dir / "manifest.toml").write_text(
        manifest.format(n=len(frames)), encoding="utf-8"
    )


def body_pixels(cx: int = 40, width: int = 20, top: int = 20, height: int = 45):
    """A rectangle of body pixels plus a brass plate on its right."""
    pixels: dict[tuple[int, int], tuple] = {}
    for y in range(top, top + height):
        for x in range(cx, cx + width):
            pixels[(x, y)] = BODY
    for y in range(34, 46):
        for x in range(cx + width, cx + width + 8):
            pixels[(x, y)] = BRASS
    return pixels


@pytest.fixture(scope="module", autouse=True)
def display():
    """pygame needs a video mode before convert_alpha() works."""
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def states_for(tmp_path: Path, frames) -> set[str]:
    build_set(tmp_path, frames)
    anim_set = load_set("synthetic", root=tmp_path)
    findings, _ = audit_set(anim_set)
    return {f.state for f in findings}


def test_duplicate_frames_are_COLAPSADO(tmp_path):
    frame = body_pixels()
    states = states_for(tmp_path, [frame, dict(frame)])
    assert "COLAPSADO" in states


def test_sprite_at_the_edge_is_CORTADO(tmp_path):
    pixels = body_pixels()
    pixels[(0, 40)] = BODY
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "CORTADO" in states


def test_plate_on_the_left_is_LADO_EQUIVOCADO(tmp_path):
    # The plate MOVES to the left: it is removed from the arm first, so the
    # probe sees the brass of a single plate. (Adding a second plate on
    # the left would leave the probe's centroid on the centre line -- see
    # test_a_plate_on_both_sides_is_not_LADO_EQUIVOCADO.)
    pixels = {k: v for k, v in body_pixels().items() if v != BRASS}
    for y in range(34, 46):
        for x in range(30, 38):
            pixels[(x, y)] = BRASS
    # the plate now sits left of the canvas centre
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "LADO_EQUIVOCADO" in states


def test_missing_plate_is_AUSENTE(tmp_path):
    pixels = {k: v for k, v in body_pixels().items() if v != BRASS}
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "AUSENTE" in states


def test_implausible_ellipse_is_FUERA_DE_RANGO(tmp_path):
    """A 2 px wide plate cannot be the shield."""
    pixels = body_pixels()
    # The plate is NARROWED to 2 px: the brass it does not have any more
    # is erased, not painted over (painting brass over brass would leave
    # the frame untouched and the clip would be reported as COLAPSADO).
    for y in range(34, 46):
        for x in range(62, 68):
            pixels.pop((x, y), None)
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "FUERA_DE_RANGO" in states


def test_probe_and_shape_disagree_is_FIRMA_AMBIGUA(tmp_path):
    """The two independent detectors disagree by more than the tolerance.

    The brass is a wide slab that STARTS left of the shape rule's
    min_col (50), so the shape rule still measures the arm (a credible
    ellipse at cx 58.5) while the probe's centroid sits at 43.5. The two
    detectors are 15 px apart, which is more than the 10 px tolerance.

    The clip's median probe column is the same 43.5, so the frame is
    not "stray" and is NOT reported as LADO_EQUIVOCADO: only the two
    detectors disagree. This is the situation of the shipped
    laser/frame_05 (probe 44.5 against shape cx 60.5).
    """
    pixels = body_pixels()
    for y in range(34, 46):
        for x in range(20, 68):
            pixels[(x, y)] = BRASS
    twin = dict(pixels)
    twin[(39, 40)] = BODY  # a different frame with the same probe and shape
    states = states_for(tmp_path, [pixels, twin])
    assert states == {"FIRMA_AMBIGUA"}


def test_a_taller_frame_is_ESCALADO(tmp_path):
    """One frame's silhouette height strays from the clip's median.

    The height is the silhouette's bounding-box height, so the outlier
    is a body that is visibly taller: rows 10..69 instead of rows
    20..64 (60 px against 45 px, a 33% deviation against a 15%
    tolerance). The two other frames share the median's height, so
    only the outlier is flagged.
    """
    tall = body_pixels(top=10, height=60)
    healthy = body_pixels()
    twin = body_pixels()
    twin[(39, 40)] = BODY  # same height, different frame
    states = states_for(tmp_path, [tall, healthy, twin])
    assert states == {"ESCALADO"}


def test_healthy_set_has_no_failures(tmp_path):
    build_set(tmp_path, [body_pixels()])
    findings, _ = audit_set(load_set("synthetic", root=tmp_path))
    fails = [f for f in findings if f.state in FAIL_STATES]
    assert not fails, [f.detail for f in fails]


def test_a_plate_on_both_sides_is_not_LADO_EQUIVOCADO(tmp_path):
    """The probe reports the CENTROID of the brass pixels.

    A frame that carries a plate on both sides has its centroid on the
    centre line, so it is not a turned-around frame and must not be
    flagged. A turned-around character has the plate MOVED to the other
    side, not a second plate added.
    """
    pixels = body_pixels(cx=40)
    for y in range(34, 46):
        for x in range(30, 38):
            pixels[(x, y)] = BRASS
    states = states_for(tmp_path, [pixels, body_pixels()])
    assert "LADO_EQUIVOCADO" not in states


# ---------------------------------------------------------------------------
# The CLI contract: `--json` must write ONLY JSON to stdout.
# ---------------------------------------------------------------------------
def test_json_report_is_pure_json():
    """pygame prints its support banner to STDOUT when it is imported.

    That banner would make the report unparseable, so the auditor sets
    PYGAME_HIDE_SUPPORT_PROMPT before importing pygame. This test is the
    guard that keeps it that way: move the import above the
    setdefault and this fails.

    stdout and stderr are captured SEPARATELY (no pipe): a pipe would
    add a shell artefact to the bytes, not a defect of the tool.
    """
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "sprite_pipeline" / "audit.py"),
            "goliath",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=300,
    )
    stdout = proc.stdout.decode("utf-8")
    stderr = proc.stderr.decode("utf-8")

    # The exit code is NOT asserted: the auditor exits 1 while the two
    # turned-around frames are still in the art, and that is correct.
    #
    # The banner check is POSITIONAL, not a substring search: a finding
    # detail could legitimately contain the word "pygame" one day, and a
    # substring search would false-positive on it. A banner always
    # PRECEDES the JSON, so the first non-blank byte must be "{".
    assert stdout.lstrip().startswith("{"), stdout[:200]
    assert "Hello from the pygame community" not in stdout, stdout[:200]

    report = json.loads(stdout)
    assert "set" in report
    assert isinstance(report["set"], str)
    assert isinstance(report["findings"], list)
    assert stderr == "", stderr
