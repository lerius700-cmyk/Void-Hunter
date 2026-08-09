"""HUD — HP / bombs / multiplier / weapon level (BLOQUE 15).

Per GDD §15:
- HP bar: green at full, yellow at half, red at low
- Bomb count: 3 icons (4 with special)
- Multiplier chain icon: changes color at 1/2/4/8/16x
- Weapon level: path icon + L1/L2/L3 + XP bar
- Score in top-right

BLOQUE 25: animated HP pulse on low HP, bomb icons pulse when ready,
weapon label color shifts with level, multiplier chain progress dots.
"""
from __future__ import annotations

import math
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.entities.player import Player
from src.systems.scoring_system import MULTIPLIER_STEPS, ScoringSystem
from src.systems.weapon_system import WeaponLevel, WeaponSystem


# HUD layout constants
HUD_MARGIN = 4
BAR_WIDTH = 60
BAR_HEIGHT = 6
ICON_SIZE = 8


class HUD:
    """Top-left: HP, bombs, weapon, XP. Top-right: score, multiplier."""

    def __init__(self) -> None:
        self.font_small: Optional[pygame.font.Font] = None
        self.font_large: Optional[pygame.font.Font] = None
        self.initialized: bool = False

    def _ensure_fonts(self) -> None:
        if self.initialized:
            return
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            self.font_small = pygame.font.Font(None, 14)
            self.font_large = pygame.font.Font(None, 22)
        except pygame.error:
            self.font_small = None
            self.font_large = None
        self.initialized = True

    def draw(
        self,
        target: pygame.Surface,
        player: Player,
        weapon: WeaponSystem,
        scoring: ScoringSystem,
        t: float = 0.0,
    ) -> None:
        self._ensure_fonts()
        # HP bar (top-left) — BLOQUE 25: animated pulse on low HP
        self._draw_hp_bar(target, player, x=HUD_MARGIN, y=HUD_MARGIN, t=t)
        # Bomb icons
        self._draw_bombs(target, player, weapon, x=HUD_MARGIN, y=HUD_MARGIN + 18, t=t)
        # Weapon level + XP
        self._draw_weapon(target, weapon, x=HUD_MARGIN, y=HUD_MARGIN + 36, t=t)
        # Multiplier
        self._draw_multiplier(target, scoring, x=HUD_MARGIN, y=HUD_MARGIN + 60, t=t)
        # Score (top-right)
        self._draw_score(target, scoring, x=INTERNAL_W - HUD_MARGIN, y=HUD_MARGIN, t=t)

    def _draw_hp_bar(self, target: pygame.Surface, player: Player, x: int, y: int, t: float = 0.0) -> None:
        ratio = max(0.0, player.hp / max(1, player.hp_max))
        # BLOQUE 25: pulse + scale shake when HP is critical
        if ratio > 0.6:
            color = (80, 200, 80)
        elif ratio > 0.3:
            color = (255, 220, 80)
        else:
            # BLOQUE 25: low-HP pulse — color shifts toward bright red on beat
            pulse = 0.5 + 0.5 * math.sin(t * 8.0)
            r = int(255 * (0.7 + 0.3 * pulse))
            g = int(40 * (1.0 - pulse))
            color = (r, g, 40)
        # BLOQUE 25: HP low adds a flash overlay
        if ratio <= 0.3 and int(t * 8) % 2 == 0:
            # Bright outer glow when low
            glow = pygame.Surface((BAR_WIDTH + 6, BAR_HEIGHT + 6), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 60, 40, 80), (0, 0, BAR_WIDTH + 6, BAR_HEIGHT + 6), 1)
            target.blit(glow, (x - 2, y - 2))
        # Outline
        pygame.draw.rect(target, (200, 200, 220), (x, y, BAR_WIDTH + 2, BAR_HEIGHT + 2), 1)
        # Fill
        fill = int(BAR_WIDTH * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (x + 1, y + 1, fill, BAR_HEIGHT))
        # Label
        if self.font_small:
            label = self.font_small.render(f"HP {player.hp}/{player.hp_max}", True, (220, 220, 240))
            target.blit(label, (x + BAR_WIDTH + 6, y - 2))

    def _draw_bombs(self, target: pygame.Surface, player: Player, weapon: WeaponSystem,
                    x: int, y: int, t: float = 0.0) -> None:
        bombs = player.bombs
        max_bombs = player.bombs_max
        for i in range(max_bombs):
            bx = x + i * (ICON_SIZE + 2)
            is_ready = i < bombs
            color = (255, 200, 80) if is_ready else (60, 60, 80)
            # BLOQUE 25: ready bombs gently pulse
            if is_ready:
                pulse = 0.7 + 0.3 * math.sin(t * 4.0 + i * 0.6)
                color = (int(255 * pulse), int(200 * pulse), int(80 * pulse))
            # Bomb icon: small circle with cross
            pygame.draw.circle(target, color, (bx + ICON_SIZE // 2, y + ICON_SIZE // 2), 3)
            # Cross lines (bomb fuse detail) only if ready
            if is_ready:
                cx_b, cy_b = bx + ICON_SIZE // 2, y + ICON_SIZE // 2
                pygame.draw.line(target, (255, 240, 180), (cx_b - 2, cy_b), (cx_b + 2, cy_b), 1)
                pygame.draw.line(target, (255, 240, 180), (cx_b, cy_b - 2), (cx_b, cy_b + 2), 1)
        if self.font_small:
            label = self.font_small.render(f"BOMBS {bombs}/{max_bombs}", True, (220, 220, 240))
            target.blit(label, (x + max_bombs * (ICON_SIZE + 2) + 4, y - 2))

    def _draw_weapon(self, target: pygame.Surface, weapon: WeaponSystem, x: int, y: int, t: float = 0.0) -> None:
        path_name = weapon.path.value.upper()
        level = weapon.level.value
        # BLOQUE 25: weapon level color shifts as level rises
        if level >= 3:
            label_color = (255, 240, 200)
        elif level >= 2:
            label_color = (220, 230, 255)
        else:
            label_color = (220, 200, 100)
        if self.font_small:
            label = self.font_small.render(f"{path_name} L{level}", True, label_color)
            target.blit(label, (x, y))
        # XP bar
        xp_needed = 10 if weapon.level == WeaponLevel.L1 else (25 if weapon.level == WeaponLevel.L2 else 50)
        xp_clamped = min(weapon.xp, xp_needed)
        ratio = xp_clamped / max(1, xp_needed)
        pygame.draw.rect(target, (200, 200, 220), (x, y + 10, BAR_WIDTH + 2, 4), 1)
        fill = int(BAR_WIDTH * ratio)
        if fill > 0:
            pygame.draw.rect(target, (255, 220, 100), (x + 1, y + 11, fill, 2))

    def _draw_multiplier(self, target: pygame.Surface, scoring: ScoringSystem,
                         x: int, y: int, t: float = 0.0) -> None:
        mult = scoring.multiplier
        # Color by tier
        if mult >= 16:
            color = (255, 200, 80)
        elif mult >= 8:
            color = (220, 120, 255)
        elif mult >= 4:
            color = (180, 100, 220)
        elif mult >= 2:
            color = (120, 200, 255)
        else:
            color = (200, 200, 200)
        if self.font_small:
            label = self.font_small.render(f"x{mult}", True, color)
            target.blit(label, (x, y))
        # BLOQUE 25: chain progress dots to next multiplier
        if mult < 16:
            for i in range(min(8, scoring.streak_count)):
                dot_x = x + 30 + i * 4
                pygame.draw.circle(target, color, (dot_x, y + 4), 1)

    def _draw_score(self, target: pygame.Surface, scoring: ScoringSystem, x: int, y: int, t: float = 0.0) -> None:
        if self.font_large is None:
            return
        text = self.font_large.render(f"{scoring.score:06d}", True, (255, 220, 100))
        target.blit(text, (x - text.get_width(), y))


# ---------------------------------------------------------------------------
# DamagePopup — floating score popup (per GDD §10)
# ---------------------------------------------------------------------------
class DamagePopup:
    """Single floating score popup. Pool-friendly."""

    def __init__(self) -> None:
        self.active: bool = False
        self.x: float = 0.0
        self.y: float = 0.0
        self.vy: float = -30.0  # float upward
        self.text: str = ""
        self.color: tuple[int, int, int] = (255, 255, 255)
        self.life: float = 0.0
        self.max_life: float = 1.0
        self.size: int = 12  # font size

    def on_spawn(self) -> None:
        pass

    def on_release(self) -> None:
        pass

    def update(self, dt: float) -> None:
        if not self.active:
            return
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 0.0:
            self.active = False


class DamagePopupPool:
    """Pool of damage popups. 32 max per GDD §11."""

    def __init__(self, capacity: int = 32) -> None:
        from src.systems.pool import Pool
        self._pool: Pool[DamagePopup] = Pool(DamagePopup, capacity)

    @property
    def active_count(self) -> int:
        return self._pool.active_count

    def spawn(
        self, x: float, y: float, text: str,
        color: tuple[int, int, int] = (255, 255, 255),
        size: int = 12,
    ) -> DamagePopup | None:
        p = self._pool.acquire()
        if p is None:
            return None
        p.x = x
        p.y = y
        p.vy = -30.0
        p.text = text
        p.color = color
        p.size = size
        p.life = 1.0
        p.max_life = 1.0
        p.active = True
        return p

    def update(self, dt: float) -> None:
        for p in self._pool:
            if p.active:
                p.update(dt)

    def draw(self, target: pygame.Surface) -> None:
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            font = pygame.font.Font(None, 14)
        except pygame.error:
            return
        for p in self._pool:
            if not p.active:
                continue
            # Alpha based on remaining life
            alpha = int(255 * max(0, p.life / p.max_life))
            text_surf = font.render(p.text, True, p.color)
            text_surf.set_alpha(alpha)
            target.blit(text_surf, (int(p.x), int(p.y)))

    def release_all(self) -> None:
        self._pool.release_all()
