"""EventBus — typed pub/sub for game-wide events.

Per GDD §11 EventBus: 25+ eventos tipados, listener que tira excepción
no rompe la cadena, subscribe/unsubscribe durante emit definido.

Usage:
    bus = EventBus()
    bus.subscribe("player_shoot", lambda evt: print(evt))
    bus.emit("player_shoot", {"x": 100, "y": 200})
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

Listener = Callable[[dict[str, Any]], None]


class EventBus:
    """Synchronous pub/sub. Listeners are called in subscription order."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)

    def subscribe(self, event_name: str, listener: Listener) -> Callable[[], None]:
        """Subscribe; returns an unsubscribe function."""
        self._listeners[event_name].append(listener)
        def _unsub() -> None:
            try:
                self._listeners[event_name].remove(listener)
            except ValueError:
                pass
        return _unsub

    def unsubscribe(self, event_name: str, listener: Listener) -> bool:
        """Remove a listener. Returns True if removed."""
        if event_name in self._listeners:
            try:
                self._listeners[event_name].remove(listener)
                return True
            except ValueError:
                return False
        return False

    def emit(self, event_name: str, payload: dict[str, Any] | None = None) -> int:
        """Emit an event synchronously. Returns count of listeners called.

        Exception isolation: a listener that raises does not break the chain.
        """
        payload = payload or {}
        listeners = list(self._listeners.get(event_name, []))  # snapshot for safety
        n = 0
        for listener in listeners:
            try:
                listener(payload)
                n += 1
            except Exception:
                # Spec: listener that throws does not break the chain.
                # We silently swallow to honor the contract. Production
                # would log to a sink; for now, no logging dependency.
                pass
        return n

    def listener_count(self, event_name: str) -> int:
        return len(self._listeners.get(event_name, []))

    def clear(self) -> None:
        """Wipe all subscriptions. Used on full game reset."""
        self._listeners.clear()


# ---------------------------------------------------------------------------
# Event name constants (25+ per GDD §11)
# ---------------------------------------------------------------------------
class Events:
    """Typed event name constants. Use these instead of stringly-typed names."""
    PLAYER_SHOOT = "player_shoot"
    PLAYER_DASH = "player_dash"
    PLAYER_HIT = "player_hit"
    PLAYER_DEATH = "player_death"
    PLAYER_RESPAWN = "player_respawn"
    PLAYER_BOMB = "player_bomb"
    PLAYER_PERFECT_DASH = "player_perfect_dash"
    ENEMY_SPAWN = "enemy_spawn"
    ENEMY_HIT = "enemy_hit"
    ENEMY_DEATH = "enemy_death"
    BULLET_SPAWN = "bullet_spawn"
    BULLET_HIT = "bullet_hit"
    MULTIPLIER_INCREASED = "multiplier_increased"
    MULTIPLIER_DECREASED = "multiplier_decreased"
    MULTIPLIER_MAX = "multiplier_max"
    WAVE_CLEARED = "wave_cleared"
    WAVE_STARTED = "wave_started"
    ACT_CLEARED = "act_cleared"
    ACT_STARTED = "act_started"
    BOSS_SPAWN = "boss_spawn"
    BOSS_HIT = "boss_hit"
    BOSS_PHASE_TRANSITION = "boss_phase_transition"
    BOSS_DEATH = "boss_death"
    POWERUP_SPAWN = "powerup_spawn"
    POWERUP_COLLECTED = "powerup_collected"
    WEAPON_LEVEL_UP = "weapon_level_up"
    WEAPON_SPECIAL_UNLOCKED = "weapon_special_unlocked"
    HITSTOP_TRIGGERED = "hitstop_triggered"
    SLOWMO_TRIGGERED = "slowmo_triggered"
    SHAKE_TRIGGERED = "shake_triggered"
    THEME_CHANGED = "theme_changed"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    PAUSE = "pause"
    RESUME = "resume"


# Count constants for self-validation
EVENT_NAMES: tuple[str, ...] = (
    Events.PLAYER_SHOOT,
    Events.PLAYER_DASH,
    Events.PLAYER_HIT,
    Events.PLAYER_DEATH,
    Events.PLAYER_RESPAWN,
    Events.PLAYER_BOMB,
    Events.PLAYER_PERFECT_DASH,
    Events.ENEMY_SPAWN,
    Events.ENEMY_HIT,
    Events.ENEMY_DEATH,
    Events.BULLET_SPAWN,
    Events.BULLET_HIT,
    Events.MULTIPLIER_INCREASED,
    Events.MULTIPLIER_DECREASED,
    Events.MULTIPLIER_MAX,
    Events.WAVE_CLEARED,
    Events.WAVE_STARTED,
    Events.ACT_CLEARED,
    Events.ACT_STARTED,
    Events.BOSS_SPAWN,
    Events.BOSS_HIT,
    Events.BOSS_PHASE_TRANSITION,
    Events.BOSS_DEATH,
    Events.POWERUP_SPAWN,
    Events.POWERUP_COLLECTED,
    Events.WEAPON_LEVEL_UP,
    Events.WEAPON_SPECIAL_UNLOCKED,
    Events.HITSTOP_TRIGGERED,
    Events.SLOWMO_TRIGGERED,
    Events.SHAKE_TRIGGERED,
    Events.THEME_CHANGED,
    Events.GAME_OVER,
    Events.VICTORY,
    Events.PAUSE,
    Events.RESUME,
)
