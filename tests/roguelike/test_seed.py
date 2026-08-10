"""Tests for src.roguelike.seed (BLOQUE 57)."""
from __future__ import annotations

import pytest

from src.roguelike.seed import RoguelikeSeed, splitmix64, splitmix64_value


# ---------------------------------------------------------------------------
# 1. Derive determinism + uniqueness
# ---------------------------------------------------------------------------
def test_derive_game_seed_deterministic() -> None:
    s1 = RoguelikeSeed.derive(level_idx=1, attempt_number=1, salt=42)
    s2 = RoguelikeSeed.derive(level_idx=1, attempt_number=1, salt=42)
    assert s1 == s2
    assert s1.master == s2.master


def test_derive_different_salt_different_seed() -> None:
    s1 = RoguelikeSeed.derive(level_idx=1, attempt_number=1, salt=42)
    s2 = RoguelikeSeed.derive(level_idx=1, attempt_number=1, salt=43)
    assert s1.master != s2.master


def test_derive_different_level_different_seed() -> None:
    s1 = RoguelikeSeed.derive(level_idx=1, attempt_number=1, salt=42)
    s2 = RoguelikeSeed.derive(level_idx=2, attempt_number=1, salt=42)
    assert s1.master != s2.master


# ---------------------------------------------------------------------------
# 2. Per-wave / per-slot uniqueness
# ---------------------------------------------------------------------------
def test_derive_wave_seed_unique_per_wave() -> None:
    game = RoguelikeSeed.derive(1, 1, 42)
    seeds = {game.derive_wave_seed(w) for w in range(10)}
    assert len(seeds) == 10, "All 10 wave seeds should be unique"


def test_derive_slot_seed_unique_per_slot() -> None:
    game = RoguelikeSeed.derive(1, 1, 42)
    slot_seeds = {game.derive_slot_seed(0, s) for s in range(20)}
    assert len(slot_seeds) == 20


# ---------------------------------------------------------------------------
# 3. Sub-seed types are independent
# ---------------------------------------------------------------------------
def test_audio_drop_particle_seeds_distinct() -> None:
    game = RoguelikeSeed.derive(1, 1, 42)
    audio = game.derive_audio_seed()
    drop = game.derive_drop_seed()
    particle = game.derive_particle_seed()
    # All 3 should be distinct from each other and from the master
    seeds = {audio, drop, particle, game.master}
    assert len(seeds) == 4


# ---------------------------------------------------------------------------
# 4. JSON round-trip
# ---------------------------------------------------------------------------
def test_serialize_json_round_trip() -> None:
    s = RoguelikeSeed.derive(level_idx=2, attempt_number=3, salt=99)
    j = s.to_json()
    loaded = RoguelikeSeed.from_json(j)
    assert s == loaded
    assert s.master == loaded.master


# ---------------------------------------------------------------------------
# 5. Out-of-range validation
# ---------------------------------------------------------------------------
def test_invalid_inputs_raise() -> None:
    with pytest.raises(ValueError, match="level_idx"):
        RoguelikeSeed.derive(level_idx=-1, attempt_number=1, salt=0)
    with pytest.raises(ValueError, match="attempt_number"):
        RoguelikeSeed.derive(level_idx=1, attempt_number=0, salt=0)
    with pytest.raises(ValueError, match="salt"):
        RoguelikeSeed.derive(level_idx=1, attempt_number=1, salt=-1)


# ---------------------------------------------------------------------------
# 6. splitmix64 properties
# ---------------------------------------------------------------------------
def test_splitmix64_period_2_64() -> None:
    """splitmix64 has period 2^64 — at most 2^64 unique outputs before
    the state wraps. We just verify that 1000 steps produce 1000 unique
    values (the period is so large we never see repeats in any test)."""
    state = 0
    values = set()
    for _ in range(1000):
        state, v = splitmix64(state)
        assert v not in values, "Repeat after 1000 steps (should not happen)"
        values.add(v)


def test_splitmix64_handles_zero_seed() -> None:
    """splitmix64 has no attractor at seed=0 (unlike some other PRNGs)."""
    v1 = splitmix64_value(0)
    v2 = splitmix64_value(1)
    assert v1 != v2
    assert v1 != 0
