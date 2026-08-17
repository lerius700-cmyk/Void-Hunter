"""Right-to-left dust stream for forward-motion feel.

Spawns small particles on the right edge of the screen at random y
positions and moves them to the left. Particles have variable size
(closer = larger) and speed (closer = faster) to sell the parallax.

Designed to be lightweight: a single pool of slots cycled in-place,
no per-frame allocations. Drawn as a 1x1 pixel with a soft alpha
rectangle (3 sizes) so it costs almost nothing on integrated GPUs.
"""
from __future__ import annotations

import random

import pygame


class DustParticle:
    __slots__ = ("alive", "x", "y", "vx", "vy", "size", "alpha")

    def __init__(self) -> None:
        self.alive = False
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.size = 0
        self.alpha = 0


class DustStream:
    """Endless dust stream scrolling right-to-left.

    Args:
        screen_w, screen_h: viewport size in pixels.
        pool_size: max simultaneous particles. 64 is plenty for a
            light dust effect; bump up for thicker atmosphere.
        spawn_rate: expected particles per second. The actual rate
            is stochastic to avoid a grid pattern.
        min_speed, max_speed: horizontal velocity range (px/s).
        colors: tuple of (r, g, b) colors to pick from per particle.
    """

    def __init__(
        self,
        screen_w: int = 480,
        screen_h: int = 270,
        pool_size: int = 64,
        spawn_rate: float = 25.0,
        min_speed: float = 60.0,
        max_speed: float = 180.0,
        colors: tuple = ((200, 200, 210), (180, 175, 190), (220, 215, 200)),
    ) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.spawn_rate = spawn_rate
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.colors = colors
        self._pool: list[DustParticle] = [DustParticle() for _ in range(pool_size)]
        self._spawn_accum = 0.0
        # Pre-allocate a single sprite (1x1 white) we tint per particle.
        self._white = pygame.Surface((1, 1), pygame.SRCALPHA)
        self._white.fill((255, 255, 255, 255))

    def update(self, dt: float) -> None:
        # Spawn new particles based on accumulated time.
        self._spawn_accum += dt * self.spawn_rate
        while self._spawn_accum >= 1.0:
            self._spawn_accum -= 1.0
            self._spawn()

        # Move + cull.
        left_bound = -8
        for p in self._pool:
            if not p.alive:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.x < left_bound or p.y < -8 or p.y > self.screen_h + 8:
                p.alive = False

    def _spawn(self) -> None:
        # Find a free slot.
        for p in self._pool:
            if not p.alive:
                p.alive = True
                # Spawn on the right edge with a small x overshoot.
                p.x = self.screen_w + random.uniform(0, 16)
                p.y = random.uniform(0, self.screen_h)
                # Speed + size correlate: faster = larger (closer to cam).
                speed = random.uniform(self.min_speed, self.max_speed)
                p.vx = -speed
                # Slight vertical drift (parallax-ish).
                p.vy = random.uniform(-6.0, 6.0)
                # Map speed -> size in [1, 3] px.
                t = (speed - self.min_speed) / max(1.0, self.max_speed - self.min_speed)
                p.size = 1 + int(t * 2.5)
                p.alpha = 140 + int(t * 100)  # 140-240
                return

    def draw(self, surface: pygame.Surface) -> None:
        for p in self._pool:
            if not p.alive:
                continue
            size = p.size
            color = self.colors[int(p.x + p.y) % len(self.colors)]
            # Render as a small soft square: tint the white sprite, then
            # scale up. Faster than building a new Surface per particle.
            tinted = pygame.Surface((size, size), pygame.SRCALPHA)
            tinted.fill((color[0], color[1], color[2], min(255, p.alpha)))
            surface.blit(tinted, (int(p.x), int(p.y)))
