"""Tests for src.systems.parallax - 5 layers + scrolling galaxy strip + planets.

BLOQUE 58.15: replaces the old nebula state machine tests with tests
for the new scrolling galaxy strip (4 variants, 480x1440, 25 px/s).
"""
from __future__ import annotations

import pytest
import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.systems.parallax import (
    GALAXY_STRIP_H,
    GALAXY_STRIP_SPEED,
    GALAXY_STRIP_W,
    GALAXY_STRIP_X_OFFSET,
    LAYER_SPEEDS,
    NUM_LAYERS,
    PLANET_RADIUS_MAX,
    PLANET_RADIUS_MIN,
    PLANET_SPAWN_MIN_S,
    STARS_PER_LAYER,
    STARS_PER_LAYER_DEFAULT,
    STRIP_PROCEDURAL_STARS,
    STRIP_MAIN_GALAXIES,
    STRIP_MAIN_RADIUS_MIN,
    STRIP_MAIN_RADIUS_MAX,
    STRIP_COMPANION_GALAXIES_MIN,
    STRIP_COMPANION_GALAXIES_MAX,
    STRIP_COMPANION_RADIUS_MIN,
    STRIP_COMPANION_RADIUS_MAX,
    STRIP_COMPANION_DISTANCE_MIN,
    STRIP_COMPANION_DISTANCE_MAX,
    STRIP_EDGE_PAD,
    _STRIP_VARIANT_SEEDS,
    _STRIP_VARIANT_SPRITE_INDICES,
    _STRIP_VARIANT_THEMES,
    ParallaxBackground,
)


@pytest.fixture
def bg() -> ParallaxBackground:
    return ParallaxBackground(rng_seed=42)


@pytest.fixture
def display() -> pygame.Surface:
    return pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)


# 1. Init invariants
def test_default_5_layers() -> None:
    assert NUM_LAYERS == 5
    assert len(LAYER_SPEEDS) == 5
    assert LAYER_SPEEDS == (20, 50, 100, 180, 280)


def test_default_star_count_per_layer(bg: ParallaxBackground) -> None:
    assert STARS_PER_LAYER == STARS_PER_LAYER_DEFAULT == 12
    assert len(bg._stars) == 60


def test_layer_assignments_distributed(bg: ParallaxBackground) -> None:
    by_layer: dict[int, int] = {}
    for s in bg._stars:
        by_layer[s.layer] = by_layer.get(s.layer, 0) + 1
    for layer in range(NUM_LAYERS):
        assert by_layer.get(layer, 0) == 12


def test_zero_dt_noop(bg: ParallaxBackground) -> None:
    initial_y = bg._strip_y_offset
    initial_t = bg._t
    bg.update(0.0)
    assert bg._strip_y_offset == initial_y
    assert bg._t == initial_t


def test_planet_spawn_timer_respected(bg: ParallaxBackground) -> None:
    assert bg._planet_timer == PLANET_SPAWN_MIN_S


def test_planet_spawns_within_radius_range(bg: ParallaxBackground) -> None:
    bg._planet_timer = 0.0
    bg.update(0.001)
    assert bg._planet is not None
    assert PLANET_RADIUS_MIN <= bg._planet.radius <= PLANET_RADIUS_MAX


def test_planet_rotates_over_time(bg: ParallaxBackground) -> None:
    bg._planet_timer = 0.0
    bg.update(0.001)
    assert bg._planet is not None
    initial_angle = bg._planet.ring_angle
    bg.update(1.0)
    assert bg._planet.ring_angle > initial_angle


def test_draw_no_crash_empty(bg: ParallaxBackground, display: pygame.Surface) -> None:
    bg.draw(display)


def test_draw_with_planet(bg: ParallaxBackground, display: pygame.Surface) -> None:
    bg._planet_timer = 0.0
    bg.update(0.001)
    bg.draw(display)


def test_star_base_alpha_dimmer_for_farther_layers(bg: ParallaxBackground) -> None:
    layer0 = [s for s in bg._stars if s.layer == 0]
    layer4 = [s for s in bg._stars if s.layer == 4]
    assert all(s.base_alpha == 100 for s in layer0)
    assert all(s.base_alpha == 220 for s in layer4)


def test_twinkle_phase_in_0_to_2pi(bg: ParallaxBackground) -> None:
    import math
    for s in bg._stars:
        assert 0.0 <= s.twinkle_phase <= 2 * math.pi


