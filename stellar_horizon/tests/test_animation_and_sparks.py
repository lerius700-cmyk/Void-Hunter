"""Tests for the sprite-sheet animation system + punchy impact sparks.

Verifies:
- AnimatedSprite loads a sheet, cycles through frames, and exposes
  the current surface.
- GameplayScene loads all 42 sprite sheets (7 active + 35 variants).
- FxLayer.emit_impact spawns the expected spark/shrapnel/flash mix.
- The new telegraph flash + kamikaze warning halos still draw.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import pygame
if not pygame.get_init():
    pygame.init()
if not pygame.font.get_init():
    pygame.font.init()

from pathlib import Path

from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.ui.animated_sprite import AnimatedSprite


# --- AnimatedSprite -----------------------------------------------------

def test_animated_sprite_cycles_frames():
    """With fps=10 and dt=0.15 the sprite should advance ~1-2 frames."""
    # Build a tiny 4-frame 2x2 sheet in memory so we don't need a
    # real asset for this unit test.
    sheet = pygame.Surface((8, 2), pygame.SRCALPHA)
    sheet.fill((10, 15, 31, 255))  # navy background
    for i in range(4):
        sheet.fill((255, 0, 0, 255), (i * 2, 0, (i + 1) * 2, 2))
    path = Path("stellar_horizon/assets/sprites/_test_anim.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(sheet, str(path))

    anim = AnimatedSprite(str(path), frame_w=2, frame_h=2,
                          frame_count=4, fps=10.0)
    # Frame 0 is the first colored region.
    first = anim.get_current_surface()
    anim.update(0.15)  # ~1.5 frames worth
    # At least one frame should have advanced.
    assert anim._index != 0, "AnimatedSprite did not advance frames"
    # And it wraps around (4 frames modulo 4).
    for _ in range(40):
        anim.update(0.15)
    assert 0 <= anim._index < 4
    path.unlink(missing_ok=True)


def test_animated_sprite_loaded_flag():
    """A missing sheet leaves the sprite in a non-loaded fallback
    (1x1 magenta), but the API still works without crashing."""
    anim = AnimatedSprite("nonexistent_path.png", frame_w=16, frame_h=16,
                          frame_count=6, fps=12.0)
    assert anim.loaded is False
    surf = anim.get_current_surface()
    assert surf is not None
    assert surf.get_width() == 16


# --- GameplayScene integration ----------------------------------------

def test_gameplay_scene_loads_sprites_split():
    """Lasers were split out into single-frame static sprites so the
    per-weapon VFX (alpha pulse, scale pulse, halo) can be applied
    in code rather than baked into 6-frame strips that the model
    rendered inconsistently.

    Total: 32 animated (7 active + 20 enemy + 5 player) + 10 laser
    single-frame = 42 sprites, same as before but split across two
    caches.
    """
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s._load_sprites()
    # Animated cache: 7 active + 20 enemy + 5 player = 32.
    assert len(s._animated) == 32
    for n in ("player", "scout", "cruiser", "heavy", "boss",
              "player_bullet", "enemy_bullet"):
        assert n in s._animated
    for n in (f"enemy_{i:02d}" for i in range(1, 21)):
        assert n in s._animated
    for n in (f"player_{i:02d}" for i in range(1, 6)):
        assert n in s._animated
    # Lasers MUST NOT be in the animated cache anymore.
    for n in (f"laser_{i:02d}" for i in range(1, 11)):
        assert n not in s._animated
    # Single-frame laser cache: 10 sprites.
    assert len(s._laser_sprites) == 10
    for n in (f"laser_{i:02d}" for i in range(1, 11)):
        assert n in s._laser_sprites
        surf = s._laser_sprites[n]
        # Each sprite is a real Surface (not the magenta 1x1 fallback).
        assert surf.get_width() >= 1
        assert surf.get_height() >= 1


def test_laser_sprites_have_per_weapon_sizes():
    """Per-weapon sprites have distinct sizes (12x4 bolts, 10x10 orbs,
    14x2 / 16x2 thin needles, 12x10 heart). The HUD and bullet draw
    code rely on these sizes to center the VFX halo correctly."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s._load_sprites()
    expected = {
        "laser_01": (12, 4), "laser_02": (12, 4),
        "laser_03": (14, 2),
        "laser_04": (10, 10), "laser_05": (10, 10),
        "laser_06": (10, 10),
        "laser_07": (16, 2),
        "laser_08": (12, 10),
        "laser_09": (10, 10),
        "laser_10": (16, 4),
    }
    for name, (w, h) in expected.items():
        surf = s._laser_sprites[name]
        assert surf.get_width() == w, (
            f"{name} width {surf.get_width()} != {w}"
        )
        assert surf.get_height() == h, (
            f"{name} height {surf.get_height()} != {h}"
        )


