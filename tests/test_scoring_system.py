"""Tests for src.systems.scoring_system (BLOQUE 11)."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.core.settings import (
    ELEMENT_BONUS,
    MULTIPLIER_DECAY_S,
    MULTIPLIER_MAX,
    STREAK_BONUS_WINDOW_S,
)
from src.systems.scoring_system import (
    MULTIPLIER_STEPS,
    HighScore,
    ScoringSystem,
)


@pytest.fixture
def s() -> ScoringSystem:
    return ScoringSystem()


# ---------------------------------------------------------------------------
# 1. Multiplier chain
# ---------------------------------------------------------------------------
def test_initial_multiplier_is_1x(s: ScoringSystem) -> None:
    assert s.multiplier == 1


def test_kill_increments_multiplier(s: ScoringSystem) -> None:
    s.on_kill(100)
    assert s.multiplier == 2


def test_kill_chain_progresses(s: ScoringSystem) -> None:
    expected = [2, 4, 8, 16]
    for exp in expected:
        s.on_kill(50)
        assert s.multiplier == exp


def test_multiplier_caps_at_16(s: ScoringSystem) -> None:
    for _ in range(10):
        s.on_kill(50)
    assert s.multiplier == MULTIPLIER_MAX == 16


def test_element_bonus_kill_jumps_2_steps(s: ScoringSystem) -> None:
    s.on_kill(50, is_element_bonus=True)
    assert s.multiplier == 4


def test_boss_kill_jumps_5_steps(s: ScoringSystem) -> None:
    s.on_kill(1000, is_boss=True)
    assert s.multiplier >= 16  # jumps 5 steps from 1


def test_decay_returns_to_1x(s: ScoringSystem) -> None:
    s.on_kill(100)
    s.update(MULTIPLIER_DECAY_S + 0.1)
    assert s.multiplier == 1


# ---------------------------------------------------------------------------
# 2. Element bonus multiplier
# ---------------------------------------------------------------------------
def test_element_bonus_multiplies_score(s: ScoringSystem) -> None:
    """base=100, mult=2, element_bonus=1.5 → 100*2*1.5 = 300."""
    s.on_kill(100, is_element_bonus=True)
    # Note: element_bonus kill also adds 2 to mult: 1 -> 4
    # 100 * 4 * 1.5 = 600
    assert s.score == 600


def test_non_element_bonus_no_extra_multiplier(s: ScoringSystem) -> None:
    s.on_kill(100)  # mult -> 2, no bonus
    assert s.score == 200


# ---------------------------------------------------------------------------
# 3. Streak bonuses
# ---------------------------------------------------------------------------
def test_streak_10_kills_bonus(s: ScoringSystem) -> None:
    for _ in range(10):
        s.on_kill(50)
    # Streak bonus = 500
    assert s.on_streak_bonus == 500


def test_streak_25_kills_bonus(s: ScoringSystem) -> None:
    for _ in range(25):
        s.on_kill(50)
    assert s.on_streak_bonus == 2500


def test_streak_50_kills_bonus(s: ScoringSystem) -> None:
    for _ in range(50):
        s.on_kill(50)
    assert s.on_streak_bonus == 5000


def test_streak_window_resets_after_3s(s: ScoringSystem) -> None:
    s.on_kill(50)
    s.streak_count = 1
    s.update(STREAK_BONUS_WINDOW_S + 0.1)
    assert s.streak_count == 0


# ---------------------------------------------------------------------------
# 4. Rank calculation
# ---------------------------------------------------------------------------
def test_rank_D_low_score(s: ScoringSystem) -> None:
    s.score = 1000
    assert s.compute_rank() == "D"


def test_rank_C(s: ScoringSystem) -> None:
    s.score = 7000
    assert s.compute_rank() == "C"


def test_rank_SSS(s: ScoringSystem) -> None:
    s.score = 100000
    assert s.compute_rank() == "SSS"


# ---------------------------------------------------------------------------
# 5. Max multiplier signal
# ---------------------------------------------------------------------------
def test_max_multiplier_signal(s: ScoringSystem) -> None:
    for _ in range(4):
        s.on_kill(50)
    assert s.on_max_multiplier is True


def test_max_multiplier_recorded(s: ScoringSystem) -> None:
    for _ in range(4):
        s.on_kill(50)
    assert s.max_multiplier == 16


# ---------------------------------------------------------------------------
# 6. High-score JSON
# ---------------------------------------------------------------------------
def test_to_highscore_has_required_fields(s: ScoringSystem) -> None:
    s.score = 12345
    s.kills = 100
    s.path = "plasma"
    s.player_name = "TestPlayer"
    hs = s.to_highscore()
    assert hs.ship == "void_hunter_v1"
    assert hs.path == "plasma"
    assert hs.score == 12345
    assert hs.kills == 100
    assert hs.player_name == "TestPlayer"
    assert hs.timestamp_iso != ""


def test_save_highscore_atomic_write(s: ScoringSystem, tmp_path: Path) -> None:
    s.score = 5000
    s.kills = 50
    f = tmp_path / "highscore.json"
    assert s.save_highscore(f) is True
    assert f.exists()
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["score"] == 5000


def test_save_highscore_creates_parent_dir(s: ScoringSystem, tmp_path: Path) -> None:
    f = tmp_path / "subdir" / "highscore.json"
    assert s.save_highscore(f) is True
    assert f.exists()


# ---------------------------------------------------------------------------
# 7. Death + bomb tracking
# ---------------------------------------------------------------------------
def test_on_death_increments(s: ScoringSystem) -> None:
    s.on_death()
    s.on_death()
    assert s.deaths == 2


def test_on_bomb_increments(s: ScoringSystem) -> None:
    s.on_bomb()
    s.on_bomb()
    s.on_bomb()
    assert s.bombs_used == 3


# ---------------------------------------------------------------------------
# 8. Boss defeated
# ---------------------------------------------------------------------------
def test_on_boss_defeated_tracks(s: ScoringSystem) -> None:
    s.on_boss_defeated("goliath")
    s.on_boss_defeated("hydra")
    assert s.bosses_defeated == ["goliath", "hydra"]


# ---------------------------------------------------------------------------
# 9. Reset
# ---------------------------------------------------------------------------
def test_reset_clears_score(s: ScoringSystem) -> None:
    s.on_kill(100)
    s.on_kill(100)
    s.reset()
    assert s.score == 0
    assert s.multiplier == 1
    assert s.kills == 0


# ---------------------------------------------------------------------------
# 10. Multiplier steps table
# ---------------------------------------------------------------------------
def test_multiplier_steps() -> None:
    assert MULTIPLIER_STEPS == (1, 2, 4, 8, 16)


def test_multiplier_max_constant() -> None:
    assert MULTIPLIER_MAX == 16


def test_decay_constant() -> None:
    assert MULTIPLIER_DECAY_S == 1.5


def test_element_bonus_constant() -> None:
    assert ELEMENT_BONUS == 1.5
