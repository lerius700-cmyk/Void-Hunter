"""SlowMo — time scale override (0.3x to 0.95x) per GDD §10.

When active, `get_factor()` returns the active scale. The consumer multiplies
FIXED_DT by this factor. Slow-mo effects stack FIFO. Hitstop has priority:
hitstop fires first, slow-mo applies when hitstop ends (engine integration
is the consumer's responsibility).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class SlowMo:
    """FIFO queue of slow-mo effects. Factor clamped to [0.3, 0.95]."""
    _queue: deque[tuple[float, int]] = field(default_factory=deque)
    _frames_remaining: int = 0
    _current_factor: float = 1.0

    def trigger(self, factor: float, frames: int) -> None:
        """Queue a slow-mo effect. factor < 0.3 → 0.3; factor > 0.95 → 0.95."""
        f = max(0.3, min(0.95, factor))
        if frames <= 0:
            return
        self._queue.append((f, frames))

    def update(self) -> None:
        if self._frames_remaining > 0:
            self._frames_remaining -= 1
        else:
            if self._queue:
                f, frames = self._queue.popleft()
                self._current_factor = f
                self._frames_remaining = frames
        # If current effect ended, factor goes back to 1.0
        if self._frames_remaining == 0 and not self._queue:
            self._current_factor = 1.0

    def get_factor(self) -> float:
        return self._current_factor

    @property
    def is_active(self) -> bool:
        return self._frames_remaining > 0 or bool(self._queue)

    def reset(self) -> None:
        self._queue.clear()
        self._frames_remaining = 0
        self._current_factor = 1.0
