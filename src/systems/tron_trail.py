"""BLOQUE 58.11 + 58.22 + 58.24: Tron-style light trail for the player PROPULSION.

When the player enters PROPULSION state, the ship leaves a continuous
glowing wall behind it (think Tron lightcycle / drift_loud reference).

BLOQUE 58.24 visual rebuild:
  The previous implementation (BLOQUE 58.22) pre-rendered rectangular
  SRCALPHA sprites (halo / body / core) and blitted each one rotated
  to the segment angle. With segments 28px long and 10-20px thick,
  the rotated rectangles produced VISIBLE "rungs" when stacked along
  a curve — the trail looked like a ladder, not a continuous beam.
  The user reported: "se ve super raro y no continuo".

  The new approach: draw the trail as a CONTINUOUS POLYLINE through
  all segment centers using pygame.draw.line. Each pair of consecutive
  segment centers is connected by a line, and we draw the polyline
  4 times with increasing width + decreasing alpha to get the
  neon glow effect:
      Pass 1 (GLOW):    width=11, alpha=40   - wide soft outer glow
      Pass 2 (HALO):    width=7,  alpha=80   - medium cyan halo
      Pass 3 (BODY):    width=4,  alpha=180  - bright cyan body
      Pass 4 (CORE):    width=2,  alpha=255  - white-cyan bright core

  This is the standard 2D technique for "neon line" effects and
  matches the drift_loud reference: a thin bright core wrapped in
  a soft cyan halo, with the whole thing tracing the ship's path
  as a single smooth line (no visible segment boundaries).

  Per-point alpha is modulated by the segment's remaining life, so
  the trail fades smoothly from head (bright) to tail (transparent).
  The head gets a small brightness boost (1.25x) to feel like a
  fresh light source being pulled by the ship.

BLOQUE 58.22 history (now superseded):
  Pre-rendered rotated sprites with soft edges. The soft edges
  blended between adjacent segments, but the rectangle shape
  produced visible "rungs" along curves.

BLOQUE 58.11 history (now superseded):
  pygame.draw.line for 3 layers (edge + body + core). Produced
  hard edges and looked like dashes.

The segment is a dataclass with:

  - cx, cy:        center position
  - angle:         direction along the segment (radians, 0=right)
  - length:        length of the segment (px)
  - thickness:     thickness perpendicular to angle (px)
  - age:           seconds since spawn
  - max_age:       seconds until removal
  - hit_cooldown:  per-enemy damage cooldown dict (key: id(enemy), val: time)

Rules (per the user's BLOQUE 58.11 decisions):
  - Trail ONLY during PROPULSION (no wake when ship is idle or dashing).
  - Color: pure neon cyan (Tron Legacy style).
  - Geometry: chain of rectangle segments (8-bit friendly).
  - Fade: slow (~2.5s) with a length cap (max_segments).
  - Collision: enemies that touch the trail take 3x bullet damage
    (TRON_TRAIL_DAMAGE_MULT = 3.0). One hit per enemy per hit_cooldown_s
    window so the enemy doesn't get melted in a single frame.

The trail is rendered with soft cyan sprites (bright core + soft halo)
for the "neon beam" feel, then drawn BEFORE the player so the ship
sits on top of the wall.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pygame  # BLOQUE 58.20: runtime import. The draw() method uses
             # pygame.draw.line, pygame.Surface, pygame.SRCALPHA, and
             # pygame.transform.rotate, all of which are needed at
             # runtime. Under TYPE_CHECKING-only imports the trail
             # would crash with NameError on the first draw and the
             # error handler would spam crash.log at 60Hz, blocking
             # the game loop.


@dataclass
class TronSegment:
    """One wall segment of the Tron trail.

    The segment is a thick line from (cx,cy) along the `angle` direction
    with the given `length` and `thickness`. Chains of these segments
    form the trail.
    """
    cx: float
    cy: float
    angle: float  # direction along the segment (radians, 0=right, pi/2=down)
    length: float
    thickness: float
    age: float = 0.0
    max_age: float = 2.5
    # Per-enemy hit cooldown. Key: id(enemy), val: time when last hit.
    # We don't store this here; the engine keeps a single dict and uses
    # segment ages to determine "active for collision".


class TronTrail:
    """BLOQUE 58.11: the player's Tron lightcycle trail.

    The trail is a list of TronSegments chained end-to-end. New segments
    are spawned at the back of the ship while the player is in
    PROPULSION. The trail updates each frame (age += dt, removes dead
    segments) and renders to a target surface.
    """

    def __init__(
        self,
        max_segments: int = 240,
        segment_length: float = 6.0,    # BLOQUE 58.24: was 28.0. The
                                         # polyline renderer (58.24) doesn't
                                         # care about segment_length for
                                         # visuals — segments are just
                                         # polyline vertices. We keep a
                                         # small value so the polyline is
                                         # dense enough for smooth curves.
        segment_thickness: float = 4.0,
        max_age: float = 2.5,
        spawn_interval_s: float = 0.018,  # ~55 Hz — high density for smooth ribbon
    ) -> None:
        # The cyan color palette (Tron Legacy neon)
        self.color_core: tuple[int, int, int] = (210, 255, 255)
        self.color_mid: tuple[int, int, int] = (0, 230, 255)
        self.color_edge: tuple[int, int, int] = (0, 160, 220)
        # Segment parameters
        self.max_segments = max_segments
        self.segment_length = segment_length
        self.segment_thickness = segment_thickness
        self.max_age = max_age
        self.spawn_interval_s = spawn_interval_s
        # The actual segment list (oldest first, newest at the end)
        self.segments: list[TronSegment] = []
        # Spawn timer (counts up to spawn_interval_s)
        self._spawn_timer: float = 0.0
        # Per-enemy hit cooldown: id(enemy) -> time when last hit
        # Enemies re-hit only after hit_cooldown_s has elapsed.
        self.hit_cooldown: dict[int, float] = {}
        self.hit_cooldown_s: float = 0.15  # ~7 Hz max hit rate per enemy
        # BLOQUE 58.11 perf: bounding box of the trail. Recomputed
        # when segments are added/removed. Used to early-exit the
        # collision check for enemies far from the trail (avoids
        # 64 * 240 = 15k distance calcs per frame when only a few
        # enemies are near the trail).
        self.bbox_min_x: float = 0.0
        self.bbox_min_y: float = 0.0
        self.bbox_max_x: float = 0.0
        self.bbox_max_y: float = 0.0
        self.bbox_dirty: bool = True

    def reset(self) -> None:
        """Clear the entire trail (e.g. on player death or state change)."""
        self.segments.clear()
        self._spawn_timer = 0.0
        self.hit_cooldown.clear()
        # Reset bbox to "no trail" state
        self.bbox_min_x = self.bbox_min_y = 0.0
        self.bbox_max_x = self.bbox_max_y = 0.0
        self.bbox_dirty = True

    # -----------------------------------------------------------------
    # (BLOQUE 58.22 sprite builder removed in 58.24 — the polyline
    # renderer doesn't need pre-rendered sprites.)
    # -----------------------------------------------------------------

    def is_active(self) -> bool:
        """True if the trail currently has any visible segments."""
        return len(self.segments) > 0

    def update(self, dt: float) -> None:
        """Age all segments, remove dead ones, expire hit cooldowns."""
        # Enforce max length cap (always — even if dt == 0, a burst-spawn
        # of 240 segments in one frame must be trimmed to max_segments
        # before the next frame renders).
        if len(self.segments) > self.max_segments:
            self.segments = self.segments[-self.max_segments:]
            self.bbox_dirty = True
        if dt <= 0.0:
            return
        # Age segments
        for seg in self.segments:
            seg.age += dt
        # Remove dead segments (in-place, oldest first)
        before_count = len(self.segments)
        self.segments = [s for s in self.segments if s.age < s.max_age]
        if len(self.segments) != before_count:
            self.bbox_dirty = True
        # Expire hit cooldowns
        expired = [k for k, t in self.hit_cooldown.items() if t <= 0.0]
        for k in expired:
            del self.hit_cooldown[k]
        # Decrement remaining cooldowns
        for k in list(self.hit_cooldown.keys()):
            self.hit_cooldown[k] -= dt

    def _recompute_bbox(self) -> None:
        """Recompute the trail's bounding box from active segments.

        BLOQUE 58.11 perf: this is O(n) over segments but called at
        most once per frame (when bbox_dirty is set). The bbox is
        used by check_enemy_collision to skip enemies far from the
        trail, which is the difference between 64 * 240 = 15k
        distance calcs/frame and 64 * 5 = 320 calcs/frame in
        typical play (most enemies are off-screen or far from
        the trail).
        """
        if not self.segments:
            self.bbox_min_x = self.bbox_min_y = 0.0
            self.bbox_max_x = self.bbox_max_y = 0.0
            self.bbox_dirty = False
            return
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        half_len = self.segment_length * 0.5
        for seg in self.segments:
            cos_a = math.cos(seg.angle)
            sin_a = math.sin(seg.angle)
            dx = cos_a * half_len
            dy = sin_a * half_len
            # The two endpoints of the segment
            x1 = seg.cx - dx
            y1 = seg.cy - dy
            x2 = seg.cx + dx
            y2 = seg.cy + dy
            if x1 < min_x: min_x = x1
            if y1 < min_y: min_y = y1
            if x2 > max_x: max_x = x2
            if y2 > max_y: max_y = y2
        # Add a margin equal to the segment thickness so the bbox
        # covers the visual area + collision radius.
        margin = self.segment_thickness
        self.bbox_min_x = min_x - margin
        self.bbox_min_y = min_y - margin
        self.bbox_max_x = max_x + margin
        self.bbox_max_y = max_y + margin
        self.bbox_dirty = False

    def spawn_if_ready(
        self,
        ship_x: float,
        ship_y: float,
        ship_angle_rad: float,
        ship_back_offset: float,
        dt: float,
    ) -> bool:
        """Spawn a new trail segment at the back of the ship.

        Args:
            ship_x, ship_y:        ship center.
            ship_angle_rad:        direction the ship is facing (radians,
                                   0=right, pi/2=down). The trail segment
                                   will be aligned with this direction.
            ship_back_offset:      distance behind the ship center to
                                   spawn the segment (in world units).
            dt:                    delta time for the spawn timer.

        Returns:
            True if a segment was spawned this call.
        """
        self._spawn_timer += dt
        if self._spawn_timer < self.spawn_interval_s:
            return False
        self._spawn_timer = 0.0
        # Spawn position: back of the ship along the ship angle.
        # The ship angle is 0=right, pi/2=down (screen coords).
        # "Behind" is the opposite direction: -angle.
        cos_a = math.cos(ship_angle_rad)
        sin_a = math.sin(ship_angle_rad)
        seg_cx = ship_x - cos_a * ship_back_offset
        seg_cy = ship_y - sin_a * ship_back_offset
        seg = TronSegment(
            cx=seg_cx,
            cy=seg_cy,
            angle=ship_angle_rad,
            length=self.segment_length,
            thickness=self.segment_thickness,
            age=0.0,
            max_age=self.max_age,
        )
        self.segments.append(seg)
        self.bbox_dirty = True  # new segment — bbox needs updating
        return True

    def draw(
        self,
        target: pygame.Surface,
        offset: tuple[int, int] = (0, 0),
    ) -> None:
        """Render the trail to the target surface.

        BLOQUE 58.24: draw the trail as a CONTINUOUS POLYLINE through
        all segment centers, not as discrete rotated sprites. The
        rotated-sprite approach (BLOQUE 58.22) produced visible "rungs"
        because each sprite is a thick rectangle, so when stacked
        along a curve the result looks like a ladder. The polyline
        approach uses pygame.draw.line to connect consecutive segment
        centers, giving a single smooth beam that follows the
        ship's exact path.

        To get the "neon" look we draw the polyline in 4 passes with
        increasing width + decreasing alpha:
          Pass 1 (GLOW):    width=11, alpha=40   - wide soft outer glow
          Pass 2 (HALO):    width=7,  alpha=80   - medium cyan halo
          Pass 3 (BODY):    width=4,  alpha=180  - bright cyan body
          Pass 4 (CORE):    width=2,  alpha=255  - white-cyan bright core

        Each pass's alpha is modulated by the segment's remaining
        life, so the trail fades smoothly from the head (bright) to
        the tail (transparent). The head gets a small brightness boost
        (1.25x) to feel like a fresh light source being pulled by
        the ship.

        This is the same rendering style as the drift_loud reference:
        a thin bright core wrapped in a soft cyan halo, with the
        whole thing tracing the ship's path.
        """
        if len(self.segments) < 1:
            return
        ox, oy = offset
        # Pre-compute screen-space points and per-point life (faded alpha)
        n = len(self.segments)
        pts: list[tuple[int, int, float]] = []  # (x, y, life_frac)
        for s in self.segments:
            life = max(0.0, 1.0 - s.age / s.max_age)
            # Quick fade-in over the first 50ms so newly-spawned segments
            # don't pop in
            fade_in = min(1.0, s.age / 0.05) if s.age < 0.05 else 1.0
            alpha_factor = life * fade_in
            if alpha_factor <= 0.001:
                continue
            pts.append((int(s.cx) + ox, int(s.cy) + oy, alpha_factor))
        if not pts:
            return
        # Multi-pass draw: each pass is a "shell" of the neon beam.
        # (width, base_alpha, color, blend_with_fade)
        passes = [
            (11,  40, self.color_edge, 0.35),  # outer wide soft glow
            (7,   80, self.color_edge, 0.55),  # mid cyan halo
            (4,  180, self.color_mid,  0.85),  # bright cyan body
            (2,  255, self.color_core, 1.00),  # white-cyan core
        ]
        # The newest segment is the head: boost its alpha
        head_x, head_y, head_life = pts[-1]
        for width, base_alpha, color, fade_strength in passes:
            for i in range(len(pts) - 1):
                x1, y1, a1 = pts[i]
                x2, y2, a2 = pts[i + 1]
                # Average life of the two endpoints; multiplied by the
                # pass-specific fade strength. This gives the trail a
                # gradient from head to tail.
                avg_life = (a1 + a2) * 0.5
                # The pass's own fade factor controls how strongly this
                # pass is affected by the trail's life gradient.
                effective = avg_life * fade_strength
                alpha = int(min(255.0, base_alpha * effective))
                if alpha < 2:
                    continue
                # Try drawing with alpha. pygame.draw.line accepts an
                # RGBA color tuple on SRCALPHA targets.
                try:
                    pygame.draw.line(
                        target,
                        (color[0], color[1], color[2], alpha),
                        (x1, y1), (x2, y2),
                        width,
                    )
                except TypeError:
                    # Some pygame versions don't accept RGBA on draw.line.
                    # Fall back to plain RGB.
                    pygame.draw.line(
                        target,
                        color,
                        (x1, y1), (x2, y2),
                        width,
                    )
        # Head boost: draw a small bright circle at the very tip of
        # the trail (the newest segment position). This is the
        # "light source" feel — like the bike is pulling a fresh
        # bit of light.
        head_alpha = int(min(255.0, 255.0 * head_life * 1.0))
        if head_alpha > 10:
            try:
                pygame.draw.circle(
                    target,
                    (self.color_core[0], self.color_core[1], self.color_core[2], head_alpha),
                    (head_x, head_y),
                    3,
                )
            except TypeError:
                pygame.draw.circle(target, self.color_core, (head_x, head_y), 3)

    def check_enemy_collision(
        self,
        enemy: Any,
        current_time: float,
        damage: int,
    ) -> bool:
        """If the enemy's hitbox overlaps any active trail segment, deal
        `damage` to the enemy. Returns True if the enemy was hit this call.

        The enemy takes damage at most once per hit_cooldown_s window
        so it can't be melted in a single frame.

        BLOQUE 58.11 perf: uses a bounding box to early-exit enemies
        that are far from the trail. This avoids iterating 240
        segments per frame for each of 64 enemies when most enemies
        are nowhere near the trail.

        BLOQUE 58.18 fix: the enemy size is read from hitbox() (which
        uses ENEMY_CONFIGS[enemy.kind].width/.height * 0.7). The
        previous code used enemy.w / enemy.h, which don't exist on
        the Enemy dataclass — that AttributeError fired every frame
        and caused the "screen freeze" the user reported.

        Args:
            enemy:        an Enemy instance.
            current_time: game time (seconds). Used for hit cooldown bookkeeping.
            damage:       damage to apply on hit (typically 3x bullet damage).

        Returns:
            True if the enemy was hit.
        """
        if not self.segments:
            return False
        e_id = id(enemy)
        # Skip if still on cooldown
        if self.hit_cooldown.get(e_id, 0.0) > 0.0:
            return False
        # Get the enemy's hitbox rect — this returns the actual width
        # and height (with the 70% forgiveness scaling per GDD §5).
        rect = enemy.hitbox()
        enemy_w = rect.width
        enemy_h = rect.height
        # BLOQUE 58.11 perf: early-exit if the enemy is way outside
        # the trail's bounding box. We add the enemy's half-extent
        # to the bbox so the enemy only needs to be NEAR the bbox
        # (not inside it) for the detailed segment check.
        if self.bbox_dirty:
            self._recompute_bbox()
        enemy_half = max(enemy_w, enemy_h) * 0.5
        ex, ey = float(enemy.x), float(enemy.y)
        if (ex + enemy_half < self.bbox_min_x
                or ex - enemy_half > self.bbox_max_x
                or ey + enemy_half < self.bbox_min_y
                or ey - enemy_half > self.bbox_max_y):
            return False
        # Detailed check: iterate segments and find the closest one
        for seg in self.segments:
            cos_a = math.cos(seg.angle)
            sin_a = math.sin(seg.angle)
            dx = cos_a * seg.length * 0.5
            dy = sin_a * seg.length * 0.5
            x1 = seg.cx - dx
            y1 = seg.cy - dy
            x2 = seg.cx + dx
            y2 = seg.cy + dy
            # Distance from enemy center to the line segment
            d = _point_to_segment_distance(ex, ey, x1, y1, x2, y2)
            # The trail thickness is added to the enemy half-extent
            hit_dist = seg.thickness * 0.5 + max(enemy_w, enemy_h) * 0.4
            if d <= hit_dist:
                # HIT — apply damage
                enemy.apply_damage(damage)
                self.hit_cooldown[e_id] = self.hit_cooldown_s
                return True
        return False


def _point_to_segment_distance(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    """Distance from point (px,py) to the line segment (x1,y1)-(x2,y2)."""
    seg_dx = x2 - x1
    seg_dy = y2 - y1
    seg_len_sq = seg_dx * seg_dx + seg_dy * seg_dy
    if seg_len_sq <= 0.0:
        # Degenerate segment (zero length) — fall back to point distance
        return math.hypot(px - x1, py - y1)
    # Project the point onto the segment
    t = ((px - x1) * seg_dx + (py - y1) * seg_dy) / seg_len_sq
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    closest_x = x1 + t * seg_dx
    closest_y = y1 + t * seg_dy
    return math.hypot(px - closest_x, py - closest_y)
