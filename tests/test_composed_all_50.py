"""BLOQUE 58.14.7 + 58.next: parametrize tests over all 50 ComposedPatterns.

Each ComposedPattern (one of 9 formations × 8 paths × 3 follow × counts 4-8 = 50)
should:
  - generate a non-empty WavePatternResult
  - have valid spawn positions (within playfield +/- a margin)
  - have valid colors (RGB tuple, channels 0-255)
  - have non-degenerate segments (no all-coincident points)
  - have a positive duration_s

Per-instance jitter (added in this BLOQUE) means the result depends on the
jitter seed. Tests pass a fixed jitter_seed for reproducibility.
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
from src.systems.wave_patterns.base import (
    PatternDifficulty, WavePatternKind, WavePatternResult, SpawnedShip,
)
from src.core.settings import INTERNAL_W, INTERNAL_H


# --- Fixtures & helpers ---

def _all_names():
    """Yield (index, name) for every ComposedPattern in the global pool."""
    return [(i, p.name) for i, p in enumerate(COMPOSED_PATTERNS)]


def _playfield_bounds(margin: float = 80.0):
    """Valid spawn region (with margin for off-screen entry)."""
    return (-margin, INTERNAL_W + margin, -margin, INTERNAL_H + margin)


# --- Pool sanity (one-time, not parametrized) ---

class TestComposedPool:
    def test_exactly_50_patterns(self):
        assert len(COMPOSED_PATTERNS) == 50, (
            f"Expected 50 ComposedPatterns, got {len(COMPOSED_PATTERNS)}"
        )

    def test_all_have_unique_names(self):
        names = [p.name for p in COMPOSED_PATTERNS]
        assert len(names) == len(set(names)), (
            f"Duplicate names in COMPOSED_PATTERNS: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_all_kind_is_composed(self):
        from src.systems.wave_patterns.base import WavePatternKind
        for p in COMPOSED_PATTERNS:
            assert p.kind == WavePatternKind.COMPOSED, (
                f"{p.name}: kind is {p.kind}, expected COMPOSED"
            )

    def test_all_difficulty_set(self):
        for p in COMPOSED_PATTERNS:
            assert isinstance(p.difficulty, PatternDifficulty), (
                f"{p.name}: bad difficulty {p.difficulty!r}"
            )


# --- Parametrized: each of the 50 generates a valid result ---

@pytest.mark.parametrize("idx,name", _all_names(),
                         ids=[n for _, n in _all_names()])
def test_composed_generates_non_empty_result(idx, name):
    """Each of the 50 must produce a WavePatternResult with >= 1 ship."""
    p = COMPOSED_PATTERNS[idx]
    rng = random.Random(42)
    result = p.generate(rng, level=3, enemy_kind="SCOUT")
    assert isinstance(result, WavePatternResult)
    assert len(result.ships) >= 1, f"{name}: empty ships list"


@pytest.mark.parametrize("idx,name", _all_names(),
                         ids=[n for _, n in _all_names()])
def test_composed_ships_have_valid_spawn_positions(idx, name):
    """All ship spawn positions within the playfield (with margin for entry)."""
    p = COMPOSED_PATTERNS[idx]
    rng = random.Random(42)
    result = p.generate(rng, level=3, enemy_kind="SCOUT")
    xmin, xmax, ymin, ymax = _playfield_bounds(margin=120.0)
    for s in result.ships:
        assert xmin <= s.spawn_x <= xmax, (
            f"{name}: ship spawn_x={s.spawn_x} out of [{xmin}, {xmax}]"
        )
        assert ymin <= s.spawn_y <= ymax, (
            f"{name}: ship spawn_y={s.spawn_y} out of [{ymin}, {ymax}]"
        )


@pytest.mark.parametrize("idx,name", _all_names(),
                         ids=[n for _, n in _all_names()])
def test_composed_ships_have_valid_colors(idx, name):
    """All ship colors are RGB tuples with channels in [0, 255]."""
    p = COMPOSED_PATTERNS[idx]
    rng = random.Random(42)
    result = p.generate(rng, level=3, enemy_kind="SCOUT")
    for s in result.ships:
        assert s.color is not None, f"{name}: ship {s.slot} has no color"
        assert len(s.color) == 3, f"{name}: ship {s.slot} bad color {s.color}"
        for ch in s.color:
            assert 0 <= ch <= 255, (
                f"{name}: ship {s.slot} color channel {ch} out of range"
            )


@pytest.mark.parametrize("idx,name", _all_names(),
                         ids=[n for _, n in _all_names()])
def test_composed_segments_non_degenerate(idx, name):
    """Segments (4-tuples of points) must have at least some non-coincident
    consecutive points — i.e., not a zero-length path."""
    p = COMPOSED_PATTERNS[idx]
    rng = random.Random(42)
    result = p.generate(rng, level=3, enemy_kind="SCOUT")
    for s in result.ships:
        segs = s.extra.get("segments", [])
        assert segs, f"{name}: ship {s.slot} has no segments"
        # At least one segment must have a real (>=1px) span
        max_span = 0.0
        for seg in segs:
            for i in range(3):
                x0, y0 = seg[i]
                x1, y1 = seg[i + 1]
                span = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                if span > max_span:
                    max_span = span
        assert max_span >= 1.0, (
            f"{name}: ship {s.slot} segments are all degenerate (max span {max_span:.2f})"
        )


@pytest.mark.parametrize("idx,name", _all_names(),
                         ids=[n for _, n in _all_names()])
def test_composed_duration_positive(idx, name):
    """duration_s must be > 0."""
    p = COMPOSED_PATTERNS[idx]
    rng = random.Random(42)
    result = p.generate(rng, level=3, enemy_kind="SCOUT")
    assert result.duration_s > 0, f"{name}: duration_s={result.duration_s}"


@pytest.mark.parametrize("idx,name", _all_names(),
                         ids=[n for _, n in _all_names()])
def test_composed_has_follow_formation_path(idx, name):
    """Each ship carries formation/path/follow in extra (the contract that
    runtime.attach_multi_segment_path reads)."""
    p = COMPOSED_PATTERNS[idx]
    rng = random.Random(42)
    result = p.generate(rng, level=3, enemy_kind="SCOUT")
    for s in result.ships:
        assert "formation" in s.extra, f"{name}: missing formation in extra"
        assert "path" in s.extra, f"{name}: missing path in extra"
        assert "follow" in s.extra, f"{name}: missing follow in extra"
        assert "segments" in s.extra, f"{name}: missing segments in extra"
        assert "segment_durations" in s.extra, (
            f"{name}: missing segment_durations in extra"
        )


# --- Determinism (one per pattern) ---

@pytest.mark.parametrize("idx,name", _all_names(),
                         ids=[n for _, n in _all_names()])
def test_composed_deterministic_with_same_seed(idx, name):
    """Same seed + level -> same ship count + duration."""
    p = COMPOSED_PATTERNS[idx]
    a = p.generate(random.Random(42), level=3, enemy_kind="SCOUT")
    b = p.generate(random.Random(42), level=3, enemy_kind="SCOUT")
    assert len(a.ships) == len(b.ships), (
        f"{name}: ship count differs ({len(a.ships)} vs {len(b.ships)})"
    )
    assert a.duration_s == pytest.approx(b.duration_s, abs=0.01), (
        f"{name}: duration differs ({a.duration_s} vs {b.duration_s})"
    )


# --- Difficulty matches the count (the contract from _DIFFICULTY_BY_COUNT) ---

class TestComposedDifficulty:
    @pytest.mark.parametrize("idx,name", _all_names(),
                             ids=[n for _, n in _all_names()])
    def test_difficulty_matches_count(self, idx, name):
        p = COMPOSED_PATTERNS[idx]
        # Extract count from name (e.g., "line_sweep_leader_n5" -> 5)
        n_str = name.rsplit("_n", 1)[-1]
        count = int(n_str)
        if count <= 5:
            assert p.difficulty == PatternDifficulty.EASY, (
                f"{name}: count={count} should be EASY, got {p.difficulty}"
            )
        elif count <= 7:
            assert p.difficulty == PatternDifficulty.MEDIUM, (
                f"{name}: count={count} should be MEDIUM, got {p.difficulty}"
            )
        else:
            assert p.difficulty == PatternDifficulty.HARD, (
                f"{name}: count={count} should be HARD, got {p.difficulty}"
            )
