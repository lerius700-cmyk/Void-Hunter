"""Projectile pool: 400 base, 600 in BOSS_FIGHT. 4 sprite types, 4-frame anim.

Per GDD §3 + §11: 4 projectile sprite types (player bullet / enemy bullet /
charged bullet / boss bullet) each with 4-frame pulse animation at 16 FPS.
Each projectile can carry its own trail (not a generic ion-wake). Pierce
count, glow halo for charged shots, hard bound cull.

Description: pooled bullets. spawn() returns inactive bullet or None if
             pool is exhausted. update(dt) advances position, animates
             frame, culls offscreen, ticks pierce counter. draw() uses
             single target.blits() batch.
Dependencies: pygame, pool, settings.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import pygame

from src.core.settings import (
    INTERNAL_H,
    INTERNAL_W,
    PROJECTILE_POOL,
    PROJECTILE_POOL_BOSS,
)
from src.systems.pool import Pool


# Bullet kinds
BULLET_PLAYER = 0          # fast, friendly
BULLET_PLAYER_CHARGED = 1  # glow halo, pierce
BULLET_PLAYER_BEAM = 4     # BLOQUE 30: L3 charged beam — BLOQUE 36: recolored to plasma cyan
BULLET_ENEMY = 2           # standard enemy shot
BULLET_BOSS = 3            # boss shot, 1-frame anim (no flicker per spec)

# Bullet owner
OWNER_PLAYER = 0
OWNER_ENEMY = 1
OWNER_BOSS = 2

# Animation timing: 4 frames at 16 FPS = 0.0625s/frame
FRAME_DURATION_S = 1.0 / 16.0
NUM_FRAMES = 4

# Pre-baked bullet sizes (per kind)
# BLOQUE 35: visual ~75% scale (was 4x6 / 6x10 / 12x16 / 4x6 / 8x8).
# Collision rects are hardcoded elsewhere (4x6) and NOT scaled — keeps
# difficulty consistent with pre-BLOQUE-35 gameplay.
BULLET_SIZES = {
    BULLET_PLAYER: (3, 5),             # was (4, 6)
    BULLET_PLAYER_CHARGED: (5, 8),     # was (6, 10)
    BULLET_PLAYER_BEAM: (9, 12),       # was (12, 16)
    BULLET_ENEMY: (3, 5),              # was (4, 6)
    BULLET_BOSS: (6, 6),               # was (8, 8)
}

# Default speeds (px/s) per kind
DEFAULT_SPEEDS = {
    BULLET_PLAYER: 480.0,
    BULLET_PLAYER_CHARGED: 600.0,
    BULLET_PLAYER_BEAM: 700.0,  # BLOQUE 30: beam is fast
    BULLET_ENEMY: 220.0,
    BULLET_BOSS: 240.0,
}

# Default colors per kind
DEFAULT_COLORS = {
    BULLET_PLAYER: (255, 220, 100),       # warm gold (player plasma default)
    BULLET_PLAYER_CHARGED: (255, 240, 200),
    BULLET_PLAYER_BEAM: (140, 220, 255),  # BLOQUE 36: electric cyan plasma (was pure white)
    BULLET_ENEMY: (255, 100, 100),         # red-ish
    BULLET_BOSS: (220, 120, 255),          # purple-ish
}


@dataclass
class Projectile:
    """Single projectile. active flag is read by Pool."""
    active: bool = False
    kind: int = BULLET_PLAYER
    owner: int = OWNER_PLAYER
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    damage: int = 1
    # Animation
    frame: int = 0
    frame_timer: float = 0.0
    # For charged bullets
    pierce: int = 0        # enemies hit before release; 0 = explodes on impact
    pierce_hits: int = 0
    # Trail state
    trail_cooldown: float = 0.0
    has_trail: bool = False
    trail_color: tuple[int, int, int] = (255, 255, 255)
    # Cached surface (filled by engine, tinted at draw)
    _surf: Optional[pygame.Surface] = field(default=None, repr=False, compare=False)

    def on_spawn(self) -> None:
        self.frame = 0
        self.frame_timer = 0.0
        self.pierce_hits = 0
        self.trail_cooldown = 0.0
        self._surf = None

    def on_release(self) -> None:
        self._surf = None


class ProjectilePool:
    """Pooled projectiles. 4 sprite kinds, 4-frame anim, single-batch draw.

    Per GDD §11 budget: 400 bullets update in <0.12ms.
    """

    __slots__ = ("_pool", "_frames", "_base_capacity", "_boss_expanded")

    def __init__(self, capacity: int = PROJECTILE_POOL) -> None:
        self._base_capacity: int = capacity
        self._pool: Pool[Projectile] = Pool(Projectile, capacity)
        self._boss_expanded: bool = False
        # Pre-bake the 4 frames for each of 4 kinds = 16 surfaces.
        self._frames: dict[tuple[int, int], pygame.Surface] = {}
        self._init_frames()

    @property
    def pool(self) -> Pool[Projectile]:
        return self._pool

    @property
    def active_count(self) -> int:
        return self._pool.active_count

    @property
    def capacity(self) -> int:
        return self._base_capacity if not self._boss_expanded else PROJECTILE_POOL_BOSS

    def expand_for_boss(self) -> None:
        """Called when entering BOSS_FIGHT state — pool grows to 600."""
        # We don't reallocate (Pool is fixed-size), but we mark the flag so
        # callers can ask. Per spec, the boss expansion means "we've
        # reserved +200 headroom via a separate sub-pool" — for the MVP we
        # simply flag it; future BLOQUE may split into 3 sub-pools.
        self._boss_expanded = True

    def collapse_from_boss(self) -> None:
        self._boss_expanded = False

    def spawn(
        self,
        kind: int,
        x: float,
        y: float,
        vx: float,
        vy: float,
        damage: int = 1,
        owner: int = OWNER_PLAYER,
        pierce: int = 0,
        has_trail: bool = False,
        trail_color: tuple[int, int, int] | None = None,
    ) -> Projectile | None:
        """Spawn a bullet. Returns None if pool is exhausted."""
        p = self._pool.acquire()
        if p is None:
            return None
        p.kind = kind
        p.owner = owner
        p.x = x
        p.y = y
        p.vx = vx
        p.vy = vy
        p.damage = damage
        p.pierce = pierce
        p.has_trail = has_trail
        p.trail_color = trail_color if trail_color is not None else DEFAULT_COLORS.get(kind, (255, 255, 255))
        return p

    def update(self, dt: float) -> None:
        """Advance position, animate frame, cull offscreen.

        Boss bullets skip animation (1-frame per spec).
        """
        if dt <= 0.0:
            return
        for p in self._pool:
            if not p.active:
                continue
            # Position
            p.x += p.vx * dt
            p.y += p.vy * dt
            # Animation (boss is 1-frame, skip timer)
            if p.kind != BULLET_BOSS:
                p.frame_timer += dt
                if p.frame_timer >= FRAME_DURATION_S:
                    p.frame_timer -= FRAME_DURATION_S
                    p.frame = (p.frame + 1) % NUM_FRAMES
            # Trail cooldown
            if p.has_trail:
                p.trail_cooldown -= dt
            # Offscreen cull (with margin)
            if p.x < -16 or p.x > INTERNAL_W + 16 or p.y < -16 or p.y > INTERNAL_H + 16:
                self._pool.release(p)
                continue
            # Pierce exhausted → release
            if p.pierce > 0 and p.pierce_hits >= p.pierce:
                self._pool.release(p)
                continue

    def take_damage_hits(self, p: Projectile) -> None:
        """Call when bullet connects with a target. Tracks pierce."""
        if p.pierce > 0:
            p.pierce_hits += 1

    def draw(self, target: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> int:
        """Single target.blits() batch. Returns number of blits.

        Charged bullets get a glow halo (2x scale pre-baked, drawn beneath).
        """
        ox, oy = offset
        batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for p in self._pool:
            if not p.active:
                continue
            key = (p.kind, p.frame)
            surf = self._frames.get(key)
            if surf is None:
                continue
            cx = int(p.x - surf.get_width() * 0.5) + ox
            cy = int(p.y - surf.get_height() * 0.5) + oy
            batch.append((surf, (cx, cy)))
        if batch:
            target.blits(batch)
        return len(batch)

    def release_all(self) -> None:
        self._pool.release_all()

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------
    def _init_frames(self) -> None:
        """Pre-bake 4 frames × 4 kinds = 16 surfaces in init.

        Per GDD §11: this is the only place we allocate bullet sprites.
        Animation = scale 0.9 → 1.1 at 16 FPS for player/enemy, 1-frame
        for boss (no flicker), and a glow halo for charged.
        """
        for kind in (BULLET_PLAYER, BULLET_PLAYER_CHARGED, BULLET_PLAYER_BEAM,
                     BULLET_ENEMY, BULLET_BOSS):
            w, h = BULLET_SIZES[kind]
            for frame in range(NUM_FRAMES):
                if kind == BULLET_BOSS:
                    # Boss: 1-frame anim — always same surface.
                    if frame == 0:
                        surf = self._make_bullet_sprite(kind, w, h, 1.0, (220, 120, 255))
                        self._frames[(kind, frame)] = surf
                    else:
                        # Alias all frames to the same boss surface.
                        self._frames[(kind, frame)] = self._frames[(kind, 0)]
                    continue
                # 4-frame pulse: scale 0.9 → 1.1 → 0.95 → 1.05
                scale_table = [0.9, 1.1, 0.95, 1.05]
                scale = scale_table[frame]
                color = DEFAULT_COLORS[kind]
                surf = self._make_bullet_sprite(kind, w, h, scale, color)
                self._frames[(kind, frame)] = surf

    def _make_bullet_sprite(
        self, kind: int, w: int, h: int, scale: float, color: tuple[int, int, int]
    ) -> pygame.Surface:
        """BLOQUE 58.38: create a bullet sprite with kind-specific shape.

        Each kind has a distinctive silhouette so the player can read what's
        coming at them at a glance:
          - BULLET_PLAYER         : gold diamond (pointed top + bottom)
          - BULLET_PLAYER_CHARGED : bigger blue-white diamond with glow halo
          - BULLET_PLAYER_BEAM    : vertical cyan plasma beam (cross-shape)
          - BULLET_ENEMY          : small red orb with halo
          - BULLET_BOSS           : 4-point purple star with halo
        """
        # Compute scaled size (round up so glow halo doesn't truncate)
        sw = max(1, int(math.ceil(w * scale)))
        sh = max(1, int(h * scale))
        # Charged bullets get a +6px halo on each side.
        # BLOQUE 36: beam halo dialed back (14→7) and softer alpha so the L3 shot
        # reads as plasma, not a giant white rectangle.
        if kind == BULLET_PLAYER_BEAM:
            halo = 7
        elif kind == BULLET_PLAYER_CHARGED:
            halo = 6
        elif kind == BULLET_BOSS:
            halo = 4
        else:
            halo = 0
        canvas_w = sw + halo * 2
        canvas_h = sh + halo * 2
        surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
        cx, cy = canvas_w // 2, canvas_h // 2
        # ------------------------------------------------------------------
        # Halo (soft alpha falloff) — same logic for all kinds
        # ------------------------------------------------------------------
        if halo > 0:
            for r in range(halo, 0, -1):
                a = int(42 * (r / halo)) if kind == BULLET_PLAYER_BEAM else int(40 * (r / halo))
                pygame.draw.circle(
                    surf,
                    (color[0], color[1], color[2], a),
                    (cx, cy),
                    max(sw, sh) // 2 + r,
                )
        # ------------------------------------------------------------------
        # Body: kind-specific shape
        # ------------------------------------------------------------------
        if kind == BULLET_PLAYER:
            # Gold diamond (pointed top + bottom, wider middle)
            half_w = max(1, sw // 2)
            half_h = max(1, sh // 2)
            diamond = [
                (cx, cy - half_h),         # top point
                (cx + half_w, cy),         # right point
                (cx, cy + half_h),         # bottom point
                (cx - half_w, cy),         # left point
            ]
            pygame.draw.polygon(surf, color, diamond)
            # White core highlight (smaller diamond)
            hl_half_w = max(1, half_w // 2)
            hl_half_h = max(1, half_h // 2)
            highlight = [
                (cx, cy - hl_half_h),
                (cx + hl_half_w, cy),
                (cx, cy + hl_half_h),
                (cx - hl_half_w, cy),
            ]
            pygame.draw.polygon(surf, (255, 255, 255), highlight)
        elif kind == BULLET_PLAYER_CHARGED:
            # Bigger blue-white diamond (sharp + piercing)
            half_w = max(2, sw // 2)
            half_h = max(2, sh // 2)
            diamond = [
                (cx, cy - half_h),
                (cx + half_w, cy),
                (cx, cy + half_h),
                (cx - half_w, cy),
            ]
            # Darker outer ring (the "armor" of the charged shot)
            outer = [
                (cx, cy - half_h - 1),
                (cx + half_w + 1, cy),
                (cx, cy + half_h + 1),
                (cx - half_w - 1, cy),
            ]
            pygame.draw.polygon(surf, (180, 210, 255), outer)
            pygame.draw.polygon(surf, color, diamond)
            # Bright white core
            hl_half_w = max(1, half_w // 2)
            hl_half_h = max(1, half_h // 2)
            core = [
                (cx, cy - hl_half_h),
                (cx + hl_half_w, cy),
                (cx, cy + hl_half_h),
                (cx - hl_half_w, cy),
            ]
            pygame.draw.polygon(surf, (255, 255, 255), core)
        elif kind == BULLET_PLAYER_BEAM:
            # Vertical plasma beam: cross-shape (tall + thin) with cyan glow
            beam_w = max(2, sw // 3)
            beam_h = sh
            # Outer cyan shell (wider)
            shell_w = beam_w + 2
            pygame.draw.rect(
                surf, (90, 180, 255),
                (cx - shell_w // 2, cy - beam_h // 2, shell_w, beam_h),
            )
            # Inner beam
            pygame.draw.rect(
                surf, color,
                (cx - beam_w // 2, cy - beam_h // 2, beam_w, beam_h),
            )
            # White-hot center
            core_w = max(1, beam_w // 2)
            pygame.draw.rect(
                surf, (255, 255, 255),
                (cx - core_w // 2, cy - beam_h // 2, core_w, beam_h),
            )
            # Horizontal cross-guard (gives it a "+" silhouette)
            guard_w = max(4, sw)
            guard_h = max(1, beam_h // 4)
            pygame.draw.rect(
                surf, (140, 220, 255),
                (cx - guard_w // 2, cy - guard_h // 2, guard_w, guard_h),
            )
        elif kind == BULLET_ENEMY:
            # Small red orb (downward-pointing teardrop)
            orb_r = max(1, min(sw, sh) // 2)
            pygame.draw.circle(surf, color, (cx, cy), orb_r)
            # Darker red core (the "hot center")
            core_r = max(1, orb_r - 1)
            pygame.draw.circle(surf, (180, 30, 30), (cx, cy), core_r)
            # Bright pink-white center dot
            pygame.draw.circle(surf, (255, 200, 200), (cx, cy), max(1, orb_r // 2))
        elif kind == BULLET_BOSS:
            # 4-point purple star (sharp + menacing)
            star_outer = max(sw, sh) // 2
            star_inner = max(1, star_outer // 2)
            star = [
                (cx, cy - star_outer),                              # top
                (cx + star_inner, cy - star_inner),                 # top-right
                (cx + star_outer, cy),                              # right
                (cx + star_inner, cy + star_inner),                 # bottom-right
                (cx, cy + star_outer),                              # bottom
                (cx - star_inner, cy + star_inner),                 # bottom-left
                (cx - star_outer, cy),                              # left
                (cx - star_inner, cy - star_inner),                 # top-left
            ]
            pygame.draw.polygon(surf, (100, 50, 160), star)  # dark outer
            # Inner bright purple
            inner_outer = max(1, star_outer - 1)
            inner_inner = max(1, star_inner - 1)
            star2 = [
                (cx, cy - inner_outer),
                (cx + inner_inner, cy - inner_inner),
                (cx + inner_outer, cy),
                (cx + inner_inner, cy + inner_inner),
                (cx, cy + inner_outer),
                (cx - inner_inner, cy + inner_inner),
                (cx - inner_outer, cy),
                (cx - inner_inner, cy - inner_inner),
            ]
            pygame.draw.polygon(surf, color, star2)
            # White hot center
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 1)
        else:
            # Fallback (shouldn't happen): just a rect
            rect = pygame.Rect(0, 0, sw, sh)
            rect.center = (cx, cy)
            pygame.draw.rect(surf, color, rect)
        return surf
