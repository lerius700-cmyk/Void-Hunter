"""RoguelikeRun lifecycle (BLOQUE 57).

Tracks a single run from start to finalize. Holds the master seed,
derives the SeededRNG, and records actions + checkpoints. State is
JSON-serializable for replay.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from src.roguelike.rng import SeededRNG
from src.roguelike.seed import RoguelikeSeed


@dataclass
class Action:
    """A single player-driven event in the run log."""
    action_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "payload": self.payload,
            "timestamp_s": self.timestamp_s,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Action":
        return Action(
            action_type=str(d["action_type"]),
            payload=dict(d.get("payload", {})),
            timestamp_s=float(d.get("timestamp_s", 0.0)),
        )


@dataclass
class Checkpoint:
    """A snapshot of the run state. Captures RNG state + run metadata."""
    name: str
    rng_state: dict[str, Any]
    score: int
    level_idx: int
    wave_idx: int
    lives: int
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rng_state": self.rng_state,
            "score": self.score,
            "level_idx": self.level_idx,
            "wave_idx": self.wave_idx,
            "lives": self.lives,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Checkpoint":
        return Checkpoint(
            name=str(d["name"]),
            rng_state=dict(d["rng_state"]),
            score=int(d.get("score", 0)),
            level_idx=int(d.get("level_idx", 0)),
            wave_idx=int(d.get("wave_idx", 0)),
            lives=int(d.get("lives", 0)),
            created_at=float(d.get("created_at", 0.0)),
        )


class RoguelikeRun:
    """A single roguelike run, from start to finalize.

    Owns:
      - master seed + derived SeededRNG
      - action log
      - checkpoint list
      - score / lives / current wave
    """

    MAX_ACTIONS: int = 1000
    MAX_CHECKPOINTS: int = 10

    def __init__(self) -> None:
        self.level_idx: int = 0
        self.attempt_number: int = 0
        self.salt: int = 0
        self.seed: RoguelikeSeed | None = None
        self.rng: SeededRNG | None = None
        self.started_at: float = 0.0
        self.score: int = 0
        self.wave_idx: int = 0
        self.lives: int = 0
        self.actions: list[Action] = []
        self.checkpoints: list[Checkpoint] = []
        self._finalized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, level_idx: int, attempt_number: int, salt: int) -> None:
        """Initialize a new run. Idempotent: resets state if called twice."""
        self.level_idx = level_idx
        self.attempt_number = attempt_number
        self.salt = salt
        self.seed = RoguelikeSeed.derive(level_idx, attempt_number, salt)
        self.rng = SeededRNG(seed=self.seed.master)
        self.started_at = time.time()
        self.score = 0
        self.wave_idx = 0
        self.lives = 0
        self.actions = []
        self.checkpoints = []
        self._finalized = False

    def checkpoint(self, name: str) -> Checkpoint:
        """Snapshot the current run state."""
        if self.rng is None:
            raise RuntimeError("Run not started; call start() first")
        if len(self.checkpoints) >= self.MAX_CHECKPOINTS:
            # Drop the oldest to keep memory bounded.
            self.checkpoints.pop(0)
        cp = Checkpoint(
            name=name,
            rng_state=self.rng.state_dict(),
            score=self.score,
            level_idx=self.level_idx,
            wave_idx=self.wave_idx,
            lives=self.lives,
            created_at=time.time(),
        )
        self.checkpoints.append(cp)
        return cp

    def restore(self, cp: Checkpoint) -> None:
        """Restore the run to a previous checkpoint."""
        if self.rng is None:
            raise RuntimeError("Run not started; call start() first")
        self.rng.load_state_dict(cp.rng_state)
        self.score = cp.score
        self.wave_idx = cp.wave_idx
        self.lives = cp.lives
        # Note: level_idx is NOT restored; it's the run's "what level
        # are we on" which is set by start(). Checkpoints within a
        # level only restore score/wave/lives/rng state.

    def log_action(self, action_type: str, payload: dict[str, Any] | None = None) -> None:
        """Append an action to the run log. Oldest dropped if over MAX_ACTIONS."""
        if self.rng is None:
            raise RuntimeError("Run not started; call start() first")
        if len(self.actions) >= self.MAX_ACTIONS:
            self.actions.pop(0)
        self.actions.append(
            Action(
                action_type=action_type,
                payload=payload or {},
                timestamp_s=time.time() - self.started_at,
            )
        )

    def finalize(self, score: int) -> dict[str, Any]:
        """Close the run and return a summary dict. Idempotent."""
        if self._finalized:
            # Return cached summary if already finalized
            return {
                "level_idx": self.level_idx,
                "attempt_number": self.attempt_number,
                "salt": self.salt,
                "seed": self.seed.master if self.seed else 0,
                "score": self.score,
                "actions": len(self.actions),
                "duration_s": 0.0,
            }
        self.score = score
        self._finalized = True
        return {
            "level_idx": self.level_idx,
            "attempt_number": self.attempt_number,
            "salt": self.salt,
            "seed": self.seed.master if self.seed else 0,
            "score": score,
            "actions": len(self.actions),
            "duration_s": time.time() - self.started_at if self.started_at else 0.0,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_json(self) -> str:
        """Serialize the full run (minus RNG) to JSON."""
        d: dict[str, Any] = {
            "level_idx": self.level_idx,
            "attempt_number": self.attempt_number,
            "salt": self.salt,
            "seed": self.seed.master if self.seed else 0,
            "score": self.score,
            "wave_idx": self.wave_idx,
            "lives": self.lives,
            "actions": [a.to_dict() for a in self.actions],
            "checkpoints": [c.to_dict() for c in self.checkpoints],
        }
        return json.dumps(d, sort_keys=True)

    @staticmethod
    def from_json(data: str) -> "RoguelikeRun":
        """Restore a run from JSON. RNG state is reconstructed from the seed."""
        obj = json.loads(data)
        run = RoguelikeRun()
        run.level_idx = int(obj["level_idx"])
        run.attempt_number = int(obj["attempt_number"])
        run.salt = int(obj["salt"])
        master = int(obj["seed"])
        run.seed = RoguelikeSeed(master=master)
        run.rng = SeededRNG(seed=master)
        run.score = int(obj.get("score", 0))
        run.wave_idx = int(obj.get("wave_idx", 0))
        run.lives = int(obj.get("lives", 0))
        run.actions = [Action.from_dict(a) for a in obj.get("actions", [])]
        run.checkpoints = [Checkpoint.from_dict(c) for c in obj.get("checkpoints", [])]
        return run
