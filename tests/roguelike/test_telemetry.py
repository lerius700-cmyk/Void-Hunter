"""Tests for src.roguelike.telemetry (BLOQUE 57)."""
from __future__ import annotations

import json
import pytest

from src.roguelike.formation_generator import FormationFamily
from src.roguelike.telemetry import DistributionTelemetry, shannon_entropy


# ---------------------------------------------------------------------------
# 1. Shannon entropy utility
# ---------------------------------------------------------------------------
def test_entropy_uniform_5_families() -> None:
    counts = {"a": 100, "b": 100, "c": 100, "d": 100, "e": 100}
    # H = log2(5) ~= 2.32
    h = shannon_entropy(counts)
    assert abs(h - 2.32) < 0.01


def test_entropy_single_family() -> None:
    counts = {"a": 100}
    h = shannon_entropy(counts)
    assert h == 0.0  # No entropy if all one family


def test_entropy_empty() -> None:
    assert shannon_entropy({}) == 0.0


# ---------------------------------------------------------------------------
# 2. record_run
# ---------------------------------------------------------------------------
def test_record_run_increments() -> None:
    tel = DistributionTelemetry()
    for i in range(5):
        tel.record_run(seed=i, run_summary={
            "formations": [
                {"family": FormationFamily.LINE, "points": [(10.0, 16.0)]}
            ]
        })
    stats = tel.get_stats()
    assert stats["run_count"] == 5
    assert stats["family_distribution"]["line"] == 5


def test_record_run_tracks_seeds_and_patterns() -> None:
    tel = DistributionTelemetry()
    tel.record_run(seed=1, run_summary={
        "formations": [{"family": FormationFamily.LINE, "points": [(10.0, 16.0)]}]
    })
    tel.record_run(seed=2, run_summary={
        "formations": [{"family": FormationFamily.SPIRAL, "points": [(50.0, 50.0)]}]
    })
    stats = tel.get_stats()
    assert stats["seed_uniqueness"] == 2
    assert stats["pattern_diversity"] == 2


def test_record_run_replay_fidelity() -> None:
    tel = DistributionTelemetry()
    for _ in range(3):
        tel.record_run(seed=0, run_summary={"replay_match": True})
    tel.record_run(seed=0, run_summary={"replay_match": False})
    stats = tel.get_stats()
    assert abs(stats["replay_fidelity"] - 0.75) < 0.01


# ---------------------------------------------------------------------------
# 3. get_stats
# ---------------------------------------------------------------------------
def test_get_stats_returns_dict() -> None:
    tel = DistributionTelemetry()
    stats = tel.get_stats()
    assert "run_count" in stats
    assert "family_distribution" in stats
    assert "seed_uniqueness" in stats
    assert "replay_fidelity" in stats
    assert "pattern_diversity" in stats
    assert "entropy_per_run" in stats


# ---------------------------------------------------------------------------
# 4. Persistence
# ---------------------------------------------------------------------------
def test_save_to_json(tmp_path) -> None:
    p = tmp_path / "stats.json"
    tel = DistributionTelemetry(persist_path=str(p))
    tel.record_run(seed=1, run_summary={
        "formations": [{"family": FormationFamily.LINE, "points": [(10.0, 16.0)]}]
    })
    tel.save()
    assert p.exists()
    with p.open() as f:
        data = json.load(f)
    assert data["run_count"] == 1


def test_reset_clears_state() -> None:
    tel = DistributionTelemetry()
    tel.record_run(seed=1, run_summary={})
    tel.record_run(seed=2, run_summary={})
    tel.reset()
    stats = tel.get_stats()
    assert stats["run_count"] == 0
    assert stats["seed_uniqueness"] == 0
