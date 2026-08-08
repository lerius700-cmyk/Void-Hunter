"""Wave manager + 18 wave JSON scripts (BLOQUE 10).

Per GDD §6: 6 waves per act × 3 acts = 18 waves. Each wave script is a
JSON file in data/waves/ with archetype counts, kill target, optional
sub-boss trigger, and special conditions. Adaptive difficulty scales
spawn rate based on player HP/score.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.settings import (
    SUBBOSS_TRIGGER_KILLS,
    WAVE_KILL_TARGET,
    WAVE_TIME_LIMIT_S,
)


WAVES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "waves"


# Default 18-wave script (per GDD §6 + §4 enemy mix table)
DEFAULT_WAVES: list[dict[str, Any]] = [
    # Act 1 (Blue Void)
    {"act": 1, "wave": 1, "theme": "blue_void", "mix": {"scout": 6}, "kill_target": 6, "time_limit_s": 25.0, "sub_boss": None},
    {"act": 1, "wave": 2, "theme": "blue_void", "mix": {"scout": 8, "cruiser": 3}, "kill_target": 11, "time_limit_s": 30.0, "sub_boss": None},
    {"act": 1, "wave": 3, "theme": "blue_void", "mix": {"scout": 7, "cruiser": 5, "heavy": 1}, "kill_target": 13, "time_limit_s": 32.0, "sub_boss": None},
    {"act": 1, "wave": 4, "theme": "blue_void", "mix": {"scout": 8, "cruiser": 7, "heavy": 3}, "kill_target": 18, "time_limit_s": 35.0, "sub_boss": None},
    {"act": 1, "wave": 5, "theme": "blue_void", "mix": {"scout": 6, "cruiser": 8, "heavy": 4, "kamikaze": 1}, "kill_target": 19, "time_limit_s": 38.0, "sub_boss": None},
    {"act": 1, "wave": 6, "theme": "blue_void", "mix": {"scout": 6, "cruiser": 6, "heavy": 4, "kamikaze": 4}, "kill_target": 20, "time_limit_s": 40.0, "sub_boss": "goliath"},
    # Act 2 (Pink Void -> Mars -> Teal)
    {"act": 2, "wave": 1, "theme": "pink_void", "mix": {"scout": 5, "cruiser": 5, "heavy": 4, "kamikaze": 2, "drone": 2}, "kill_target": 18, "time_limit_s": 38.0, "sub_boss": None},
    {"act": 2, "wave": 2, "theme": "pink_void", "mix": {"scout": 4, "cruiser": 4, "heavy": 4, "kamikaze": 3, "drone": 3}, "kill_target": 18, "time_limit_s": 40.0, "sub_boss": None},
    {"act": 2, "wave": 3, "theme": "mars", "mix": {"scout": 3, "cruiser": 3, "heavy": 3, "kamikaze": 3, "drone": 4, "sniper": 2}, "kill_target": 18, "time_limit_s": 42.0, "sub_boss": None},
    {"act": 2, "wave": 4, "theme": "mars", "mix": {"scout": 2, "cruiser": 2, "heavy": 2, "kamikaze": 3, "drone": 3, "sniper": 2, "turret": 1}, "kill_target": 15, "time_limit_s": 45.0, "sub_boss": None},
    {"act": 2, "wave": 5, "theme": "teal", "mix": {"scout": 1, "cruiser": 1, "heavy": 2, "kamikaze": 3, "drone": 2, "sniper": 2, "turret": 1}, "kill_target": 12, "time_limit_s": 50.0, "sub_boss": None},
    {"act": 2, "wave": 6, "theme": "teal", "mix": {"scout": 1, "cruiser": 1, "heavy": 1, "kamikaze": 2, "drone": 1, "sniper": 2, "turret": 1}, "kill_target": 9, "time_limit_s": 60.0, "sub_boss": "hydra"},
    # Act 3 (Purple Dusk -> Gold/Amber)
    {"act": 3, "wave": 1, "theme": "purple_dusk", "mix": {"scout": 1, "cruiser": 1, "heavy": 1, "kamikaze": 1, "drone": 1, "sniper": 1, "turret": 1, "carrier": 1}, "kill_target": 8, "time_limit_s": 50.0, "sub_boss": None},
    {"act": 3, "wave": 2, "theme": "purple_dusk", "mix": {"scout": 1, "cruiser": 1, "heavy": 1, "kamikaze": 2, "drone": 1, "sniper": 1, "turret": 1, "carrier": 1}, "kill_target": 9, "time_limit_s": 55.0, "sub_boss": None},
    {"act": 3, "wave": 3, "theme": "gold_amber", "mix": {"scout": 1, "cruiser": 1, "heavy": 1, "kamikaze": 2, "drone": 1, "sniper": 1, "turret": 1, "carrier": 1}, "kill_target": 9, "time_limit_s": 60.0, "sub_boss": None},
    {"act": 3, "wave": 4, "theme": "gold_amber", "mix": {"scout": 1, "heavy": 1, "kamikaze": 2, "drone": 1, "sniper": 1, "turret": 1, "carrier": 2}, "kill_target": 9, "time_limit_s": 60.0, "sub_boss": None},
    {"act": 3, "wave": 5, "theme": "gold_amber", "mix": {"scout": 1, "heavy": 1, "kamikaze": 1, "drone": 1, "sniper": 1, "turret": 2, "carrier": 2}, "kill_target": 9, "time_limit_s": 65.0, "sub_boss": None},
    {"act": 3, "wave": 6, "theme": "gold_amber", "mix": {"scout": 1, "heavy": 1, "kamikaze": 1, "drone": 1, "sniper": 1, "turret": 2, "carrier": 3}, "kill_target": 10, "time_limit_s": 90.0, "sub_boss": "phantom_then_nemesis"},
]


@dataclass
class WaveState:
    """Live state of an in-progress wave."""
    wave_index: int = 0
    kills: int = 0
    elapsed_s: float = 0.0
    cleared: bool = False
    failed: bool = False
    # Adaptive difficulty multiplier (1.0 = baseline, 1.2 = harder)
    difficulty_mult: float = 1.0


class WaveManager:
    """18-wave scriptable manager. JSON-loadable, adaptive difficulty."""

    def __init__(self, scripts: list[dict[str, Any]] | None = None) -> None:
        self.scripts: list[dict[str, Any]] = scripts or DEFAULT_WAVES
        self.current: WaveState = WaveState()
        self.on_wave_cleared: bool = False
        self.on_wave_failed: bool = False
        self.on_sub_boss_trigger: str | None = None

    @classmethod
    def from_json_dir(cls, directory: Path | None = None) -> "WaveManager":
        """Load wave scripts from data/waves/*.json. Falls back to defaults."""
        directory = directory or WAVES_DIR
        if not directory.exists():
            return cls(DEFAULT_WAVES)
        scripts: list[dict[str, Any]] = []
        for path in sorted(directory.glob("act*_wave*.json")):
            with open(path, encoding="utf-8") as f:
                scripts.append(json.load(f))
        if not scripts:
            return cls(DEFAULT_WAVES)
        return cls(scripts)

    def validate(self) -> tuple[bool, str]:
        """Sanity check: 18 waves, kill_targets positive, themes known."""
        if len(self.scripts) != 18:
            return False, f"expected 18 waves, got {len(self.scripts)}"
        for i, s in enumerate(self.scripts):
            if "kill_target" not in s or s["kill_target"] <= 0:
                return False, f"wave {i} missing kill_target"
            if "theme" not in s:
                return False, f"wave {i} missing theme"
        return True, "ok"

    def start_wave(self, index: int) -> None:
        """Begin wave[index]."""
        if not (0 <= index < len(self.scripts)):
            raise IndexError(f"wave {index} out of range")
        self.current = WaveState(wave_index=index)
        self.on_wave_cleared = False
        self.on_wave_failed = False
        self.on_sub_boss_trigger = None

    def current_wave(self) -> dict[str, Any]:
        return self.scripts[self.current.wave_index]

    def on_kill(self) -> None:
        """Called when an enemy dies. Tracks wave progress."""
        self.current.kills += 1
        if self.current.kills >= self.current_wave()["kill_target"]:
            self.current.cleared = True
            self.on_wave_cleared = True
        # Sub-boss trigger: at SUBBOSS_TRIGGER_KILLS, fire the sub_boss event
        if (self.on_sub_boss_trigger is None
                and self.current_wave().get("sub_boss")
                and self.current.kills >= SUBBOSS_TRIGGER_KILLS):
            self.on_sub_boss_trigger = self.current_wave()["sub_boss"]

    def update(self, dt: float) -> None:
        """Advance elapsed time; fail wave if time limit exceeded."""
        self.current.elapsed_s += dt
        time_limit = self.current_wave().get("time_limit_s", WAVE_TIME_LIMIT_S)
        if self.current.elapsed_s >= time_limit and not self.current.cleared:
            self.current.failed = True
            self.on_wave_failed = True

    def adapt_difficulty(self, player_hp_pct: float, score: int) -> float:
        """Adjust spawn rate based on player performance.

        HP > 80% AND high score → harder (1.2x).
        HP < 30% → easier (0.8x).
        """
        if player_hp_pct > 0.8 and score > 50000:
            self.current.difficulty_mult = 1.2
        elif player_hp_pct < 0.3:
            self.current.difficulty_mult = 0.8
        else:
            self.current.difficulty_mult = 1.0
        return self.current.difficulty_mult

    def total_kills_remaining(self) -> int:
        target: int = self.current_wave()["kill_target"]
        return max(0, target - self.current.kills)

    def reset(self) -> None:
        self.current = WaveState()
        self.on_wave_cleared = False
        self.on_wave_failed = False
        self.on_sub_boss_trigger = None
