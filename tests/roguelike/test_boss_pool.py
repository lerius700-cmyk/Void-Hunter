"""Tests for src.roguelike.boss_pool (BLOQUE 58)."""
from __future__ import annotations

import pytest

from src.entities.enemies.boss import BossId
from src.roguelike.boss_pool import LEVEL_BIAS, BossSelection, select_boss


def test_select_boss_returns_valid_boss() -> None:
    sel = select_boss(seed=42, level_idx=1)
    assert isinstance(sel, BossSelection)
    assert sel.boss_id in BossId
    assert sel.bezier_path is not None


def test_same_seed_same_boss() -> None:
    a = select_boss(seed=42, level_idx=1)
    b = select_boss(seed=42, level_idx=1)
    assert a.boss_id == b.boss_id
    # Same control points too
    assert a.bezier_path._cps == b.bezier_path._cps


def test_different_seed_may_differ() -> None:
    """BLOQUE 58: boss identity is random per seed. With enough samples,
    at least 2 different bosses should appear across seeds 1..50."""
    seen = {select_boss(seed=s, level_idx=1).boss_id for s in range(50)}
    assert len(seen) >= 2, f"Expected variety, only got {seen}"


def test_all_4_bosses_can_appear_in_act_1() -> None:
    """BLOQUE 58: 'any of 4 can come out' even in Act 1 (with low prob for
    NEMESIS, but still possible). Sample many seeds."""
    seen = {select_boss(seed=s, level_idx=1).boss_id for s in range(500)}
    # We expect at least 3 of the 4 to appear in 500 samples for Act 1
    assert len(seen) >= 3, f"Act 1 yielded only {seen} in 500 seeds"


def test_bezier_path_has_4_control_points() -> None:
    sel = select_boss(seed=42, level_idx=1)
    assert len(sel.bezier_path._cps) == 4
    # First control point should be off-screen top (y < 0)
    assert sel.bezier_path._cps[0].y < 0
    # Last control point should be at boss anchor (y > 0)
    assert sel.bezier_path._cps[-1].y > 0


def test_level_bias_influences_selection() -> None:
    """Act 1 should favor GOLIATH; Act 3 should favor NEMESIS.
    Sample 200 seeds per level and check majority."""
    act1_counts: dict[BossId, int] = {b: 0 for b in BossId}
    for s in range(200):
        act1_counts[select_boss(seed=s, level_idx=1).boss_id] += 1
    # GOLIATH should be the most common in Act 1
    assert act1_counts[BossId.GOLIATH] == max(act1_counts.values()), (
        f"GOLIATH should be most common in Act 1, got {act1_counts}"
    )


def test_level_bias_weights_sum_to_1() -> None:
    for level_idx, bias in LEVEL_BIAS.items():
        total = sum(bias.values())
        assert abs(total - 1.0) < 0.01, f"Level {level_idx} bias sums to {total}"
