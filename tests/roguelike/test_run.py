"""Tests for src.roguelike.run (BLOQUE 57)."""
from __future__ import annotations

import json
import pytest

from src.roguelike.run import Action, Checkpoint, RoguelikeRun


# ---------------------------------------------------------------------------
# 1. Lifecycle
# ---------------------------------------------------------------------------
def test_run_start_initializes_state() -> None:
    run = RoguelikeRun()
    run.start(level_idx=2, attempt_number=3, salt=42)
    assert run.level_idx == 2
    assert run.attempt_number == 3
    assert run.salt == 42
    assert run.rng is not None
    assert run.score == 0
    assert run.actions == []
    assert run.checkpoints == []


def test_run_start_resets_existing_state() -> None:
    run = RoguelikeRun()
    run.start(1, 1, 1)
    run.score = 999
    run.log_action("test", {})
    run.start(2, 2, 2)
    assert run.score == 0
    assert run.actions == []


# ---------------------------------------------------------------------------
# 2. Checkpoint / restore
# ---------------------------------------------------------------------------
def test_checkpoint_restore_preserves_rng() -> None:
    run = RoguelikeRun()
    run.start(1, 1, 42)
    # Advance the RNG by some calls
    for _ in range(50):
        run.rng.random()
    cp = run.checkpoint("after_50")
    # Advance further
    for _ in range(50):
        run.rng.random()
    # Restore
    run.restore(cp)
    # Replay the 50 calls — RNG state should match
    rng_after_restore = run.rng.random()
    # Build a fresh run from the same checkpoint logic
    fresh = RoguelikeRun()
    fresh.start(1, 1, 42)
    for _ in range(50):
        fresh.rng.random()
    fresh_after = fresh.rng.random()
    assert rng_after_restore == fresh_after


def test_checkpoint_bounded() -> None:
    run = RoguelikeRun()
    run.start(1, 1, 0)
    for i in range(RoguelikeRun.MAX_CHECKPOINTS + 5):
        run.checkpoint(f"cp_{i}")
    assert len(run.checkpoints) == RoguelikeRun.MAX_CHECKPOINTS
    # Oldest should be gone
    assert run.checkpoints[0].name == "cp_5"


# ---------------------------------------------------------------------------
# 3. log_action
# ---------------------------------------------------------------------------
def test_log_action_incremental() -> None:
    run = RoguelikeRun()
    run.start(1, 1, 0)
    run.log_action("wave_complete", {"wave": 1})
    run.log_action("wave_complete", {"wave": 2})
    assert len(run.actions) == 2
    assert run.actions[0].action_type == "wave_complete"
    assert run.actions[0].payload == {"wave": 1}
    assert run.actions[1].payload == {"wave": 2}


def test_log_action_bounded() -> None:
    run = RoguelikeRun()
    run.start(1, 1, 0)
    for i in range(RoguelikeRun.MAX_ACTIONS + 10):
        run.log_action("x", {"i": i})
    assert len(run.actions) == RoguelikeRun.MAX_ACTIONS


# ---------------------------------------------------------------------------
# 4. JSON serialization
# ---------------------------------------------------------------------------
def test_to_json_from_json_round_trip() -> None:
    run = RoguelikeRun()
    run.start(level_idx=2, attempt_number=3, salt=42)
    run.score = 12345
    run.lives = 3
    run.log_action("wave", {"i": 0})
    j = run.to_json()
    loaded = RoguelikeRun.from_json(j)
    assert loaded.level_idx == 2
    assert loaded.attempt_number == 3
    assert loaded.salt == 42
    assert loaded.score == 12345
    assert loaded.lives == 3
    assert len(loaded.actions) == 1


# ---------------------------------------------------------------------------
# 5. finalize
# ---------------------------------------------------------------------------
def test_finalize_calculates_summary() -> None:
    run = RoguelikeRun()
    run.start(1, 1, 0)
    for i in range(10):
        run.log_action("wave", {})
    summary = run.finalize(score=9999)
    assert summary["score"] == 9999
    assert summary["actions"] == 10
    assert summary["level_idx"] == 1
    assert summary["seed"] is not None


def test_finalize_idempotent() -> None:
    run = RoguelikeRun()
    run.start(1, 1, 0)
    s1 = run.finalize(score=100)
    s2 = run.finalize(score=999)
    assert s1["score"] == 100
    assert s2["score"] == 100  # second call returns cached summary
