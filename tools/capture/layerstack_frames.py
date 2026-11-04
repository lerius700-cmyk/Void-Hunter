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
  5. The proof set cannot SHRINK silently: a committed golden whose frame
     is GONE from the FRAMES table is reported, not ignored. The reference
     is the FRAMES TABLE, not the captured subset -- comparing against the
     captured subset would report every unselected golden as an orphan
     and `--only` could never be used.
  6. The proof fixtures cannot be DESTROYED by accident: the default
     `--out` is a scratch directory outside the repository, so a bare
     capture cannot rewrite the committed proof. Rewriting it takes an
     explicit `--out tools/golden/layerstack`, and the harness says so
     out loud when it happens.

The scene is DRAWN EXACTLY ONCE per capture: a draw mutates the scene
(`_draw_engine_flame` emits a spark with `random.random()` DURING the
draw), so rendering the same scene twice yields two different frames.

THE SHAKE. Five of the six frames have a screen shake that truncates to
(0, 0): the layers that consume the shake are never moved, so a
regression in the shake plumbing would leave all five identical. The
sixth frame (`shake`) forces the runtime's trauma so the INTEGER shake
is (8, 8), and it is the frame that proves the shake travels through
the stack exactly once.

Usage:
    python tools/capture/layerstack_frames.py
        captures into the SCRATCH directory (the default `--out`), never
        into the committed proof;
    python tools/capture/layerstack_frames.py --out tools/golden/layerstack
        REWRITES the committed proof -- the only way to do it, and the
        harness warns about it;
    python tools/capture/layerstack_frames.py --check
        compares the fresh capture against the committed proof;
    python tools/capture/layerstack_frames.py --check --only enemies
        compares ONE frame against the committed proof;
    python tools/capture/layerstack_frames.py --check --shake  (diagnostic:
        forces the shake on EVERY frame, so the five non-shake goldens
        report as diverged -- that is the point of the flag)
