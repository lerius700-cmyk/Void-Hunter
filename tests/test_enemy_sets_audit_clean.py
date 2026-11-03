"""BLOQUE 75: the enemy sets must audit CLEAN, and no art may be orphaned.

The declarations (`distinct`, `cut_margin = 0`) are what make the enemy art
auditable: the art repeats poses and touches the canvas edges ON PURPOSE.
Nothing pinned that, though -- the anchors test discards the findings, so
replacing one death pose would change the md5-group count, the auditor would
flag it, and CI would stay green.

This file is the guard: the auditor must return ZERO findings for every enemy
set, and every clip directory on disk must be referenced by a clip.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set
from sprite_pipeline.audit import audit_set

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


@pytest.fixture(scope="module")
def display() -> Iterator[None]:
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


@pytest.mark.parametrize("name", ENEMY_SETS)
def test_the_enemy_set_audits_clean(enemies_root: Path, display: None, name: str) -> None:
    """Zero findings: every finding the art really has is DECLARED."""
    anim_set = load_set(name, root=enemies_root)
    findings, _ = audit_set(anim_set)
    assert findings == [], [(f.clip, f.frame, f.state, f.detail) for f in findings]


@pytest.mark.parametrize("name", ENEMY_SETS)
def test_every_clip_directory_is_declared(enemies_root: Path, name: str) -> None:
    """Art on disk that no clip references would be ignored in silence."""
    anim_set = load_set(name, root=enemies_root)
    declared = {clip.dir for clip in anim_set.clips.values()}
    on_disk = {
        path.name
        for path in anim_set.path.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    }
    assert on_disk == declared, f"{name}: {sorted(on_disk)} vs {sorted(declared)}"
