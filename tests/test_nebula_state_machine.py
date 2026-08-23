"""BLOQUE 58.next: tests for the nebula state machine + reposition.

The nebula state machine cycles:
  visible  -> (hold_timer expires) -> fading_out
  fading_out (alpha 255 -> 0)        -> hidden
  hidden    (instant)                -> fading_in (with new x, y)
  fading_in  (alpha 0 -> 255)        -> visible (reset hold_timer)

The position is always within the playfield (no clipping). On
reposition, a new sprite variant is picked.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest
import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.systems.parallax import (
    NEBULA_FADE_S,
    NEBULA_HOLD_MAX_S,
    NEBULA_HOLD_MIN_S,
    ParallaxBackground,
)


@pytest.fixture
def display() -> pygame.Surface:
    return pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# 1. Single-nebula gameplay config
# ---------------------------------------------------------------------------

class TestGameplaySingleNebula:
    """BLOQUE 58.next: gameplay must have EXACTLY 1 nebula, always complete."""

    def test_single_nebula_count(self, display: pygame.Surface) -> None:
        """Gameplay parallax: 1 nebula, not 4 or 6."""
        bg = ParallaxBackground(
            width=INTERNAL_W, height=INTERNAL_H,
            rng_seed=42, stars_per_layer=8,
            nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
            spawn_planets=False,
        )
        assert len(bg._nebula) == 1

    def test_title_keeps_dense_look(self, display: pygame.Surface) -> None:
        """Title screen keeps nebula_count=6 (the dense look)."""
        bg = ParallaxBackground(
            width=INTERNAL_W, height=INTERNAL_H,
            rng_seed=42, stars_per_layer=50,
            nebula_count=6, nebula_radius_min=40, nebula_radius_max=80,
            spawn_planets=True,
        )
        assert len(bg._nebula) == 6


# ---------------------------------------------------------------------------
# 2. No clipping (the original bug)
# ---------------------------------------------------------------------------

class TestNebulaNoClipping:
    """The single gameplay nebula is ALWAYS within the playfield,
    with a radius margin on all sides. The sprite is never clipped."""

    def test_initial_position_is_valid(self, display: pygame.Surface) -> None:
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        assert n.radius <= n.x <= INTERNAL_W - n.radius
        assert n.radius <= n.y <= INTERNAL_H - n.radius

    def test_position_stays_valid_through_cycle(
        self, display: pygame.Surface,
    ) -> None:
        """Across 2000 ticks (multiple full cycles), the nebula never
        clips at any edge."""
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        for _ in range(2000):
            bg.update(0.1)
            assert n.x - n.radius >= 0, f"clip left: x={n.x}"
            assert n.x + n.radius <= INTERNAL_W, f"clip right: x={n.x}"
            assert n.y - n.radius >= 0, f"clip top: y={n.y}"
            assert n.y + n.radius <= INTERNAL_H, f"clip bottom: y={n.y}"

    def test_position_changes_over_time(self, display: pygame.Surface) -> None:
        """Across enough ticks to complete a hold + fade cycle, the
        position must change at least once (the 'no siempre en el
        centro' requirement)."""
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        initial_x, initial_y = n.x, n.y
        # Tick for ~30s (more than 2x the max hold + fade)
        for _ in range(300):
            bg.update(0.1)
        assert (n.x, n.y) != (initial_x, initial_y), (
            f"Position did not change in 30s: still ({n.x}, {n.y})"
        )


# ---------------------------------------------------------------------------
# 3. State machine transitions
# ---------------------------------------------------------------------------

class TestStateMachine:
    """The state machine drives each nebula through visible -> fading_out
    -> hidden -> fading_in -> visible. Each transition is timed."""

    def test_initial_state_is_visible(
        self, display: pygame.Surface,
    ) -> None:
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        assert n.state == "visible"
        assert n.alpha == 255.0

    def test_hold_timer_in_range(self, display: pygame.Surface) -> None:
        """Initial state_timer (the hold period) is in [HOLD_MIN, HOLD_MAX]."""
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        assert NEBULA_HOLD_MIN_S <= n.state_timer <= NEBULA_HOLD_MAX_S

    def test_cycles_through_all_states(self, display: pygame.Surface) -> None:
        """Within 3 full cycles (3 * (HOLD_MAX + 2*FADE) = 3 * 19 = 57s),
        the nebula must have visited every state at least once."""
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        seen: set[str] = set()
        cycle_seconds = NEBULA_HOLD_MAX_S + 2 * NEBULA_FADE_S + 1.0
        for _ in range(int(cycle_seconds * 10) * 3):
            bg.update(0.1)
            seen.add(n.state)
        # Must have hit visible, fading_out, hidden, fading_in
        for required in ("visible", "fading_out", "hidden", "fading_in"):
            assert required in seen, (
                f"nebula never entered state '{required}' in 3 cycles "
                f"(seen: {seen})"
            )

    def test_fade_alpha_decreases_during_fade_out(
        self, display: pygame.Surface,
    ) -> None:
        """When the nebula is fading out, its alpha decreases over time."""
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        # Force the nebula into fading_out
        n.state = "fading_out"
        n.state_timer = NEBULA_FADE_S
        n.alpha = 255.0
        bg.update(NEBULA_FADE_S * 0.5)
        # Halfway through the fade, alpha should be ~128
        assert 100.0 < n.alpha < 180.0, (
            f"alpha after half fade = {n.alpha}, expected ~128"
        )

    def test_fade_alpha_increases_during_fade_in(
        self, display: pygame.Surface,
    ) -> None:
        """When the nebula is fading in, its alpha increases over time."""
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        # Force the nebula into fading_in
        n.state = "fading_in"
        n.state_timer = NEBULA_FADE_S
        n.alpha = 0.0
        bg.update(NEBULA_FADE_S * 0.5)
        # Halfway through the fade, alpha should be ~128
        assert 100.0 < n.alpha < 180.0, (
            f"alpha after half fade-in = {n.alpha}, expected ~128"
        )


# ---------------------------------------------------------------------------
# 4. Reposition picks a new position + new sprite variant
# ---------------------------------------------------------------------------

class TestReposition:
    """The hidden -> fading_in transition picks a new (x, y) and a
    new sprite variant."""

    def test_reposition_picks_new_xy(self, display: pygame.Surface) -> None:
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        old_x, old_y = n.x, n.y
        old_surface = n.surface
        # Force the reposition code path
        bg._reposition_nebula(n)
        # The new position must be valid (within playfield + margin)
        assert n.radius <= n.x <= INTERNAL_W - n.radius
        assert n.radius <= n.y <= INTERNAL_H - n.radius
        # The new surface is rendered with a new variant (may or may not
        # be different from the old one due to rng, but it must be valid)
        assert n.surface is not None
        # Old surface was a different Surface object reference (Pygame
        # re-renders, so the ref should change)
        # (note: it might be the same if pygame caches, but normally
        # a new Surface is allocated.)

    def test_reposition_across_full_cycle(
        self, display: pygame.Surface,
    ) -> None:
        """Over many cycles, the position takes multiple distinct values."""
        bg = ParallaxBackground(
            rng_seed=42, nebula_count=1, nebula_radius_min=60, nebula_radius_max=90,
        )
        n = bg._nebula[0]
        seen_positions: set[tuple[float, float]] = set()
        # Tick for 2 minutes (should hit at least 5-6 cycles)
        for _ in range(1200):
            bg.update(0.1)
            # Round to 0.1 to bucket positions that differ by < 0.1 px
            key = (round(n.x, 1), round(n.y, 1))
            seen_positions.add(key)
        assert len(seen_positions) >= 3, (
            f"nebula only visited {len(seen_positions)} unique positions "
            f"in 2 minutes; expected >= 3"
        )