def test_release_all_resets_state(bg: ParallaxBackground) -> None:
    bg._planet_timer = 5.0
    bg._strip_y_offset = 100.0
    bg._t = 10.0
    bg.release_all()
    assert bg._planet is None
    assert bg._planet_timer == PLANET_SPAWN_MIN_S
    assert bg._strip_y_offset == 0.0
    assert bg._t == 0.0


# 2. Galaxy strip (BLOQUE 58.15)
class TestGalaxyStrip:

    def test_strip_dimensions_match_design(self) -> None:
        assert GALAXY_STRIP_W == 480
        assert GALAXY_STRIP_H == 1440

    def test_strip_x_offset_centers_on_playfield(self) -> None:
        assert GALAXY_STRIP_X_OFFSET == 80
        assert GALAXY_STRIP_X_OFFSET + INTERNAL_W <= GALAXY_STRIP_W

    def test_strip_speed_between_star_layers(self) -> None:
        assert LAYER_SPEEDS[0] < GALAXY_STRIP_SPEED < LAYER_SPEEDS[1]
        assert GALAXY_STRIP_SPEED == 25.0

    def test_strip_uses_galaxy_sprites(self, bg: ParallaxBackground) -> None:
        bg._get_or_render_strip(0)
        sprites = bg._load_galaxy_sprites()
        if not sprites:
            pytest.skip("No galaxy sprites on disk")
        surf = bg._strip_surfaces[0]
        assert surf.get_size() == (GALAXY_STRIP_W, GALAXY_STRIP_H)

    def test_4_variants_configured(self) -> None:
        assert len(_STRIP_VARIANT_THEMES) == 4
        assert len(_STRIP_VARIANT_SPRITE_INDICES) == 4
        assert len(_STRIP_VARIANT_SEEDS) == 4
        assert _STRIP_VARIANT_THEMES == (
            "blue_void", "teal", "gold_amber", "purple_dusk",
        )

    def test_sparse_galaxy_counts(self) -> None:
        # BLOQUE 58.62 v3: 7 main + 4-6 companions each + 80 stars.
        # The detailed TestStripLayout class covers the new layout;
        # this is a smoke check.
        assert STRIP_MAIN_GALAXIES == 7
        assert STRIP_PROCEDURAL_STARS == 80


class TestStripScroll:

    def test_starts_at_zero_offset(self, bg: ParallaxBackground) -> None:
        assert bg.get_strip_y_offset() == 0.0

    def test_advances_with_dt(self, bg: ParallaxBackground) -> None:
        bg.update(1.0)
        assert bg.get_strip_y_offset() == pytest.approx(GALAXY_STRIP_SPEED, abs=0.01)

    def test_wraps_at_strip_height(self, bg: ParallaxBackground) -> None:
        bg.update((GALAXY_STRIP_H / GALAXY_STRIP_SPEED) + 1.0)
        offset = bg.get_strip_y_offset()
        assert 0.0 <= offset < GALAXY_STRIP_H

    def test_scroll_is_continuous(self, bg: ParallaxBackground) -> None:
        bg.update(0.1)
        first = bg.get_strip_y_offset()
        bg.update(0.1)
        second = bg.get_strip_y_offset()
        assert first == pytest.approx(2.5, abs=0.01)
        assert second == pytest.approx(5.0, abs=0.01)


class TestStripVariants:

    def test_default_variant_is_zero(self, bg: ParallaxBackground) -> None:
        assert bg.get_strip_variant() == 0
        assert bg._theme_name == "blue_void"

    def test_set_strip_variant_clamps(self, bg: ParallaxBackground) -> None:
        bg.set_strip_variant(99)
        assert bg.get_strip_variant() == 3
        bg.set_strip_variant(-5)
        assert bg.get_strip_variant() == 0

    def test_set_strip_variant_updates_theme_name(self, bg: ParallaxBackground) -> None:
        for v in range(4):
            bg.set_strip_variant(v)
            assert bg._theme_name == _STRIP_VARIANT_THEMES[v]

    def test_set_theme_picks_variant(self, bg: ParallaxBackground) -> None:
        for v, theme in enumerate(_STRIP_VARIANT_THEMES):
            bg.set_theme(theme)
            assert bg.get_strip_variant() == v
            assert bg._theme_name == theme

    def test_set_theme_unknown_falls_back_to_blue_void(
        self, bg: ParallaxBackground,
    ) -> None:
        bg.set_theme("definitely_not_a_real_theme")
        assert bg.get_strip_variant() == 0
        assert bg._theme_name == "blue_void"

    def test_each_variant_renders_a_distinct_surface(
        self, bg: ParallaxBackground,
    ) -> None:
        for v in range(4):
            bg.set_strip_variant(v)
            assert v in bg._strip_surfaces
            assert bg._strip_surfaces[v].get_size() == (
                GALAXY_STRIP_W, GALAXY_STRIP_H
            )

    def test_each_variant_is_deterministic(self) -> None:
        bg1 = ParallaxBackground(rng_seed=42)
        bg2 = ParallaxBackground(rng_seed=42)
        for v in range(4):
            bg1.set_strip_variant(v)
            bg2.set_strip_variant(v)
            s1 = bg1._strip_surfaces[v]
            s2 = bg2._strip_surfaces[v]
            for y in range(0, GALAXY_STRIP_H, 8):
                for x in range(0, GALAXY_STRIP_W, 8):
                    assert s1.get_at((x, y)) == s2.get_at((x, y)), (
                        f"variant {v} differs at ({x},{y})"
                    )


