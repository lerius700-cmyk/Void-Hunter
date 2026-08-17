"""Tests for src.systems.parallax — 5 layers + 6 nebula + planets (BLOQUE 4)."""
from __future__ import annotations

import pytest
import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.systems.parallax import (
    LAYER_SPEEDS,
    NUM_LAYERS,
    PLANET_RADIUS_MAX,
    PLANET_RADIUS_MIN,
    PLANET_SPAWN_MAX_S,
    PLANET_SPAWN_MIN_S,
    STARS_PER_LAYER,
    ParallaxBackground,
)


@pytest.fixture
def bg() -> ParallaxBackground:
    return ParallaxBackground(rng_seed=42)


@pytest.fixture
def display() -> pygame.Surface:
    return pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# 1. Init invariants
# ---------------------------------------------------------------------------
def test_default_5_layers(bg: ParallaxBackground) -> None:
    """GDD §4: 5 star layers."""
    assert NUM_LAYERS == 5
    assert len(LAYER_SPEEDS) == 5
    # Speeds per GDD §4
    assert LAYER_SPEEDS == (20, 50, 100, 180, 280)


def test_default_6_nebula(bg: ParallaxBackground) -> None:
    assert len(bg._nebula) == 6


def test_default_5_layers_50_stars_each(bg: ParallaxBackground) -> None:
    """5 × 50 = 250 stars total.

    BLOQUE 58.12: default changed to 12 stars/layer (was 50). This test
    fixture uses `bg` which is the default-configured ParallaxBackground.
    The `bg` fixture creates one with stars_per_layer=12 (the new default).
    Title screen overrides to 50 for the dense look.
    """
    assert STARS_PER_LAYER == 12
    assert len(bg._stars) == NUM_LAYERS * STARS_PER_LAYER


def test_layer_assignments_distributed(bg: ParallaxBackground) -> None:
    """Each layer has 50 stars."""
    from collections import Counter
    counts = Counter(s.layer for s in bg._stars)
    for layer in range(NUM_LAYERS):
        assert counts[layer] == STARS_PER_LAYER


# ---------------------------------------------------------------------------
# 2. Update — wrap, twinkle, planet timer
# ---------------------------------------------------------------------------
def test_star_wraps_at_bottom(bg: ParallaxBackground) -> None:
    """Star at y > INTERNAL_H wraps to top."""
    s = bg._stars[0]
    s.y = INTERNAL_H + 5
    bg.update(0.001)
    assert s.y < INTERNAL_H


def test_nebula_wraps_at_bottom(bg: ParallaxBackground) -> None:
    n = bg._nebula[0]
    n.y = INTERNAL_H + 200
    bg.update(0.001)
    assert n.y < 0  # wrapped to top


def test_planet_spawn_timer_respected(bg: ParallaxBackground) -> None:
    """No planet until timer expires."""
    assert bg._planet is None
    bg._planet_timer = 0.5
    bg.update(0.4)
    assert bg._planet is None
    bg.update(0.2)
    assert bg._planet is not None


def test_planet_spawns_within_radius_range(bg: ParallaxBackground) -> None:
    """Spawned planet has radius in [8, 24]."""
    for _ in range(5):
        bg._planet = None
        bg._planet_timer = 0.0
        bg.update(0.001)
        if bg._planet is not None:
            assert PLANET_RADIUS_MIN <= bg._planet.radius <= PLANET_RADIUS_MAX
            return
    pytest.fail("No planet spawned after 5 attempts")


def test_planet_rotates_over_time(bg: ParallaxBackground) -> None:
    """Ring angle changes with time."""
    bg._planet_timer = 0.0
    bg.update(0.001)
    assert bg._planet is not None
    initial_angle = bg._planet.ring_angle
    bg.update(1.0)
    assert bg._planet.ring_angle != initial_angle


def test_zero_dt_noop(bg: ParallaxBackground) -> None:
    """dt=0 doesn't crash or change state."""
    initial_t = bg._t
    bg.update(0.0)
    assert bg._t == initial_t


# ---------------------------------------------------------------------------
# 3. Theme change
# ---------------------------------------------------------------------------
def test_set_theme_retints_nebula(bg: ParallaxBackground) -> None:
    """set_theme updates nebula colors per the new theme."""
    initial_colors = [n.color for n in bg._nebula]
    bg.set_theme("pink_void")
    new_colors = [n.color for n in bg._nebula]
    # Pink void is dominated by magenta — colors should differ.
    assert initial_colors != new_colors


def test_set_theme_to_unknown_keeps_current(bg: ParallaxBackground) -> None:
    """Unknown theme name falls back to blue_void (default) — no crash."""
    bg.set_theme("nonexistent_theme_xyz")
    # Should not raise; nebula colors get the blue_void palette.
    for n in bg._nebula:
        assert isinstance(n.color, tuple)
        assert len(n.color) == 3


