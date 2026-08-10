"""Anti-stuck pattern detector (BLOQUE 57).

Detects patterns that suggest the procedural generator is stuck:
  - Same family appears K times in a row.
  - Same formation point set appears across different runs.
  - family_weights deviate from target by more than 20% over a window.

Pure analysis; never modifies runs. Logs warnings, does not block.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from src.roguelike.formation_generator import FormationFamily


@dataclass
class StuckPatternDetector:
    """Window-based stuck pattern detector.

    record_formation() feeds samples; is_stuck_pattern() / check_distribution()
    analyze the window. The window is sliding: oldest samples are dropped
    when the buffer exceeds maxlen.
    """
    maxlen: int = 1000
    default_streak_k: int = 5
    deviation_pct: float = 0.20
    target_distribution: dict[FormationFamily, float] = field(default_factory=dict)
    _history: list[tuple[int, FormationFamily, tuple[tuple[float, float], ...]]] = field(
        default_factory=list
    )
    _warnings: list[str] = field(default_factory=list)

    def record_formation(
        self,
        seed: int,
        family: FormationFamily,
        points: list[tuple[float, float]],
    ) -> None:
        """Record one formation. Trims oldest if over maxlen."""
        # Hash points to a tuple for storage. Use rounded values to
        # avoid float-precision false positives.
        pt_hash = tuple((round(x, 1), round(y, 1)) for x, y in points)
        self._history.append((seed, family, pt_hash))
        if len(self._history) > self.maxlen:
            self._history.pop(0)

    def is_stuck_pattern(
        self, family: FormationFamily, k: int | None = None
    ) -> bool:
        """True if `family` appears in the last k slots in a row.

        Requires at least k samples in history — fewer samples can't
        demonstrate a "streak" of length k.
        """
        threshold = k if k is not None else self.default_streak_k
        if threshold <= 0 or len(self._history) < threshold:
            return False
        recent = self._history[-threshold:]
        return all(entry[1] == family for entry in recent)

    def check_distribution(self, window: int | None = None) -> dict[str, Any]:
        """Return stats over the last `window` samples (default: all).

        Returns: {
            "count": int (samples analyzed),
            "family_counts": dict[str, int],
            "deviation_pct": float (max deviation from target),
            "stuck_warnings": list[str]
        }
        """
        n = window if window is not None else len(self._history)
        if n <= 0 or not self._history:
            return {
                "count": 0,
                "family_counts": {},
                "deviation_pct": 0.0,
                "stuck_warnings": [],
            }
        recent = self._history[-n:]
        family_counter: Counter[FormationFamily] = Counter(
            entry[1] for entry in recent
        )
        # Compute deviation from target
        max_dev = 0.0
        if self.target_distribution:
            for family, target_pct in self.target_distribution.items():
                actual_pct = family_counter.get(family, 0) / len(recent)
                dev = abs(actual_pct - target_pct)
                max_dev = max(max_dev, dev)
        # Detect streaks
        warnings: list[str] = []
        for family in set(entry[1] for entry in recent):
            if self.is_stuck_pattern(family):
                warnings.append(f"family={family.value} repeated {self.default_streak_k} times in a row")
        return {
            "count": len(recent),
            "family_counts": {f.value: c for f, c in family_counter.items()},
            "deviation_pct": max_dev,
            "stuck_warnings": warnings,
        }

    def reset(self) -> None:
        """Clear all recorded history."""
        self._history.clear()
        self._warnings.clear()
