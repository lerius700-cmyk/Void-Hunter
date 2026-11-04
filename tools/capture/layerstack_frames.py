"""BLOQUE 75 Fase 2: the deterministic golden-frame harness.

The golden frames are the proof that the LayerStack changed NOTHING. That
proof is only worth something if the capture is reproducible, so this
harness is built to be reproducible by construction:

  * the GLOBAL `random` module is seeded before the scene is built -- the
    runtime uses it in 31 screen-affecting places and seeds only
    `_asteroid_rng`;
  * the scene is REBUILT for every capture (a reused scene keeps its RNG
    state and its entity positions);
  * time advances by a FIXED dt, never by the wall clock;
  * the input is scripted through the very channels the runtime reads
    (`GameplayRuntime._read_input`, gameplay_runtime.py:765-785).

Two adaptations to the original brief were needed, both forced by pygame
2.6.1 and both documented here:

  * `pygame.key.set_pressed` and `pygame.mouse.set_pressed` do not exist
    in pygame 2 (they are pygame 1.x APIs), and SDL's key/button state is
    only fed by real hardware events, so posting a KEYDOWN does not move
    `pygame.key.get_pressed()`. The harness therefore replaces the
    PRODUCER of the input snapshot with a scripted one. The runtime only
    ever does `keys[pygame.K_x]` and `mouse_buttons[0] / [2]`, so a tiny
    duck-typed object is enough -- and it is the same channel the runtime
    reads, at the same line.
  * `GameplayRuntime.on_enter()` is what populates the wave queue
    (`_populate_level1_queue`), the boss pose and the asteroid spawner.
    Without it the frames would contain nothing but the background, the
    player and the HUD -- a vacuous proof. The harness calls it exactly
    like `GameplayScene.on_enter` does (src/ui/scenes.py:1291-1292).

THE GUARANTEES ARE ENFORCED, NOT ASSUMED. A guarantee the check
cannot see is a hypothesis, so each one fails loudly:

  1. An unknown `--only` name captures NOTHING and the check says so and
     exits 1 (`_select_frames`). A proof that cannot fail is not a proof.
  2. The scene is rebuilt for every frame, and the harness ENFORDS it:
     the scene object of each frame is kept and a scene that shows up
     twice aborts the run (`_assert_fresh_scene`). Reusing a scene would
     make the frames repeatable but wrong -- the check has to see it.
  3. `--check` compares the fresh capture against the COMMITTED golden
     frames, not only against a second fresh capture. Two captures inside
     one process are identical even when the nondeterminism is
     per-process; the committed frame is the property that matters.
     The comparison is PIXEL-LEVEL (RGB + alpha), because that is what
     Task 4 asserts, and a PNG re-encode must not be able to fake a
     regression. The byte digest is reported too.
  4. A MISSING golden set is a FAILURE, never a pass (`_check`). Skipping
     the comparison would leave the weaker intra-process check that #3
     exists to replace, and the Phase 2 gate (P2-G2) would go green with
     ZERO proof fixtures.
  5. The proof set cannot SHRINK silently: the committed golden files and
     the captured frames have to be the SAME set. A golden with no capture
     (a frame dropped from the FRAMES table) is reported, not ignored.

The scene is DRAWN EXACTLY ONCE per capture: a draw mutates the scene
(`_draw_engine_flame` emits a spark with `random.random()` DURING the
draw), so rendering the same scene twice yields two different frames.

Usage:
    python tools/capture/layerstack_frames.py --out tools/golden/layerstack
    python tools/capture/layerstack_frames.py --check
"""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import hashlib
import random
import sys
from pathlib import Path
from typing import TypeAlias

import pygame

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.core.settings import INTERNAL_H, INTERNAL_W  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime  # noqa: E402

SEED = 20261103
DT = 1.0 / 60.0

# The committed golden frames: the proof itself.
GOLDEN_DIR = ROOT / "tools" / "golden" / "layerstack"

# (name, ticks, keys, mouse_buttons, is_boss)
Frame: TypeAlias = tuple[str, int, tuple[int, ...], tuple[int, ...], bool]

# The five frames the proof needs: enemies on screen, the boss, the mine in
# its open3 state, the player firing, and the HUD populated.
#
# Each entry is (name, ticks, keys, mouse_buttons, is_boss):
#   ticks         -- fixed 60 Hz steps advanced before the capture
#   keys          -- keys held for the WHOLE frame (pygame key constants)
#   mouse_buttons -- mouse buttons held for the WHOLE frame (0=LMB, 2=RMB)
#   is_boss       -- build the runtime in boss mode (GOLIATH) or in gameplay
#
# `mine_open` runs 403 ticks, not the 300 of the original brief: the
# MINE-ASTEROID only crosses OPENING_Y_THRESHOLD (y >= 120) at tick 378 and
# needs the 0.6 s closed -> open1 -> open2 -> open3 sequence to reach its
# terminal `open3` state, which it does at tick 403. At 300 ticks the mine
# was still `closed`, so the frame would not have shown what its name
# promises.
FRAMES: tuple[Frame, ...] = (
    ("enemies", 180, (pygame.K_LEFT, pygame.K_a), (), False),
    ("boss", 240, (pygame.K_RIGHT,), (), True),
    ("mine_open", 403, (pygame.K_UP, pygame.K_a), (), False),
    ("firing", 360, (pygame.K_a,), (2,), False),
    ("hud", 420, (pygame.K_d,), (), False),
)

