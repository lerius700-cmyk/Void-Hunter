"""BLOQUE 75 Fase 2: the pipeline must draw the enemy at the SAME size.

The runtime scales the enemy sprite by `_ship_scale_enemy` (1.05) and
truncates: `int(32 * 1.05) == 33`. The pipeline must reproduce that
EXACTLY, or the golden frames differ by a pixel on every edge.

Two things are checked here:

    1. the compositor scales a "frames" part by the part's OWN scale, with
       the SAME truncation the runtime uses (`int(w * scale)`);
    2. the CLIP's own canvas reaches `draw_part`, so a clip that declares
       one is centred on ITS canvas and not on the set's.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.anchors import AnchorSet
from src.anim.clip import ClipPlayer
from src.anim.manifest import Part, load_set
from src.entities.enemies.enemy import Enemy, EnemyKind
from src.ui.gameplay_runtime import GameplayRuntime

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
)

# A set whose body part declares the runtime's scale. Its frame is 32x32,
# exactly like the enemy art.
SCALED_MANIFEST = """
[meta]
name    = "SCALED"
version = 1
canvas  = [32, 32]
anchor  = [16, 16]

[[clips]]
id     = "idle"
dir    = "idle"
frames = 1
fps    = 10

[[parts]]
id    = "body"
draw  = "frames"
pivot = "fixed"
z     = 0
scale = [1.05, 1.05]
"""

# A set with TWO canvas sizes: one clip declares its own, the other one
# inherits the set's. This is the mine's situation (32x32 death art inside
# a 64x64 set).
CANVAS_MANIFEST = """
[meta]
name    = "CANVAS"
version = 1
canvas  = [64, 64]
anchor  = [32, 32]

[[clips]]
id     = "small"
dir    = "small"
frames = 1
fps    = 10
canvas = [32, 32]

[[clips]]
id     = "wide"
dir    = "wide"
frames = 1
fps    = 10

[[parts]]
id    = "body"
draw  = "frames"
pivot = "fixed"
z     = 0
"""


@pytest.fixture(scope="module")
def display():
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _write_set(root: Path, name: str, manifest: str, frames: dict[str, int]) -> Path:
    """Write a set with one opaque PNG per clip directory.

    `frames` maps a clip DIRECTORY to the size of its frame. The set is
    written under `root` (pytest's tmp_path), never inside the repository.
    """
    set_dir = root / name
    for dir_name, size in frames.items():
        frames_dir = set_dir / dir_name
        frames_dir.mkdir(parents=True, exist_ok=True)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((200, 100, 50, 255))
        pygame.image.save(surf, str(frames_dir / "frame_00.png"))
    (set_dir / "manifest.toml").write_text(manifest, encoding="utf-8")
    return set_dir


def _player(anim_set) -> ClipPlayer:
    """A player with an EMPTY anchor table.

    The anchor is not what these tests are about, and the compositor
    degrades to a centred blit when the frame is not in the table.
    """
    return ClipPlayer(anim_set, AnchorSet(entries={}))


def test_the_runtime_scales_the_enemy_by_1_05():
    runtime = GameplayRuntime(lambda *a, **k: None, is_boss=False, act=1, audio=None)
    assert runtime._ship_scale_enemy == 1.05
    assert int(32 * runtime._ship_scale_enemy) == 33


def test_the_enemy_manifests_declare_that_scale():
    from src.anim.manifest import load_set

    enemies = ROOT / "Assets" / "sprites" / "enemies"
    for name in ("scout", "cruiser", "drone", "heavy", "kamikaze", "sniper", "turret"):
        anim_set = load_set(name, root=enemies)
        body = anim_set.part("body")
        assert body.scale == (1.05, 1.05), name


def test_the_art_the_runtime_scales_is_32_32():
    """The 32 of `int(32 * 1.05)` is the ENEMY's own art size.

    The runtime scales the PNG the pipeline draws; if the art were not
    32x32 the target size would be a different number.
    """
    enemy = Enemy(kind=EnemyKind.SCOUT)
    path = ROOT / "Assets" / "sprites" / enemy.animation_path
    assert path.is_file(), path
    surf = pygame.image.load(str(path))
    assert surf.get_size() == (32, 32)


def test_the_pipeline_scales_the_frame_the_way_the_runtime_does(tmp_path):
    """32x32 at 1.05 -> 33x33, with the runtime's OWN truncation."""
    _write_set(tmp_path, "scaled", SCALED_MANIFEST, {"idle": 32})
    anim_set = load_set("scaled", root=tmp_path)
    player = _player(anim_set)
    body = anim_set.part("body")
    assert body.scale == (1.05, 1.05)

    raw = player.surface("idle", 0)
    assert raw is not None
    assert raw.get_size() == (32, 32)

    scaled = player.scaled_surface("idle", 0, body)
    assert scaled is not None
    # EXACTLY the runtime's arithmetic (gameplay_runtime.py:5455).
    assert scaled.get_size() == (int(raw.get_width() * 1.05), int(raw.get_height() * 1.05))
    assert scaled.get_size() == (33, 33)


def test_the_scaled_frame_is_what_lands_on_the_target(tmp_path):
    """The compositor DRAWS the scaled surface, not the raw one."""
    _write_set(tmp_path, "scaled", SCALED_MANIFEST, {"idle": 32})
    anim_set = load_set("scaled", root=tmp_path)
    player = _player(anim_set)

    target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(target, "idle", 0, origin=(120, 180))

    rect = target.get_bounding_rect()
    assert rect.size == (33, 33), (
        f"the drawn frame is {rect.size}, not the 33x33 the runtime draws"
    )


def test_a_part_without_a_scale_returns_the_raw_surface():
    """GOLIATH declares no scale: the raw surface comes back untouched.

    This is what keeps the boss from moving: the scaled path is a no-op
    for a part that declares no scale.
    """
    anim_set = load_set("goliath")
    player = _player(anim_set)
    body = anim_set.part("body")
    assert body.scale == (1.0, 1.0)

    raw = player.surface("javelin", 3)
    assert raw is not None
    assert player.scaled_surface("javelin", 3, body) is raw


def test_the_clip_canvas_overrides_the_set_canvas(tmp_path):
    """A clip that declares a canvas is centred on ITS OWN canvas."""
    _write_set(tmp_path, "canvas", CANVAS_MANIFEST, {"small": 32, "wide": 64})
    anim_set = load_set("canvas", root=tmp_path)
    player = _player(anim_set)

    # The clip declares 32x32: the frame lands on (origin - 32/2).
    small_target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(small_target, "small", 0, origin=(100, 100))
    assert small_target.get_bounding_rect().topleft == (84, 84)

    # The other clip inherits the set's 64x64: (origin - 64/2).
    wide_target = pygame.Surface((240, 360), pygame.SRCALPHA)
    player.draw(wide_target, "wide", 0, origin=(100, 100))
    assert wide_target.get_bounding_rect().topleft == (68, 68)
