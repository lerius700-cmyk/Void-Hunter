"""Parallax background — 5 star layers + 6 nebula types + planets.

Per GDD §4 ParallaxBackground: 5 layers con velocidades [20, 50, 100, 180,
280] px/s. 6 nebula types procedurales. Planets con atmosphere + rings
animados. Theme change reapplies tints.

Description: the background scrolls top→bottom (the player moves up the
             play field against incoming waves). Stars tile vertically;
             nebula drifts; planets spawn on a timer and slowly rotate.
Dependencies: pygame, settings, palette, easing.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.utils.palette import THEMES, get_theme


# Star layer scroll speeds (px/s). Layer 0 = farthest, slowest.
LAYER_SPEEDS: tuple[int, ...] = (20, 50, 100, 180, 280)
NUM_LAYERS = 5

# Star count per layer (per screen height)
# BLOQUE 58.12: lowered from 50 to 12 default — user wants ~80% black space.
# Title screen keeps the dense look; gameplay uses sparse.
STARS_PER_LAYER_DEFAULT = 12

# Planet spawn timer (seconds)
PLANET_SPAWN_MIN_S = 8.0
PLANET_SPAWN_MAX_S = 18.0

# Planet sizes (radius in px)
PLANET_RADIUS_MIN = 8
PLANET_RADIUS_MAX = 24

# Backward-compat alias (used by some tests)
STARS_PER_LAYER = STARS_PER_LAYER_DEFAULT


@dataclass
class Star:
    """Single star with twinkle state."""
    x: float
    y: float
    layer: int
    base_alpha: int
    twinkle_phase: float  # 0..2π


@dataclass
class Nebula:
    """Single nebula cloud.

    BLOQUE 58.14.1: each nebula pre-renders a noise-based cloud surface
    on init (see `_render_nebula_surface`). The cached Surface is blit
    each frame, so the cloud looks like a real procedural nebula
    (variable density, wisps, multiple soft puffs blended) instead of
    a single solid circle.
    """
    x: float
    y: float
    radius: float
    color: tuple[int, int, int]
    vx: float = 0.0
    vy: float = 8.0  # drift down with parallax
    # Cached pre-rendered surface (set by _render_nebula_surface after
    # init). Holds the procedural cloud pixels with alpha.
    surface: Optional[pygame.Surface] = None


@dataclass
class Planet:
    """Single planet with atmosphere + ring."""
    x: float
    y: float
    radius: int
    color: tuple[int, int, int]
    ring_color: tuple[int, int, int]
    ring_angle: float = 0.0  # ring orientation
    ring_width: int = 2


class ParallaxBackground:
    """5-layer parallax + nebula + planet atmosphere + rings.

    Per GDD §11: parallax render <0.40ms.
    """

    def __init__(
        self,
        width: int = INTERNAL_W,
        height: int = INTERNAL_H,
        rng_seed: int | None = 42,
        stars_per_layer: int = STARS_PER_LAYER_DEFAULT,
        nebula_count: int = 6,
        nebula_radius_min: int = 40,
        nebula_radius_max: int = 80,
        spawn_planets: bool = True,
    ) -> None:
        """BLOQUE 58.12: configurable density for sparse gameplay background.

        BLOQUE 58.13.3: added nebula_radius_min / nebula_radius_max so the
        gameplay background can have ONE LARGE off-center nebula (instead
        of 6 small ones). Title screen keeps the dense 6-small default.

        Args:
            stars_per_layer: number of stars per parallax layer.
                Default 12 (sparse, ~80% black). Title screen overrides
                to 50 for the dense look.
            nebula_count: number of nebula clouds. Default 6 (title). 0
                for gameplay (pure stars). 1 + large radius for a single
                dramatic off-center cloud.
            nebula_radius_min: minimum nebula radius. Default 40.
            nebula_radius_max: maximum nebula radius. Default 80.
            spawn_planets: if False, no planets spawn. Default True (title).
        """
        self._w = width
        self._h = height
        self._rng = random.Random(rng_seed)
        self._stars: list[Star] = []
        self._nebula: list[Nebula] = []
        self._planet: Optional[Planet] = None
        self._planet_timer: float = PLANET_SPAWN_MIN_S
        self._t: float = 0.0
        self._theme_name: str = "blue_void"
        self._stars_per_layer = stars_per_layer
        self._nebula_count = nebula_count
        self._nebula_radius_min = nebula_radius_min
        self._nebula_radius_max = nebula_radius_max
        self._spawn_planets_enabled = spawn_planets
        self._init_stars()
        self._init_nebula()

    def set_theme(self, name: str) -> None:
        """Re-tint stars and nebula for a new theme. Called on act transition."""
        self._theme_name = name
        theme = get_theme(name)
        # Re-tint nebula colors and re-render their surfaces
        nebula_swatches = theme["nebula"]
        for i, n in enumerate(self._nebula):
            n.color = nebula_swatches[i % len(nebula_swatches)]
            # Re-render the cloud surface with the new color
            n.surface = self._render_nebula_surface(n)

    @property
    def active_count(self) -> int:
        return len(self._stars) + len(self._nebula) + (1 if self._planet else 0)

    def update(self, dt: float) -> None:
        """Advance parallax, twinkle, planet rotation, planet spawn timer."""
        if dt <= 0.0:
            return
        self._t += dt
        # Stars: scroll down, wrap, twinkle
        for s in self._stars:
            speed = LAYER_SPEEDS[s.layer]
            s.y += speed * dt
            if s.y > self._h:
                s.y -= self._h
        # Nebula: drift down
        for n in self._nebula:
            n.y += n.vy * dt
            if n.y - n.radius > self._h:
                n.y = -n.radius
                n.x = self._rng.uniform(0, self._w)
        # Planet: rotate ring, scroll slowly
        if self._planet is not None:
            self._planet.ring_angle = (self._planet.ring_angle + 8.0 * dt) % 360.0
            self._planet.y += 12.0 * dt
            if self._planet.y - self._planet.radius > self._h:
                self._planet = None
        else:
            if not self._spawn_planets_enabled:
                return
            self._planet_timer -= dt
            if self._planet_timer <= 0.0:
                self._spawn_planet()
                self._planet_timer = self._rng.uniform(PLANET_SPAWN_MIN_S, PLANET_SPAWN_MAX_S)

    def draw(self, target: pygame.Surface) -> None:
        """Render: nebula → stars → planet. No blits() batch (parallax
        uses 3 distinct surface types with different alpha, single-call
        per layer is OK per spec).

        BLOQUE 58.14.1: nebulas are blitted from their pre-rendered
        procedural cloud surfaces (see `_render_nebula_surface`), so the
        per-frame cost is just one blit per nebula.
        """
        # 1. Nebula (blit cached procedural cloud surface)
        for n in self._nebula:
            if n.surface is not None:
                target.blit(n.surface,
                            (int(n.x - n.radius), int(n.y - n.radius)),
                            special_flags=pygame.BLEND_PREMULTIPLIED)
            else:
                # Fallback (shouldn't happen since _init_nebula always
                # pre-renders). Draw a soft circle.
                surf = pygame.Surface((n.radius * 2, n.radius * 2), pygame.SRCALPHA)
                for r in range(int(n.radius), 0, -2):
                    a = int(20 * (r / n.radius))
                    pygame.draw.circle(surf, (*n.color, a),
                                       (n.radius, n.radius), r)
                target.blit(surf, (int(n.x - n.radius), int(n.y - n.radius)))
        # 2. Stars (5 layers, 1 blit per star = NUM_LAYERS * STARS_PER_LAYER
        #    blits. Acceptable since these are tiny 1x1 surfaces; could be
        #    batched in BLOQUE 11 optimization pass if needed.)
        for s in self._stars:
            twinkle = 0.7 + 0.3 * math.sin(self._t * 2.0 + s.twinkle_phase)
            a = int(min(255, s.base_alpha * twinkle))
            color = (200, 200, 220, a) if s.layer < 2 else (255, 255, 255, a)
            target.set_at((int(s.x), int(s.y) % self._h), color)
        # 3. Planet
        if self._planet is not None:
            self._draw_planet(target, self._planet)

    def release_all(self) -> None:
        """Reset to initial state. Used on scene transition."""
        self._init_stars()
        self._init_nebula()
        self._planet = None
        self._planet_timer = PLANET_SPAWN_MIN_S
        self._t = 0.0

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------
    def _init_stars(self) -> None:
        self._stars = []
        for layer in range(NUM_LAYERS):
            for _ in range(self._stars_per_layer):
                self._stars.append(Star(
                    x=self._rng.uniform(0, self._w),
                    y=self._rng.uniform(0, self._h),
                    layer=layer,
                    base_alpha=100 + layer * 30,  # farther = dimmer
                    twinkle_phase=self._rng.uniform(0, 2 * math.pi),
                ))

    def _init_nebula(self) -> None:
        """BLOQUE 58.12: configurable nebula count. Default 6 (title), 0 (gameplay).

        BLOQUE 58.13.3: when nebula_count == 1, place the single nebula in
        the bottom-right quadrant (off-center, away from ship spawn paths
        and the sub-boss entry point at y=20). It uses nebula_radius_min /
        nebula_radius_max so the user can request a large dramatic cloud.

        BLOQUE 58.14.1: each nebula pre-renders a noise-based cloud surface
        (multiple soft puffs blended with value noise). The cached
        Surface is blit in `draw()` instead of drawing concentric
        circles per frame.
        """
        self._nebula = []
        if self._nebula_count == 0:
            return
        theme = get_theme(self._theme_name)
        nebula_swatches = theme["nebula"]
        for i in range(self._nebula_count):
            if self._nebula_count == 1:
                # BLOQUE 58.13.3: single nebula → off-center bottom-right.
                x = self._w * 0.70
                y = self._h * 0.85
                radius = self._rng.uniform(
                    self._nebula_radius_min, self._nebula_radius_max
                )
            else:
                # BLOQUE 58.12: dense mode (title screen) — random scatter
                x = self._rng.uniform(0, self._w)
                y = self._rng.uniform(-self._h, self._h * 2)
                radius = self._rng.uniform(
                    self._nebula_radius_min, self._nebula_radius_max
                )
            n = Nebula(
                x=x,
                y=y,
                radius=radius,
                color=nebula_swatches[i % len(nebula_swatches)],
            )
            n.surface = self._render_nebula_surface(n)
            self._nebula.append(n)

    def _render_nebula_surface(self, n: Nebula) -> pygame.Surface:
        """BLOQUE 58.14.1: procedurally generate a cloud-like surface
        using value noise + multiple soft puffs blended together.

        Output: a square Surface (size 2*radius × 2*radius) with
        per-pixel alpha. Denser in the center, wispy at the edges,
        with 6-8 soft "puff" hotspots that create depth.

        Pure-stdlib (math + random) so we don't pull in numpy just
        for nebulas. The base is a low-resolution value noise grid
        upsampled to the surface size.
        """
        size = int(n.radius * 2)
        if size <= 0:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        # 1. Low-resolution value noise grid (6x6 random, then bilinear
        #    upsample to surface size). Higher res grid = more cloud detail.
        grid = 6
        cell = size / grid
        corners = [[self._rng.random() for _ in range(grid + 1)]
                   for _ in range(grid + 1)]
        # 2. Add 8 "puff" hotspots (Gaussian blobs at random positions
        #    within the nebula). This breaks the regularity of the
        #    noise field and gives it cloud-like depth + wisps.
        puffs = []
        for _ in range(8):
            puff_cx = self._rng.uniform(0.15, 0.85) * size
            puff_cy = self._rng.uniform(0.15, 0.85) * size
            puff_r = self._rng.uniform(0.20, 0.45) * size
            puff_strength = self._rng.uniform(0.30, 0.65)
            puffs.append((puff_cx, puff_cy, puff_r, puff_strength))
        # 3. Build the alpha mask: noise * radial_falloff + puffs.
        cx = cy = size / 2.0
        max_r = n.radius
        max_alpha = 195  # dense, visible cloud
        r2_max = max_r * max_r
        # Pre-compute noise per pixel (bilinear)
        def sample_noise(px: int, py: int) -> float:
            gx = min(int(px / cell), grid - 1)
            gy = min(int(py / cell), grid - 1)
            tx = (px / cell) - gx
            ty = (py / cell) - gy
            tx = tx * tx * (3.0 - 2.0 * tx)
            ty = ty * ty * (3.0 - 2.0 * ty)
            c00 = corners[gy][gx]
            c10 = corners[gy][gx + 1]
            c01 = corners[gy + 1][gx]
            c11 = corners[gy + 1][gx + 1]
            a = c00 + (c10 - c00) * tx
            b = c01 + (c11 - c01) * tx
            return a + (b - a) * ty
        # Build alpha array
        for py in range(size):
            dy = py - cy
            dy2 = dy * dy
            for px in range(size):
                dx = px - cx
                r2 = dx * dx + dy2
                if r2 > r2_max:
                    continue
                # Radial falloff: 1.0 at center, 0.0 at edge, smoothstep
                t = 1.0 - (r2 / r2_max)
                radial = t * t * (3.0 - 2.0 * t)
                # Get noise value (cloudy background)
                n_val = sample_noise(px, py)
                # Add puff contributions (overrides noise where puffs are)
                puff_total = 0.0
                for (pcx, pcy, pr, ps) in puffs:
                    ddx = px - pcx
                    ddy = py - pcy
                    d2 = ddx * ddx + ddy * ddy
                    if d2 < pr * pr:
                        pt = 1.0 - (d2 / (pr * pr))
                        # Smoothstep
                        pt = pt * pt * (3.0 - 2.0 * pt)
                        puff_total = max(puff_total, ps * pt)
                # Combine: max of (noise * 0.6, puff) * radial
                a = max(n_val * 0.7, puff_total) * radial
                a = min(1.0, a)
                if a > 0.01:
                    alpha = int(a * max_alpha)
                    # set_at on a Surface is per-pixel
        # 4. Rasterize to a Surface (use per-pixel set_at for transparency)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        for py in range(size):
            dy = py - cy
            dy2 = dy * dy
            for px in range(size):
                dx = px - cx
                r2 = dx * dx + dy2
                if r2 > r2_max:
                    continue
                t = 1.0 - (r2 / r2_max)
                radial = t * t * (3.0 - 2.0 * t)
                n_val = sample_noise(px, py)
                puff_total = 0.0
                for (pcx, pcy, pr, ps) in puffs:
                    ddx = px - pcx
                    ddy = py - pcy
                    d2 = ddx * ddx + ddy * ddy
                    if d2 < pr * pr:
                        pt = 1.0 - (d2 / (pr * pr))
                        pt = pt * pt * (3.0 - 2.0 * pt)
                        puff_total = max(puff_total, ps * pt)
                a = max(n_val * 0.7, puff_total) * radial
                a = min(1.0, a)
                if a > 0.01:
                    alpha = int(a * max_alpha)
                    # Slight color variation per puff for depth
                    cr = n.color[0]
                    cg = n.color[1]
                    cb = n.color[2]
                    if puff_total > n_val * 0.7:
                        # Inside a puff — brighten slightly
                        cr = min(255, cr + 20)
                        cg = min(255, cg + 20)
                        cb = min(255, cb + 20)
                    surf.set_at((px, py), (cr, cg, cb, alpha))
        return surf

    def _spawn_planet(self) -> None:
        theme = get_theme(self._theme_name)
        self._planet = Planet(
            x=self._rng.uniform(self._w * 0.2, self._w * 0.8),
            y=-self._rng.uniform(20, 40),
            radius=self._rng.randint(PLANET_RADIUS_MIN, PLANET_RADIUS_MAX),
            color=theme.get("accent", (200, 200, 200)),
            ring_color=theme.get("accent", (200, 200, 200)),
        )

    def _draw_planet(self, target: pygame.Surface, p: Planet) -> None:
        cx, cy = int(p.x), int(p.y)
        # Atmosphere halo (2 concentric soft circles)
        halo = pygame.Surface((p.radius * 4, p.radius * 4), pygame.SRCALPHA)
        for r in range(p.radius * 2, 0, -1):
            a = int(40 * (r / (p.radius * 2.0)))
            pygame.draw.circle(halo, (*p.color, a), (halo.get_width() // 2, halo.get_height() // 2), r)
        target.blit(halo, (cx - halo.get_width() // 2, cy - halo.get_height() // 2))
        # Planet body
        pygame.draw.circle(target, p.color, (cx, cy), p.radius)
        # Outline (1px darker)
        outline_color = (max(0, p.color[0] - 40), max(0, p.color[1] - 40), max(0, p.color[2] - 40))
        pygame.draw.circle(target, outline_color, (cx, cy), p.radius, 1)
        # Ring (ellipse, rotated)
        ring_w = p.radius * 2 + 6
        ring_h = max(2, p.radius // 3)
        # Build ring surface, then rotate.
        ring_surf = pygame.Surface((ring_w, ring_h * 2 + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(ring_surf, (*p.ring_color, 200),
                            (0, ring_h // 2 + 1, ring_w, ring_h))
        pygame.draw.ellipse(ring_surf, (*p.ring_color, 100),
                            (0, ring_h // 2 + 1, ring_w, ring_h), 1)
        rotated = pygame.transform.rotate(ring_surf, p.ring_angle)
        target.blit(rotated, (cx - rotated.get_width() // 2, cy - rotated.get_height() // 2))
