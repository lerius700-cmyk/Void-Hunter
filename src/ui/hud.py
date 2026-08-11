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
# BLOQUE 53b: HP bar (Mega Man / Star Fox) — wider with 10 sub-segments.
HP_BAR_WIDTH = 100
HP_BAR_HEIGHT = 8
HP_BAR_SEGMENTS = 10
BAR_WIDTH = 60
BAR_HEIGHT = 6
ICON_SIZE = 8
# BLOQUE 53c: gold ring HUD position
GOLD_RING_ICON_SIZE = 6
GOLD_RING_HUD_X = 110
# BLOQUE 53d: tech upgrade HUD position
TECH_ICON_SIZE = 6
TECH_HUD_X = 160


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
        # BLOQUE 53b: redesigned as Mega Man / Star Fox segmented bar
        self._draw_hp_bar(target, player, x=HUD_MARGIN, y=HUD_MARGIN, t=t)
        # Bomb icons — pushed down to make room for gold ring + tech
        # icon row below the HP bar.
        self._draw_bombs(target, player, weapon,
                          x=HUD_MARGIN, y=HUD_MARGIN + 32, t=t)
        # Weapon level + XP
        self._draw_weapon(target, weapon,
                           x=HUD_MARGIN, y=HUD_MARGIN + 50, t=t)
        # Multiplier
        self._draw_multiplier(target, scoring,
                                x=HUD_MARGIN, y=HUD_MARGIN + 74, t=t)
        # BLOQUE 58.8: dash heat bar (Star Fox style)
        self._draw_dash_heat(target, player,
                              x=HUD_MARGIN, y=HUD_MARGIN + 90, t=t)
        # BLOQUE 26: kill counter
        self._draw_kill_count(target, scoring, t=t)
        # Score (top-right)
        self._draw_score(target, scoring, x=INTERNAL_W - HUD_MARGIN, y=HUD_MARGIN, t=t)

    def _draw_dash_heat(self, target: pygame.Surface, player: Player,
                         x: int, y: int, t: float = 0.0) -> None:
        """BLOQUE 58.8: Star Fox style dash heat bar.

        Bar fills cyan -> yellow -> red as heat increases. When over the
        RESUME_THRESHOLD (25%), the bar pulses red and the dash is
        blocked. Below threshold, dash is available.
        """
        from src.core.settings import (
            PLAYER_DASH_HEAT_MAX, PLAYER_DASH_HEAT_RESUME_THRESHOLD,
        )
        w, h = 80, 6
        ratio = max(0.0, min(1.0, player.dash_heat / PLAYER_DASH_HEAT_MAX))
        # Color tier: cyan (cool) -> yellow (warm) -> red (overheat)
        if ratio < 0.5:
            color = (80, 220, 240)
            outline = (140, 200, 220)
        elif ratio < 0.85:
            color = (255, 220, 80)
            outline = (220, 200, 140)
        else:
            # Overheat zone — pulse red
            pulse = 0.5 + 0.5 * math.sin(t * 12.0)
            r = int(220 + 35 * pulse)
            g = int(50 * (1.0 - pulse))
            color = (r, g, 50)
            outline = (220, 100, 80)
        # Frame
        pygame.draw.rect(target, outline, (x - 1, y - 1, w + 2, h + 2), 1)
        # Empty background
        pygame.draw.rect(target, (30, 20, 30), (x, y, w, h))
        # Fill (proportional to heat)
        fill = int(w * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (x, y, fill, h))
        # Threshold marker (where dash becomes available again)
        th_x = x + int(w * PLAYER_DASH_HEAT_RESUME_THRESHOLD / PLAYER_DASH_HEAT_MAX)
        pygame.draw.line(target, (180, 180, 200), (th_x, y - 1), (th_x, y + h + 1), 1)
        # Label
        if self.font_small:
            label = self.font_small.render("DASH", True, (200, 220, 240))
            target.blit(label, (x + w + 4, y - 2))

    def _draw_hp_bar(self, target: pygame.Surface, player: Player, x: int, y: int, t: float = 0.0) -> None:
        # BLOQUE 53b: redesigned HP bar — Mega Man / Star Fox style.
        # 100px wide, 8px tall, divided into 10 visible segments. Color
        # shifts from green to yellow to red. Critical HP pulses.
        w, h = HP_BAR_WIDTH, HP_BAR_HEIGHT
        ratio = max(0.0, player.hp / max(1, player.hp_max))
        # Color tier
        if ratio > 0.6:
            color = (80, 220, 100)
            outline = (180, 230, 200)
        elif ratio > 0.3:
            color = (255, 220, 80)
            outline = (220, 220, 200)
        else:
            pulse = 0.5 + 0.5 * math.sin(t * 8.0)
            r = int(255 * (0.7 + 0.3 * pulse))
            g = int(40 * (1.0 - pulse))
            color = (r, g, 40)
            outline = (220, 200, 180)
        # Critical HP outer glow
        if ratio <= 0.3 and int(t * 8) % 2 == 0:
            glow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 60, 40, 100), (0, 0, w + 8, h + 8), 2)
            target.blit(glow, (x - 4, y - 4))
        # Frame (outline)
        pygame.draw.rect(target, outline, (x - 1, y - 1, w + 2, h + 2), 1)
        # Empty background
        pygame.draw.rect(target, (30, 20, 30), (x, y, w, h))
        # Fill (proportional)
        fill = int(w * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (x, y, fill, h))
        # Segment dividers (vertical lines every w/HP_BAR_SEGMENTS)
        seg_w = w // HP_BAR_SEGMENTS
        for i in range(1, HP_BAR_SEGMENTS):
            sx = x + i * seg_w
            pygame.draw.line(target, (10, 10, 15), (sx, y), (sx, y + h), 1)
        # Label
        if self.font_small:
            label = self.font_small.render(
                f"HP {player.hp}/{player.hp_max}", True, (220, 220, 240)
            )
            target.blit(label, (x + w + 6, y - 2))
        # BLOQUE 53c: gold ring counter (small icons next to HP)
        self._draw_gold_ring_counter(target, player, x, y + h + 4, t)
        # BLOQUE 53d: tech upgrade icons (small squares next to ring counter)
        self._draw_tech_icons(target, player, x, y + h + 12)

    def _draw_gold_ring_counter(self, target: pygame.Surface, player: Player,
                                 x: int, y: int, t: float = 0.0) -> None:
        """BLOQUE 53c: show 3 small gold ring slots. Filled = collected."""
        for i in range(3):
            cx = x + i * (GOLD_RING_ICON_SIZE + 3)
            cy = y + GOLD_RING_ICON_SIZE // 2
            if i < player.gold_rings and not player.hp_doubled:
                # Filled gold ring (collected)
                pygame.draw.circle(target, (255, 220, 80), (cx, cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)
                # Inner glow
                pygame.draw.circle(target, (255, 200, 60), (cx, cy),
                                   GOLD_RING_ICON_SIZE // 2 - 1, 1)
            elif player.hp_doubled:
                # All rings consumed (HP doubled)
                pygame.draw.circle(target, (255, 240, 160), (cx, cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)
                # Checkmark inside
                pygame.draw.line(target, (255, 255, 200),
                                  (cx - 2, cy), (cx - 1, cy + 1), 1)
                pygame.draw.line(target, (255, 255, 200),
                                  (cx - 1, cy + 1), (cx + 2, cy - 1), 1)
            else:
                # Empty slot
                pygame.draw.circle(target, (80, 80, 100), (cx, cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)

    def _draw_tech_icons(self, target: pygame.Surface, player: Player,
                          x: int, y: int) -> None:
        """BLOQUE 53d: small icons for each tech upgrade collected."""
        for i, upgrade_id in enumerate(player.tech_upgrades):
            ix = x + i * (TECH_ICON_SIZE + 2)
            # Color by upgrade type
            if upgrade_id == "HP_BOOST_10":
                color = (120, 255, 180)
            elif upgrade_id == "GOLIATH_SUMMON":
                color = (255, 200, 100)
            else:
                color = (200, 200, 220)
            # Filled square
            pygame.draw.rect(target, color, (ix, y, TECH_ICON_SIZE, TECH_ICON_SIZE))
            pygame.draw.rect(target, (40, 40, 60), (ix, y, TECH_ICON_SIZE, TECH_ICON_SIZE), 1)

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

    def _draw_kill_count(self, target: pygame.Surface, scoring: ScoringSystem, t: float = 0.0) -> None:
        """BLOQUE 26: small kill counter under score."""
        if self.font_small is None:
            return
        # Format as "KILLS: 00042"
        text = self.font_small.render(f"KILLS: {scoring.kills:05d}", True, (180, 200, 220))
        target.blit(text, (INTERNAL_W - text.get_width() - HUD_MARGIN, HUD_MARGIN + 18))


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
