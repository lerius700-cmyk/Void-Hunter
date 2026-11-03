"""BLOQUE 75: the declared semantics must match what the runtime does.

`mode` and `on_end` are PARSED but not enforced in Phase 1, so nothing
else would catch a declaration that contradicts the code. This test is the
consumer: it reads the manifest and the runtime and compares them.
"""
from __future__ import annotations

import sys
import tomllib
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
    idle = anim_set.clip("idle")
    thrust = anim_set.clip("thrust")
    damage = anim_set.clip("damage")
    death = anim_set.clip("death")
    # The runtime branches on `loop` (src/anim/clip.py:54): a looping clip
    # WRAPS, a one-shot HOLDS on its last frame. `on_end` declares what the
    # ENTITY does when the clip ends (the enemy goes back to idle). The
    # two are asserted TOGETHER, so the manifest cannot drift away from
    # the runtime without one of them failing.
    assert idle.loop is True
    assert idle.on_end == "loop"
    assert thrust.loop is True
    assert thrust.on_end == "loop"
    # damage and death are one-shots that RETURN to idle: the runtime
    # resets `animation_frame` and `animation_state` (enemy.py:714-717).
    assert damage.loop is False
    assert damage.on_end == "reset"
    assert death.loop is False
    assert death.on_end == "reset"


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


def test_the_mine_clips_carry_no_fps(enemies_root: Path) -> None:
    """The mine's clips are STATIC: no fps applies to them.

    `closed` holds five VARIANTS and `open1`/`open2`/`open3` hold a
    single frame each; the frame is chosen by the mine's STATE
    (mine_state) and is never advanced by time -- `_update_mine_asteroid()`
    returns before the animation tick. The `death` clip is
    `mode = "archive"` and is never played either. Declaring an fps would
    be a FALSE declaration (they do not animate at any rate), so the
    manifest declares none and the loader's default applies.

    This test exists so nobody "fixes" it later by adding an fps.
    """
    anim_set = load_set("mine_asteroid", root=enemies_root)
    for clip in anim_set.clips.values():
        # The loader's default for a clip that declares no fps
        # (src/anim/manifest.py:450).
        assert clip.fps == 10.0, (
            f"{clip.id}: the mine's clips do not animate -- they carry the "
            f"loader's default fps, not a declared one"
        )
    # And the manifest declares NONE of them.
    raw = tomllib.loads(
        (enemies_root / "mine_asteroid" / "manifest.toml").read_text(
            encoding="utf-8"
        )
    )
    for entry in raw.get("clips", []):
        assert "fps" not in entry, f"{entry.get('id')}: the mine's clips declare no fps"
