"""BLOQUE 58.11 + 58.22: Tron-style light trail for the player PROPULSION.

When the player enters PROPULSION state, the ship leaves a continuous
glowing wall behind it (think Tron lightcycle / drift_loud reference).

BLOQUE 58.22 visual rebuild:
  The previous implementation used pygame.draw.line for each of 3 layers
  (edge halo + body + core). pygame.draw.line produces hard edges, so even
  with 2px overlap between consecutive segments, the trail looked like
  a string of dashes, not a continuous beam. That didn't match the
  reference the user wanted.

  The new approach: pre-render SRCALPHA sprites with SOFT alpha
  gradients at init time (halo / body / core), then BLIT each sprite
  rotated to the segment angle. Because each sprite has soft edges,
  adjacent sprites blend visually into a continuous glowing ribbon.
  This is the standard 2D technique for "neon light beam" effects
  (also used by the reference image, which has zero hard edges).

Geometry: segments are now 18 px long (was 8), so at 330 px/s
propulsion speed with 55Hz spawn (every 18ms = 5.94px per spawn)
consecutive sprites overlap by 12 px. The soft edges blend over that
overlap, giving a seamless beam look.

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
        segment_length: float = 28.0,   # BLOQUE 58.22: was 8.0. 28px gives
                                         # ~24px overlap at 330 px/s, so the
                                         # soft-edged sprites blend seamlessly
                                         # with no visible segment boundaries.
        segment_thickness: float = 4.0,  # was 3.0; slightly wider for the wall
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
        # BLOQUE 58.22: pre-rendered alpha sprites for the beam look.
        # The sprite is drawn ONCE at init with a soft alpha gradient
        # (gaussian-like falloff from the centerline to the edges).
        # At draw time we blit the sprite rotated to the segment angle,
        # so the soft edges blend between adjacent segments -> continuous
        # ribbon. This is the standard 2D technique for "neon beam" and
        # what the user wants (see drift_loud reference).
        self._halo_sprite, self._body_sprite, self._core_sprite = self._build_sprites()

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
    # BLOQUE 58.22: pre-rendered soft-alpha sprites
    # -----------------------------------------------------------------
    def _build_sprites(self) -> tuple[pygame.Surface, pygame.Surface, pygame.Surface]:
        """Build three SRCALPHA sprites used to render each segment.

        Each sprite is a horizontal "puffy bar" of length = segment_length
        with a vertical alpha gradient that falls off softly at top/bottom.
        The alpha is also tapered at the long ends so adjacent sprites
        blend smoothly when chained.

        Sizes (relative to segment_thickness=4):
          - halo:  thickness * 4 + 4 = 20px tall (large soft glow)
          - body:  thickness * 2 + 2 = 10px tall (visible main body)
          - core:  thickness * 1     =  4px tall (bright center)

        The vertical falloff uses (1 - t^2)^0.7 which gives a relatively
        flat center with smooth edges — closer to the "neon beam" look
        of the drift_loud reference than the previous steeper curve.

        Returns:
            (halo_sprite, body_sprite, core_sprite) — all pygame.Surface
            with per-pixel alpha (SRCALPHA), centered on (length/2, h/2).
        """
        L = int(self.segment_length)  # length along the trail
        # Halo is 4x the body thickness for a strong outer glow
        H_halo = int(self.segment_thickness * 4.0) + 4
        H_body = int(self.segment_thickness * 2.0) + 2
        H_core = max(3, int(self.segment_thickness))

        def _render(thickness_h: int, base_color: tuple[int, int, int],
                    max_alpha: int, end_taper: float,
                    v_curve: float = 0.7) -> pygame.Surface:
            """Render a single soft-edge sprite.

            Args:
                thickness_h:  vertical extent (perpendicular to length).
                base_color:   RGB of the beam.
                max_alpha:    peak alpha at the very center.
                end_taper:    how aggressively the alpha falls off at the
                              two long ends (0 = no taper, 1 = strong taper).
                v_curve:      exponent on the vertical (1 - t^2) curve.
                              Lower = flatter center, more "tube" look.
                              Higher = more concentrated center.
            """
            W = L
            H = thickness_h
            surf = pygame.Surface((W, H), pygame.SRCALPHA)
            cx = W * 0.5
            cy = H * 0.5
            # Half-thicknesses (the gradient falloff radii)
            half_h = H * 0.5
            # We loop per pixel — small surfaces (~20x20), cheap.
            for y in range(H):
                dy = y - cy
                # Vertical alpha: soft falloff from center to edge.
                # (1 - t^2)^v_curve. Lower v_curve -> flatter center.
                if half_h > 0:
                    t_v = abs(dy) / half_h
                    if t_v > 1.0:
                        continue  # outside the bar
                    v_alpha = (1.0 - t_v * t_v) ** v_curve
                else:
                    v_alpha = 1.0
                for x in range(W):
                    dx = x - cx
                    # Horizontal alpha: long-edge taper. We taper only
                    # the very ends, so the body is uniform in the middle
                    # and softly fades at the two long edges.
                    t_h = abs(dx) / (W * 0.5)  # 0=center, 1=end
                    if t_h > 1.0:
                        continue
                    h_alpha = (1.0 - t_h) ** end_taper if end_taper > 0 else 1.0
                    a = max_alpha * v_alpha * h_alpha
                    if a < 1.0:
                        continue
                    a_int = min(255, int(a))
                    surf.set_at((x, y), (base_color[0], base_color[1], base_color[2], a_int))
            return surf

        # Halo: wide, low-alpha, very gentle end taper
        # (end_taper < 1 makes the alpha decay as a curve CONCAVE-UP,
        # so the middle is nearly uniform and only the last ~10% of
        # each end fades out. Adjacent sprites blend seamlessly.)
        halo = _render(H_halo, self.color_edge, 160, end_taper=0.4, v_curve=0.5)
        # Body: medium width, high alpha, almost no end taper
        body = _render(H_body, self.color_mid, 240, end_taper=0.2, v_curve=0.6)
        # Core: thin, full alpha, essentially no end taper
        core = _render(H_core, self.color_core, 255, end_taper=0.15, v_curve=0.7)
        return halo, body, core

    # -----------------------------------------------------------------
    # End BLOQUE 58.22 sprite builder
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

        BLOQUE 58.22: each segment is rendered by blitting the
        pre-rendered soft-alpha sprite (halo + body + core) rotated
        to the segment angle. Because the sprites have soft edges,
        adjacent sprites blend into a continuous glowing beam
        (Tron Legacy / drift_loud style) — the hard-edge "dashes"
        look from the previous pygame.draw.line approach is gone.

        The newest segment is rendered LAST with a brighter boost
        (the "head" of the trail — looks like the bike is pulling
        a fresh light source).

        Older segments are faded via an alpha multiplier based on
        remaining life. The first 50ms has a fade-in so segments
        don't pop in.
        """
        if not self.segments:
            return
        ox, oy = offset
        # Index of the newest segment (= head of the trail)
        head_idx = len(self.segments) - 1
        for idx, seg in enumerate(self.segments):
            life_frac = max(0.0, 1.0 - seg.age / seg.max_age)
            # Fade-in over the first 50ms so the trail doesn't pop
            fade_in = min(1.0, seg.age / 0.05) if seg.age < 0.05 else 1.0
            base_alpha = life_frac * fade_in
            if base_alpha <= 0.0:
                continue
            is_head = (idx == head_idx)
            # Boost the head a bit (looks like a fresh light source)
            head_boost = 1.25 if is_head else 1.0
            # We rotate the sprite so it points along the segment angle.
            # The sprite is drawn horizontally (length along +x, thickness
            # along +y). pygame.transform.rotate rotates CCW by degrees;
            # our angle is the screen-coord angle (0=right, pi/2=down).
            # pygame's y axis is also down, so a positive angle rotates
            # the sprite from "pointing right" to "pointing down" —
            # which is exactly what we want.
            angle_deg = -math.degrees(seg.angle)  # pygame rotates opposite
            try:
                halo_rot = pygame.transform.rotate(self._halo_sprite, angle_deg)
                body_rot = pygame.transform.rotate(self._body_sprite, angle_deg)
                core_rot = pygame.transform.rotate(self._core_sprite, angle_deg)
            except Exception:
                # Fallback: just blit unrotated (will look wrong but won't crash)
                halo_rot = self._halo_sprite
                body_rot = self._body_sprite
                core_rot = self._core_sprite
            # Compute the top-left position so the rotated sprite is
            # centered on (seg.cx + ox, seg.cy + oy).
            cx = int(seg.cx) + ox
            cy = int(seg.cy) + oy

            def _blit_faded(surf: pygame.Surface, alpha_mult: float) -> None:
                """Blit surf centered on (cx,cy) with an extra alpha
                multiplier (used for age fade)."""
                a = base_alpha * alpha_mult * head_boost
                if a >= 0.999:
                    target.blit(surf, surf.get_rect(center=(cx, cy)))
                else:
                    # Apply per-blit alpha. We scale the sprite's alpha
                    # channel by `a` (clamped) and blit.
                    scaled = surf.copy()
                    try:
                        scaled.set_alpha(int(min(255, max(0, a * 255))))
                    except Exception:
                        pass
                    target.blit(scaled, scaled.get_rect(center=(cx, cy)))

            # 3 layers: halo (widest, dimmest) -> body -> core (brightest)
            _blit_faded(halo_rot, 1.0)
            _blit_faded(body_rot, 1.0)
            _blit_faded(core_rot, 1.0)

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
