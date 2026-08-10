"""Distribution telemetry (BLOQUE 57).

Tracks run-level statistics over a sliding window:
  - family_distribution: count per formation family
  - seed_uniqueness: how many unique master seeds seen
  - replay_fidelity: % of replays that matched the original (caller-reported)
  - pattern_diversity: count of unique formation point sets
  - entropy_per_run: Shannon entropy of family distribution

State is JSON-serializable for offline analysis. Optional persistence
to data/roguelike_stats.json.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.roguelike.formation_generator import FormationFamily


DEFAULT_STATS_PATH: str = "data/roguelike_stats.json"


def shannon_entropy(counts: dict[str, int]) -> float:
    """Shannon entropy in bits. H = -sum p * log2(p). 0 if empty."""
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


@dataclass
class DistributionTelemetry:
    """In-memory stats for the procedural generator. Persists to JSON.

    record_run() feeds samples; get_stats() returns aggregate metrics;
    reset() clears all state.
    """
    max_runs: int = 1000
    persist_path: str | None = DEFAULT_STATS_PATH
    _run_count: int = 0
    _family_counter: Counter[FormationFamily] = field(default_factory=Counter)
    _unique_seeds: set[int] = field(default_factory=set)
    _patterns: set[tuple[tuple[float, float], ...]] = field(default_factory=set)
    _replay_matches: int = 0
    _replay_total: int = 0

    def record_run(
        self,
        seed: int,
        run_summary: dict[str, Any],
    ) -> None:
        """Record one completed run. `run_summary` may contain:
        - "formations": list of {"family": FormationFamily, "points": list}
        - "replay_match": bool (optional, for replay_fidelity tracking)
        """
        self._run_count += 1
        self._unique_seeds.add(int(seed))
        for entry in run_summary.get("formations", []):
            family = entry["family"]
            points = entry.get("points", [])
            self._family_counter[family] += 1
            pt_hash = tuple((round(x, 1), round(y, 1)) for x, y in points)
            self._patterns.add(pt_hash)
        if "replay_match" in run_summary:
            self._replay_total += 1
            if run_summary["replay_match"]:
                self._replay_matches += 1
        # Cap memory: if too many runs, drop the oldest family counts
        # proportionally. We don't track per-run history beyond the
        # counter, so there's nothing else to trim.
        if self._run_count > self.max_runs:
            # Halve all counts to keep things bounded. New runs will
            # re-inflate them. This is a rough sliding window.
            for k in list(self._family_counter.keys()):
                self._family_counter[k] = self._family_counter[k] // 2

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate stats. Always safe to call."""
        family_dict: dict[str, int] = {
            f.value: c for f, c in self._family_counter.items()
        }
        return {
            "run_count": self._run_count,
            "family_distribution": family_dict,
            "seed_uniqueness": len(self._unique_seeds),
            "replay_fidelity": (
                self._replay_matches / self._replay_total
                if self._replay_total > 0
                else 1.0
            ),
            "pattern_diversity": len(self._patterns),
            "entropy_per_run": shannon_entropy(family_dict),
        }

    def reset(self) -> None:
        """Clear all in-memory stats."""
        self._run_count = 0
        self._family_counter.clear()
        self._unique_seeds.clear()
        self._patterns.clear()
        self._replay_matches = 0
        self._replay_total = 0

    def save(self, path: str | None = None) -> None:
        """Persist current stats to JSON. No-op if persist_path is None."""
        path = path or self.persist_path
        if not path:
            return
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("w", encoding="utf-8") as f:
                json.dump(self.get_stats(), f, sort_keys=True, indent=2)
        except OSError:
            # Best-effort. Don't crash on disk errors.
            pass
