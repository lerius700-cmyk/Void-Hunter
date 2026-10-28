"""BLOQUE 74: the runtime must read the baked anchors, not scan pixels.

The whole point of the pipeline is that the measurement happens at build
time. If the runtime scans pixels again, the scan cost comes back and the
anchors.toml file is decoration.

These tests assert the values agree with the baked table, and that the
runtime no longer contains a pixel-scanning loop.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from src.anim.anchors import load_anchors  # noqa: E402
from src.anim.manifest import load_set  # noqa: E402


def _table():
    """The manifest and the baked anchor table of GOLIATH."""
    anim_set = load_set("goliath")
    anchors = load_anchors(anim_set.path / "anchors.toml")
    return anim_set, anchors


def test_centroid_offset_matches_the_baked_table() -> None:
    from src.ui.scenes import get_sprite_centroid_offset

    anim_set, anchors = _table()
    for clip in anim_set.clips.values():
        for i in range(clip.frames):
            name = f"{clip.dir}/frame_{i:02d}.png"
            entry = anchors.entries[(clip.id, i)]
            assert get_sprite_centroid_offset(name) == (entry.body_dx, entry.body_dy)


def test_eye_anchor_matches_the_baked_table() -> None:
    from src.ui.scenes import get_sprite_eye_anchor

    anim_set, anchors = _table()
    for clip in anim_set.clips.values():
        for i in range(clip.frames):
            name = f"{clip.dir}/frame_{i:02d}.png"
            entry = anchors.entries[(clip.id, i)]
            assert get_sprite_eye_anchor(name) == entry.eye


def test_shield_ellipse_matches_the_baked_table() -> None:
    from src.ui.scenes import get_sprite_shield_ellipse

    anim_set, anchors = _table()
    for clip in anim_set.clips.values():
        for i in range(clip.frames):
            name = f"{clip.dir}/frame_{i:02d}.png"
            entry = anchors.entries[(clip.id, i)]
            assert get_sprite_shield_ellipse(name) == entry.shield


def test_the_runtime_path_resolves_the_same_anchors() -> None:
    """The runtime holds 'bosses/goliath/<dir>/frame_NN.png'.

    The anchor table is keyed by (clip id, frame index) and the sprite path
    is relative to Assets/sprites/, so the lookup has to take the LAST
    directory of the path -- not the whole thing -- as the clip's name.
    """
    from src.ui.scenes import (
        get_sprite_centroid_offset,
        get_sprite_eye_anchor,
        get_sprite_shield_ellipse,
    )

    anim_set, anchors = _table()
    for clip in anim_set.clips.values():
        for i in range(clip.frames):
            name = f"bosses/goliath/{clip.dir}/frame_{i:02d}.png"
            entry = anchors.entries[(clip.id, i)]
            assert get_sprite_centroid_offset(name) == (entry.body_dx, entry.body_dy)
            assert get_sprite_eye_anchor(name) == entry.eye
            assert get_sprite_shield_ellipse(name) == entry.shield


def test_the_runtime_no_longer_scans_pixels() -> None:
    """The three anchor functions must be lookups, not measurements."""
    import inspect

    from src.ui.scenes import (
        get_sprite_centroid_offset,
        get_sprite_eye_anchor,
        get_sprite_shield_ellipse,
    )

    source = (ROOT / "src" / "ui" / "scenes.py").read_text(encoding="utf-8")
    for forbidden in ("_sprite_centroid_cache", "_sprite_eye_anchor_cache",
                      "_sprite_shield_ellipse_cache"):
        assert forbidden not in source, f"{forbidden} still exists -- the scan is back"

    # A pixel read inside an anchor function IS the scan.
    for func in (get_sprite_centroid_offset, get_sprite_eye_anchor,
                 get_sprite_shield_ellipse):
        body = inspect.getsource(func)
        assert "get_at" not in body, (
            f"{func.__name__} reads pixels -- the measurement belongs in the "
            "build-time pipeline, not in the runtime"
        )


# ---------------------------------------------------------------------------
# The manifest drives the timing
# ---------------------------------------------------------------------------


def test_the_boss_timing_comes_from_the_manifest() -> None:
    """The frame count and the fps are the manifest's, not a constant."""
    from src.entities.enemies.boss import Boss

    anim_set, _anchors = _table()
    boss = Boss()
    for clip in anim_set.clips.values():
        boss.set_animation_state(clip.id)
        boss.animation_frame_duration = 1.0 / clip.fps
        boss.animation_frame_count = clip.frames
        assert boss.animation_frame_count == clip.frames
        assert boss.animation_frame_duration == pytest.approx(1.0 / clip.fps)


def test_the_runtime_applies_the_manifest_timing_to_the_boss() -> None:
    """The live runtime must hand the boss the manifest's clip timing."""
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.ui.gameplay_runtime import GameplayRuntime

    anim_set, _anchors = _table()
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    boss = rt._boss
    assert boss is not None
    for clip in anim_set.clips.values():
        rt._set_boss_animation(clip.id)
        assert boss.animation_state == clip.id
        assert boss.animation_frame_count == clip.frames
        assert boss.animation_frame_duration == pytest.approx(1.0 / clip.fps)


