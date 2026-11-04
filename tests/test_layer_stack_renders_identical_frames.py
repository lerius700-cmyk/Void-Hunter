"""BLOQUE 75 Fase 2: the proof. The frame must not change by a pixel.

The golden frames were captured from the runtime BEFORE the LayerStack
existed (Task 1). After the refactor, every one of them must be
PIXEL-IDENTICAL. This is the only thing that proves checkpoint 2A: the
frame loop was reorganised into layers without changing what is drawn.

The sixth frame (`shake`) is the one the five originals could NOT prove:
their screen shake truncates to (0, 0), so the layers that consume the
shake were never exercised by the committed set. A regression in the
shake plumbing would have left all of them identical.

THE GOLDEN FRAMES ARE BLIND TO THE PATH. "0 pixels moved" proves the
PICTURE, not the CODE: a runtime that never calls the compositor draws
exactly the same pixels. So checkpoint 2B (the enemy bodies drawn by the
compositor) needs a SECOND proof -- one that spies on the compositor and
asserts it was called, with the right clip and the right frame, and that
the body is not blitted twice. Those tests live at the bottom of this
file: this file owns the proof of "the pipeline is the pipeline now".
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
GOLDEN = ROOT / "tools" / "golden" / "layerstack"
HARNESS = ROOT / "tools" / "capture" / "layerstack_frames.py"


@pytest.fixture(scope="module")
def display():
    """A video mode: `Surface.convert_alpha()` needs one.

    The comparison is done in THIS process, so the frame has to be
    loadable here -- and loading it with an alpha channel needs the
    display format, which needs an initialized video mode.
    """
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.mark.parametrize(
    "name",
    ("enemies", "boss", "mine_open", "firing", "hud", "shake"),
)
def test_the_frame_is_pixel_identical(tmp_path, name, display):
    if not (GOLDEN / f"{name}.png").is_file():
        pytest.skip(f"no golden frame for {name}")
    proc = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--out",
            str(tmp_path),
            "--only",
            name,
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    golden = pygame_pixels(GOLDEN / f"{name}.png")
    current = pygame_pixels(tmp_path / f"{name}.png")
    assert golden == current, (
        f"{name}: the frame changed -- "
        f"{sum(1 for a, b in zip(golden, current) if a != b)} differing pixels"
    )


def pygame_pixels(path: Path):
    """The frame's pixels as a flat tuple of RGB triples."""
    surf = pygame.image.load(str(path)).convert_alpha()
    return tuple(surf.get_at((x, y))[:3] for y in range(surf.get_height())
                 for x in range(surf.get_width()))


# ---------------------------------------------------------------------------
# BLOQUE 75 (Task 8): the SECOND proof. The pipeline is actually used.
#
# These tests live HERE, and not in a file of their own, because this file
# owns the proof of checkpoint 2B: the golden frames above prove the
# PICTURE did not move, and the tests below prove the PATH changed. A
# checkpoint whose only proof is the picture is a hypothesis.
# ---------------------------------------------------------------------------


def _runtime_with_one_enemy(kind: str, *, x: float = 120.0, y: float = 200.0):
    """A runtime holding exactly ONE active enemy, and that enemy.

    The enemy is spawned through the pool (so it is `active` and in
    `pool`, which is what `_draw_enemy_pass` iterates) and then posed by
    hand: the pipeline must draw the frame the ENTITY holds, not one the
    pipeline re-derives.
    """
    from src.entities.enemies.enemy import EnemyKind
    from src.ui.gameplay_runtime import GameplayRuntime

    runtime = GameplayRuntime(
        lambda *args, **kwargs: None, is_boss=False, act=1, audio=None
    )
    enemy = runtime._enemies.spawn(EnemyKind(kind), x, y)
    assert enemy is not None
    return runtime, enemy


def _spy_on_the_compositor(monkeypatch):
    """Record every call the runtime makes into the compositor.

    Two spies, because they answer two different questions:

      * `ClipPlayer.draw` -- WHICH clip and WHICH frame the runtime asked
        for (the clip id and the frame index are arguments of the call);
      * `clip.draw_part` -- WHICH part was drawn and WHICH surface was
        blitted (the compositor's own entry point into the target).

    Both call the real implementation: the spies OBSERVE, they do not
    replace the drawing.
    """
    from src.anim import clip as anim_clip
    from src.anim.clip import ClipPlayer

    draws: list[tuple[str, int, tuple[int, int], tuple[str, ...] | None]] = []
    parts: list[tuple[str, object, object, tuple[int, int]]] = []

    real_draw = ClipPlayer.draw
    real_draw_part = anim_clip.draw_part

    def spy_draw(self, target, clip_id, frame, origin, part_ids=None):
        draws.append((clip_id, frame, origin, part_ids))
        return real_draw(self, target, clip_id, frame, origin, part_ids)

    def spy_draw_part(target, part, surf, anchor, origin, canvas):
        parts.append((part.id, surf, origin, canvas))
        return real_draw_part(target, part, surf, anchor, origin, canvas)

    monkeypatch.setattr(ClipPlayer, "draw", spy_draw)
    monkeypatch.setattr(anim_clip, "draw_part", spy_draw_part)
    return draws, parts