def test_animated_sprites_advance_on_update():
    """Every loaded animated sprite should accumulate elapsed time
    and advance its frame index on update()."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s._load_sprites()
    # Run a non-multiple-of-frame_count number of updates so the
    # index doesn't wrap exactly back to 0. At 12 fps, 50 updates of
    # 1/120s = 0.417s = 5 frames (one short of a full cycle). The
    # index should land on 5, NOT on 0.
    for _ in range(50):
        for anim in s._animated.values():
            anim.update(1 / 120)
    for n, anim in s._animated.items():
        assert anim._elapsed >= 0.0, f"{n} elapsed went negative"
        # Every sprite's frame index should now be 5 (or wrapped to
        # some non-zero value, but with 5 frames ticked it should be
        # exactly 5).
        assert anim._index == 5, (
            f"{n} frame index is {anim._index}, expected 5 "
            f"(elapsed={anim._elapsed:.3f}s)"
        )


# --- Punchy impact sparks ----------------------------------------------

def test_emit_impact_spawns_sparks_shrapnel_flash():
    """emit_impact should spawn 12 P_SPARK + 4 P_DEBRIS + 1 P_FLASH
    (kind 11) for a total of 17 particles. We measure via the pool's
    active_count delta across the call."""
    fx = FxLayer(pool_size=128)
    pre = fx.engine._pool.active_count
    fx.emit_impact(100.0, 100.0, count=12, color=(255, 240, 100))
    post = fx.engine._pool.active_count
    delta = post - pre
    # 12 sparks + 4 shrapnel + 1 flash = 17
    assert delta == 17, f"expected 17 particles, got {delta}"


def test_emit_impact_positions_match_xy():
    """All 17 spawned particles should be at the requested (x, y)."""
    fx = FxLayer(pool_size=128)
    fx.emit_impact(123.0, 234.0, count=12)
    for p in fx.engine._pool._items:
        if p.active:
            # Coordinates may move in one frame but the initial spawn
            # position was within a few pixels of (123, 234).
            assert abs(p.x - 123.0) < 5.0
            assert abs(p.y - 234.0) < 5.0


# --- Scene clock + bullet VFX wiring --------------------------------

def test_gameplay_scene_tracks_elapsed_time():
    """GameplayScene must accumulate scene time so the bullet VFX
    (alpha pulse, scale pulse, halo) can phase off of it."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    assert s._elapsed == 0.0
    s.update(1 / 120, [])
    assert abs(s._elapsed - (1 / 120)) < 1e-6
    s.update(1 / 60, [])
    assert abs(s._elapsed - (1 / 120 + 1 / 60)) < 1e-6


def test_spawned_bullet_has_consistent_spawn_time():
    """After a few frames, a fired bullet should have spawn_time
    close to the scene's _elapsed at the moment it was spawned."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    # Run 10 frames to let _elapsed accumulate.
    for _ in range(10):
        s.update(1 / 120, [])
    assert s._elapsed > 0.0
    # Drive player.update() directly with a keys dict so the SPACE
    # key fires (scene.update reads pygame.key.get_pressed() which
    # returns all False in headless mode and would override our
    # manual firing flag).
    s.player.firing = True
    s.player.shoot_cooldown = 0.0
    s.player.update(1 / 120, {pygame.K_SPACE: True},
                    s.player_bullets, now=s._elapsed)
    alive = [b for b in s.player_bullets if b.alive]
    assert len(alive) == 1
    # The bullet was spawned with now=s._elapsed, so its
    # spawn_time should match exactly.
    assert alive[0].spawn_time == s._elapsed
    assert alive[0].weapon == 0
