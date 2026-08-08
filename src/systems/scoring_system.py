"""Scoring system — multiplier chain 1x-16x + decay 1.5s + high-score JSON (BLOQUE 11).

Per GDD §7:
  score = base × multiplier × element_bonus × streak × difficulty_mult
  multiplier: 1x → 2x → 4x → 8x → 16x max, decay 1.5s sin kill
  element bonus: +50% si player element == enemy weakness
  streak: 10 kills en 3s → +5000pts bonus
  high-score JSON: {ship, path, score, time, date, ...}

Boss kill: +5 chain step, set timer to 3.0s (no decay).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.settings import (
    ELEMENT_BONUS,
    MULTIPLIER_DECAY_S,
    MULTIPLIER_MAX,
    STREAK_BONUS_CAP,
    STREAK_BONUS_WINDOW_S,
)


# Multiplier steps: 1x, 2x, 4x, 8x, 16x
MULTIPLIER_STEPS: tuple[int, ...] = (1, 2, 4, 8, 16)
MULTIPLIER_STEP_INDEX_MAX = len(MULTIPLIER_STEPS) - 1  # 4 = index of 16x


@dataclass
class HighScore:
    """Persistent high-score entry."""
    schema_version: int = 1
    ship: str = "void_hunter_v1"
    path: str = "plasma"
    score: int = 0
    time_seconds: float = 0.0
    lives_remaining: int = 0
    bombs_used: int = 0
    deaths: int = 0
    kills: int = 0
    max_multiplier: int = 1
    act_reached: int = 1
    bosses_defeated: list[str] = field(default_factory=list)
    rank: str = "D"
    difficulty: str = "Normal"
    timestamp_iso: str = ""
    player_name: str = ""


class ScoringSystem:
    """Multiplier chain + decay + high-score persistence."""

    def __init__(self) -> None:
        self.score: int = 0
        self.multiplier_index: int = 0  # 0 = 1x
        self.decay_timer: float = 0.0
        # Streak
        self.streak_count: int = 0
        self.streak_window: float = 0.0
        # Stats
        self.kills: int = 0
        self.deaths: int = 0
        self.bombs_used: int = 0
        self.max_multiplier: int = 1
        self.time_seconds: float = 0.0
        self.bosses_defeated: list[str] = []
        self.act_reached: int = 1
        self.lives_remaining: int = 0
        self.path: str = "plasma"
        self.difficulty: str = "Normal"
        self.player_name: str = ""
        # Outputs
        self.score_delta: int = 0
        self.on_max_multiplier: bool = False
        self.on_chain_break: bool = False
        self.on_streak_bonus: int = 0

    @property
    def multiplier(self) -> int:
        return MULTIPLIER_STEPS[self.multiplier_index]

    def reset(self) -> None:
        self.score = 0
        self.multiplier_index = 0
        self.decay_timer = 0.0
        self.streak_count = 0
        self.streak_window = 0.0
        self.kills = 0
        self.deaths = 0
        self.bombs_used = 0
        self.max_multiplier = 1
        self.time_seconds = 0.0
        self.bosses_defeated = []
        self.act_reached = 1
        self.score_delta = 0
        self.on_max_multiplier = False
        self.on_chain_break = False
        self.on_streak_bonus = 0

    def on_kill(self, base_score: int, is_boss: bool = False, is_element_bonus: bool = False) -> int:
        """Register a kill. Returns the points awarded this frame."""
        self.kills += 1
        # Multiplier step
        if is_boss:
            self.multiplier_index = min(MULTIPLIER_STEP_INDEX_MAX, self.multiplier_index + 5)
            self.decay_timer = 3.0  # no decay
        elif is_element_bonus:
            self.multiplier_index = min(MULTIPLIER_STEP_INDEX_MAX, self.multiplier_index + 2)
            self.decay_timer = MULTIPLIER_DECAY_S
        else:
            self.multiplier_index = min(MULTIPLIER_STEP_INDEX_MAX, self.multiplier_index + 1)
            self.decay_timer = MULTIPLIER_DECAY_S
        # Multiplier max signal
        if self.multiplier_index == MULTIPLIER_STEP_INDEX_MAX:
            self.on_max_multiplier = True
        # Track max
        if self.multiplier > self.max_multiplier:
            self.max_multiplier = self.multiplier
        # Compute points
        bonus = ELEMENT_BONUS if is_element_bonus else 1.0
        # Streak window refresh
        self.streak_count += 1
        self.streak_window = STREAK_BONUS_WINDOW_S
        # Milestone bonus popup (separate from multiplier formula per GDD §7)
        if self.streak_count == 10:
            self.on_streak_bonus = 500
            self.score += 500
        elif self.streak_count == 25:
            self.on_streak_bonus = 2500
            self.score += 2500
        elif self.streak_count == 50:
            self.on_streak_bonus = 5000
            self.score += 5000
        # Award base × multiplier × bonus (streak is separate via popups)
        awarded = int(base_score * self.multiplier * bonus)
        self.score += awarded
        self.score_delta = awarded
        return awarded

    def on_bomb(self) -> None:
        self.bombs_used += 1

    def on_death(self) -> None:
        self.deaths += 1

    def on_boss_defeated(self, boss_name: str) -> None:
        self.bosses_defeated.append(boss_name)

    def on_act_reached(self, act: int) -> None:
        if act > self.act_reached:
            self.act_reached = act

    def update(self, dt: float) -> None:
        """Decay multiplier + streak window."""
        if dt <= 0.0:
            return
        # Multiplier decay
        if self.multiplier_index > 0:
            self.decay_timer -= dt
            if self.decay_timer <= 0.0:
                self.multiplier_index -= 1
                self.decay_timer = MULTIPLIER_DECAY_S
                if self.multiplier == 1:
                    self.on_chain_break = True
        # Streak window
        if self.streak_count > 0:
            self.streak_window -= dt
            if self.streak_window <= 0.0:
                self.streak_count = 0
        # Time
        self.time_seconds += dt

    def consume_signals(self) -> None:
        self.score_delta = 0
        self.on_max_multiplier = False
        self.on_chain_break = False
        self.on_streak_bonus = 0

    def compute_rank(self) -> str:
        """Compute rank based on score (D, C, B, A, S, S+, SSS)."""
        s = self.score
        if s < 5000:
            return "D"
        if s < 10000:
            return "C"
        if s < 20000:
            return "B"
        if s < 30000:
            return "A"
        if s < 40000:
            return "S"
        if s < 50000:
            return "S+"
        return "SSS"

    def to_highscore(self) -> HighScore:
        return HighScore(
            ship="void_hunter_v1",
            path=self.path,
            score=self.score,
            time_seconds=self.time_seconds,
            lives_remaining=self.lives_remaining,
            bombs_used=self.bombs_used,
            deaths=self.deaths,
            kills=self.kills,
            max_multiplier=self.max_multiplier,
            act_reached=self.act_reached,
            bosses_defeated=list(self.bosses_defeated),
            rank=self.compute_rank(),
            difficulty=self.difficulty,
            timestamp_iso=datetime.now().isoformat(),
            player_name=self.player_name,
        )

    def save_highscore(self, path: Path) -> bool:
        """Save to JSON. Atomic write (temp + rename) per spec."""
        path.parent.mkdir(parents=True, exist_ok=True)
        hs = self.to_highscore()
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(asdict(hs), f, indent=2)
            tmp.replace(path)
            return True
        except OSError:
            return False
