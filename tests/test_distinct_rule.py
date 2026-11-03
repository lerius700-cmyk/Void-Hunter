"""BLOQUE 75: COLAPSADO against a DECLARED number of distinct images.

The enemy art cycles 1-4 poses to fill ten slots at 12.5 FPS. The shipped
rule ("any duplicate md5 inside a clip") reads all of it as a collapsed
animation -- 29 of the 33 live clips. With `distinct` declared, the finding
is raised only when the art disagrees with the DECLARATION.
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
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _write_set(tmp_path: Path, distinct: int | None, frames: int) -> None:
    """`frames` frames, of which 3 are distinct images."""
    import pygame

    set_dir = tmp_path / "probe"
    (set_dir / "idle").mkdir(parents=True, exist_ok=True)
    colors = ((255, 255, 255, 255), (255, 0, 0, 255), (0, 0, 255, 255))
    for i in range(frames):
        surf = pygame.Surface((8, 8), pygame.SRCALPHA, 32)
        surf.fill(colors[i % 3])
        pygame.image.save(surf, str(set_dir / "idle" / f"frame_{i:02d}.png"))
    declared = "" if distinct is None else f"distinct = {distinct}\n"
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [8, 8]\n'
        'anchor = [4, 4]\n'
        'cut_margin = 0\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = %d\n' % frames
        + declared
        + '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
        encoding="utf-8",
    )


def _collapsed(tmp_path: Path) -> bool:
    findings, _ = audit_set(load_set("probe", root=tmp_path))
    return any(f.state == "COLAPSADO" for f in findings)


def test_a_matching_declaration_is_clean(tmp_path, display):
    _write_set(tmp_path, distinct=3, frames=9)
    assert _collapsed(tmp_path) is False


def test_a_stale_declaration_is_a_finding(tmp_path, display):
    """The manifest says 2, the art has 3: the manifest is stale."""
    _write_set(tmp_path, distinct=2, frames=9)
    assert _collapsed(tmp_path) is True


def test_without_a_declaration_any_duplicate_is_a_finding(tmp_path, display):
    """The shipped rule, unchanged: GOLIATH declares no `distinct`."""
    _write_set(tmp_path, distinct=None, frames=9)
    assert _collapsed(tmp_path) is True
