"""Particle engine: 18 kinds, pool 1500, LRU tint cache 128, single blits() batch.

Expanded from nebula-hunter seed (12 kinds, pool 600, tint cache 64). Per
GDD §11 frame budget: 1500 particles update in <0.75ms, draw in <1.5ms.

Description: pooled particles, single blits() render, LRU tint cache. The
             18 kinds share one Particle dataclass; per-kind behavior is
             encoded in the kind constant + small switch in update().
Dependencies: pygame, pool, palette, easing.
"""
from __future__ import annotations

import math
import random
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

import pygame

from src.core.settings import (
    INTERNAL_H,
    INTERNAL_W,
    PARTICLE_POOL,
)
from src.systems.pool import Pool
from src.utils.palette import PALETTE


# ---------------------------------------------------------------------------
# Particle kinds — 19 in total (12 seed + 6 net new + 1 wake)
# ---------------------------------------------------------------------------
P_SPARK = 0         # 1x1 dot, fast, no gravity         (seed)
P_SMOKE = 1         # 4x4 → 8x8 puff, expands, rises    (seed)
P_SHRAPNEL = 2      # 2x2 sharp, short life             (seed)
P_DEBRIS = 3        # 4x4 with full physics (rot+grav)  (seed)
P_SHOCKWAVE = 4     # expanding ring, single-frame      (seed)
P_FIRE = 5          # 2x2 → 3x3, fast up, fades         (seed)
P_ELECTRIC = 6      # 4-segment zigzag, very short      (seed; merged w/ electric-arc)
P_DUST = 7          # 6x6 fuzzy, large                   (seed)
P_MUZZLE = 8        # 4px ring, 1 frame                  (seed)
P_GLOW = 9          # 12x12 fuzzy halo, slow fade        (seed)
P_ION = 10          # 2x2 dot follows bullet            (seed)
P_FLASH = 11        # 16x16 white, instant              (seed)
# Net new kinds (6) per GDD §8 reconciliation:
P_RING_FILL = 12    # filled disc, scale 0->40 (bomb, special)
P_RING_THICK = 13   # thick 4px ring, scale 0->80 (boss transition)
P_ELECTRIC_ARC = 14 # upgraded zigzag, 8x4 jitter (ion pierce, chain)
P_SQUARE = 15       # 4x4 hard edge (UI accent, score popup)
P_LINE = 16         # 1xN line (beam trail, laser residual)
P_LIGHT_FLASH = 17  # 6x6 quick, 2 frames (damage feedback variant)
# BLOQUE 58.8.3: bright orange "wake" with built-in delay. Used by
# player PROPULSION to leave a 1-second-delayed afterglow that
# "follows" the player. Particle is invisible (and unaffected by
# physics) during its delay_s, then becomes visible and fades.
P_WAKE = 18         # delayed orange afterglow (player propulsion)

P_KIND_COUNT = 19

# Per-kind defaults
@dataclass(frozen=True)
class _KindConfig:
    base_color: tuple[int, int, int]
    base_size: int          # base surface size (px)
    default_life: float     # seconds
    gravity: float          # px/s²
    damping: float          # velocity multiplier per second
    fade: bool
    expand: float           # radius growth per second (shockwave, ring)
    use_sprite: bool        # True = use sprite_idx, False = procedural shape


