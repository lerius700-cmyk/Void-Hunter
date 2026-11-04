"""BLOQUE 75 (fix round 1): the enemies root must be resolved ONCE.

`src/anim/clip.py::_enemies_root` probes the filesystem for the root
of the enemy sets. It is called by `load_player_for_kind`, which the
runtime calls for EVERY ACTIVE ENEMY, EVERY FRAME.

The ClipPlayer was cached; the ROOT was not. So the probe --
`Path(__file__).resolve()`, ~72-90 us on Windows -- ran once per enemy
per frame, and the draw path cost 20x what it cost before the pipeline
existed.

This file COUNTS the resolutions. It does not time anything: a timing
assertion is flaky, a count is not. The count must not grow with the
number of frames or with the number of enemies.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import subprocess
import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.entities.enemies.enemy import EnemyKind
from src.ui.gameplay_runtime import GameplayRuntime


@pytest.fixture(scope="module")
def display():
    """A video mode: `Surface.convert_alpha()` needs one."""
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _count_root_resolutions(monkeypatch) -> list[Path]:
    """Count the filesystem resolutions of the clip module's OWN path.

    `Path.resolve` cannot be told apart by name alone -- the whole
    tree resolves paths -- so only the resolutions of
    `src/anim/clip.py` are counted: that is the one on the hot path.
    """
    resolutions: list[Path] = []
    real_resolve = Path.resolve

    def counting_resolve(self, strict=False):
        result = real_resolve(self, strict)
        if self.name == "clip.py" and self.parent.name == "anim":
            resolutions.append(result)
        return result

    monkeypatch.setattr(Path, "resolve", counting_resolve)
    return resolutions


def _draw_enemies(count: int, frames: int) -> None:
    """Draw `count` enemies for `frames` frames.

    The runtime owns the hot path: `_draw_enemy_pass` is what the game
    calls, and it asks the pipeline for every active enemy, every
    frame.
    """
    runtime = GameplayRuntime(
        lambda *args, **kwargs: None, is_boss=False, act=1, audio=None
    )
    for index in range(count):
        enemy = runtime._enemies.spawn(
            EnemyKind("scout"), 40.0 + index * 30.0, 200.0
        )
        assert enemy is not None
        enemy.animation_state = "idle"
        enemy.animation_frame = 0
    target = pygame.Surface((320, 480))
    for _ in range(frames):
        runtime._draw_enemy_pass(target, 0, 0)


def test_the_root_is_not_resolved_once_per_enemy_and_frame(display, monkeypatch):
    """The count must not grow with the frames or with the enemies.

    The discriminator: with the root resolved on every call, the count
    grows with `enemies * frames`. With the root memoized, it does not
    move at all.
    """
    resolutions = _count_root_resolutions(monkeypatch)

    _draw_enemies(1, 1)
    small = len(resolutions)
    _draw_enemies(3, 4)
    large = len(resolutions)

    assert small <= 1, (
        f"the enemies root was resolved {small} times for ONE enemy and "
        f"ONE frame: it must be resolved at most once"
    )
    assert large == small, (
        f"the enemies root was resolved {large - small} more times for 3 "
        f"enemies and 4 frames than for 1 enemy and 1 frame: the path is "
        f"re-resolved from the FILESYSTEM on the hot path (once per "
        f"enemy, per frame) -- {large} resolutions in total"
    )


def test_the_enemies_root_is_memoized(display, monkeypatch):
    """The root function itself must hold a cache.

    The cache is what makes the count above flat: the first call
    resolves the path, every other call is a hit.
    """
    from src.anim import clip as clip_module

    cache_clear = getattr(clip_module._enemies_root, "cache_clear", None)
    assert cache_clear is not None, (
        "the enemies root is NOT memoized: it resolves the path from the "
        "filesystem on EVERY call (once per enemy, per frame)"
    )
    cache_clear()

    _draw_enemies(2, 2)

    info = clip_module._enemies_root.cache_info()
    assert info.misses == 1, (
        f"the enemies root was resolved {info.misses} times for 2 enemies "
        f"and 2 frames: it must be resolved ONCE and reused"
    )


def test_the_enemies_root_is_not_resolved_at_import_time():
    """A frozen build never touches the source tree.

    The root is resolved on CALL, never on import: a frozen build
    reads `_MEIPASS` at runtime and must not look at the source tree
    when the module is loaded. The memoization must not turn into a
    module-level constant.
    """
    code = (
        "import os\n"
        "os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')\n"
        "os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')\n"
        "from pathlib import Path\n"
        "real = Path.resolve\n"
        "count = []\n"
        "def counting(self, strict=False):\n"
        "    result = real(self, strict)\n"
        "    if self.name == 'clip.py' and self.parent.name == 'anim':\n"
        "        count.append(1)\n"
        "    return result\n"
        "Path.resolve = counting\n"
        "import src.anim.clip\n"
        "print(len(count))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # The LAST line is the count: pygame prints a banner on stdout.
    count = proc.stdout.strip().splitlines()[-1]
    assert count == "0", (
        f"importing src.anim.clip resolved the enemies root "
        f"{count} times: the root must be resolved on CALL, never at "
        f"import time (a frozen build has no source tree)"
    )