"""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import hashlib
import random
import sys
import tempfile
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

# The default `--out`: a SCRATCH directory OUTSIDE the repository. The
# proof fixtures must not be rewritable by a stray capture -- the default
# `--out` used to be GOLDEN_DIR, so a bare
# `python tools/capture/layerstack_frames.py` silently OVERWROTE the
# committed proof with a fresh capture. The proof is now rewritten only on
# purpose: `--out tools/golden/layerstack`.
SCRATCH_DIR = Path(tempfile.gettempdir()) / "void-hunter" / "layerstack_capture"

# (name, ticks, keys, mouse_buttons, is_boss, shake)
Frame: TypeAlias = tuple[str, int, tuple[int, ...], tuple[int, ...], bool, bool]

# The six frames the proof needs: enemies on screen, the boss, the mine in
# its open3 state, the player firing, the HUD populated, and one frame
# with the screen shake forced.
#
# Each entry is (name, ticks, keys, mouse_buttons, is_boss, shake):
#   ticks         -- fixed 60 Hz steps advanced before the capture
#   keys          -- keys held for the WHOLE frame (pygame key constants)
#   mouse_buttons -- mouse buttons held for the WHOLE frame (0=LMB, 2=RMB)
#   is_boss       -- build the runtime in boss mode (GOLIATH) or in gameplay
#   shake         -- force the screen shake to a non-zero integer offset
#
# `mine_open` runs 403 ticks, not the 300 of the original brief: the
# MINE-ASTEROID only crosses OPENING_Y_THRESHOLD (y >= 120) at tick 378 and
# needs the 0.6 s closed -> open1 -> open2 -> open3 sequence to reach its
# terminal `open3` state, which it does at tick 403. At 300 ticks the mine
# was still `closed`, so the frame would not have shown what its name
# promises.
#
# `shake` is the `firing` scene WITH the shake forced: the same tick
# discipline, so the difference between the two frames is exactly the
# shake. It is captured from the runtime that still draws INLINE -- a
# golden captured after the LayerStack existed would compare the stack
# against itself, and the proof would be vacuous.
FRAMES: tuple[Frame, ...] = (
    ("enemies", 180, (pygame.K_LEFT, pygame.K_a), (), False, False),
    ("boss", 240, (pygame.K_RIGHT,), (), True, False),
    ("mine_open", 403, (pygame.K_UP, pygame.K_a), (), False, False),
    ("firing", 360, (pygame.K_a,), (2,), False, False),
    ("hud", 420, (pygame.K_d,), (), False, False),
    ("shake", 360, (pygame.K_a,), (2,), False, True),
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
    known = sorted(name for name, _ticks, _k, _m, _b, _s in FRAMES)
    if only is None:
        return list(FRAMES)
    if only not in known:
        raise HarnessError(
            f"unknown frame name {only!r}; the known frames are: {', '.join(known)}"
        )
    return [frame for frame in FRAMES if frame[0] == only]


def _force_shake(scene: GameplayRuntime) -> None:
    """Force the runtime's screen shake to a non-zero INTEGER offset.

    The shake is the Eiserloh trauma^2 model (`src/systems/screen_shake.py`):
    `offset = max_px * trauma^2 * noise`. The trauma alone is not enough --
    the noise is what gives the offset its SIGN and its MAGNITUDE, and it
    is refreshed by `ScreenShake.update()` on every runtime tick.

    So the harness pins all three: trauma 1.0, noise (1.0, 1.0) and the
    production `max_px` of 8.0. The offset is then (8.0, 8.0) and the
    runtime's `int()` truncation keeps it at (8, 8) -- the same shake the
    Task 1 review measured.

    The state is set AFTER the last tick: `GameplayRuntime.update()` calls
    `ScreenShake.update()`, which would decay the trauma and re-roll the
    noise.
    """
    shake = scene._shake
    shake.trauma = 1.0
    shake._noise_x = 1.0
    shake._noise_y = 1.0


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


def capture(out_dir: Path, only: str | None = None, force_shake: bool = False) -> dict[str, str]:
    """Capture the frames and return {name: md5}."""
    frames = _select_frames(only)
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    _install_scripted_input()
    out_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    used_scenes: list[tuple[str, GameplayRuntime]] = []
    for name, ticks, keys, mouse_buttons, is_boss, shake in frames:
        scene = _build_scene(is_boss)
        _assert_fresh_scene(scene, name, used_scenes)
        used_scenes.append((name, scene))
        target = pygame.Surface((INTERNAL_W, INTERNAL_H))
        for _tick in range(ticks):
            _press(keys, mouse_buttons)
            scene.update(DT)
            _release()
        if shake or force_shake:
            _force_shake(scene)
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


def _check(only: str | None, golden_dir: Path, force_shake: bool = False) -> int:
    """Capture twice, compare the captures and the committed goldens."""
    with tempfile.TemporaryDirectory() as tmp:
        first = capture(Path(tmp) / "first", only, force_shake)
        second = capture(Path(tmp) / "second", only, force_shake)
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
        # The proof set cannot SHRINK silently. A committed golden whose
        # frame is GONE from the FRAMES table would never be looked at, so
        # the committed set is compared against the FRAMES TABLE -- NOT
        # against the captured subset. Comparing against the captured
        # subset would make `--only` illegal: every golden that was not
        # selected would be reported as an orphan and the check could
        # never run over a single frame.
        #
        # The other direction is already covered above: a CAPTURED frame
        # with no committed golden is reported as a divergence.
        frame_names = {frame[0] for frame in FRAMES}
        committed = {path.stem for path in golden_dir.glob("*.png")}
        for name in sorted(committed - frame_names):
            diverged.append(
                f"  {name}: there is a committed golden frame with no capture "
                "to compare against (the frame is gone from the FRAMES table)"
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
    parser.add_argument(
        "--out",
        type=Path,
        default=SCRATCH_DIR,
        help=(
            "where the captured frames are written; the default is a SCRATCH "
            "directory outside the repository, so a bare capture can never "
            "rewrite the committed proof (pass --out tools/golden/layerstack "
            "to rewrite it on purpose)"
        ),
    )
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
    parser.add_argument(
        "--shake",
        action="store_true",
        help=(
            "force the screen shake to (8, 8) on EVERY frame, not only on the "
            "frames whose entry asks for it (diagnostic)"
        ),
    )
    args = parser.parse_args(argv)

    try:
        if args.check:
            return _check(args.only, args.golden, args.shake)
        if args.out.resolve() == GOLDEN_DIR.resolve():
            print(
                f"WARNING: rewriting the committed proof fixtures in {args.out} "
                "-- this is the only way to do it, and it is on purpose"
            )
        digests = capture(args.out, args.only, args.shake)
    except HarnessError as exc:
        print(f"ERROR: {exc}")
        return 1
    if not digests:
        print("ERROR: nothing was captured")
        return 1
    for name, digest in sorted(digests.items()):
        print(f"{name}: {digest}")
    print(f"frames written to: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