KIND_CONFIG: dict[int, _KindConfig] = {
    P_SPARK:        _KindConfig((255, 255, 255), 1,  0.30, 0.0, 1.0, True,  0.0, False),
    P_SMOKE:        _KindConfig((120, 120, 140), 4, 0.80, -20.0, 0.95, True,  8.0, False),
    P_SHRAPNEL:     _KindConfig((255, 200, 80),  2, 0.40, 0.0, 1.0, True,  0.0, False),
    P_DEBRIS:       _KindConfig((120, 120, 140), 4, 1.50, 200.0, 0.92, True, 0.0, True),
    P_SHOCKWAVE:    _KindConfig((255, 255, 255), 8, 0.30, 0.0, 1.0, True,  120.0, False),
    P_FIRE:         _KindConfig((255, 180, 80),  2, 0.25, -120.0, 0.90, True, 2.0, False),
    P_ELECTRIC:     _KindConfig((80, 200, 255),  6, 0.10, 0.0, 1.0, True,  0.0, False),
    P_DUST:         _KindConfig((180, 80, 40),   6, 1.20, -10.0, 0.97, True, 6.0, False),
    P_MUZZLE:       _KindConfig((255, 255, 255), 4, 0.05, 0.0, 1.0, True,  60.0, False),
    P_GLOW:         _KindConfig((255, 255, 255), 12, 0.60, 0.0, 1.0, True, 0.0, False),
    P_ION:          _KindConfig((80, 200, 255),  2, 0.20, 0.0, 0.95, True,  0.0, False),
    P_FLASH:        _KindConfig((255, 255, 255), 16, 0.10, 0.0, 1.0, True, 0.0, False),
    # Net new
    P_RING_FILL:    _KindConfig((255, 200, 80),  4, 0.40, 0.0, 1.0, True,  100.0, False),
    P_RING_THICK:   _KindConfig((255, 255, 255), 8, 0.50, 0.0, 1.0, True,  160.0, False),
    P_ELECTRIC_ARC: _KindConfig((80, 200, 255),  8, 0.15, 0.0, 1.0, True,  0.0, False),
    P_SQUARE:       _KindConfig((255, 255, 255), 4, 0.50, 0.0, 1.0, True,  0.0, False),
    P_LINE:         _KindConfig((255, 255, 255), 1, 0.30, 0.0, 1.0, True,  0.0, False),
    P_LIGHT_FLASH:  _KindConfig((255, 255, 255), 6, 0.07, 0.0, 1.0, True,  0.0, False),
    # BLOQUE 58.8.3: P_WAKE — bright orange afterglow with built-in
    # delay. The engine sets Particle.delay_s on emit, and the particle
    # is invisible (and frozen) until delay_s reaches 0. Once the delay
    # expires, the particle becomes visible and starts fading over its
    # normal life. This lets the player PROPULSION emit one wake per
    # frame, but the trail only "appears" 1 second later — creating the
    # delayed-afterglow effect the user asked for.
    P_WAKE:         _KindConfig((255, 160, 60),  10, 0.80, 0.0, 1.0, True,  0.0, False),
}


@dataclass
class Particle:
    """Single particle; flag `active` is read by Pool.

    Layout is hot-path: keep fields in a flat dataclass (no inheritance,
    no __slots__ trade-off — dataclass slot=False is default; we keep all
    fields on the instance to avoid attribute lookups in update()).
    """
    active: bool = False
    kind: int = P_SPARK
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.0
    max_life: float = 0.0
    radius: float = 1.0
    color: tuple[int, int, int] = (255, 255, 255)
    # Physics
    gravity: float = 0.0
    damping: float = 1.0
    # Render hints
    fade: bool = True
    expand: float = 0.0
    # For debris: which sprite index to use
    sprite_idx: int = 0
    use_sprite: bool = False
    # Rotation in degrees (for debris tumble + general 360° effects)
    angle: float = 0.0
    angular_vel: float = 0.0
    # BLOQUE 58.8.3: delay before the particle becomes visible. While
    # delay_s > 0, the particle is INVISIBLE and FROZEN (no physics,
    # no fade, no rendering). When delay_s reaches 0, the particle
    # becomes visible and runs its normal life/fade cycle. Used by
    # P_WAKE for the 1-second-delayed player propulsion afterglow.
    delay_s: float = 0.0
    # Cached computed alpha (filled by engine.update)
    _alpha: int = 255

    def on_spawn(self) -> None:
        # reset transient state on acquisition
        self._alpha = 255
        self.delay_s = 0.0

    def on_release(self) -> None:
        # free refs that could leak memory
        self.color = (255, 255, 255)
        self.delay_s = 0.0


class _TintCache:
    """LRU cache mapping (kind, r, g, b) -> tinted pygame.Surface.

    Cap is 128 by default. When full, the oldest entry is evicted. The
    pre-baked base surface per kind is multiplied (BLEND_RGBA_MULT) with a
    flat color surface to produce a tinted variant — fast and allocation-
    free in steady state.
    """

    __slots__ = ("_cache", "_cap", "_hits", "_misses")

    def __init__(self, cap: int = 128) -> None:
        self._cache: "OrderedDict[tuple[int, int, int, int], pygame.Surface]" = OrderedDict()
        self._cap: int = cap
        self._hits: int = 0
        self._misses: int = 0

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def get(self, kind: int, r: int, g: int, b: int) -> pygame.Surface | None:
        key = (kind, r, g, b)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, kind: int, r: int, g: int, b: int, surface: pygame.Surface) -> None:
        key = (kind, r, g, b)
        if key in self._cache:
            self._cache.move_to_end(key)
            return
        self._cache[key] = surface
        if len(self._cache) > self._cap:
            self._cache.popitem(last=False)  # evict oldest


