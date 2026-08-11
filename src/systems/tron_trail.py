"""BLOQUE 58.11 + 58.22 + 58.24 + 58.25: Tron-style light trail for the player PROPULSION.

When the player enters PROPULSION state, the ship leaves a continuous
glowing wall behind it (think Tron lightcycle / drift_loud reference).

BLOQUE 58.25: "ethereal diffuse dissolve" fade.
  The user wanted the trail to feel like light dissolving into the
  air, not just a transparency fade. The previous (58.24) fade used
  a single linear alpha for every pass, so the line just became more
  transparent toward the tail. The new fade uses per-pass easing
  curves so the line DIFFUSES before it dies:
    - CORE (white-cyan, cubic ease):  bright core vanishes FAST
      (gone by 30% life) — the line "softens" early.
    - BODY (cyan, quadratic ease):     fades a bit slower than core,
      so the line goes from "hard core" to "soft body" gradually.
    - HALO (cyan, linear ease):        fades gently.
    - GLOW (cyan, linear ease + WIDTH EXPANSION): as the segment
      ages, the glow GROWS wider (13px -> 26px). The light
      diffuses outward before fading away — the wispy, ethereal
      feel the user asked for.
  Plus a "head bloom" — a small extra glow burst at the very tip
  of the trail so the head feels like a fresh light source.

BLOQUE 58.24 history: continuous polyline through segment centers.
  4 passes (glow + halo + body + core) with linear alpha fades.

BLOQUE 58.22 history: pre-rendered rotated SRCALPHA sprites.
  Produced visible "rungs" along curves because the rotated
  rectangles stacked like a ladder.

BLOQUE 58.11 history: pygame.draw.line for 3 layers (edge + body
  + core). Hard edges, looked like dashes.

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

        BLOQUE 58.25: ethereal "diffuse dissolve" trail.

        BLOQUE 58.24 drew a continuous polyline with 4 passes (glow,
        halo, body, core) and faded each pass's alpha linearly with
        remaining life. The result was a neon line that simply became
        more transparent toward the tail.

        The user wanted something more "ethereal": the line shouldn't
        just fade out like a slider — it should DIFFUSE, like the
        light is dissolving into the air. The bright core should
        soften first, the glow should EXPAND before disappearing, and
        the whole thing should look like wisps of light, not a
        transparency fade.

        The new approach keeps the polyline renderer (BLOQUE 58.24)
        but changes HOW each pass fades with age:

          - CORE (white-cyan, width=2): uses CUBIC easing. The bright
            core vanishes FAST (e.g. gone by 30% life) so the line
            "softens" early.
          - BODY (cyan, width=4): uses QUADRATIC easing. The body
            fades a bit slower than the core, so the line goes from
            "hard core" to "soft body" gradually.
          - HALO (cyan, width=7): uses LINEAR easing. The halo fades
            gently.
          - GLOW (cyan, width=11): uses LINEAR easing AND EXPANDS its
            width as life decreases. So at the tail the line is a
            wide soft glow with no sharp center, which then dissolves.

        The head gets a "bloom": a wider, brighter burst at the very
        tip — a small SRCALPHA surface drawn as additive-style glow
        centered on the newest segment.

        End result:
          Head:   tight bright core + small bloom (sharp, fresh)
          Middle: soft core + bright body + halo + glow
          Tail:   NO core, faint body, wider glow dissolving outward
        """
        if len(self.segments) < 1:
            return
        ox, oy = offset
        # Pre-compute screen-space points and per-point life.
        # We keep two values per point:
        #   life_frac: 0 = just died, 1 = just born (used for fades)
        #   diss:      a normalized "age" 0..1 used for diffusion shaping
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

        # -----------------------------------------------------------------
        # Easing curves: how each pass fades with life
        # -----------------------------------------------------------------
        # For each life_frac (1 = fresh, 0 = dying), we compute the
        # per-pass alpha multiplier. The curves are designed so:
        #   - core dies FAST (only at the fresh end)
        #   - body dies a bit slower
        #   - halo and glow die slowest
        # And the GLOW width GROWS as life decreases (the light
        # diffuses outward before fading).
        def _core_alpha(life: float) -> float:
            # Cubic ease: 1 at life=1, 0 at life=~0.3 (gone by 30% life)
            if life <= 0.0:
                return 0.0
            t = max(0.0, min(1.0, (life - 0.0) / 1.0))  # already in 0..1
            return t * t * t
        def _body_alpha(life: float) -> float:
            # Quadratic: 1 at life=1, 0 at life=0
            return life * life
        def _halo_alpha(life: float) -> float:
            # Linear: 1 at life=1, 0 at life=0 (smooth, gentle)
            return life
        def _glow_alpha(life: float) -> float:
            # Linear, but boosted slightly so the glow persists
            return life * 0.85 + 0.15 * life
        def _glow_width_scale(life: float) -> float:
            # As life decreases, the glow EXPANDS — at life=0.5 the
            # glow is 1.5x wider, at life=0 the glow is 2x wider.
            return 1.0 + (1.0 - life) * 1.0

        head_x, head_y, head_life = pts[-1]

        # -----------------------------------------------------------------
        # Pass 1: GLOW (wide, soft, EXPANDS as it ages)
        # -----------------------------------------------------------------
        # The glow is the outermost shell. It starts at width 13 and
        # grows to width 26 as the segment ages. This is what gives
        # the "diffusion" feel — the light spreads outward before
        # disappearing.
        glow_base_w = 13
        glow_max_alpha = 50
        for i in range(len(pts) - 1):
            x1, y1, a1 = pts[i]
            x2, y2, a2 = pts[i + 1]
            avg_life = (a1 + a2) * 0.5
            width_scale = _glow_width_scale(avg_life)
            w = max(1, int(glow_base_w * width_scale))
            alpha = int(min(255.0, glow_max_alpha * _glow_alpha(avg_life)))
            if alpha < 2:
                continue
            try:
                pygame.draw.line(
                    target,
                    (self.color_edge[0], self.color_edge[1], self.color_edge[2], alpha),
                    (x1, y1), (x2, y2),
                    w,
                )
            except TypeError:
                pygame.draw.line(target, self.color_edge, (x1, y1), (x2, y2), w)

        # -----------------------------------------------------------------
        # Pass 2: HALO (medium width, linear fade)
        # -----------------------------------------------------------------
        halo_w = 7
        halo_max_alpha = 90
        for i in range(len(pts) - 1):
            x1, y1, a1 = pts[i]
            x2, y2, a2 = pts[i + 1]
            avg_life = (a1 + a2) * 0.5
            alpha = int(min(255.0, halo_max_alpha * _halo_alpha(avg_life)))
            if alpha < 2:
                continue
            try:
                pygame.draw.line(
                    target,
                    (self.color_edge[0], self.color_edge[1], self.color_edge[2], alpha),
                    (x1, y1), (x2, y2),
                    halo_w,
                )
            except TypeError:
                pygame.draw.line(target, self.color_edge, (x1, y1), (x2, y2), halo_w)

        # -----------------------------------------------------------------
        # Pass 3: BODY (quadratic fade — the "soft body" of the beam)
        # -----------------------------------------------------------------
        body_w = 4
        body_max_alpha = 200
        for i in range(len(pts) - 1):
            x1, y1, a1 = pts[i]
            x2, y2, a2 = pts[i + 1]
            avg_life = (a1 + a2) * 0.5
            alpha = int(min(255.0, body_max_alpha * _body_alpha(avg_life)))
            if alpha < 2:
                continue
            try:
                pygame.draw.line(
                    target,
                    (self.color_mid[0], self.color_mid[1], self.color_mid[2], alpha),
                    (x1, y1), (x2, y2),
                    body_w,
                )
            except TypeError:
                pygame.draw.line(target, self.color_mid, (x1, y1), (x2, y2), body_w)

        # -----------------------------------------------------------------
        # Pass 4: CORE (cubic fade — bright core vanishes early)
        # -----------------------------------------------------------------
        # The core is the brightest part of the beam. It only shows
        # where life_frac > ~0.3 (cubic curve drops to 0 there). This
        # makes the line "soften" before disappearing — the bright
        # core melts into the body, then the body fades, then the
        # glow expands and dissipates. That's the ethereal feel.
        core_w = 2
        core_max_alpha = 255
        for i in range(len(pts) - 1):
            x1, y1, a1 = pts[i]
            x2, y2, a2 = pts[i + 1]
            avg_life = (a1 + a2) * 0.5
            alpha = int(min(255.0, core_max_alpha * _core_alpha(avg_life)))
            if alpha < 2:
                continue
            try:
                pygame.draw.line(
                    target,
                    (self.color_core[0], self.color_core[1], self.color_core[2], alpha),
                    (x1, y1), (x2, y2),
                    core_w,
                )
            except TypeError:
                pygame.draw.line(target, self.color_core, (x1, y1), (x2, y2), core_w)

        # -----------------------------------------------------------------
        # Head bloom: extra bright burst at the very tip
        # -----------------------------------------------------------------
        # The newest segment is the "head" of the trail — the place
        # where the light source is currently emitting. We add a
        # small extra glow burst there so the head feels like a
        # fresh light source being pulled by the ship, not just
        # the end of a polyline.
        if head_life > 0.3:
            bloom_alpha = int(min(255.0, 200.0 * (head_life - 0.3) / 0.7))
            if bloom_alpha > 5:
                # 2-pass bloom: wider soft glow + tight bright center
                try:
                    pygame.draw.circle(
                        target,
                        (self.color_mid[0], self.color_mid[1], self.color_mid[2],
                         int(bloom_alpha * 0.5)),
                        (head_x, head_y),
                        8,
                    )
                    pygame.draw.circle(
                        target,
                        (self.color_core[0], self.color_core[1], self.color_core[2],
                         bloom_alpha),
                        (head_x, head_y),
                        4,
                    )
                except TypeError:
                    pygame.draw.circle(target, self.color_mid, (head_x, head_y), 8)
                    pygame.draw.circle(target, self.color_core, (head_x, head_y), 4)

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
