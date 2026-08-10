"""Tests for src.roguelike.anti_stuck (BLOQUE 57)."""
from __future__ import annotations

from src.roguelike.anti_stuck import StuckPatternDetector
from src.roguelike.formation_generator import FormationFamily


# ---------------------------------------------------------------------------
# 1. Recording
# ---------------------------------------------------------------------------
def test_record_formation_increments() -> None:
    det = StuckPatternDetector()
    for i in range(10):
        det.record_formation(i, FormationFamily.LINE, [(i * 10.0, 16.0)])
    stats = det.check_distribution()
    assert stats["count"] == 10
    assert stats["family_counts"].get("line") == 10


# ---------------------------------------------------------------------------
# 2. Distribution check
# ---------------------------------------------------------------------------
def test_check_distribution_window() -> None:
    det = StuckPatternDetector()
    for i in range(100):
        det.record_formation(i, FormationFamily.LINE, [(10.0, 16.0)])
    for i in range(50):
        det.record_formation(i, FormationFamily.SPIRAL, [(20.0, 20.0)])
    stats = det.check_distribution()
    assert stats["count"] == 150
    assert stats["family_counts"].get("line") == 100
    assert stats["family_counts"].get("spiral") == 50


def test_deviation_pct_calculated() -> None:
    det = StuckPatternDetector(
        target_distribution={FormationFamily.LINE: 0.5, FormationFamily.SPIRAL: 0.5}
    )
    for _ in range(50):
        det.record_formation(0, FormationFamily.LINE, [(10.0, 16.0)])
    for _ in range(50):
        det.record_formation(0, FormationFamily.SPIRAL, [(20.0, 20.0)])
    stats = det.check_distribution()
    assert stats["deviation_pct"] < 0.01  # perfect 50/50


# ---------------------------------------------------------------------------
# 3. Stuck pattern detection
# ---------------------------------------------------------------------------
def test_is_stuck_pattern_correct() -> None:
    det = StuckPatternDetector(default_streak_k=5)
    for _ in range(4):
        det.record_formation(0, FormationFamily.LINE, [(10.0, 16.0)])
    # 4 in a row, not stuck yet
    assert not det.is_stuck_pattern(FormationFamily.LINE)
    # 5 in a row, stuck
    det.record_formation(0, FormationFamily.LINE, [(10.0, 16.0)])
    assert det.is_stuck_pattern(FormationFamily.LINE)


def test_is_stuck_pattern_resets_on_change() -> None:
    det = StuckPatternDetector(default_streak_k=3)
    det.record_formation(0, FormationFamily.LINE, [(0.0, 0.0)])
    det.record_formation(0, FormationFamily.LINE, [(0.0, 0.0)])
    det.record_formation(0, FormationFamily.SPIRAL, [(0.0, 0.0)])
    # Now last 3 = [LINE, LINE, SPIRAL]; not stuck on LINE
    assert not det.is_stuck_pattern(FormationFamily.LINE)
    assert not det.is_stuck_pattern(FormationFamily.SPIRAL)


# ---------------------------------------------------------------------------
# 4. Reset
# ---------------------------------------------------------------------------
def test_reset_clears_history() -> None:
    det = StuckPatternDetector()
    for i in range(10):
        det.record_formation(i, FormationFamily.LINE, [(0.0, 0.0)])
    det.reset()
    stats = det.check_distribution()
    assert stats["count"] == 0
