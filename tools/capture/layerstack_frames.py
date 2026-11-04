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

import pygame

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.core.settings import INTERNAL_H, INTERNAL_W  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime  # noqa: E402

SEED = 20261103
DT = 1.0 / 60.0

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
FRAMES: tuple[tuple[str, int, tuple[int, ...], tuple[int, ...], bool], ...] = (
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
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    _install_scripted_input()
    out_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    for name, ticks, keys, mouse_buttons, is_boss in FRAMES:
        if only is not None and only != name:
            continue
        scene = _build_scene(is_boss)
        target = pygame.Surface((INTERNAL_W, INTERNAL_H))
        for tick in range(ticks):
            _press(keys, mouse_buttons)
            scene.update(DT)
            _release()
            if tick == ticks - 1:
                scene.draw(target)
        path = out_dir / f"{name}.png"
        pygame.image.save(target, str(path))
        digests[name] = hashlib.md5(path.read_bytes()).hexdigest()
    return digests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "tools" / "golden" / "layerstack")
    parser.add_argument("--only", default=None, help="capture a single frame by name")
    parser.add_argument(
        "--check",
        action="store_true",
        help="capture twice and fail if the bytes differ",
    )
    args = parser.parse_args()

    if args.check:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            first = capture(Path(tmp) / "first", args.only)
            second = capture(Path(tmp) / "second", args.only)
        drifted = {k: (first[k], second[k]) for k in first if first[k] != second[k]}
        if drifted:
            print("NOT REPRODUCIBLE:")
            for name, (a, b) in drifted.items():
                print(f"  {name}: {a} != {b}")
            return 1
        print("REPRODUCIBLE:", ", ".join(sorted(first)))
        return 0

    digests = capture(args.out, args.only)
    for name, digest in sorted(digests.items()):
        print(f"{name}: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
