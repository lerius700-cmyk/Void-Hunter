"""BLOQUE 75: the enemy manifests must describe the assets that exist.

The canvas is the SPRITE canvas (measured), NOT the hitbox in
ENEMY_CONFIGS. The mine mixes two: its open/closed states are 64x64 and
its death art is 32x32, which is why `clip.canvas` exists.
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

from src.anim.manifest import load_set

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
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


def test_every_enemy_set_has_a_manifest(enemies_root):
    for name in ENEMY_SETS:
        assert (enemies_root / name / "manifest.toml").is_file(), name


def test_every_clip_directory_exists(enemies_root):
    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        for clip in anim_set.clips.values():
            assert (anim_set.path / clip.dir).is_dir(), f"{name}/{clip.id}"


def test_frame_count_matches_manifest(enemies_root):
    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        for clip in anim_set.clips.values():
            pngs = sorted((anim_set.path / clip.dir).glob("frame_*.png"))
            assert len(pngs) == clip.frames, f"{name}/{clip.id}"


def test_every_frame_has_the_declared_canvas(enemies_root, display):
    """The clip's own canvas, or the set's when the clip declares none."""
    import pygame

    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        for clip in anim_set.clips.values():
            expected = clip.canvas or anim_set.canvas
            for png in sorted((anim_set.path / clip.dir).glob("frame_*.png")):
                surf = pygame.image.load(str(png)).convert_alpha()
                assert surf.get_size() == expected, f"{name}/{clip.id}/{png.name}"


def test_the_mine_declares_two_canvases(enemies_root):
    """The special case: 64x64 states, 32x32 death art."""
    anim_set = load_set("mine_asteroid", root=enemies_root)
    assert anim_set.canvas == (64, 64)
    assert anim_set.clip("death").canvas == (32, 32)
    assert anim_set.clip("closed").canvas is None
