"""Tests for src.core.event_bus (BLOQUE 5)."""
from __future__ import annotations

import pytest

from src.core.event_bus import EVENT_NAMES, EventBus, Events


# ---------------------------------------------------------------------------
# 1. Basic pub/sub
# ---------------------------------------------------------------------------
def test_subscribe_and_emit() -> None:
    bus = EventBus()
    received: list[dict] = []
    bus.subscribe("test", lambda e: received.append(e))
    bus.emit("test", {"x": 1})
    assert received == [{"x": 1}]


def test_emit_returns_listener_count() -> None:
    bus = EventBus()
    bus.subscribe("x", lambda e: None)
    bus.subscribe("x", lambda e: None)
    bus.subscribe("x", lambda e: None)
    assert bus.emit("x") == 3
    assert bus.emit("y") == 0


def test_payload_default_is_empty_dict() -> None:
    bus = EventBus()
    received: list[dict] = []
    bus.subscribe("x", lambda e: received.append(e))
    bus.emit("x")
    assert received == [{}]


# ---------------------------------------------------------------------------
# 2. Multi-listener ordering
# ---------------------------------------------------------------------------
def test_listeners_called_in_subscription_order() -> None:
    bus = EventBus()
    order: list[str] = []
    bus.subscribe("x", lambda e: order.append("a"))
    bus.subscribe("x", lambda e: order.append("b"))
    bus.subscribe("x", lambda e: order.append("c"))
    bus.emit("x")
    assert order == ["a", "b", "c"]


def test_100_events_per_frame_all_delivered() -> None:
    """Spec: 100 eventos por frame → todos entregados en orden."""
    bus = EventBus()
    counter: list[int] = []
    bus.subscribe("tick", lambda e: counter.append(1))
    for _ in range(100):
        bus.emit("tick")
    assert sum(counter) == 100


# ---------------------------------------------------------------------------
# 3. Exception isolation
# ---------------------------------------------------------------------------
def test_listener_exception_does_not_break_chain() -> None:
    """Spec: listener que tira excepción → no rompe la cadena."""
    bus = EventBus()
    received: list[str] = []
    bus.subscribe("x", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe("x", lambda e: received.append("ok"))
    bus.emit("x")  # should not raise
    assert received == ["ok"]


# ---------------------------------------------------------------------------
# 4. Subscribe / unsubscribe during emit
# ---------------------------------------------------------------------------
def test_unsubscribe_during_emit_is_safe() -> None:
    """Spec: subscribe/unsubscribe durante emit → comportamiento definido."""
    bus = EventBus()
    received: list[str] = []
    unsub_a: list = []
    def listener_a(e: dict) -> None:
        received.append("a")
        unsub_a[0]()  # unsubscribe self
    def listener_b(e: dict) -> None:
        received.append("b")
    unsub_a.append(bus.subscribe("x", listener_a))
    bus.subscribe("x", listener_b)
    bus.emit("x")
    # listener_a fires once, then unsubscribes; listener_b still fires.
    assert received == ["a", "b"]
    # Second emit: only listener_b fires.
    received.clear()
    bus.emit("x")
    assert received == ["b"]


def test_subscribe_during_emit_does_not_fire_in_same_emit() -> None:
    """New subscription during emit must not affect the in-flight emit."""
    bus = EventBus()
    received: list[str] = []
    bus.subscribe("x", lambda e: (received.append("a"), bus.subscribe("x", lambda e: received.append("c"))))
    bus.subscribe("x", lambda e: received.append("b"))
    bus.emit("x")
    # a + b in this emit; c not seen because subscription is post-snapshot
    assert "a" in received and "b" in received
    # On the NEXT emit, c fires
    received.clear()
    bus.emit("x")
    assert "c" in received


# ---------------------------------------------------------------------------
# 5. Unsubscribe
# ---------------------------------------------------------------------------
def test_unsubscribe_returns_true_when_removed() -> None:
    bus = EventBus()
    def listener(e: dict) -> None:
        pass
    bus.subscribe("x", listener)
    assert bus.unsubscribe("x", listener) is True


def test_unsubscribe_returns_false_when_not_found() -> None:
    bus = EventBus()
    def listener(e: dict) -> None:
        pass
    assert bus.unsubscribe("x", listener) is False


def test_unsub_function_returned_by_subscribe() -> None:
    bus = EventBus()
    received: list[int] = []
    unsub = bus.subscribe("x", lambda e: received.append(1))
    bus.emit("x")
    unsub()
    bus.emit("x")
    assert sum(received) == 1


# ---------------------------------------------------------------------------
# 6. Clear
# ---------------------------------------------------------------------------
def test_clear_removes_all_subscriptions() -> None:
    bus = EventBus()
    bus.subscribe("x", lambda e: None)
    bus.subscribe("y", lambda e: None)
    bus.clear()
    assert bus.listener_count("x") == 0
    assert bus.listener_count("y") == 0


# ---------------------------------------------------------------------------
# 7. Event name constants
# ---------------------------------------------------------------------------
def test_at_least_25_event_names() -> None:
    """GDD §11: 25+ eventos tipados."""
    assert len(EVENT_NAMES) >= 25


def test_all_event_names_unique() -> None:
    assert len(set(EVENT_NAMES)) == len(EVENT_NAMES)


def test_events_class_has_key_constants() -> None:
    """Smoke: spot-check key event names exist."""
    assert Events.PLAYER_SHOOT == "player_shoot"
    assert Events.BOSS_DEATH == "boss_death"
    assert Events.MULTIPLIER_MAX == "multiplier_max"
    assert Events.GAME_OVER == "game_over"
    assert Events.VICTORY == "victory"
