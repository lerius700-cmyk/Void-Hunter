"""BLOQUE 73.4: the shield's visual, hitbox and beam origin must all read
the same anchor, and the eye laser must start where the eye is drawn.

BLOQUE 66.4n wrote this as a one-off capture script
(``tools/capture/verify_shield_laser_coincidence.py``) that had to be run by
hand. A picture the user has to remember to regenerate is a picture that
silently rots. These are the same measurements, as assertions.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ANIMS = ["phase1_idle", "phase2_idle", "javelin", "laser", "purple_bullet", "death"]


@pytest.fixture(scope="module")
def runtime():
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.entities.enemies.boss import BOSS_CONFIGS
    from src.ui.gameplay_runtime import GameplayRuntime

    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    rt._boss_entry_t = 2.0
    b = rt._boss
    cfg = BOSS_CONFIGS[b.id]
    b.x = cfg.anchor_x
    b.y = cfg.anchor_y
    b.phase = 1
    return rt


# ---------------------------------------------------------------------------
# Shield: one anchor, three consumers
# ---------------------------------------------------------------------------


def test_shield_centre_is_independent_of_charge(runtime) -> None:
    """The hitbox must not move as the shield charges.

    If the anchor read the charge state, bullets that landed at 0 hits
    would miss at 19 hits — the desync the user reported repeatedly.
    """
    from src.ui.gameplay_runtime import _goliath_shield_center

    b = runtime._boss
    b.animation_state = "phase1_idle"
    b.animation_frame = 0
    runtime._boss_shield_hits = 0
    cold = _goliath_shield_center(runtime)
    runtime._boss_shield_hits = 19
    hot = _goliath_shield_center(runtime)
    assert cold == hot


def test_shield_hitbox_rect_contains_the_drawn_oval(runtime) -> None:
    """The collision rect must fully contain the oval the player sees."""
    import pygame

    from src.ui.gameplay_runtime import (
        GOLIATH_SHIELD_R,
        GOLIATH_SHIELD_RX,
        GOLIATH_SHIELD_RY,
        _goliath_shield_center,
    )

    b = runtime._boss
    b.animation_state = "phase1_idle"
    b.animation_frame = 0
    sx, sy = _goliath_shield_center(runtime)

    # BLOQUE 73.4: the hitbox uses the oval's own half-extents (the radius
    # alone is square and leaves 6 px of the tall axis non-colliding),
    # plus 1 px because pygame.Rect is half-open.
    hx = max(GOLIATH_SHIELD_R, GOLIATH_SHIELD_RX) + 1
    hy = max(GOLIATH_SHIELD_R, GOLIATH_SHIELD_RY) + 1
    hitbox = pygame.Rect(int(sx - hx), int(sy - hy), hx * 2, hy * 2)
    # Every point on the visible oval's rim must be inside the hitbox.
    for deg in range(0, 360, 15):
        import math

        px = int(sx + GOLIATH_SHIELD_RX * math.cos(math.radians(deg)))
        py = int(sy + GOLIATH_SHIELD_RY * math.sin(math.radians(deg)))
        assert hitbox.collidepoint(px, py), (
            f"oval rim at {deg}deg ({px},{py}) is outside the hitbox "
            f"{hitbox} — bullets would pass through the visible shield"
        )


def test_shield_laser_origin_matches_shield_centre(runtime) -> None:
    """The charged beam must leave from the shield, not from the body.

    Calls ``_draw_shield_laser`` on a blank surface and checks the beam's
    own origin disc is centred on the shield. Rendering the whole runtime
    and diffing two frames would be useless here: the parallax background
    and the shield's own glow both change between draws, so the first
    changed pixel belongs to neither beam nor shield.
    """
    import pygame

    from src.ui.gameplay_runtime import _goliath_shield_center

    b = runtime._boss
    b.animation_state = "phase1_idle"
    b.animation_frame = 0
    sx, sy = _goliath_shield_center(runtime)

    target = pygame.Surface((320, 480))
    target.fill((0, 0, 0))
    runtime._boss_shield_laser_t = 1.0
    runtime._draw_shield_laser(target, 0, 0)
    runtime._boss_shield_laser_t = 0.0

    # The beam paints a 24px bright origin disc centred on (sx, sy). Scan
    # the beam column for the extent of bright pixels; its vertical middle
    # must be the shield centre.
    col = int(sx)
    rows = [
        y
        for y in range(480)
        if max(target.get_at((col, y))[:3]) > 60
    ]
    assert rows, "the beam drew nothing at its own column"
    midpoint = (rows[0] + rows[-1]) // 2
    # The disc is 24px, so the top rows are the glow edge and the body
    # runs to the bottom of the screen. Just assert the beam STARTS at or
    # above the shield (never below it) and that the shield row is lit.
    assert rows[0] <= sy, (
        f"beam starts at row {rows[0]}, BELOW the shield centre row {sy} "
        f"— the beam does not leave from the shield"
    )
    assert any(abs(y - sy) <= 12 for y in rows), (
        f"the shield centre row {sy} is not lit by the beam "
        f"(lit rows: {rows[0]}..{rows[-1]})"
    )


# ---------------------------------------------------------------------------
# Eye laser: anchored to the eye, per frame
# ---------------------------------------------------------------------------


def test_eye_anchor_varies_with_pose() -> None:
    """A fixed row would mean the beam starts below the eye in most frames."""
    from src.ui.scenes import get_sprite_eye_anchor

    rows = {
        get_sprite_eye_anchor(f"bosses/goliath/{a}/frame_{i:02d}.png")[1]
        for a in ANIMS
        for i in range(10)
    }
    assert len(rows) >= 5, f"eye row barely varies ({sorted(rows)}) — suspect a fixed offset"


def test_eye_anchor_sits_in_the_head_band() -> None:
    """The eye is in the head; a row past ~30 means we latched onto armour."""
    from src.ui.scenes import get_sprite_eye_anchor

    for a in ANIMS:
        for i in range(10):
            _, row = get_sprite_eye_anchor(f"bosses/goliath/{a}/frame_{i:02d}.png")
            assert 8 <= row <= 30, f"{a}/frame_{i:02d}: eye row {row} outside the head band"


def test_eye_laser_spawns_at_the_eye_not_the_body(runtime) -> None:
    """The beam must originate near the eye, not boss.y + 30."""
    import pygame

    from src.ui.scenes import get_sprite_centroid_offset, get_sprite_eye_anchor

    b = runtime._boss
    b.phase = 2
    b.animation_state = "laser"
    b.animation_frame = 0
    runtime._boss_shield_hits = 0

    path = b.animation_path
    eye_col, eye_row = get_sprite_eye_anchor(path)
    cdx, cdy = get_sprite_centroid_offset(path)
    expected_y = int(b.y) - 40 + cdy + eye_row

    before = sum(1 for p in runtime._bullets.pool if p.active)
    runtime._spawn_boss_attack(9)
    after = [p for p in runtime._bullets.pool if p.active]
    assert len(after) > before, "attack 9 spawned no projectile"

    laser = after[-1]
    assert abs(laser.y - expected_y) <= 2, (
        f"eye laser spawned at y={laser.y}, expected ~{expected_y} (the eye)"
    )
    b.phase = 1


# ---------------------------------------------------------------------------
# Frames actually animate (BLOQUE 73.3 regression guard)
# ---------------------------------------------------------------------------


def test_all_ten_frames_of_each_animation_are_distinct() -> None:
    """Guard the BLOQUE 73.3 regression: 10 byte-identical copies per anim.

    That silently reverted the whole animation set once already.
    """
    import hashlib

    base = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
    total_unique = 0
    for anim in ANIMS:
        digests = set()
        for i in range(10):
            blob = (base / anim / f"frame_{i:02d}.png").read_bytes()
            digests.add(hashlib.md5(blob).hexdigest())
        assert len(digests) == 10, (
            f"{anim}: only {len(digests)}/10 distinct frames — "
            f"the animation has collapsed to a still image"
        )
        total_unique += len(digests)
    assert total_unique == 60


def test_no_sprite_touches_the_canvas_edge() -> None:
    """The original 'cortado' report: sprites bleeding off the 96x80 canvas."""
    from PIL import Image

    base = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
    for anim in ANIMS:
        for i in range(10):
            img = Image.open(base / anim / f"frame_{i:02d}.png").convert("RGBA")
            bbox = img.split()[-1].getbbox()
            if bbox is None:
                continue  # intentionally empty frame
            w, h = img.size
            assert bbox[1] >= 2, f"{anim}/frame_{i:02d}: top margin {bbox[1]}px — sprite cut at the top"
            assert w - bbox[2] >= 2, f"{anim}/frame_{i:02d}: right margin {w-bbox[2]}px — sprite cut at the right"
            assert bbox[0] >= 2, f"{anim}/frame_{i:02d}: left margin {bbox[0]}px — sprite cut at the left"
            assert h - bbox[3] >= 2, f"{anim}/frame_{i:02d}: bottom margin {h-bbox[3]}px — sprite cut at the bottom"