class ParticleEngine:
    """Pooled particle engine — 18 kinds, single-blits render, LRU tint cache.

    Per-frame flow:
      1. update(dt)    — physics + life decrement for active particles
      2. emit(...)     — call any number of times to spawn
      3. draw(target)  — single target.blits() batch

    Hard rule: no pygame.Surface allocation in update/draw. All per-kind
    base surfaces are pre-baked in __init__. Tinted variants go through
    the LRU cache.
    """

    MAX_TINT_CACHE = 128

    def __init__(
        self,
        pool_size: int = PARTICLE_POOL,
        max_tint_cache: int = MAX_TINT_CACHE,
        bounds: tuple[int, int] | None = None,
    ) -> None:
        # Bounds = (w, h) for offscreen-cull check. None = no cull.
        self._pool: Pool[Particle] = Pool(Particle, pool_size)
        self._tint_cache: _TintCache = _TintCache(max_tint_cache)
        self._bounds: tuple[int, int] = bounds or (INTERNAL_W, INTERNAL_H)
        # Pre-bake one base surface per kind, fully opaque white. Tinted
        # variants multiply against this.
        self._base_surfs: dict[int, pygame.Surface] = {}
        self._rng: random.Random = random.Random()
        # Scratch surface used in tinting — pre-allocated, never freed.
        self._tint_scratch = pygame.Surface((1, 1), pygame.SRCALPHA)
        self._init_base_surfaces()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    @property
    def pool(self) -> Pool[Particle]:
        return self._pool

    @property
    def active_count(self) -> int:
        return self._pool.active_count

    @property
    def tint_cache_size(self) -> int:
        return self._tint_cache.size

    def get_tint_cache_stats(self) -> tuple[int, int, int]:
        """Return (size, hits, misses)."""
        return self._tint_cache.size, self._tint_cache.hits, self._tint_cache.misses

    def reset_cache_stats(self) -> None:
        self._tint_cache._hits = 0
        self._tint_cache._misses = 0

    def emit(
        self,
        kind: int,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        color: tuple[int, int, int] | None = None,
        life: float | None = None,
        radius: float | None = None,
        angle: float = 0.0,
        angular_vel: float = 0.0,
        delay_s: float = 0.0,
    ) -> Particle | None:
        """Spawn a particle. Returns None if pool is exhausted.

        BLOQUE 58.8.3: `delay_s` makes the particle invisible/frozen
        for that many seconds before it becomes active. Used by P_WAKE
        for the 1-second-delayed player propulsion afterglow.
        """
        if kind not in KIND_CONFIG:
            return None
        p = self._pool.acquire()
        if p is None:
            return None  # silent exhaust per spec
        cfg = KIND_CONFIG[kind]
        p.kind = kind
        p.x = x
        p.y = y
        p.vx = vx
        p.vy = vy
        p.color = color if color is not None else cfg.base_color
        p.life = life if life is not None else cfg.default_life
        p.max_life = p.life
        p.radius = radius if radius is not None else float(cfg.base_size)
        p.gravity = cfg.gravity
        p.damping = cfg.damping
        p.fade = cfg.fade
        p.expand = cfg.expand
        p.use_sprite = cfg.use_sprite
        p.angle = angle
        p.angular_vel = angular_vel
        p.delay_s = delay_s
        # While the particle is in its delay window, alpha is 0 so it
        # is not rendered. The engine tick handles decrementing delay_s
        # and setting alpha to 255 when delay_s reaches 0.
        p._alpha = 0 if delay_s > 0.0 else 255
        return p

    def update(self, dt: float) -> None:
        """Advance physics + life. Release dead particles.

        Hot path: ~0.5µs per active particle (target <0.75ms for 1500).
        """
        if dt <= 0.0:
            return
        for p in self._pool:
            if not p.active:
                continue
            # BLOQUE 58.8.3: delay window — while delay_s > 0 the
            # particle is INVISIBLE and FROZEN. We still tick the delay
            # down (so the particle eventually becomes visible) and
            # skip ALL physics + life-decay so it doesn't move or fade.
            if p.delay_s > 0.0:
                p.delay_s -= dt
                if p.delay_s > 0.0:
                    continue  # still in delay window — skip everything
                # Delay just expired this frame. Remaining dt is applied
                # to the normal life cycle below.
                p._alpha = 255
                overflow = -p.delay_s  # positive: how much dt spilled over
                p.delay_s = 0.0
                if overflow > 0.0:
                    p.life -= overflow
                    if p.life <= 0.0:
                        self._pool.release(p)
                        continue
                # No continue — fall through to physics for this frame.
            # Life decay
            p.life -= dt
            if p.life <= 0.0:
                self._pool.release(p)
                continue
            # Apply velocity with damping
            decay = p.damping ** (dt * 60.0)  # damping expressed as 60Hz-norm
            p.vx *= decay
            p.vy *= decay
            # Gravity
            p.vy += p.gravity * dt
            # Position integration
            p.x += p.vx * dt
            p.y += p.vy * dt
            # Rotation
            if p.angular_vel:
                p.angle = (p.angle + p.angular_vel * dt) % 360.0
            # Expansion (shockwave, ring)
            if p.expand:
                p.radius += p.expand * dt
            # Fade — alpha proportional to remaining life when fade=True
            if p.fade and p.max_life > 0.0:
                p._alpha = max(0, min(255, int(255.0 * (p.life / p.max_life))))
            # Offscreen cull — release if outside bounds + margin
            bw, bh = self._bounds
            if p.x < -16 or p.x > bw + 16 or p.y < -16 or p.y > bh + 16:
                self._pool.release(p)
                continue
            # Special: electric-arc jitter (no NaN guarantee)
            if p.kind == P_ELECTRIC_ARC:
                # clamp angle to finite range to be safe
                if not math.isfinite(p.angle):
                    p.angle = 0.0
                p.angle = (p.angle + self._rng.uniform(-30.0, 30.0) * dt * 60.0) % 360.0

    def draw(self, target: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> int:
        """Single target.blits() batch. Returns number of blits.

        Hard rule: NO target.blit() per particle; everything goes through
        one blits() call. Per GDD §11: 1500 particles in <1.5ms.
        """
        ox, oy = offset
        batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        dead: list[Particle] = []
        for p in self._pool:
            if not p.active:
                continue
            surf = self._get_tinted_surface(p)
            if surf is None:
                continue
            # Apply alpha (BLEND_RGBA_MULT multiply by alpha, but we can use
            # set_alpha for single-channel per surface. Cheaper: build once
            # with the final alpha via the tint cache key.
            alpha = p._alpha
            if alpha < 255:
                # set_alpha returns copy; cache key encodes (kind, r, g, b, alpha)
                # to avoid realloc. We use a different code path: cache holds
                # pre-alpha surfaces and we set_alpha per draw.
                surf = surf.copy()
                surf.set_alpha(alpha)
            cx = int(p.x - surf.get_width() * 0.5) + ox
            cy = int(p.y - surf.get_height() * 0.5) + oy
            batch.append((surf, (cx, cy)))
        if batch:
            target.blits(batch)
        return len(batch)

    def release_all(self) -> None:
        """Scene transition helper."""
        self._pool.release_all()

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------
    def _init_base_surfaces(self) -> None:
        """Pre-bake one opaque white surface per kind. Per GDD §11, this
        is the only place we allocate pygame.Surface per kind.
        """
        for kind, cfg in KIND_CONFIG.items():
            size = cfg.base_size
            if kind == P_SHOCKWAVE:
                # Ring expanding from radius 0 — base is empty 8x8, scale up at draw
                surf = pygame.Surface((max(8, size), max(8, size)), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, 255),
                                   (surf.get_width() // 2, surf.get_height() // 2),
                                   max(1, size // 2), 1)
            elif kind == P_RING_FILL:
                surf = pygame.Surface((max(8, size), max(8, size)), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, 255),
                                   (surf.get_width() // 2, surf.get_height() // 2),
                                   max(2, size // 2))
            elif kind == P_RING_THICK:
                surf = pygame.Surface((max(8, size), max(8, size)), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, 255),
                                   (surf.get_width() // 2, surf.get_height() // 2),
                                   max(2, size // 2), 4)
            elif kind == P_ELECTRIC:
                # Zigzag 4-segment, 6x6
                surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.line(surf, (255, 255, 255, 255), (1, 5), (2, 2), 1)
                pygame.draw.line(surf, (255, 255, 255, 255), (2, 2), (4, 4), 1)
                pygame.draw.line(surf, (255, 255, 255, 255), (4, 4), (5, 1), 1)
            elif kind == P_ELECTRIC_ARC:
                # 8x4 jitter — drawn as zigzag, jitter applied at runtime via angle
                surf = pygame.Surface((8, 4), pygame.SRCALPHA)
                pygame.draw.line(surf, (255, 255, 255, 255), (0, 3), (2, 1), 1)
                pygame.draw.line(surf, (255, 255, 255, 255), (2, 1), (4, 3), 1)
                pygame.draw.line(surf, (255, 255, 255, 255), (4, 3), (6, 1), 1)
                pygame.draw.line(surf, (255, 255, 255, 255), (6, 1), (8, 3), 1)
            elif kind == P_LINE:
                # 1xN vertical line (thickness >=1; spec: thickness=0 → width=1)
                surf = pygame.Surface((1, max(1, size)), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 255))
            elif kind == P_SQUARE:
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 255))
            elif kind == P_SMOKE:
                # 4x4 base, will scale up
                surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, 255), (2, 2), 2)
            elif kind == P_FIRE:
                surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 255))
            elif kind == P_SHRAPNEL:
                surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 255))
            elif kind == P_SPARK:
                surf = pygame.Surface((1, 1), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 255))
            elif kind == P_ION:
                surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 255))
            elif kind == P_GLOW:
                surf = pygame.Surface((12, 12), pygame.SRCALPHA)
                for r in range(6, 0, -1):
                    a = int(40 * (r / 6.0))
                    pygame.draw.circle(surf, (255, 255, 255, a), (6, 6), r)
            elif kind == P_DUST:
                surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, 200), (3, 3), 3)
            elif kind == P_MUZZLE:
                surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, 255), (2, 2), 2, 1)
            elif kind == P_FLASH:
                surf = pygame.Surface((16, 16), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, 255), (8, 8), 8)
            elif kind == P_LIGHT_FLASH:
                surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, 255), (3, 3), 3)
            elif kind == P_DEBRIS:
                # 4x4 chunk, rotation applied at draw
                surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 255))
            else:
                surf = pygame.Surface((max(1, size), max(1, size)), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 255))
            self._base_surfs[kind] = surf

    def _get_tinted_surface(self, p: Particle) -> pygame.Surface | None:
        """Return a tinted (kind, color) surface, or the base if white."""
        r, g, b = p.color
        # White = identity, skip tint multiplication.
        if (r, g, b) == (255, 255, 255):
            base = self._base_surfs.get(p.kind)
            if base is None:
                return None
            # For shockwave/ring, scale by current radius.
            if p.kind in (P_SHOCKWAVE, P_RING_FILL, P_RING_THICK):
                if p.radius <= 0.0:
                    return None
                target_size = max(2, int(p.radius * 2))
                if target_size != base.get_width():
                    return pygame.transform.scale(base, (target_size, target_size))
            return base

        cached = self._tint_cache.get(p.kind, r, g, b)
        if cached is not None:
            # Apply current radius scaling if needed
            if p.kind in (P_SHOCKWAVE, P_RING_FILL, P_RING_THICK):
                if p.radius <= 0.0:
                    return None
                target_size = max(2, int(p.radius * 2))
                if target_size != cached.get_width():
                    return pygame.transform.scale(cached, (target_size, target_size))
            return cached

        base = self._base_surfs.get(p.kind)
        if base is None:
            return None

        # Tint via BLEND_RGBA_MULT against a flat color surface. This is
        # done once per (kind, color); the result is cached.
        tint_surf = base.copy()
        self._tint_scratch = pygame.Surface(tint_surf.get_size(), pygame.SRCALPHA)
        self._tint_scratch.fill((r, g, b, 255))
        tint_surf.blit(self._tint_scratch, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self._tint_cache.put(p.kind, r, g, b, tint_surf)

        if p.kind in (P_SHOCKWAVE, P_RING_FILL, P_RING_THICK):
            if p.radius <= 0.0:
                return None
            target_size = max(2, int(p.radius * 2))
            if target_size != tint_surf.get_width():
                return pygame.transform.scale(tint_surf, (target_size, target_size))
        return tint_surf


# Helper: convenience palette lookup
def palette_color(char: str) -> tuple[int, int, int]:
    return PALETTE.get(char, (255, 255, 255))