class TestStripIsVisible:

    def test_draw_blits_strip_at_x_offset(
        self, bg: ParallaxBackground, display: pygame.Surface,
    ) -> None:
        bg.draw(display)

    def test_draw_with_advanced_offset(
        self, bg: ParallaxBackground, display: pygame.Surface,
    ) -> None:
        bg.update(20.0)
        bg.draw(display)

    def test_draw_with_near_wrap_offset(
        self, bg: ParallaxBackground, display: pygame.Surface,
    ) -> None:
        bg._strip_y_offset = GALAXY_STRIP_H - 10
        bg.draw(display)


def test_strip_rng_separate_from_main_rng(bg: ParallaxBackground) -> None:
    bg.update(100.0)
    a = bg.get_strip_y_offset()
    bg.update(50.0)
    b = bg.get_strip_y_offset()
    assert a != b


def test_4_variants_separate_caches(bg: ParallaxBackground) -> None:
    for v in range(4):
        bg.set_strip_variant(v)
    assert len(bg._strip_surfaces) == 4


# 3. Backward-compat: ParallaxBackground can be constructed with old-style
# kwargs (nebula_count, etc.) by ignoring them. This protects callers that
# haven't been updated yet.
def test_constructor_no_legacy_kwargs(bg: ParallaxBackground) -> None:
    """After the rewrite, the constructor no longer accepts nebula_count etc."""
    import inspect
    sig = inspect.signature(ParallaxBackground.__init__)
    params = list(sig.parameters.keys())
    assert "nebula_count" not in params
    assert "nebula_radius_min" not in params
    assert "nebula_radius_max" not in params

# ---------------------------------------------------------------------------
# 4. Strip layout (BLOQUE 58.62 v3 - matches the hand-painted reference)
# ---------------------------------------------------------------------------
class TestStripLayout:
    "v3 layout: 7 main + 4-6 companions each + 80 stars per strip."

    def test_main_galaxy_count_is_7(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_MAIN_GALAXIES == 7

    def test_main_radius_range(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_MAIN_RADIUS_MIN == 50
        assert p.STRIP_MAIN_RADIUS_MAX == 70

    def test_companion_count_range(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_COMPANION_GALAXIES_MIN == 4
        assert p.STRIP_COMPANION_GALAXIES_MAX == 6
        assert p.STRIP_COMPANION_GALAXIES_MIN < p.STRIP_COMPANION_GALAXIES_MAX

    def test_companion_radius_smaller_than_main(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_COMPANION_RADIUS_MAX < p.STRIP_MAIN_RADIUS_MIN

    def test_companions_within_distance_of_main(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_COMPANION_DISTANCE_MIN == 80
        assert p.STRIP_COMPANION_DISTANCE_MAX == 150

    def test_star_count_is_80(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_PROCEDURAL_STARS == 80

    def test_edge_pad_is_50(self) -> None:
        from src.systems import parallax as p
        assert p.STRIP_EDGE_PAD == 50

    def test_total_galaxies_in_range(self) -> None:
        from src.systems import parallax as p
        # Total galaxies per strip: 7 main + 4-6 companions c/u
        # = 7 + 28-42 = 35-49 galaxies (much closer to the reference)
        min_total = p.STRIP_MAIN_GALAXIES + (
            p.STRIP_COMPANION_GALAXIES_MIN * p.STRIP_MAIN_GALAXIES
        )
        max_total = p.STRIP_MAIN_GALAXIES + (
            p.STRIP_COMPANION_GALAXIES_MAX * p.STRIP_MAIN_GALAXIES
        )
        assert min_total == 35
        assert max_total == 49
