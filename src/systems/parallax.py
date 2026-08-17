"""Parallax background — 5 star layers + 6 nebula (AI sprites) + planets.

Per GDD §4 ParallaxBackground: 5 layers con velocidades [20, 50, 100, 180,
280] px/s. 6 nebula types cargadas como sprites AI pre-generados.
Planets con atmosphere + rings animados. Theme change reaplica tints
a las estrellas (las nebulosas conservan sus colores baked-in).

Description: the background scrolls top→bottom (the player moves up the
             play field against incoming waves). Stars tile vertically;
             nebula drifts; planets spawn on a timer and slowly rotate.
Dependencies: pygame, settings, palette, easing.

BLOQUE 58.14.3: replaced the procedural spiral-arm renderer
(_render_nebula_surface used to compute arm distance + dust lane +
embedded stars per pixel — slow, and visually weak: it looked like
"a solid blue blob with a few soft puffs", not a galaxy). Now each
nebula picks one of 4 AI-generated spiral galaxy sprites
(Assets/background/galaxy_sprite_*.png) and smoothscales it to fit
the nebula's radius. Same per-frame cost (one blit), DRAMATICALLY
better look — real spiral arms, bright core, embedded stars.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.utils.palette import THEMES, get_theme


# BLOQUE 58.14.3: 4 AI-generated spiral galaxy sprites in blue/purple
# palette. Generated with image_synthesize, processed by
# tools/process_galaxy_sprites.py (remove dark bg, square-pad, LANCZOS
# resize to 280x280 to fit nebula_radius_max=140 with some bleed).
# Path is resolved relative to this file so it works regardless of cwd.
_THIS_DIR = Path(__file__).resolve().parent
_GALAXY_SPRITE_PATHS: tuple[Path, ...] = tuple(
    _THIS_DIR.parent.parent
    / "Assets" / "background" / f"galaxy_sprite_{i:02d}.png"
    for i in range(1, 5)
)
# Fallback size when a sprite is missing — used for the soft-circle
# fallback path so nebulas still have something on screen.
_GALAXY_FALLBACK_RADIUS_PX = 60


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

    BLOQUE 58.14.3: each nebula picks one of 4 AI-generated spiral
    galaxy sprites and smoothscales it to fit `radius` (see
    `_render_nebula_surface`). The cached Surface is blit each
    frame, so the cloud looks like a REAL spiral galaxy (proper
    arms, bright core, embedded stars) instead of a procedural
    approximation. The `color` field is kept for backward compat
    (some tests assert on it after `set_theme`) but it's no
    longer used for rendering — the sprite already has the right
    palette baked in.
    """
    x: float
    y: float
    radius: float
    color: tuple[int, int, int]
    vx: float = 0.0
    vy: float = 8.0  # drift down with parallax
    # Cached pre-rendered surface (set by _render_nebula_surface after
    # init). Holds the AI sprite scaled to (radius*2, radius*2).
    surface: Optional[pygame.Surface] = None
    # Index into the loaded galaxy sprite list (for debugging only).
    sprite_variant: int = 0


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
        # BLOQUE 58.14.3: lazy-loaded AI galaxy sprite cache. Filled
        # on first nebula render, shared across all nebulas.
        self._galaxy_sprites: Optional[list[pygame.Surface]] = None
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
        """Re-tint stars for a new theme. Called on act transition.

        BLOQUE 58.14.3: nebula surfaces are NOT re-rendered on theme
        change — they use AI sprites with baked-in colors (which
        already match the blue/purple default palette). The `color`
        field on each nebula is still updated for backward compat
        with code/tests that read it, but the rendered surface
        stays the same.
        """
        self._theme_name = name
        theme = get_theme(name)
        nebula_swatches = theme["nebula"]
        for i, n in enumerate(self._nebula):
            n.color = nebula_swatches[i % len(nebula_swatches)]

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
        """BLOQUE 58.14.3: build the nebula surface from an AI sprite.

        Replaces the procedural spiral-arm renderer (BLOQUE 58.14.2)
        which produced a weak "solid blue blob" look. Now we pick
        one of 4 AI-generated spiral galaxy sprites and smoothscale
        it to fit `n.radius`. Result: real spiral arms, bright core,
        embedded stars, proper soft edges.

        If no AI sprite is found on disk, falls back to a simple
        gradient circle so the game still has something on screen.
        """
        sprites = self._load_galaxy_sprites()
        size = max(8, int(n.radius * 2))
        if sprites:
            # Pick a variant (random per nebula so consecutive nebulas
            # look different). The variant is recorded on the nebula
            # for debugging / future deterministic-replay support.
            variant = self._rng.randrange(len(sprites))
            n.sprite_variant = variant
            src = sprites[variant]
            return pygame.transform.smoothscale(src, (size, size))
        # Fallback: soft gradient circle.
        return self._fallback_nebula_surface(n, size)

    def _load_galaxy_sprites(self) -> list[pygame.Surface]:
        """Lazy-load the 4 AI-generated galaxy sprites from disk.

        Cached on first call so the file I/O happens once per
        ParallaxBackground lifetime. Returns an empty list if no
        sprite is found, signaling the fallback path.
        """
        if self._galaxy_sprites is not None:
            return self._galaxy_sprites
        loaded: list[pygame.Surface] = []
        for path in _GALAXY_SPRITE_PATHS:
            try:
                # convert_alpha() needs a display, but in test mode
                # there's no display. Fall back to raw load (still
                # has alpha from the PNG).
                raw = pygame.image.load(str(path))
                try:
                    surf = raw.convert_alpha()
                except pygame.error:
                    surf = raw
                loaded.append(surf)
            except (pygame.error, FileNotFoundError, OSError):
                continue
        self._galaxy_sprites = loaded
        return loaded

    def _fallback_nebula_surface(self, n: Nebula, size: int) -> pygame.Surface:
        """Soft gradient circle for when AI sprites are missing.

        Concentric circles with decreasing alpha give a "fuzzy ball"
        look. Not a galaxy, but at least the player can see the
        nebula exists and the gameplay still works.
        """
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        r_max = size // 2
        if r_max <= 0:
            return surf
        for r in range(r_max, 0, -1):
            t = r / r_max
            a = int(40 * t)  # softer than the full nebula
            pygame.draw.circle(surf, (*n.color, a),
                               (r_max, r_max), r)
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
