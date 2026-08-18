"""Power-up rings (Starfox 64 style).

Two kinds:
  * SILVER — heals 1 life. Most common drop (10% from enemies).
  * GOLD — heals 2 lives AND counts toward the gold ring stack
    (3 gold rings = +3 max lives, max 2 stacks = 9 lives total).

Pickup is automatic via a 30 px magneto radius around the player.
No button press required.

Rings stay on screen for 15 seconds with a 3-second fade-out tail
so they don't linger forever after a wave ends.
"""
from __future__ import annotations

import math

import pygame


class PowerUpKind:
    SILVER = "silver"  # heals 1
    GOLD = "gold"      # heals 2 + counts toward gold stack


# Drop rates per the user's spec.
ENEMY_DROP_RATE_SILVER = 0.10
ENEMY_DROP_RATE_GOLD = 0.05


class PowerUp:
    SIZE = 10                # render size (px)
    PICKUP_RADIUS = 30.0      # magneto radius
    LIFETIME_S = 15.0         # full-opacity duration
    FADE_DURATION_S = 3.0     # tail fade after LIFETIME_S
    SPIN_SPEED_RAD_S = 2.0    # visual rotation around its own center

    __slots__ = (
        "x", "y", "kind", "spawn_time", "alive",
    )

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.kind: str = PowerUpKind.SILVER
        self.spawn_time: float = 0.0
        self.alive: bool = False

    def spawn(self, x: float, y: float, kind: str, now: float) -> None:
        self.x = x
        self.y = y
        self.kind = kind
        self.spawn_time = now
        self.alive = True

    def update(self, dt: float, player, now: float) -> bool:
        """Advance the power-up one frame.

        Returns True if the power-up was picked up by the player this
        frame (caller should apply the effect and remove it from the
        list). Returns False otherwise.
        """
        if not self.alive:
            return False
        age = now - self.spawn_time
        if age >= self.LIFETIME_S + self.FADE_DURATION_S:
            self.alive = False
            return False
        # Magneto pickup — Euclidean distance to the player.
        dx = player.x - self.x
        dy = player.y - self.y
        if (dx * dx + dy * dy) <= self.PICKUP_RADIUS * self.PICKUP_RADIUS:
            self.alive = False
            return True
        return False

    def current_alpha(self, now: float) -> int:
        """Return the current alpha (0-255) for rendering. Full opacity
        for the first LIFETIME_S seconds, then linear fade to 0.
        """
        age = now - self.spawn_time
        if age < self.LIFETIME_S:
            return 255
        fade_progress = (age - self.LIFETIME_S) / self.FADE_DURATION_S
        fade_progress = max(0.0, min(1.0, fade_progress))
        return int(255 * (1.0 - fade_progress))

    def draw(self, surface: pygame.Surface, now: float) -> None:
        if not self.alive:
            return
        alpha = self.current_alpha(now)
        if alpha <= 0:
            return
        # Spin angle: small slow rotation just for visual interest.
        age = now - self.spawn_time
        angle = age * self.SPIN_SPEED_RAD_S
        # Render a 4-petal star pattern (a "ring" silhouette) so the
        # gold/silver distinction reads even at 10 px.
        cx, cy = int(self.x), int(self.y)
        if self.kind == PowerUpKind.GOLD:
            inner_color = (255, 220, 110)
            outer_color = (255, 150, 50)
        else:
            inner_color = (220, 230, 255)
            outer_color = (140, 170, 220)
        # Outer glow disc (radius 6) at low alpha.
        glow_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*outer_color, int(alpha * 0.45)),
                           (8, 8), 7)
        surface.blit(glow_surf, (cx - 8, cy - 8))
        # The "ring" itself: a hollow circle (outer radius 4, inner
        # radius 2) plus 4 small dots around it that orbit slowly so
        # the player can tell the ring is "alive".
        ring_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, (*inner_color, alpha),
                           (10, 10), 4, 2)
        # Four orbital dots.
        for i in range(4):
            a = angle + i * (math.pi / 2)
            ox = 10 + math.cos(a) * 5
            oy = 10 + math.sin(a) * 5
            pygame.draw.circle(ring_surf, (*outer_color, alpha),
                               (int(ox), int(oy)), 1)
        surface.blit(ring_surf, (cx - 10, cy - 10))

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.SIZE // 2),
                           int(self.y - self.SIZE // 2),
                           self.SIZE, self.SIZE)


def roll_enemy_drop(rng: "random.Random | None" = None) -> str | None:
    """Roll a power-up drop for a freshly-killed enemy.

    10% silver, 5% gold. Returns the PowerUpKind or None if no drop.
    """
    import random
    r = rng if rng is not None else random
    roll = r.random()
    # Gold is rarer so check it first; if it's not gold, check silver.
    if roll < ENEMY_DROP_RATE_GOLD:
        return PowerUpKind.GOLD
    if roll < ENEMY_DROP_RATE_GOLD + ENEMY_DROP_RATE_SILVER:
        return PowerUpKind.SILVER
    return None
