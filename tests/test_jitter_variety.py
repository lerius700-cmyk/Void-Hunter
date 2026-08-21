"""BLOQUE 58.next: tests for per-instance jitter on ComposedPattern.

Jitter is the feature that makes two COMPOSED picks of the same
(formation, path, follow) recipe look different. These tests verify:
  - Two calls with DIFFERENT outer rng seeds produce different results
    (path control points shifted, colors shifted, duration shifted)
  - Two calls with the SAME outer rng seed are byte-for-byte identical
    (determinism preserved)
  - Jitter is bounded: the perturbation is small enough that the
    pattern is still recognizable (e.g. a V is still a V).
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from src.systems.wave_patterns.composed import COMPOSED_PATTERNS


# ---------------------------------------------------------------------------
# Variety: two different seeds => two different results
# ---------------------------------------------------------------------------

class TestJitterVariety:
    """Same (formation, path, follow) called twice with different outer
    seeds should produce different-looking waves. Without jitter, the
    results would be byte-for-byte identical except for entry_x."""

    def test_two_seeds_produce_different_paths(self):
        """Pick a representative pattern. Run twice with different seeds.
        Assert the first segment's control points differ (path jitter)."""
        p = COMPOSED_PATTERNS[0]  # first one
        a = p.generate(random.Random(1), level=3, enemy_kind="SCOUT")
        b = p.generate(random.Random(2), level=3, enemy_kind="SCOUT")
        a_seg0 = a.ships[0].extra["segments"][0]
        b_seg0 = b.ships[0].extra["segments"][0]
        # At least one of the 4 control points should differ by > 0.1px
        max_diff = 0.0
        for ap, bp in zip(a_seg0, b_seg0):
            d = max(abs(ap[0] - bp[0]), abs(ap[1] - bp[1]))
            max_diff = max(max_diff, d)
        assert max_diff > 0.1, (
            f"Jitter did not perturb path control points (max diff {max_diff})"
        )

    def test_two_seeds_produce_different_colors(self):
        """Color jitter: at least one ship's color channel differs."""
        p = COMPOSED_PATTERNS[0]
        a = p.generate(random.Random(10), level=3, enemy_kind="SCOUT")
        b = p.generate(random.Random(20), level=3, enemy_kind="SCOUT")
        assert a.ships[0].color != b.ships[0].color, (
            "Jitter did not perturb color of first ship"
        )

    def test_two_seeds_produce_different_durations(self):
        """Duration jitter: 8.0 ± 0.8 — should differ between seeds."""
        p = COMPOSED_PATTERNS[0]
        a = p.generate(random.Random(100), level=3, enemy_kind="SCOUT")
        b = p.generate(random.Random(200), level=3, enemy_kind="SCOUT")
        assert abs(a.duration_s - b.duration_s) > 0.01, (
            f"Duration identical ({a.duration_s} vs {b.duration_s})"
        )

    @pytest.mark.parametrize("idx", [0, 12, 25, 37, 49])
    def test_jitter_varies_for_5_patterns(self, idx):
        """Jitter should kick in for at least 5 patterns in the pool."""
        p = COMPOSED_PATTERNS[idx]
        a = p.generate(random.Random(1), level=3, enemy_kind="SCOUT")
        b = p.generate(random.Random(2), level=3, enemy_kind="SCOUT")
        a_seg0 = a.ships[0].extra["segments"][0]
        b_seg0 = b.ships[0].extra["segments"][0]
        max_diff = 0.0
        for ap, bp in zip(a_seg0, b_seg0):
            d = max(abs(ap[0] - bp[0]), abs(ap[1] - bp[1]))
            max_diff = max(max_diff, d)
        assert max_diff > 0.1, (
            f"COMPOSED_PATTERNS[{idx}] did not jitter (max diff {max_diff})"
        )


# ---------------------------------------------------------------------------
# Determinism: same seed => identical results
# ---------------------------------------------------------------------------

class TestJitterDeterminism:
    """Same outer seed must always produce the same result, even with jitter."""

    def test_same_seed_identical(self):
        p = COMPOSED_PATTERNS[0]
        a = p.generate(random.Random(42), level=3, enemy_kind="SCOUT")
        b = p.generate(random.Random(42), level=3, enemy_kind="SCOUT")
        # Paths
        a_seg0 = a.ships[0].extra["segments"][0]
        b_seg0 = b.ships[0].extra["segments"][0]
        for ap, bp in zip(a_seg0, b_seg0):
            assert ap == pytest.approx(bp, abs=0.01)
        # Colors
        assert a.ships[0].color == b.ships[0].color
        # Duration
        assert a.duration_s == pytest.approx(b.duration_s, abs=0.001)

    @pytest.mark.parametrize("idx", [0, 12, 25, 37, 49])
    def test_determinism_for_5_patterns(self, idx):
        p = COMPOSED_PATTERNS[idx]
        a = p.generate(random.Random(777), level=3, enemy_kind="SCOUT")
        b = p.generate(random.Random(777), level=3, enemy_kind="SCOUT")
        a_seg0 = a.ships[0].extra["segments"][0]
        b_seg0 = b.ships[0].extra["segments"][0]
        for ap, bp in zip(a_seg0, b_seg0):
            assert ap == pytest.approx(bp, abs=0.01), (
                f"COMPOSED_PATTERNS[{idx}] not deterministic"
            )


# ---------------------------------------------------------------------------
# Bounds: jitter shouldn't break the playfield or degenerate the path
# ---------------------------------------------------------------------------

class TestJitterBounds:
    """Jitter is bounded so patterns stay recognizable and on-screen."""

    def test_jitter_keeps_ships_in_playfield(self):
        """Even with jitter, ships should stay near the playfield."""
        p = COMPOSED_PATTERNS[0]
        for seed in range(20):
            r = p.generate(random.Random(seed), level=3, enemy_kind="SCOUT")
            for s in r.ships:
                assert -120 <= s.spawn_x <= 320 + 120, (
                    f"ship {s.slot} spawn_x={s.spawn_x} out of bounds (seed={seed})"
                )
                assert -120 <= s.spawn_y <= 480 + 120, (
                    f"ship {s.slot} spawn_y={s.spawn_y} out of bounds (seed={seed})"
                )

    def test_jitter_keeps_duration_in_range(self):
        """Duration is 8.0 ± 0.8 = [7.2, 8.8]."""
        p = COMPOSED_PATTERNS[0]
        for seed in range(30):
            r = p.generate(random.Random(seed), level=3, enemy_kind="SCOUT")
            assert 7.0 <= r.duration_s <= 9.0, (
                f"duration_s={r.duration_s} out of [7, 9] (seed={seed})"
            )

    def test_jitter_keeps_colors_in_range(self):
        """Colors stay in [0, 255]."""
        p = COMPOSED_PATTERNS[0]
        for seed in range(20):
            r = p.generate(random.Random(seed), level=3, enemy_kind="SCOUT")
            for s in r.ships:
                assert s.color is not None
                for ch in s.color:
                    assert 0 <= ch <= 255, (
                        f"color channel {ch} out of [0,255] (seed={seed})"
                    )
