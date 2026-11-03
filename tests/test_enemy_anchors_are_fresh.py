"""BLOQUE 75: the enemy anchors must not be stale.

The freshness check compares TEXT and never writes: a test that rewrote the
committed file would make the repo's own state depend on the test order.
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
from sprite_pipeline.audit import audit_set, render_anchors_toml
from sprite_pipeline.sets import discover_sets

ENEMY_ROOT = ROOT / "Assets" / "sprites" / "enemies"

# The list of sets comes from DISCOVERY, not from a hard-coded list: a set
# added later is then covered automatically instead of being silently
# uncovered.
#
# `KNOWN_SETS` is the cross-check that keeps the discovery honest. Without
# it, a discovery that returned nothing would make the tests below pass
# VACUOUSLY (the loop body would never run). With it, a known set that
# disappears is a failure -- and a NEW set still needs no edit here.
KNOWN_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)

ENEMY_SETS = tuple(sorted(path.name for path in discover_sets(ENEMY_ROOT)))


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ENEMY_ROOT


def test_the_enemy_sets_are_discovered():
    """The discovery must find the known sets -- and must find SOME."""
    assert ENEMY_SETS, "no enemy set was discovered under the enemies root"
    missing = sorted(set(KNOWN_SETS) - set(ENEMY_SETS))
    assert not missing, f"the discovery lost these sets: {missing}"


def test_every_enemy_set_has_its_anchors(enemies_root):
    for name in ENEMY_SETS:
        assert (enemies_root / name / "anchors.toml").is_file(), name


def test_the_enemy_anchors_are_fresh(enemies_root, display):
    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        _, measurements = audit_set(anim_set)
        rendered = render_anchors_toml(anim_set, measurements)
        on_disk = (enemies_root / name / "anchors.toml").read_text(encoding="utf-8")
        assert rendered == on_disk, f"{name}: the anchors are stale"


def test_the_enemy_anchors_are_lf(enemies_root):
    for name in ENEMY_SETS:
        raw = (enemies_root / name / "anchors.toml").read_bytes()
        assert b"\r\n" not in raw, name
