"""Hitstop — pause game logic for N frames (dt=0) while render continues.

Per GDD §10: hitstop range 3-12 frames, configurable per event. Priority
over slowmo: if both are active, hitstop fires first.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Hitstop:
    """Frame counter for hitstop pauses.

    When `frames_remaining > 0`, the consumer should set dt=0 for game
    logic. Render keeps running (post-processing, particles, shake, etc.
    stay alive during hitstop).
    """
    frames_remaining: int = 0
    _queue: deque[int] = field(default_factory=deque)

    def trigger(self, frames: int) -> None:
        """Queue a hitstop. If frames <= 0, no-op (spec edge case)."""
        if frames <= 0:
            return
        # Concatenate: subsequent hitstops extend the pause.
        self._queue.append(frames)

    def update(self) -> None:
        """Decrement counter; promote next queued hitstop when current ends."""
        if self.frames_remaining > 0:
            self.frames_remaining -= 1
        else:
            if self._queue:
                self.frames_remaining = self._queue.popleft()

    @property
    def is_active(self) -> bool:
        return self.frames_remaining > 0

    def reset(self) -> None:
        self.frames_remaining = 0
        self._queue.clear()
