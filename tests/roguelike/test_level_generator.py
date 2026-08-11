"""Tests for src.roguelike.level_generator (BLOQUE 58)."""
from __future__ import annotations

import pytest

from src.roguelike.level_generator import (
    LEVEL_SHIP_COUNTS,
    LevelEventKind,
    ProceduralLevel,
    generate_procedural_level,
)


# ---------------------------------------------------------------------------
# 1. Structure
# ---------------------------------------------------------------------------
def test_generates_4_waves_per_level() -> None:
    level = generate_procedural_level(level_idx=1, seed=42)
    assert len(level.waves()) == 4


def test_sub_boss_at_fixed_position() -> None:
    """BLOQUE 58 invariant: sub-boss after wave 2 (event index 4: wave 1,
    powerup, wave 2, powerup, SUB_BOSS)."""
    level = generate_procedural_level(level_idx=1, seed=42)
    sub = level.sub_boss()
    assert sub is not None
    # Sub-boss comes after wave_idx=1 (the 2nd wave, 0-indexed)
    assert sub.kind == LevelEventKind.SUB_BOSS


def test_final_boss_at_end() -> None:
    level = generate_procedural_level(level_idx=1, seed=42)
    final = level.final_boss()
    assert final is not None
    assert final.kind == LevelEventKind.FINAL_BOSS
    # Should be the LAST event
    assert level.events[-1].kind == LevelEventKind.FINAL_BOSS


# ---------------------------------------------------------------------------
# 2. INVARIANTS: ship counts are FIXED
# ---------------------------------------------------------------------------
def test_ship_counts_are_fixed_per_level() -> None:
    """BLOQUE 58 invariant: ship counts do NOT change between seeds."""
    counts_a = [w.formation["count"] for w in generate_procedural_level(1, 42).waves()]
    counts_b = [w.formation["count"] for w in generate_procedural_level(1, 99).waves()]
    assert counts_a == counts_b
    assert counts_a == LEVEL_SHIP_COUNTS[1]


def test_ship_counts_match_table() -> None:
    level = generate_procedural_level(level_idx=1, seed=42)
    counts = [w.formation["count"] for w in level.waves()]
    assert counts == [12, 19, 14, 17]


# ---------------------------------------------------------------------------
# 3. Procedural content varies by seed
# ---------------------------------------------------------------------------
def test_formation_type_varies_by_seed() -> None:
    """BLOQUE 58: formation type IS randomized per seed."""
    a = [w.formation["formation_type"] for w in generate_procedural_level(1, 42).waves()]
    b = [w.formation["formation_type"] for w in generate_procedural_level(1, 99).waves()]
    # Different seeds should give different formations
    assert a != b


def test_same_seed_same_level() -> None:
    """Acceptance demo: same seed -> same level structure."""
    a = generate_procedural_level(level_idx=1, seed=42)
    b = generate_procedural_level(level_idx=1, seed=42)
    # Compare event types + formation types + counts
    a_summary = [(e.kind, e.formation["formation_type"] if e.formation else None) for e in a.events]
    b_summary = [(e.kind, e.formation["formation_type"] if e.formation else None) for e in b.events]
    assert a_summary == b_summary


# ---------------------------------------------------------------------------
# 4. Powerup drops
# ---------------------------------------------------------------------------
def test_powerup_drops_between_waves() -> None:
    """BLOQUE 58: powerup drops happen between waves (3 drops in 4 waves)."""
    level = generate_procedural_level(level_idx=1, seed=42)
    drops = level.powerup_drops()
    assert len(drops) == 3  # 4 waves => 3 powerup drops (between them)


# ---------------------------------------------------------------------------
# 5. Boss pool integration
# ---------------------------------------------------------------------------
def test_sub_boss_has_bezier_entrance() -> None:
    level = generate_procedural_level(level_idx=1, seed=42)
    sub = level.sub_boss()
    assert sub.boss_selection.bezier_path is not None


def test_final_boss_has_bezier_entrance() -> None:
    level = generate_procedural_level(level_idx=1, seed=42)
    final = level.final_boss()
    assert final.boss_selection.bezier_path is not None
    # Should have 4 control points (cubic)
    assert len(final.boss_selection.bezier_path._cps) == 4


# ---------------------------------------------------------------------------
# 6. Multiple levels
# ---------------------------------------------------------------------------
def test_act_1_ship_counts() -> None:
    level = generate_procedural_level(level_idx=1, seed=42)
    counts = [w.formation["count"] for w in level.waves()]
    assert counts == [12, 19, 14, 17]


def test_act_2_ship_counts() -> None:
    level = generate_procedural_level(level_idx=2, seed=42)
    counts = [w.formation["count"] for w in level.waves()]
    assert counts == [15, 22, 18, 20]


def test_act_3_ship_counts() -> None:
    level = generate_procedural_level(level_idx=3, seed=42)
    counts = [w.formation["count"] for w in level.waves()]
    assert counts == [18, 25, 22, 24]


# ---------------------------------------------------------------------------
# 7. Default seed
# ---------------------------------------------------------------------------
def test_default_seed_derives_from_level() -> None:
    level = generate_procedural_level(level_idx=2, seed=None)
    assert level.seed > 0
    # Deterministic: same call gives same seed
    again = generate_procedural_level(level_idx=2, seed=None)
    assert level.seed == again.seed
