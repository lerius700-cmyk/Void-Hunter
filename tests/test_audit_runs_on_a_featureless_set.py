"""BLOQUE 75: the auditor must survive a set with NO detected features.

The enemy sets declare a single `body` part: no shield plate, no eye.
The shipped auditor asked for both unconditionally, so it raised
ManifestError before it measured a single frame -- and it labelled an
unresolved feature as "measured", which `load_anchors` reads as a real
anchor at (0, 0).
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

from src.anim.manifest import load_set
from sprite_pipeline.audit import audit_set


@pytest.fixture(scope="module")
def display():
    """pygame needs a video mode before convert_alpha() works."""
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _write_probe_set(tmp_path: Path) -> None:
    """A minimal set: one clip, one body-only part, two identical frames."""
    import pygame

    set_dir = tmp_path / "probe"
    (set_dir / "idle").mkdir(parents=True)
    for i in range(2):
        surf = pygame.Surface((8, 8), pygame.SRCALPHA, 32)
        surf.fill((255, 255, 255, 255))
        pygame.image.save(surf, str(set_dir / "idle" / f"frame_{i:02d}.png"))
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'version = 1\n'
        'canvas = [8, 8]\n'
        'anchor = [4, 4]\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'dir = "idle"\n'
        'frames = 2\n'
        'fps = 12.5\n'
        'loop = true\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n'
        'pivot = "fixed"\n'
        'z = 0\n',
        encoding="utf-8",
    )


def test_the_auditor_measures_a_set_without_features(tmp_path, display):
    _write_probe_set(tmp_path)
    anim_set = load_set("probe", root=tmp_path)
    findings, measurements = audit_set(anim_set)
    assert len(measurements) == 2


def test_an_unresolved_feature_is_not_labelled_measured(tmp_path, display):
    """A feature the set does not declare is UNRESOLVED, not measured.

    "measured" with a (0, 0) value is the eye-at-the-corner hazard: a
    consumer would launch the beam from the corner of the canvas.
    """
    _write_probe_set(tmp_path)
    anim_set = load_set("probe", root=tmp_path)
    _, measurements = audit_set(anim_set)
    for m in measurements:
        assert m.eye is None
        assert m.eye_source == "missing"
        assert m.shield is None
        assert m.shield_source == "missing"
