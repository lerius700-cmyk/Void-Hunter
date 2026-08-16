"""Wave spec dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WaveSpec:
    id: str
    duration_s: float
    spawns: list[dict] = field(default_factory=list)
