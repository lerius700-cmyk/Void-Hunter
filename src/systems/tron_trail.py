"""BLOQUE 58.11: Tron-style light trail for the player PROPULSION.

When the player enters PROPULSION state, the ship leaves a continuous
chain of glowing wall segments behind it (think Tron lightcycle).
The trail is a series of small thick-line segments chained end-to-end
to form a glowing ribbon. Each segment is a dataclass with:

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

The trail is rendered with a soft cyan gradient (bright core + faint
halo) for the "neon" feel, then drawn BEFORE the player so the ship
sits on top of the wall.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame


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
        segment_length: float = 8.0,
        segment_thickness: float = 3.0,
        max_age: float = 2.5,
        spawn_interval_s: float = 0.018,  # ~55 Hz — high density for smooth ribbon
    ) -> None:
        # The cyan color palette (Tron Legacy neon)
        self.color_core: tuple[int, int, int] = (180, 255, 255)
        self.color_mid: tuple[int, int, int] = (0, 220, 255)
        self.color_edge: tuple[int, int, int] = (0, 140, 200)
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
        target: pygame.Surface,  # type: ignore[name-defined]
        offset: tuple[int, int] = (0, 0),
    ) -> None:
        """Render the trail to the target surface.

        Each segment is drawn as a thick line (length x thickness) with
        a soft cyan gradient: bright core, mid cyan body, faint edge.
        Older segments are dimmer (fade out over max_age).
        """
        if not self.segments:
            return
        ox, oy = offset
        for seg in self.segments:
            # Alpha proportional to remaining life
            life_frac = max(0.0, 1.0 - seg.age / seg.max_age)
            # Quick fade-in for the first 50ms (looks nicer than popping in)
            fade_in = min(1.0, seg.age / 0.05) if seg.age < 0.05 else 1.0
            alpha = int(255 * life_frac * fade_in)
            if alpha <= 0:
                continue
            # Compute the segment's two endpoints
            cos_a = math.cos(seg.angle)
            sin_a = math.sin(seg.angle)
            dx = cos_a * seg.length * 0.5
            dy = sin_a * seg.length * 0.5
            x1 = int(seg.cx - dx) + ox
            y1 = int(seg.cy - dy) + oy
            x2 = int(seg.cx + dx) + ox
            y2 = int(seg.cy + dy) + oy
            # Per-layer alpha
            core_a = int(255 * life_frac * fade_in)
            mid_a = int(180 * life_frac * fade_in)
            edge_a = int(90 * life_frac * fade_in)
            # Layer 1: faint outer halo (widest, dimmest)
            try:
                pygame.draw.line(  # type: ignore[name-defined]
                    target, (*self.color_edge, edge_a),
                    (x1, y1), (x2, y2),
                    max(1, int(seg.thickness) + 2),
                )
                # Layer 2: cyan body
                pygame.draw.line(
                    target, (*self.color_mid, mid_a),
                    (x1, y1), (x2, y2),
                    max(1, int(seg.thickness)),
                )
                # Layer 3: bright white-cyan core
                pygame.draw.line(
                    target, (*self.color_core, core_a),
                    (x1, y1), (x2, y2),
                    max(1, int(seg.thickness) - 1),
                )
            except TypeError:
                # Some pygame versions don't support per-line alpha.
                # Fall back to plain colored lines.
                pygame.draw.line(
                    target, self.color_mid,
                    (x1, y1), (x2, y2),
                    max(1, int(seg.thickness)),
                )

    def check_enemy_collision(
        self,
        enemy,
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

        Args:
            enemy:        an Enemy instance (must have x, y, w, h).
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
        # BLOQUE 58.11 perf: early-exit if the enemy is way outside
        # the trail's bounding box. We add the enemy's half-extent
        # to the bbox so the enemy only needs to be NEAR the bbox
        # (not inside it) for the detailed segment check.
        if self.bbox_dirty:
            self._recompute_bbox()
        enemy_half = max(enemy.w, enemy.h) * 0.5
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
            hit_dist = seg.thickness * 0.5 + max(enemy.w, enemy.h) * 0.4
            if d <= hit_dist:
                # HIT — apply damage
                enemy.apply_damage(damage)  # type: ignore[attr-defined]
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
