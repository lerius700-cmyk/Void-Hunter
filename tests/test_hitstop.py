"""Tests for src.systems.hitstop + src.systems.slowmo (BLOQUE 5)."""
from __future__ import annotations

import pytest

from src.systems.hitstop import Hitstop
from src.systems.slowmo import SlowMo


# ---------------------------------------------------------------------------
# Hitstop
# ---------------------------------------------------------------------------
def test_hitstop_initial_inactive() -> None:
    h = Hitstop()
    assert not h.is_active


def test_hitstop_trigger_zero_noop() -> None:
    """Spec: trigger(0) → no aplica."""
    h = Hitstop()
    h.trigger(0)
    h.update()
    assert not h.is_active


def test_hitstop_trigger_twelve_active() -> None:
    h = Hitstop()
    h.trigger(12)
    h.update()  # promote from queue
    assert h.is_active
    assert h.frames_remaining == 12


def test_hitstop_decrements_per_update() -> None:
    h = Hitstop()
    h.trigger(5)
    h.update()
    for expected in (4, 3, 2, 1, 0):
        h.update()
        assert h.frames_remaining == expected


def test_hitstop_concurrent_triggers_queue() -> None:
    """Multiple triggers queue and play in order."""
    h = Hitstop()
    h.trigger(3)
    h.trigger(2)
    h.update()  # call 1: promote 3
    assert h.frames_remaining == 3
    # 3 decrements to bring 3→0, then 1 more to promote next
    for _ in range(4):
        h.update()
    assert h.frames_remaining == 2


def test_hitstop_reset_clears_queue() -> None:
    h = Hitstop()
    h.trigger(5)
    h.trigger(3)
    h.reset()
    assert h._queue == h._queue.__class__()  # empty
    assert h.frames_remaining == 0


# ---------------------------------------------------------------------------
# SlowMo
# ---------------------------------------------------------------------------
def test_slowmo_initial_factor_one() -> None:
    s = SlowMo()
    assert s.get_factor() == 1.0
    assert not s.is_active


def test_slowmo_trigger_factor_clamped() -> None:
    """factor < 0.3 → 0.3; > 0.95 → 0.95."""
    s = SlowMo()
    s.trigger(0.1, 10)
    s.update()
    assert s.get_factor() == 0.3
    s._frames_remaining = 0
    s._queue.clear()
    s.trigger(2.0, 10)
    s.update()
    assert s.get_factor() == 0.95


def test_slowmo_trigger_frames_zero_noop() -> None:
    s = SlowMo()
    s.trigger(0.5, 0)
    s.update()
    assert s.get_factor() == 1.0


def test_slowmo_active_returns_correct_factor() -> None:
    s = SlowMo()
    s.trigger(0.5, 10)
    s.update()
    assert s.get_factor() == 0.5
    assert s.is_active


def test_slowmo_returns_to_one_after_duration() -> None:
    s = SlowMo()
    s.trigger(0.5, 3)
    s.update()
    assert s.get_factor() == 0.5
    for _ in range(3):
        s.update()
    assert s.get_factor() == 1.0
    assert not s.is_active


def test_slowmo_reset_clears_state() -> None:
    s = SlowMo()
    s.trigger(0.5, 10)
    s.update()
    s.reset()
    assert s.get_factor() == 1.0
    assert not s.is_active


def test_slowmo_queue_fifo() -> None:
    s = SlowMo()
    s.trigger(0.5, 2)
    s.trigger(0.7, 2)
    s.update()  # promote 0.5
    assert s.get_factor() == 0.5
    # 2 decrements bring frames to 0; one more update promotes 0.7
    for _ in range(3):
        s.update()
    assert s.get_factor() == 0.7


# ---------------------------------------------------------------------------
# Priority: hitstop + slowmo concurrent
# ---------------------------------------------------------------------------
def test_hitstop_and_slowmo_concurrent_priority() -> None:
    """Spec: 'hitstop + slowmo concurrentes → prioridad a hitstop'.

    The consumer's responsibility to gate slowmo on hitstop.is_active.
    This test documents the contract.
    """
    h = Hitstop()
    s = SlowMo()
    h.trigger(3)
    s.trigger(0.5, 10)
    h.update()
    s.update()
    assert h.is_active
    # Consumer should NOT apply s.get_factor() while h.is_active.
    # Per spec, slowmo starts after hitstop ends.
    for _ in range(3):
        h.update()
    assert not h.is_active
    # slowmo still queued
    assert s.is_active
    assert s.get_factor() == 0.5