class _SpySurface(pygame.Surface):
    """A surface that records every blit INTO it.

    `pygame.Surface` is an immutable C type, so `blit` cannot be patched
    on the class -- but it CAN be subclassed, and a subclass carries a
    `__dict__` where the record lives. The target itself is the spy, so
    the record cannot miss a blit that goes through another surface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blits: list[object] = []

    def blit(self, source, dest, *args, **kwargs):
        self.blits.append(source)
        return super().blit(source, dest, *args, **kwargs)


def test_the_enemy_body_goes_through_the_compositor(display, monkeypatch):
    """The compositor must draw the enemy BODY (checkpoint 2B).

    The golden frames cannot see this: a runtime that never calls the
    compositor draws exactly the same pixels. So the pipeline is spied
    on directly, and it must be called with the enemy's OWN clip and
    frame -- the runtime keeps counting, the pipeline never re-derives.
    """
    runtime, enemy = _runtime_with_one_enemy("scout")
    enemy.animation_state = "thrust"
    enemy.animation_frame = 3
    draws, parts = _spy_on_the_compositor(monkeypatch)

    target = pygame.Surface((320, 480))
    runtime._draw_enemy_pass(target, 0, 0)

    assert draws, (
        "the compositor was NEVER called: the enemy body did not go "
        "through the pipeline (the golden frames cannot see this)"
    )
    assert draws == [("thrust", 3, (120, 200), ("body",))], (
        f"the compositor was called with {draws}: the clip id and the "
        "frame must be the enemy's own"
    )
    assert [part[0] for part in parts] == ["body"]
    assert parts[0][2] == (120, 200), (
        "the origin must be the enemy's position with the shake applied"
    )


def test_the_mine_states_map_to_their_own_clips(display, monkeypatch):
    """The mine's FOUR states are four clips, and each picks its frame.

    The mine is the special case: its `closed` state holds FIVE
    VARIANTS (the frame is the variant, clamped to 0..4) and the `open*`
    states are single frames. The mine's `animation_state` is NOT used:
    `Enemy.animation_path` ignores it too.
    """
    cases = (
        ("closed", 3, "closed", 3),
        ("open1", 0, "open1", 0),
        ("open2", 0, "open2", 0),
        ("open3", 0, "open3", 0),
    )
    # The spies are installed ONCE: re-installing them inside the loop
    # would chain spy over spy.
    draws, _parts = _spy_on_the_compositor(monkeypatch)
    for mine_state, variant, expected_clip, expected_frame in cases:
        draws.clear()
        runtime, enemy = _runtime_with_one_enemy("mine_asteroid")
        enemy.mine_state = mine_state
        enemy.mine_variant = variant

        target = pygame.Surface((320, 480))
        runtime._draw_enemy_pass(target, 0, 0)

        assert draws == [(expected_clip, expected_frame, (120, 200), ("body",))], (
            f"the mine in state {mine_state!r} (variant {variant}) was drawn "
            f"with {draws}, not with ({expected_clip!r}, {expected_frame})"
        )


def test_the_flash_draws_the_overlay_and_not_the_body_twice(display, monkeypatch):
    """The flash is an OVERLAY: the body is drawn ONCE.

    The body is the compositor's job now. If the runtime ALSO blitted
    it, every flashed enemy would be brighter than it should be (the
    semi-transparent pixels are blended twice) and the golden frames
    would move. So the number of blits into the target is pinned: ONE
    body (from the compositor) and ONE overlay (from the runtime).
    """
    runtime, enemy = _runtime_with_one_enemy("scout")
    enemy.animation_state = "idle"
    enemy.animation_frame = 0
    enemy.hit_timer = 0.1  # the white damage flash

    target = _SpySurface((320, 480))
    draws, _parts = _spy_on_the_compositor(monkeypatch)

    runtime._draw_enemy_pass(target, 0, 0)

    assert len(draws) == 1, (
        f"the compositor was called {len(draws)} times for ONE enemy"
    )
    assert len(target.blits) == 2, (
        f"the target received {len(target.blits)} blits, expected 2 (the body "
        "from the compositor + the flash overlay): the body is drawn TWICE"
    )


def test_the_flash_overlay_is_still_drawn(display, monkeypatch):
    """The flash must still be VISIBLE: the overlay is on top of the body.

    The previous test pins HOW MANY blits; this one pins that the white
    wash is really there -- a runtime that drew only the body would pass
    the count and show no hit feedback at all.
    """
    plain = pygame.Surface((320, 480))
    runtime, enemy = _runtime_with_one_enemy("scout")
    enemy.animation_state = "idle"
    enemy.animation_frame = 0
    runtime._draw_enemy_pass(plain, 0, 0)

    flashing = pygame.Surface((320, 480))
    runtime2, enemy2 = _runtime_with_one_enemy("scout")
    enemy2.animation_state = "idle"
    enemy2.animation_frame = 0
    enemy2.hit_timer = 0.1
    runtime2._draw_enemy_pass(flashing, 0, 0)

    plain_pixels = pygame.image.tostring(plain, "RGBA")
    flash_pixels = pygame.image.tostring(flashing, "RGBA")
    assert plain_pixels != flash_pixels, (
        "the flashing enemy looks exactly like the plain one: the white "
        "overlay is not being drawn"
    )
