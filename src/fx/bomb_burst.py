"""BLOQUE 58.14.7: Bomb burst VFX — orange/yellow procedural circles.

Reuses the same soft-alpha technique we built for the nebulae:
  - 5x5 value noise grid + Gaussian puffs
  - Radial alpha falloff (no hard edges)
  - Smoothstep soft edges

But tinted with bomb colors (orange/yellow palette) and animated
over a short life (0.4s): scale up + fade out. The bomb spawns
3 concentric rings with different sizes and intensities to give
a "shockwave + heat" feel.

Wire-up:
    burst = BombBurst(cx, cy)
    # each frame:
    burst.update(dt)
    burst.draw(target)
"""
from __future__ import annotations

import math
import random

import pygame


# Bomb palette: yellow core -> orange edge.
_HOT_COLOR = (255, 240, 180)       # bright yellow-white
_BOMB_COLOR = (255, 160, 50)       # hot orange
_RIM_COLOR = (255, 80, 30)         # red-orange (dimmest, outermost)


def _make_soft_circle(
    size: int,
    color: tuple[int, int, int],
    seed: int,
    max_alpha: int = 200,
) -> pygame.Surface:
    """Build a soft, noise-textured circle with the same recipe as the
    nebula: bilinear value noise + Gaussian puffs + radial alpha
    falloff + smoothstep. The result has no hard edges.
    """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size / 2.0, size / 2.0
    radius = size / 2.0
    rng = random.Random(seed)

    grid_n = 5
    noise_grid = [[rng.random() for _ in range(grid_n)] for _ in range(grid_n)]
    num_puffs = 3
    puffs: list[tuple[float, float, float, float]] = []
    for _ in range(num_puffs):
        p_cx = rng.uniform(cx - radius * 0.3, cx + radius * 0.3)
        p_cy = rng.uniform(cy - radius * 0.3, cy + radius * 0.3)
        p_sigma = rng.uniform(radius * 0.15, radius * 0.4)
        p_intensity = rng.uniform(0.5, 1.0)
        puffs.append((p_cx, p_cy, p_sigma, p_intensity))

    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist > radius:
                continue
            t_radial = dist / radius
            radial_falloff = 1.0 - t_radial * t_radial

            gx = (x / size) * (grid_n - 1)
            gy = (y / size) * (grid_n - 1)
            ix = int(gx)
            iy = int(gy)
            fx = gx - ix
            fy = gy - iy
            ix1 = min(ix + 1, grid_n - 1)
            iy1 = min(iy + 1, grid_n - 1)
            v00 = noise_grid[iy][ix]
            v10 = noise_grid[iy][ix1]
            v01 = noise_grid[iy1][ix]
            v11 = noise_grid[iy1][ix1]
            v0 = v00 * (1 - fx) + v10 * fx
            v1 = v01 * (1 - fx) + v11 * fx
            noise_val = v0 * (1 - fy) + v1 * fy

            puff_val = 0.0
            for p_cx, p_cy, p_sigma, p_intensity in puffs:
                ddx = (x - p_cx) / p_sigma
                ddy = (y - p_cy) / p_sigma
                dd2 = ddx * ddx + ddy * ddy
                if dd2 < 16:
                    g = p_intensity * math.exp(-dd2 / 2.0)
                    if g > puff_val:
                        puff_val = g

            density = max(noise_val * 0.5, puff_val) * radial_falloff
            lo, hi = 0.2, 0.6
            if density < lo:
                continue
            elif density > hi:
                density = 1.0
            else:
                t = (density - lo) / (hi - lo)
                density = t * t * (3 - 2 * t)

            alpha = int(density * max_alpha)
            surf.set_at((x, y), (*color, alpha))
    return surf


class BombBurst:
    """One bomb explosion: 3 concentric rings, expanding, fading.

    Each ring is pre-rendered at init (soft, no edges), then scaled
    and faded over its lifetime. Total duration: 0.4s.
    """

    LIFE_S: float = 0.4

    def __init__(self, cx: float, cy: float, seed: int = 0xB0FB) -> None:
        self.x = cx
        self.y = cy
        self.life = 0.0
        self.max_r = 96.0
        # Pre-render 3 rings (innermost hot, outer rim).
        self._rings: list[tuple[pygame.Surface, float, int, tuple[int, int, int]]] = []
        for i, (color, size, max_alpha) in enumerate([
            (_HOT_COLOR, 96, 230),
            (_BOMB_COLOR, 128, 200),
            (_RIM_COLOR, 160, 160),
        ]):
            surf = _make_soft_circle(size, color, seed + i, max_alpha)
            self._rings.append((surf, size, max_alpha, color))

    def update(self, dt: float) -> None:
        self.life = min(self.life + dt, self.LIFE_S)

    @property
    def is_alive(self) -> bool:
        return self.life < self.LIFE_S

    def draw(self, target: pygame.Surface) -> None:
        t = self.life / self.LIFE_S  # 0..1
        # Each ring expands from 0.6 -> 1.0 of its full size, fading.
        for surf, size, _max_alpha, color in self._rings:
            # Stagger: ring 0 reaches full at t=0.2, ring 1 at 0.5, ring 2 at 0.9
            stagger = (self._rings.index((surf, size, _max_alpha, color))) * 0.2
            local_t = max(0.0, min(1.0, (t - stagger) / 0.6))
            scale = 0.5 + 0.5 * local_t
            alpha_factor = 1.0 - local_t
            if alpha_factor <= 0:
                continue
            w = int(size * scale)
            h = w
            if w <= 0:
                continue
            scaled = pygame.transform.smoothscale(surf, (w, h))
            scaled.set_alpha(int(scaled.get_alpha() * alpha_factor))
            rect = scaled.get_rect(center=(int(self.x), int(self.y)))
            target.blit(scaled, rect)