# The scripted input state. The runtime reads the keyboard snapshot and the
# mouse snapshot once per update, so both live here and are mutated in
# place between updates.
_KEY_STATE: dict[int, bool] = {}
_MOUSE_STATE: list[bool] = [False, False, False]


class HarnessError(RuntimeError):
    """A guarantee of the harness was violated.

    Every one of these aborts the run with exit code 1: a check that cannot
    fail is not a check.
    """


class _ScriptedKeys:
    """Duck-type of the snapshot `pygame.key.get_pressed()` returns.

    pygame 2 has no `set_pressed`, so the harness scripts the producer
    instead. `GameplayRuntime._read_input` only indexes it with key
    constants (`keys[pygame.K_a]`), which is exactly what this does.
    """

    def __init__(self, state: dict[int, bool]) -> None:
        self._state = state

    def __getitem__(self, key: int) -> bool:
        return self._state.get(key, False)


class _ScriptedMouse:
    """Duck-type of the snapshot `pygame.mouse.get_pressed()` returns.

    The runtime reads index 0 (LMB, charge shot) and index 2 (RMB, rapid
    fire).
    """

    def __init__(self, state: list[bool]) -> None:
        self._state = state

    def __getitem__(self, index: int) -> bool:
        return self._state[index]


_KEYS = _ScriptedKeys(_KEY_STATE)
_MOUSE = _ScriptedMouse(_MOUSE_STATE)


