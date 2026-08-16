"""Fixed-timestep clock wrapper."""
from __future__ import annotations

import pygame

from stellar_horizon.settings import FPS_TARGET


class FixedClock:
    def __init__(self, target_fps: int = FPS_TARGET) -> None:
        self.target_fps = target_fps
        self.clock = pygame.time.Clock()

    def tick(self) -> int:
        return self.clock.tick(self.target_fps)