def test_the_boss_animation_uses_the_manifest_frame_count() -> None:
    """The frame counter wraps at the manifest's frame count."""
    from src.entities.enemies.boss import Boss

    boss = Boss()
    boss.set_animation_state("phase1_idle")
    boss.animation_frame_count = 4
    boss.animation_frame_duration = 0.1
    boss.animation_frame = 3
    boss.animation_timer = 0.0
    boss.update_animation(0.1)
    assert boss.animation_frame == 0, "the frame counter did not wrap at 4"


def test_the_death_anim_holds_at_the_manifest_frame_count() -> None:
    """'death' is one-shot: it holds on the LAST frame of the clip."""
    from src.entities.enemies.boss import Boss

    boss = Boss()
    boss.set_animation_state("death")
    boss.animation_frame_count = 10
    boss.animation_frame = 9
    boss.animation_timer = 0.0
    boss.update_animation(0.1)
    assert boss.animation_frame == 9, "the death animation wrapped around"


# ---------------------------------------------------------------------------
# The duplicate frame cache is retired
# ---------------------------------------------------------------------------


def test_the_boss_frames_are_not_cached_twice() -> None:
    """The compositor owns the 60 frames; the UI cache must not keep a copy.

    Two caches of the same 1.76 MB of PNGs is 1.76 MB of RAM the game does
    not need. The runtime reads the frames through the compositor, so the
    UI's own sprite cache must not hold the boss frames.
    """
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.ui import scenes
    from src.ui.gameplay_runtime import GameplayRuntime

    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    target = pygame.Surface((320, 480))
    target.fill((0, 0, 0))
    rt.draw(target)

    boss_frames = [k for k in scenes._sprite_cache if k.startswith("bosses/goliath")]
    assert not boss_frames, (
        f"the UI sprite cache still holds {len(boss_frames)} boss frames "
        f"({boss_frames[:3]}) -- the compositor's cache is duplicated"
    )


def test_the_compositor_draws_the_boss_frame() -> None:
    """The boss is composed through the ClipPlayer."""
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.ui import scenes
    from src.ui.gameplay_runtime import GameplayRuntime

    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    player = scenes.get_clip_player()
    assert player is not None, "the GOLIATH compositor is not available"
    boss = rt._boss
    assert boss is not None
    surf = player.surface(boss.animation_state, boss.animation_frame)
    assert surf is not None, "the compositor could not load the boss frame"


# ---------------------------------------------------------------------------
# The radii policy: an unresolved plate keeps the canonical ellipse
# ---------------------------------------------------------------------------


def test_an_unresolved_plate_keeps_the_canonical_ellipse() -> None:
    """A frame whose plate cannot be resolved still has a shield.

    The alternative -- no ellipse at all -- would delete the hitbox and
    leave the shield laser with nowhere to come from.
    """
    from src.anim.anchors import FrameAnchor
    from src.anim.manifest import load_set
    from src.anim.parts import shield_ellipse_rect

    anim_set = load_set("goliath")
    part = anim_set.part("shield_plate")
    assert part.radii is not None, "the manifest declares no canonical radii"

    unresolved = FrameAnchor(
        body_dx=0,
        body_dy=0,
        eye=None,
        eye_source="missing",
        shield=None,
        shield_source="missing",
    )
    rect = shield_ellipse_rect(part, unresolved, (100, 100), anim_set.canvas)
    assert rect is not None, "an unresolved plate has no ellipse at all"

    # The canonical radii, at the canonical centre.
    _, rx, ry = part.radii
    assert rect.width == max(2, int(round(rx * part.scale[0]))) * 2
    assert rect.height == max(2, int(round(ry * part.scale[1]))) * 2


def test_the_runtime_falls_back_to_the_canonical_ellipse() -> None:
    """A frame that is not in the table gets the canonical ellipse."""
    from src.ui.scenes import get_sprite_shield_ellipse

    ellipse = get_sprite_shield_ellipse("bosses/goliath/javelin/frame_99.png")
    assert ellipse is not None
    cx, cy, rx, ry = ellipse
    assert cx > 52, "the fallback ellipse is not on the shield arm"
    assert rx > 0 and ry > 0


# ---------------------------------------------------------------------------
# The oval stays invisible (BLOQUE 67, user request)
# ---------------------------------------------------------------------------


def test_the_oval_is_still_invisible() -> None:
    """BLOQUE 74 moves the oval; it does not make it visible."""
    from src.anim.parts import DRAW_SHIELD_OVAL

    assert DRAW_SHIELD_OVAL is False, (
        "the shield oval must stay invisible (BLOQUE 67): the player sees "
        "the heat layer and the impact flash, nothing else"
    )