def test_set_theme_during_gameplay_zero_glitch(bg: ParallaxBackground) -> None:
    """Theme change mid-update: draw without crash."""
    bg.set_theme("mars")
    bg.update(0.1)
    bg.draw(display := pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA))


# ---------------------------------------------------------------------------
# 4. Draw
# ---------------------------------------------------------------------------
def test_draw_no_crash_empty(bg: ParallaxBackground, display: pygame.Surface) -> None:
    bg.draw(display)


def test_draw_with_planet(bg: ParallaxBackground, display: pygame.Surface) -> None:
    bg._planet_timer = 0.0
    bg.update(0.001)
    bg.draw(display)


# ---------------------------------------------------------------------------
# 5. Star twinkle
# ---------------------------------------------------------------------------
def test_star_base_alpha_dimmer_for_farther_layers(bg: ParallaxBackground) -> None:
    """Layer 0 (farthest) has lower base_alpha than layer 4 (closest)."""
    layer0 = [s for s in bg._stars if s.layer == 0]
    layer4 = [s for s in bg._stars if s.layer == NUM_LAYERS - 1]
    avg_0 = sum(s.base_alpha for s in layer0) / len(layer0)
    avg_4 = sum(s.base_alpha for s in layer4) / len(layer4)
    assert avg_0 < avg_4


def test_twinkle_phase_in_0_to_2pi(bg: ParallaxBackground) -> None:
    import math
    for s in bg._stars:
        assert 0 <= s.twinkle_phase <= 2 * math.pi


# ---------------------------------------------------------------------------
# 6. release_all
# ---------------------------------------------------------------------------
def test_release_all_resets_state(bg: ParallaxBackground) -> None:
    bg._stars[0].x = 999.0  # corrupt
    bg._planet_timer = 999.0
    bg._planet = object()  # type: ignore[assignment]
    bg.release_all()
    assert bg._planet is None
    assert bg._planet_timer == PLANET_SPAWN_MIN_S
    assert bg._t == 0.0
    # Stars regenerated
    assert len(bg._stars) == NUM_LAYERS * STARS_PER_LAYER


# ---------------------------------------------------------------------------
# 7. Performance smoke
# ---------------------------------------------------------------------------
def test_250_stars_5_layers_update_under_1ms(bg: ParallaxBackground) -> None:
    import time
    bg.update(1 / 60)  # warmup
    t0 = time.perf_counter()
    for _ in range(60):
        bg.update(1 / 60)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.060, f"update too slow: {elapsed*1000:.1f}ms / 60 frames"


def test_parallax_draw_under_10ms(bg: ParallaxBackground, display: pygame.Surface) -> None:
    import time
    bg.draw(display)  # warmup
    t0 = time.perf_counter()
    for _ in range(20):
        bg.draw(display)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.200, f"draw too slow: {elapsed*1000:.1f}ms / 20 frames"


# ---------------------------------------------------------------------------
# 8. BLOQUE 58.14.3: AI galaxy sprites
# ---------------------------------------------------------------------------
def test_nebula_uses_ai_galaxy_sprite() -> None:
    """BLOQUE 58.14.3: each nebula surface is built from one of 4
    AI-generated galaxy sprites. The surface should be 2*radius x
    2*radius (so the blit covers the right area)."""
    bg = ParallaxBackground(rng_seed=42)
    for n in bg._nebula:
        assert n.surface is not None
        expected_size = max(8, int(n.radius * 2))
        assert n.surface.get_width() == expected_size
        assert n.surface.get_height() == expected_size


def test_nebula_has_galaxy_sprite_variant() -> None:
    """Each nebula records which AI sprite variant it used."""
    bg = ParallaxBackground(rng_seed=42)
    for n in bg._nebula:
        assert 0 <= n.sprite_variant < 4


def test_galaxy_sprites_loaded() -> None:
    """The 4 AI galaxy sprites are on disk and the loader finds them."""
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    galaxy_dir = project_root / "Assets" / "background"
    found = list(galaxy_dir.glob("galaxy_sprite_*.png"))
    assert len(found) >= 1, (
        f"No galaxy_sprite_*.png found in {galaxy_dir}. "
        "Run image_synthesize to generate them."
    )


def test_set_theme_does_not_crash_with_ai_sprites() -> None:
    """Theme change after init should still work: the surface stays
    valid (the AI sprite has its own colors, we don't re-render)."""
    bg = ParallaxBackground(rng_seed=42)
    initial_surfaces = [n.surface for n in bg._nebula]
    bg.set_theme("pink_void")
    # Surfaces should be the same objects (no re-render in BLOQUE 58.14.3).
    for n, s in zip(bg._nebula, initial_surfaces):
        assert n.surface is s
    # Draw should still work after the theme change.
    bg.draw(pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA))