def _install_scripted_input() -> None:
    """Route the runtime's input snapshot to the scripted state.

    `pygame.mouse.get_pos()` is pinned to the middle of the playfield: the
    dummy video driver reports (0, 0), which would aim the ship at the
    top-left corner. The runtime's own headless fallback uses the centre
    too (gameplay_runtime.py:786-791).
    """
    setattr(pygame.key, "get_pressed", lambda: _KEYS)
    setattr(pygame.mouse, "get_pressed", lambda: _MOUSE)
    setattr(pygame.mouse, "get_pos", lambda: (INTERNAL_W // 2, INTERNAL_H // 2))


def _select_frames(only: str | None) -> list[Frame]:
    """The frames to capture, or an error if `only` names no frame.

    An unknown name is an ERROR, not an empty set: a check over zero
    frames has nothing to say and would pass by default.
    """
    known = sorted(name for name, _ticks, _k, _m, _b in FRAMES)
    if only is None:
        return list(FRAMES)
    if only not in known:
        raise HarnessError(
            f"unknown frame name {only!r}; the known frames are: {', '.join(known)}"
        )
    return [frame for frame in FRAMES if frame[0] == only]


def _assert_fresh_scene(
    scene: GameplayRuntime, name: str, used: list[tuple[str, GameplayRuntime]]
) -> None:
    """Fail loudly if a scene object is used for two frames.

    The scene is REBUILT for every capture: a reused scene keeps its RNG
    state and its entity positions, so the frames would be rendered from a
    CONTINUED world. That guarantee is enforced here, not left to a
    comment -- a check that cannot see a violation is a hypothesis.
    """
    for previous_name, previous_scene in used:
        if previous_scene is scene:
            raise HarnessError(
                f"the scene of the frame {previous_name!r} was REUSED for the frame "
                f"{name!r}: the scene must be rebuilt for every capture"
            )


def _build_scene(is_boss: bool) -> GameplayRuntime:
    """A fresh gameplay runtime, with the global RNG seeded.

    `transition_to` is a no-op: the harness never leaves the scene.
    `audio=None` keeps the runtime muted, so no sound device is needed.
    """
    random.seed(SEED)
    pygame.event.clear()
    scene = GameplayRuntime(
        lambda *args, **kwargs: None, is_boss=is_boss, act=1, audio=None
    )
    scene.on_enter()
    return scene


def _press(keys: tuple[int, ...], mouse_buttons: tuple[int, ...]) -> None:
    _KEY_STATE.clear()
    for key in keys:
        _KEY_STATE[key] = True
    _MOUSE_STATE[:] = [False, False, False]
    for button in mouse_buttons:
        _MOUSE_STATE[button] = True


def _release() -> None:
    _KEY_STATE.clear()
    _MOUSE_STATE[:] = [False, False, False]


def capture(out_dir: Path, only: str | None = None) -> dict[str, str]:
    """Capture the frames and return {name: md5}."""
    frames = _select_frames(only)
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    _install_scripted_input()
    out_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    used_scenes: list[tuple[str, GameplayRuntime]] = []
    for name, ticks, keys, mouse_buttons, is_boss in frames:
        scene = _build_scene(is_boss)
        _assert_fresh_scene(scene, name, used_scenes)
        used_scenes.append((name, scene))
        target = pygame.Surface((INTERNAL_W, INTERNAL_H))
        for _tick in range(ticks):
            _press(keys, mouse_buttons)
            scene.update(DT)
            _release()
        # The scene is DRAWN EXACTLY ONCE. A draw mutates the scene
        # (`_draw_engine_flame` emits a spark with `random.random()` DURING
        # the draw), so rendering the same scene twice yields two
        # DIFFERENT frames -- the frame would not be reproducible.
        scene.draw(target)
        path = out_dir / f"{name}.png"
        pygame.image.save(target, str(path))
        digests[name] = hashlib.md5(path.read_bytes()).hexdigest()
    return digests


def _rgba(path: Path) -> bytes:
    """The pixels of a PNG as raw RGBA bytes.

    A golden that cannot be read is a divergence too, so the failure is
    reported instead of raised.
    """
    try:
        surface = pygame.image.load(str(path))
    except (pygame.error, OSError) as exc:
        raise HarnessError(f"the committed golden {path} could not be read: {exc}") from exc
    return pygame.image.tostring(surface, "RGBA")


def _pixel_diff(left: bytes, right: bytes) -> int:
    """The number of differing pixels between two RGBA byte strings."""
    return sum(
        1 for i in range(0, min(len(left), len(right)), 4) if left[i:i + 4] != right[i:i + 4]
    )


def _check(only: str | None, golden_dir: Path) -> int:
    """Capture twice, compare the captures and the committed goldens."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        first = capture(Path(tmp) / "first", only)
        second = capture(Path(tmp) / "second", only)
        captured = Path(tmp) / "first"
        if not first:
            print("ERROR: nothing was captured: a check over zero frames cannot fail")
            return 1

        drifted = {k: (first[k], second[k]) for k in first if first[k] != second[k]}
        if drifted:
            print("NOT REPRODUCIBLE:")
            for name, (a, b) in drifted.items():
                print(f"  {name}: {a} != {b}")
            return 1
        print("REPRODUCIBLE:", ", ".join(sorted(first)))

        # The committed golden frames. Two captures inside ONE process are
        # identical even when the nondeterminism is per-process (a
        # module-level `random.random()`, a PYTHONHASHSEED-dependent
        # order). The committed frame is the property that matters: it is
        # what Task 4 asserts pixel-by-pixel.
        #
        # A MISSING golden set is a FAILURE, never a pass. Skipping the
        # comparison would leave the weaker intra-process check -- the one
        # this comparison exists to replace -- and the Phase 2 gate (P2-G2)
        # would go green with ZERO proof fixtures.
        if not golden_dir.is_dir():
            print(
                f"GOLDENS MISSING: {golden_dir} does not exist: "
                "the committed proof fixtures are missing"
            )
            return 1
        diverged: list[str] = []
        for name, digest in sorted(first.items()):
            golden_path = golden_dir / f"{name}.png"
            if not golden_path.is_file():
                diverged.append(
                    f"  {name}: there is no committed golden frame to compare against"
                )
                continue
            golden_digest = hashlib.md5(golden_path.read_bytes()).hexdigest()
            golden_pixels = _rgba(golden_path)
            captured_pixels = _rgba(captured / f"{name}.png")
            if golden_pixels != captured_pixels:
                differ = _pixel_diff(golden_pixels, captured_pixels)
                diverged.append(
                    f"  {name}: the captured frame differs from the committed one "
                    f"({differ} pixels differ)"
                )
            elif golden_digest != digest:
                print(f"NOTE: {name}: the pixels match but the bytes differ (the PNG encoder)")
        # The proof set cannot SHRINK silently. The comparison walks the
        # CAPTURED frames, so a committed golden with no capture (a frame
        # dropped from the FRAMES table) would never be looked at. The two
        # sets have to be the same set: a capture with no golden is already
        # reported above, and a golden with no capture is reported here.
        committed = {path.stem for path in golden_dir.glob("*.png")}
        for name in sorted(committed - set(first)):
            diverged.append(
                f"  {name}: there is a committed golden frame with no capture "
                "to compare against"
            )
        if diverged:
            print("GOLDEN DIVERGED:")
            for line in diverged:
                print(line)
            return 1
        print("GOLDENS MATCH:", ", ".join(sorted(first)))
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=GOLDEN_DIR)
    parser.add_argument("--only", default=None, help="capture a single frame by name")
    parser.add_argument(
        "--golden",
        type=Path,
        default=GOLDEN_DIR,
        help="the committed golden frames the capture is compared against",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="capture twice and fail if the bytes differ",
    )
    args = parser.parse_args(argv)

    try:
        if args.check:
            return _check(args.only, args.golden)
        digests = capture(args.out, args.only)
    except HarnessError as exc:
        print(f"ERROR: {exc}")
        return 1
    if not digests:
        print("ERROR: nothing was captured")
        return 1
    for name, digest in sorted(digests.items()):
        print(f"{name}: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
