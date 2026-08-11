"""Tests for src.roguelike.powerup_pool (BLOQUE 58)."""
from __future__ import annotations

import pytest

from src.roguelike.powerup_pool import (
    DEFAULT_WEIGHTS,
    PowerupDrop,
    PowerupKind,
    select_powerup,
)


def test_select_powerup_returns_valid_kind() -> None:
    drop = select_powerup(seed=42)
    assert isinstance(drop, PowerupDrop)
    assert drop.kind in PowerupKind


def test_same_seed_same_drop() -> None:
    a = select_powerup(seed=42)
    b = select_powerup(seed=42)
    assert a.kind == b.kind


def test_different_seeds_have_variety() -> None:
    seen = {select_powerup(seed=s).kind for s in range(50)}
    # At least 2 different powerups in 50 seeds
    assert len(seen) >= 2


def test_default_weights_sum_to_1() -> None:
    total = sum(DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 0.01


def test_gold_ring_is_most_common() -> None:
    """Default weights: gold_ring=0.50, the highest. After 200 samples
    it should be the most common drop."""
    counts: dict[PowerupKind, int] = {k: 0 for k in PowerupKind}
    for s in range(200):
        counts[select_powerup(seed=s).kind] += 1
    assert counts[PowerupKind.GOLD_RING] == max(counts.values()), (
        f"gold_ring should be most common, got {counts}"
    )


def test_nothing_is_rare() -> None:
    """NOTHING has weight 0.05 — should be the rarest in 200 samples."""
    counts: dict[PowerupKind, int] = {k: 0 for k in PowerupKind}
    for s in range(200):
        counts[select_powerup(seed=s).kind] += 1
    assert counts[PowerupKind.NOTHING] < counts[PowerupKind.GOLD_RING]
