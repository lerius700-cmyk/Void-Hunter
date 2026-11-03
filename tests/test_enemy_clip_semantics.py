"""BLOQUE 75: the declared semantics must match what the runtime does.

`mode` and `on_end` are PARSED but not enforced in Phase 1, so nothing
else would catch a declaration that contradicts the code. This test is the
consumer: it reads the manifest and the runtime and compares them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import load_set
from src.entities.enemies.enemy import Enemy

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
)


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


def test_the_runtime_fps_is_the_declared_fps(enemies_root: Path) -> None:
    # ANIMATION_FRAME_DURATION lives on the Enemy class, not at module level.
    runtime_fps = 1.0 / Enemy.ANIMATION_FRAME_DURATION
    assert runtime_fps == 12.5
    for name in ENEMY_SETS:
        anim_set = load_set(name, root=enemies_root)
        for clip in anim_set.clips.values():
            assert clip.fps == runtime_fps, f"{name}/{clip.id}"


@pytest.mark.parametrize("name", ENEMY_SETS)
def test_the_sequences_declare_what_the_runtime_does(enemies_root: Path, name: str) -> None:
    anim_set = load_set(name, root=enemies_root)
    assert anim_set.clip("idle").on_end == "loop"
    assert anim_set.clip("thrust").on_end == "loop"
    # damage and death are one-shots that RETURN to idle: the runtime
    # resets `animation_frame` and `animation_state` (enemy.py:714-717).
    assert anim_set.clip("damage").on_end == "reset"
    assert anim_set.clip("death").on_end == "reset"


def test_the_mine_declares_its_states(enemies_root: Path) -> None:
    anim_set = load_set("mine_asteroid", root=enemies_root)
    assert anim_set.clip("closed").mode == "variants"
    assert anim_set.clip("open1").mode == "state"
    assert anim_set.clip("open2").mode == "state"
    assert anim_set.clip("open3").mode == "state"
    # The death clip exists on disk but the runtime never plays it:
    # `Enemy.animation_path` always returns the mine's STATE path.
    assert anim_set.clip("death").mode == "archive"


def test_the_mine_states_match_the_runtime_directories(enemies_root: Path) -> None:
    anim_set = load_set("mine_asteroid", root=enemies_root)
    # open3 reuses the `open/` directory (BLOQUE 65).
    assert anim_set.clip("open3").dir == "open"
    assert anim_set.clip("closed").frames == 5  # five asteroid VARIANTS
