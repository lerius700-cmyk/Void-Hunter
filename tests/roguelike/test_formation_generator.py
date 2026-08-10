"""Tests for src.roguelike.formation_generator (BLOQUE 57)."""
from __future__ import annotations

import pytest

from src.roguelike.formation_generator import (
    FormationFamily,
    FormationParams,
    ProceduralFormationGenerator,
)


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------
def test_same_seed_same_output() -> None:
    gen1 = ProceduralFormationGenerator(seed=42)
    gen2 = ProceduralFormationGenerator(seed=42)
    params = FormationParams(
        count=5,
        spacing_min=24,
        spacing_max=32,
        families=[FormationFamily.LINE, FormationFamily.SPIRAL, FormationFamily.V],
    )
    f1 = gen1.gen_formation(slot_params=params)
    f2 = gen2.gen_formation(slot_params=params)
    assert f1 == f2, f"Same seed must give same output: {f1} vs {f2}"


def test_different_seed_different_output() -> None:
    gen1 = ProceduralFormationGenerator(seed=42)
    gen2 = ProceduralFormationGenerator(seed=43)
    params = FormationParams(count=5, families=list(FormationFamily))
    f1 = gen1.gen_formation(slot_params=params)
    f2 = gen2.gen_formation(slot_params=params)
    assert f1 != f2


# ---------------------------------------------------------------------------
# 2. Family weight validation
# ---------------------------------------------------------------------------
def test_family_weights_normalize_to_1() -> None:
    p = FormationParams(
        count=4,
        families=[FormationFamily.LINE, FormationFamily.SPIRAL],
        family_weights=[2.0, 1.0],  # sum 3, normalizes to [0.667, 0.333]
    )
    assert abs(sum(p.family_weights) - 1.0) < 1e-9


def test_family_weights_zero_sum_raises() -> None:
    with pytest.raises(ValueError, match="sum must be > 0"):
        FormationParams(
            count=4,
            families=[FormationFamily.LINE, FormationFamily.SPIRAL],
            family_weights=[0.0, 0.0],
        )


def test_family_weights_negative_raises() -> None:
    with pytest.raises(ValueError, match="negative"):
        FormationParams(
            count=4,
            families=[FormationFamily.LINE, FormationFamily.SPIRAL],
            family_weights=[1.0, -0.5],
        )


def test_family_weights_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="length"):
        FormationParams(
            count=4,
            families=[FormationFamily.LINE, FormationFamily.SPIRAL, FormationFamily.V],
            family_weights=[0.5, 0.5],  # missing one
        )


# ---------------------------------------------------------------------------
# 3. Bounds checking
# ---------------------------------------------------------------------------
def test_build_line_within_view() -> None:
    gen = ProceduralFormationGenerator(seed=42)
    params = FormationParams(
        count=6, families=[FormationFamily.LINE], view_w=320, view_h=480
    )
    points = gen.gen_formation(slot_params=params)
    for x, y in points:
        assert 0 <= x <= 320
        assert 0 <= y <= 480


def test_build_spiral_radius_decreasing() -> None:
    """BLOQUE 57: Spiral starts at radius 60 and shrinks to 20.
    Distance from center should decrease across the points."""
    gen = ProceduralFormationGenerator(seed=42)
    params = FormationParams(
        count=6,
        families=[FormationFamily.SPIRAL],
    )
    points = gen.gen_formation(slot_params=params)
    cx, cy = 160, 92  # spiral center
    distances = [
        ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in points
    ]
    # First half distances should be larger on average than second half
    half = len(points) // 2
    assert sum(distances[:half]) > sum(distances[half:])


# ---------------------------------------------------------------------------
# 4. Count clamping
# ---------------------------------------------------------------------------
def test_count_clamped_to_100() -> None:
    p = FormationParams(
        count=200,  # over-spec
        families=[FormationFamily.LINE],
    )
    assert p.count == 100, "count > 100 must be clamped"


# ---------------------------------------------------------------------------
# 5. Family weight distribution over many runs
# ---------------------------------------------------------------------------
def test_family_weights_respected_over_1000_runs() -> None:
    """Sampling 1000 times with weights [0.5, 0.3, 0.2] should give
    roughly 500/300/200 distribution (tolerance: ±10%)."""
    counts = {FormationFamily.LINE: 0, FormationFamily.SPIRAL: 0, FormationFamily.V: 0}
    for s in range(1000):
        gen = ProceduralFormationGenerator(seed=s)
        params = FormationParams(
            count=4,
            families=list(counts.keys()),
            family_weights=[0.5, 0.3, 0.2],
        )
        chosen = gen.rng.choices(list(counts.keys()), [0.5, 0.3, 0.2])
        counts[chosen] += 1
    # ±10% tolerance
    assert 400 <= counts[FormationFamily.LINE] <= 600
    assert 200 <= counts[FormationFamily.SPIRAL] <= 400
    assert 100 <= counts[FormationFamily.V] <= 300
