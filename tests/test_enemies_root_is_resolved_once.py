"""BLOQUE 75 (fix rounds 1 and 2): the enemy hot path touches no disk.

`src/anim/clip.py::_enemies_root` probes the filesystem for the root
of the enemy sets. It is called by `load_player_for_kind`, which the
runtime calls for EVERY ACTIVE ENEMY, EVERY FRAME.

The ClipPlayer was cached; the ROOT was not. So the probe --
`Path(__file__).resolve()`, ~72-90 us on Windows -- ran once per enemy
per frame, and the draw path cost 20x what it cost before the pipeline
existed.

FIX ROUND 1 pinned that ONE call: the guard counted the resolutions of
`src/anim/clip.py` and nothing else, so it could not see ANY OTHER
filesystem work on the hot path. A manifest that is re-read on every
enemy, every frame, is invisible to it.

FIX ROUND 2 broadens the guarantee: the hot path does NO per-frame
filesystem resolution -- WHICHEVER call does it. The broad guard below
counts the filesystem OPERATIONS themselves (the leaves that actually
touch the disk), so a manifest that is re-read, an anchor table that is
re-parsed or a PNG that is re-decoded are all VISIBLE.

This file COUNTS the filesystem operations. It does not time anything:
a timing assertion is flaky, a count is not. The count must not grow
with the number of frames or with the number of enemies.
"""
from __future__ import annotations

import builtins
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

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


def _path_of(target: Any) -> str:
    """The path an operation was performed on, as text."""
    if isinstance(target, os.PathLike):
        try:
            return str(os.fspath(target))
        except TypeError:
            return repr(target)
    if isinstance(target, (str, bytes)):
        return str(target)
    return repr(target)


def _short(path: str) -> str:
    """The last two components of a path: enough to name the file."""
    return "/".join(path.replace("\\", "/").rsplit("/", 2)[-2:])


def _describe_ops(ops: list[tuple[str, str]]) -> str:
    """A readable summary of the counted operations."""
    counts: dict[tuple[str, str], int] = {}
    for label, path in ops:
        key = (label, path)
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return "(none)"
    return ", ".join(
        f"{count} x {label} ({_short(path)})"
        for (label, path), count in sorted(counts.items())
    )


class _FilesystemCounter:
    """Counts the filesystem operations the code under test performs.

    The count is taken at the LEAVES -- the functions that actually
    touch the disk -- so that nothing is missed:

    ``Path.resolve``
        The path resolution of the hot path. Its internals are
        platform-dependent (Windows resolves through a Win32 call that
        no Python-level wrapper can see), so the ENTRY POINT is
        counted, not only the stat it may perform.
    ``os.stat`` / ``os.lstat``
        ``Path.stat``, ``Path.is_file``, ``Path.exists`` and every
        ``os.path`` predicate bottom out here.
    ``io.open``
        ``Path.open``, ``Path.read_bytes`` and ``Path.read_text`` all
        bottom out here. (``builtins.open`` is a DIFFERENT binding of
        the same function, so it is counted on its own.)
    ``os.listdir`` / ``os.scandir`` / ``os.open`` / ``os.access`` /
    ``os.readlink``
        The rest of the read-side leaves: a directory listing or a
        permission probe is filesystem work too.
    ``pygame.image.load``
        The PNG decode. SDL reads the file itself, so it is invisible
        to the Python-level wrappers above -- and it is the most
        expensive one of all.

    A COUNT, never a duration: a timing assertion is flaky, a count is
    not.
    """

    _LEAVES: tuple[tuple[str, Any, str], ...] = (
        ("Path.resolve", Path, "resolve"),
        ("os.stat", os, "stat"),
        ("os.lstat", os, "lstat"),
        ("os.listdir", os, "listdir"),
        ("os.scandir", os, "scandir"),
        ("os.open", os, "open"),
        ("os.access", os, "access"),
        ("os.readlink", os, "readlink"),
        ("io.open", io, "open"),
        ("builtins.open", builtins, "open"),
    )

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.ops: list[tuple[str, str]] = []
        for label, module, attribute in self._LEAVES:
            original = getattr(module, attribute)
            monkeypatch.setattr(
                module, attribute, self._wrap(label, original)
            )
        original_load = pygame.image.load
        monkeypatch.setattr(
            pygame.image, "load", self._wrap("pygame.image.load", original_load)
        )

    def _wrap(
        self, label: str, func: Callable[..., Any]
    ) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.ops.append((label, _path_of(args[0]) if args else ""))
            return func(*args, **kwargs)

        return wrapper

    def reset(self) -> list[tuple[str, str]]:
        """Forget the operations counted so far, and return them."""
        counted = self.ops
        self.ops = []
        return counted


