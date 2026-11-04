"""BLOQUE 75 (fix round 1): the flash fallback must draw the BODY.

`src/ui/gameplay_runtime.py::_draw_enemy_scaled` draws the enemy body
through the COMPOSITOR. When the compositor cannot draw it -- a missing
or malformed manifest, a missing anchor table, an absent clip, a
missing frame PNG -- the runtime falls back to its own blit. That
fallback body blit sat in the `elif` of the flash test, so a FLASHING
enemy on that path rendered as a flat translucent silhouette with NO
body under it: only the 70% white wash, floating on the playfield.

NOTHING in the repo could see it:

  * the golden frames never reach the fallback -- all eight enemy sets
    load, every clip and frame exists, and `build.spec` bundles
    `Assets/sprites` wholesale;
  * no test forced the pipeline to fail.

So this file is the test that CAN: it forces the pipeline to return
None (the reviewer's Mutation A), flashes the enemy, and looks at the
COLOURS that reach the target. A flat silhouette has ONE colour; a
body under a white wash carries the body's own palette.
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

from src.core.settings import HIT_FLASH_OPACITY
from src.entities.enemies.enemy import EnemyKind
from src.ui.gameplay_runtime import GameplayRuntime


@pytest.fixture(scope="module")
def display():
    """A video mode: `Surface.convert_alpha()` needs one."""
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _runtime_with_one_enemy():
    """A runtime holding exactly ONE active enemy, and that enemy.

    The enemy is spawned through the pool (so it is `active` and in
    `pool`, which is what `_draw_enemy_pass` iterates) and posed by
    hand: the pipeline must draw the frame the ENTITY holds.
    """
    runtime = GameplayRuntime(
        lambda *args, **kwargs: None, is_boss=False, act=1, audio=None
    )
    enemy = runtime._enemies.spawn(EnemyKind("scout"), 120, 200)
    assert enemy is not None
    enemy.animation_state = "idle"
    enemy.animation_frame = 0
    return runtime, enemy


def _break_the_pipeline(monkeypatch) -> None:
    """The pipeline cannot draw this enemy (Mutation A of the review).

    This is the ERROR PATH the fallback exists to serve: the set could
    not be loaded, the clip is absent, the frame PNG is missing. The
    runtime has to draw the body the old way.
    """
    monkeypatch.setattr(
        GameplayRuntime,
        "_draw_enemy_body_via_pipeline",
        lambda self, *args, **kwargs: None,
    )


def _drawn_colours(surface: pygame.Surface) -> dict[tuple[int, int, int], int]:
    """The colours the surface actually shows, and how many pixels each.

    The target starts BLACK, so black is "nothing was drawn here".
    """
    colours: dict[tuple[int, int, int], int] = {}
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            rgb = tuple(surface.get_at((x, y))[:3])
            if rgb == (0, 0, 0):
                continue
            colours[rgb] = colours.get(rgb, 0) + 1
    return colours


def _wash_colour() -> tuple[int, int, int]:
    """The colour a lone white wash leaves on black.

    The overlay is white at `sprite_alpha * HIT_FLASH_OPACITY`, so a
    fully opaque pixel of the body becomes `255 * HIT_FLASH_OPACITY`.
    """
    grey = int(255 * HIT_FLASH_OPACITY)
    return (grey, grey, grey)


def test_the_flash_fallback_draws_the_body_under_the_overlay(display, monkeypatch):
    """A flashing enemy on the fallback path must carry the BODY.

    The discriminator: with the body missing, EVERY drawn pixel is the
    flat white wash (one single colour). With the body under the wash,
    the frame carries the body's own palette, tinted.
    """
    _break_the_pipeline(monkeypatch)
    runtime, enemy = _runtime_with_one_enemy()
    enemy.hit_timer = 0.1  # the white damage flash

    target = pygame.Surface((320, 480))
    runtime._draw_enemy_pass(target, 0, 0)

    colours = _drawn_colours(target)
    assert colours, "nothing at all was drawn: the flash overlay is missing too"

    wash = _wash_colour()
    washed = set(colours)
    assert washed - {wash}, (
        f"the flashing enemy is a flat overlay silhouette: every drawn "
        f"pixel is the white wash {wash}, so the BODY is missing -- the "
        f"fallback body blit never ran (colours: {sorted(washed)})"
    )


def test_the_flash_fallback_draws_exactly_what_the_pipeline_would_draw(
    display, monkeypatch
):
    """The fallback must render the SAME frame as the pipeline.

    The fallback exists to stand in for the pipeline. When the pipeline
    is forced to fail, the frame must not change: the same body, under
    the same overlay, at the same place.
    """
    pipeline_target = pygame.Surface((320, 480))
    runtime, enemy = _runtime_with_one_enemy()
    enemy.hit_timer = 0.1
    runtime._draw_enemy_pass(pipeline_target, 0, 0)
    assert _drawn_colours(pipeline_target), (
        "the pipeline drew nothing: the comparison below would be vacuous"
    )

    _break_the_pipeline(monkeypatch)
    fallback_target = pygame.Surface((320, 480))
    runtime2, enemy2 = _runtime_with_one_enemy()
    enemy2.hit_timer = 0.1
    runtime2._draw_enemy_pass(fallback_target, 0, 0)

    drawn = pygame.image.tostring(pipeline_target, "RGBA")
    fallback = pygame.image.tostring(fallback_target, "RGBA")
    differing = sum(1 for a, b in zip(drawn, fallback) if a != b) // 4
    assert differing == 0, (
        f"the fallback drew a DIFFERENT frame than the pipeline: "
        f"{differing} differing pixels. The body is missing under the "
        f"flash overlay (fallback colours: "
        f"{sorted(_drawn_colours(fallback_target))})"
    )


def test_the_plain_fallback_still_draws_the_body(display, monkeypatch):
    """The NON-flash fallback is untouched by the fix -- and pinned.

    The fix moved the body blit INTO the flash branch; the `elif`
    branch (no flash) still draws it, and it must keep doing so.
    """
    _break_the_pipeline(monkeypatch)
    runtime, enemy = _runtime_with_one_enemy()

    target = pygame.Surface((320, 480))
    runtime._draw_enemy_pass(target, 0, 0)

    colours = _drawn_colours(target)
    assert colours, "the fallback drew nothing at all"
    assert set(colours) != {_wash_colour()}, (
        "the fallback drew only the white wash: the body is missing"
    )
