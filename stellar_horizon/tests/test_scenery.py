"""Tests for the procedural scenery (mountains + dust stream).

Verifies:
- MountainLayer._height_at returns a value in [0, max_height].
- MountainLayer.update advances the scroll position.
- MountainLayer.draw produces a non-zero number of polygon points.
- DustStream._spawn + update moves particles leftward and culls them
  when they leave the screen.
- GameplayScene exposes the new scenery state.
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

from stellar_horizon.fx.dust import DustStream
from stellar_horizon.ui.mountains import MountainLayer


# --- MountainLayer ------------------------------------------------------

def test_mountain_height_in_range():
    m = MountainLayer(horizon_y=200, max_height=60, color=(10, 10, 10),
                      scroll_speed=30.0, seed=42)
    for x in range(-200, 200, 10):
        h = m._height_at(x)
        assert 0.0 <= h <= 60.0, f"height {h} out of [0, 60] at x={x}"


def test_mountain_height_depends_on_x():
    m = MountainLayer(horizon_y=200, max_height=60, color=(10, 10, 10),
                      scroll_speed=30.0, seed=42)
    heights = {m._height_at(x) for x in range(0, 500, 5)}
    # Across 100 samples the ridge should have more than 3 distinct
    # heights (otherwise the layer would look like a flat line).
    assert len(heights) > 3, f"too few distinct heights: {heights}"


def test_mountain_update_advances_scroll():
    m = MountainLayer(horizon_y=200, max_height=60, color=(10, 10, 10),
                      scroll_speed=50.0, seed=1)
    m.update(1.0)
    assert getattr(m, "_scroll_offset", 0.0) > 0.0


def test_mountain_draw_writes_pixels():
    m = MountainLayer(horizon_y=200, max_height=60, color=(180, 90, 70),
                      scroll_speed=20.0, seed=7)
    m.update(0.5)
    surf = pygame.Surface((480, 270))
    m.draw(surf, 480)
    # At least some non-zero pixels in the lower half (where the
    # silhouette lives).
    found_color = False
    for y in range(180, 270, 4):
        for x in range(0, 480, 8):
            r, g, b, _ = surf.get_at((x, y))
            if (r, g, b) == (180, 90, 70):
                found_color = True
                break
        if found_color:
            break
    assert found_color, "MountainLayer.draw did not paint any ridge pixels"


# --- DustStream ---------------------------------------------------------

def test_dust_spawn_creates_particle():
    d = DustStream(screen_w=480, screen_h=270, pool_size=4, spawn_rate=0.0)
    # Force a single spawn by manipulating accum directly.
    d._spawn_accum = 1.0
    d.update(1 / 60)
    alive = [p for p in d._pool if p.alive]
    assert len(alive) == 1


def test_dust_particle_moves_leftward():
    d = DustStream(screen_w=480, screen_h=270, pool_size=4, spawn_rate=0.0)
    d._spawn_accum = 1.0
    d.update(1 / 60)
    p = next(p for p in d._pool if p.alive)
    start_x = p.x
    d.update(1 / 30)  # another 33ms
    assert p.x < start_x, f"dust did not move left: {start_x} -> {p.x}"


def test_dust_particle_culled_off_left_edge():
    d = DustStream(screen_w=100, screen_h=50, pool_size=4, spawn_rate=0.0,
                   min_speed=200.0, max_speed=200.0)
    d._spawn_accum = 1.0
    d.update(1 / 60)
    p = next(p for p in d._pool if p.alive)
    # Tick long enough for the particle to leave the left edge.
    for _ in range(60):
        d.update(1 / 30)
    assert not p.alive, "dust particle should be culled after leaving the screen"


# --- GameplayScene integration ----------------------------------------

def test_gameplay_scene_has_scenery():
    from pathlib import Path
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    assert len(s._mountains) == 3
    assert s._dust is not None
    # Foreground layer should be the fastest (largest scroll_speed).
    speeds = [m.scroll_speed for m in s._mountains]
    assert speeds == sorted(speeds), f"mountains not parallax-sorted: {speeds}"


def test_thruster_emit_is_now_noop():
    """After the sprite-sheet refactor the thruster is baked into
    the player animation, so _emit_thruster is a no-op. Verify it
    does NOT spawn P_FIRE/P_WAKE particles (those came from the old
    implementation and were removed)."""
    from pathlib import Path
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    pre = s.fx.engine._pool.active_count
    s.player.thrusting = True
    s.player.x, s.player.y = 100.0, 130.0
    for _ in range(30):  # ~0.25s at 120fps
        s._emit_thruster(1 / 120)
    post = s.fx.engine._pool.active_count
    assert post == pre, (
        f"thruster emit should be a no-op now (pre={pre}, post={post})"
    )
