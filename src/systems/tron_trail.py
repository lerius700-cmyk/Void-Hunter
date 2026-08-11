"""BLOQUE 58.11 + 58.22 + 58.24 + 58.25 + 58.27 + 58.28 + 58.29 + 58.30: Tron-style light trail for the player PROPULSION.

When the player enters PROPULSION state, the ship leaves a continuous
glowing wall behind it (think Tron lightcycle / drift_loud reference).

BLOQUE 58.30: blue-white neon tube.
  The user wanted the trail to look like the yellow line in their
  reference screenshot — a thin neon line where:
    - The OUTER EDGES of the line are ROYAL BLUE
    - The CENTER of the line is WHITE-HOT
    - Smooth gradient from blue (edges) to white (center)
  This is the classic "neon tube / plasma beam" look — like a glass
  tube with white-hot plasma inside and a blue glass shell. The
  per-layer colors are:
    GLOW (outermost): royal blue (65, 105, 225)
    HALO:             blue-white
    BODY:             light cyan-white
    CORE (innermost): pure white
  Plus a "head bloom" of bright white at the very tip.

BLOQUE 58.29 history: thin trail (matching engine fire thickness).
  BLOQUE 58.28 went too far in the opposite direction: it made the
  trail a THICK puff (core=4, body=8, halo=16, glow=24) thinking the
  user wanted a thick beam. The user actually wanted a THIN line
  matching the engine fire plume (which is a narrow column, not a
  wide puff). Reverted to thin:
    - CORE:  2 px
    - BODY:  3 px
    - HALO:  5 px
    - GLOW:  8 px
  Plus a tight multi-streak (offsets +/- 1 and +/- 2 px) so the
  spectral feel remains but the line stays narrow.

BLOQUE 58.28 history: tried to match the engine fire by making
  the trail thicker. User said the opposite — the fire is THIN
  and the trail should match that thinness, not a thick puff.

BLOQUE 58.27: spectral multi-streak transparent trail.
  The user wanted the trail to feel like the reference images
  (long-exposure light streaks with reds, blues, whites, plus
  particles). The new approach:
    - MUCH MORE TRANSPARENT: every pass's base alpha is ~50% of
      before, so even the head is partially see-through.
    - SPECTRAL COLOR SHIFT: the line's color interpolates from
      white-cyan at the head to blue/violet at the tail. This is
      a "cooling" effect — the hot light cools to a cool color as
      it dissipates.
    - MULTI-STREAK: the trail is drawn 3 times with small
      perpendicular offsets (-2, 0, +2 px). The center streak is
      the brightest, the side streaks are dimmer. This creates a
      "ghost trail" / "spectrum" feel like the reference image.
    - STEEP TAIL FADE: alpha is multiplied by life^1.5..1.9 (was
      linear/quadratic), so the tail fades faster than the head
      and the line "dissolves" into nothing.
    - SPARKLE PARTICLES: ~8 small white dots are sprinkled along
      the trail, fading with the segment's life. Like the
      reference image's "stars" along the light streaks.

BLOQUE 58.25 history: "ethereal diffuse dissolve" — per-pass easing
  curves so the line softened before disappearing. Glow expanded
  as the line aged.

BLOQUE 58.24 history: continuous polyline through segment centers
  with 4 passes (glow/halo/body/core) and linear alpha fades.

BLOQUE 58.22 history: pre-rendered rotated SRCALPHA sprites.
  Produced visible "rungs" along curves.

BLOQUE 58.11 history: pygame.draw.line for 3 layers.

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
        # BLOQUE 58.30: blue + white palette (was cyan-only).
        # The trail is now a thin neon-tube-style beam:
        #   - Outer edges: royal blue
        #   - Center: white-hot
        # The GLOW layer uses the royal blue, the CORE uses white.
        self.color_core: tuple[int, int, int] = (255, 255, 255)  # white (innermost)
        self.color_mid:  tuple[int, int, int] = (200, 230, 255)  # light cyan-white
        self.color_edge: tuple[int, int, int] = (65, 105, 225)   # royal blue (outermost)
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

        BLOQUE 58.30: blue + white neon-tube beam.

        The user wants a thin line (BLOQUE 58.29) with a
        CROSS-SECTION gradient:
          - Outer edges of the line: ROYAL BLUE
          - Center of the line: WHITE
          - Smooth gradient blue -> white from outside in
        Like a glass tube with white-hot plasma inside and a blue
        glass shell. Each layer has a fixed color from the
        gradient (no longitudinal shift anymore):
          GLOW (outermost, widest,  dimmest): royal blue
          HALO:                                blue-white
          BODY:                                light cyan-white
          CORE (innermost, thinnest, brightest): white

        The fade with life is still steep (life^1.5..2.0) so the
        tail dissolves quickly. Multi-streak is preserved but
        tight (offsets +/- 1 and +/- 2 px) so the line stays
        narrow.
        """
        if len(self.segments) < 1:
            return
        ox, oy = offset
        # Pre-compute screen-space points and per-point life.
        pts: list[tuple[int, int, float]] = []
        for s in self.segments:
            life = max(0.0, 1.0 - s.age / s.max_age)
            fade_in = min(1.0, s.age / 0.05) if s.age < 0.05 else 1.0
            alpha_factor = life * fade_in
            if alpha_factor <= 0.001:
                continue
            pts.append((int(s.cx) + ox, int(s.cy) + oy, alpha_factor))
        if not pts:
            return

        # -----------------------------------------------------------------
        # Multi-streak: 5 thin parallel lines with small perpendicular offsets
        # -----------------------------------------------------------------
        # BLOQUE 58.29: tight offsets to keep the line NARROW.
        # BLOQUE 58.30: tighter (1 px) so the blue/white gradient
        # reads clearly through the line.
        streak_configs = [
            (-2.0, 0.25, 1.0),  # far-left ghost (very faint, royal blue)
            (-1.0, 0.5,  1.0),  # left ghost
            ( 0.0, 1.0,  1.0),  # center bright streak (white)
            (+1.0, 0.5,  1.0),  # right ghost
            (+2.0, 0.25, 1.0),  # far-right ghost (very faint, royal blue)
        ]

        def _draw_pass(
            width: int,
            base_alpha: float,
            life_curve_power: float,
            color: tuple[int, int, int],
            width_expand: float = 0.0,
        ) -> None:
            """Draw one "pass" (a layer of the neon beam) across all streaks.

            Args:
                width: base line width in px.
                base_alpha: peak alpha at life=1.
                life_curve_power: alpha is multiplied by life^power.
                color: the RGB color for THIS layer (per the blue->white
                       cross-section gradient).
                width_expand: how much the width GROWS as life decreases.
            """
            for perp_off, alpha_mult, width_mult in streak_configs:
                for i in range(len(pts) - 1):
                    x1, y1, a1 = pts[i]
                    x2, y2, a2 = pts[i + 1]
                    avg_life = (a1 + a2) * 0.5
                    life_width = 1.0 + (1.0 - avg_life) * width_expand
                    actual_width = max(1, int(width * life_width * width_mult))
                    life_factor = avg_life ** life_curve_power
                    alpha = int(min(255.0, base_alpha * life_factor * alpha_mult))
                    if alpha < 2:
                        continue
                    if perp_off != 0.0:
                        dx = x2 - x1
                        dy = y2 - y1
                        seg_len = math.hypot(dx, dy)
                        if seg_len > 0.01:
                            perp_x = -dy / seg_len
                            perp_y = dx / seg_len
                            ox1 = int(perp_x * perp_off)
                            oy1 = int(perp_y * perp_off)
                            ox2 = ox1
                            oy2 = oy1
                        else:
                            ox1 = oy1 = ox2 = oy2 = 0
                    else:
                        ox1 = oy1 = ox2 = oy2 = 0
                    try:
                        pygame.draw.line(
                            target,
                            (color[0], color[1], color[2], alpha),
                            (x1 + ox1, y1 + oy1),
                            (x2 + ox2, y2 + oy2),
                            actual_width,
                        )
                    except TypeError:
                        pygame.draw.line(
                            target,
                            color,
                            (x1 + ox1, y1 + oy1),
                            (x2 + ox2, y2 + oy2),
                            actual_width,
                        )

        # BLOQUE 58.30: cross-section blue -> white gradient.
        # GLOW is the OUTERMOST layer -> royal blue.
        # CORE is the INNERMOST layer -> pure white.
        # Each layer has a fixed color (no longitudinal shift).
        _draw_pass(width=8, base_alpha=22, life_curve_power=1.5,
                   color=self.color_edge, width_expand=1.2)   # royal blue glow
        _draw_pass(width=5, base_alpha=45, life_curve_power=1.6,
                   color=self.color_mid, width_expand=0.7)    # blue-white halo
        _draw_pass(width=3, base_alpha=110, life_curve_power=1.7,
                   color=(220, 240, 255), width_expand=0.3)    # light cyan-white body
        _draw_pass(width=2, base_alpha=180, life_curve_power=2.0,
                   color=self.color_core, width_expand=0.0)   # white core

        # -----------------------------------------------------------------
        # Head bloom: tight white burst at the very tip
        # -----------------------------------------------------------------
        # The head is the "newest" segment — where the engine is
        # currently emitting. We add a small bright white bloom so
        # the head feels like a fresh light source.
        head_x, head_y, head_life = pts[-1]
        if head_life > 0.4:
            bloom_alpha = int(min(255.0, 220.0 * (head_life - 0.4) / 0.6))
            if bloom_alpha > 5:
                try:
                    # Outer blue glow (4 px)
                    pygame.draw.circle(
                        target,
                        (self.color_edge[0], self.color_edge[1], self.color_edge[2],
                         int(bloom_alpha * 0.4)),
                        (head_x, head_y),
                        4,
                    )
                    # Bright white center (2 px)
                    pygame.draw.circle(
                        target,
                        (255, 255, 255, bloom_alpha),
                        (head_x, head_y),
                        2,
                    )
                except TypeError:
                    pygame.draw.circle(target, self.color_edge, (head_x, head_y), 4)
                    pygame.draw.circle(target, (255, 255, 255), (head_x, head_y), 2)

        # -----------------------------------------------------------------
        # Sparkle particles: tiny white stars along the trail
        # -----------------------------------------------------------------
        # BLOQUE 58.30: small white sparkles along the line (like
        # the "stars" in the reference image). They fade with the
        # segment life.
        if len(pts) > 4:
            step = max(1, len(pts) // 8)
            for i in range(2, len(pts) - 1, step):
                sx, sy, sl = pts[i]
                if sl < 0.2:
                    continue
                spark_alpha = int(min(255.0, 180.0 * sl))
                try:
                    pygame.draw.circle(
                        target,
                        (255, 255, 255, spark_alpha),
                        (sx, sy),
                        1,
                    )
                except TypeError:
                    pygame.draw.circle(target, (255, 255, 255), (sx, sy), 1)

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