def _runtime_with_enemies(count: int) -> tuple[Any, list[Any]]:
    """A runtime with `count` scout enemies, ready to draw.

    The runtime is built ONCE and REUSED: its construction reads the
    background, the tiles and the fonts from the disk, and that work
    is NOT what the hot path is being measured for.
    """
    runtime = GameplayRuntime(
        lambda *args, **kwargs: None, is_boss=False, act=1, audio=None
    )
    enemies = []
    for index in range(count):
        enemy = runtime._enemies.spawn(
            EnemyKind("scout"), 40.0 + index * 30.0, 200.0
        )
        assert enemy is not None
        enemy.animation_state = "idle"
        enemy.animation_frame = 0
        enemies.append(enemy)
    return runtime, enemies


def _draw_active(
    runtime: Any, enemies: list[Any], active: int, frames: int
) -> None:
    """Draw the first `active` enemies for `frames` frames."""
    for index, enemy in enumerate(enemies):
        enemy.active = index < active
    target = pygame.Surface((320, 480))
    for _ in range(frames):
        runtime._draw_enemy_pass(target, 0, 0)


def _draw_enemies(count: int, frames: int) -> None:
    """Draw `count` enemies for `frames` frames.

    The runtime owns the hot path: `_draw_enemy_pass` is what the game
    calls, and it asks the pipeline for every active enemy, every
    frame.
    """
    runtime, enemies = _runtime_with_enemies(count)
    _draw_active(runtime, enemies, count, frames)


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


def test_the_hot_path_does_no_filesystem_work(display, monkeypatch) -> None:
    """The enemy draw path must not touch the filesystem at all.

    The guarantee is not "the root is resolved once": it is "the hot
    path does no per-frame filesystem resolution" -- WHICHEVER call
    does it. The narrow guard above only sees the resolutions of
    `clip.py`, so a manifest that is re-read, or an anchor table that
    is re-parsed, or a PNG that is re-decoded on the enemy path is
    INVISIBLE to it.

    The WARM-UP matters: the first draw is the one that reads the
    manifest, the anchor table and the PNG. What is measured is the
    draw that happens on EVERY frame of the game.
    """
    runtime, enemies = _runtime_with_enemies(3)
    counter = _FilesystemCounter(monkeypatch)

    # The counter must be ARMED. It has to see a filesystem operation
    # that this test performs ON PURPOSE: a counter that sees nothing
    # would make every assertion below pass for the WRONG reason.
    probe = ROOT / "src" / "anim" / "clip.py"
    probe.stat()
    assert counter.reset(), (
        "the counter did not see the filesystem operation the test "
        "performed on purpose: it is not counting, and the assertions "
        "below would pass for the WRONG reason"
    )

    # The warm-up: the draw that must happen ONCE. It is what makes
    # this test independent of the ORDER the tests run in -- run alone,
    # the caches are cold and this draw is the one that reads the
    # manifest, the anchor table and the PNG.
    _draw_active(runtime, enemies, 3, 4)
    counter.reset()

    # ONE enemy, ONE frame.
    _draw_active(runtime, enemies, 1, 1)
    small = counter.reset()

    # THREE enemies, FOUR frames.
    _draw_active(runtime, enemies, 3, 4)
    large = counter.reset()

    assert len(large) == len(small), (
        f"the enemy draw path performed {len(large)} filesystem "
        f"operations for 3 enemies and 4 frames but only {len(small)} "
        f"for 1 enemy and 1 frame: the filesystem work GROWS with the "
        f"enemies and the frames -- the hot path is doing per-frame "
        f"filesystem work. Operations: {_describe_ops(large)}"
    )
    assert not small, (
        f"the enemy draw path performed {len(small)} filesystem "
        f"operations for 1 enemy and 1 frame: the hot path must do NO "
        f"filesystem work once it is warm. Operations: "
        f"{_describe_ops(small)}"
    )


def test_the_counter_sees_the_operations_it_claims_to_see(
    display, monkeypatch
) -> None:
    """The counter must SEE what it claims to see.

    A guard that counts the wrong leaves is as bad as no guard: it
    would report "zero filesystem work" while the disk was being read.
    """
    counter = _FilesystemCounter(monkeypatch)
    clip = ROOT / "src" / "anim" / "clip.py"
    png = ROOT / "Assets" / "sprites" / "enemies" / "scout" / "idle" / "frame_00.png"

    def seen(action: Callable[[], Any]) -> bool:
        counter.reset()
        action()
        return bool(counter.ops)

    assert seen(lambda: clip.resolve()), "Path.resolve was not counted"
    assert seen(lambda: clip.stat()), "Path.stat was not counted"
    assert seen(lambda: clip.is_file()), "Path.is_file was not counted"
    assert seen(lambda: clip.open("rb").close()), "Path.open was not counted"
    assert seen(lambda: clip.read_bytes()), "Path.read_bytes was not counted"
    assert seen(
        lambda: clip.read_text(encoding="utf-8")
    ), "Path.read_text was not counted"
    assert seen(
        lambda: open(clip, "rb").close()
    ), "builtins.open was not counted"
    assert seen(
        lambda: pygame.image.load(str(png))
    ), "pygame.image.load was not counted"
