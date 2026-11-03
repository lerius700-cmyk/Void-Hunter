"""BLOQUE 75: one threshold, read by the auditor AND the repair.

The enemy art is authored tight to its canvas: 29 of the 33 live clips
touch the edge by design. GOLIATH's 2 px margin exists because the AI
generator drew the boss's limbs past the canvas. The margin is a property
of the ART, so each set declares its own -- and the auditor and the repair
must read the SAME value, or a frame the auditor flags could be one the
repair cannot reach.
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
from src.anim.measure import CORTADO_MARGIN, effective_cut_margin, is_cut_off
from sprite_pipeline.audit import audit_set


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def test_is_cut_off_takes_the_margin():
    assert is_cut_off((0, 3, 3, 3), 2) is True
    assert is_cut_off((0, 3, 3, 3), 0) is False
    assert is_cut_off((2, 2, 2, 2), 2) is False


def test_goliath_uses_the_pipeline_default():
    anim_set = load_set("goliath")
    assert effective_cut_margin(anim_set) == CORTADO_MARGIN


def test_a_set_declares_its_own_margin(tmp_path):
    set_dir = tmp_path / "probe"
    set_dir.mkdir(parents=True)
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [8, 8]\n'
        'anchor = [4, 4]\n'
        'cut_margin = 0\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 1\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
        encoding="utf-8",
    )
    anim_set = load_set("probe", root=tmp_path)
    assert effective_cut_margin(anim_set) == 0


def test_a_tight_silhouette_is_cut_off_only_when_the_margin_says_so(
    tmp_path, display
):
    """The same frame: CORTADO at margin 2, clean at margin 0."""
    import pygame

    set_dir = tmp_path / "probe"
    (set_dir / "idle").mkdir(parents=True)
    surf = pygame.Surface((8, 8), pygame.SRCALPHA, 32)
    surf.fill((255, 255, 255, 255))
    pygame.image.save(surf, str(set_dir / "idle" / "frame_00.png"))

    def _manifest(margin: int) -> str:
        return (
            '[meta]\n'
            'name = "PROBE"\n'
            'canvas = [8, 8]\n'
            'anchor = [4, 4]\n'
            f'cut_margin = {margin}\n'
            '\n'
            '[[clips]]\n'
            'id = "idle"\n'
            'frames = 1\n'
            '\n'
            '[[parts]]\n'
            'id = "body"\n'
            'draw = "frames"\n'
        )

    (set_dir / "manifest.toml").write_text(_manifest(2), encoding="utf-8")
    findings, _ = audit_set(load_set("probe", root=tmp_path))
    assert any(f.state == "CORTADO" for f in findings)

    (set_dir / "manifest.toml").write_text(_manifest(0), encoding="utf-8")
    findings, _ = audit_set(load_set("probe", root=tmp_path))
    assert not any(f.state == "CORTADO" for f in findings)
