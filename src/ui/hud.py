"""HUD — BLOQUE 58.41: minimalist with dynamic score color.

User feedback (BLOQUE 58.41):
- HUD should be more minimalist
- Bomb icon should be a missile (not a round bomb)
- Score color reflects performance:
  * 100% kills: blood red + bright glow + gold border
  * 99%: red, no glow, no border
  * 99% → 49%: red → yellow
  * 49% → 20%: yellow → white
  * <20%: white

Layout (minimalist):
  - Top-left: HP bar (compact)
  - Below HP: Overheat bar (compact)
  - Right column: Score (dynamic color, gold-bordered at 100%)
"""
from __future__ import annotations

import math
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.entities.player import Player
from src.systems.scoring_system import ScoringSystem
from src.systems.weapon_system import WeaponSystem


# Layout — BLOQUE 58.41 (minimalist)
HUD_MARGIN = 3
ROW_H = 11  # tighter spacing
ICON_SIZE = 8
GOLD_RING_ICON_SIZE = 5
HP_BAR_W = 80
HP_BAR_H = 5
HP_BAR_SEGMENTS = 8
HEAT_BAR_W = 60
HEAT_BAR_H = 4
SCORE_FONT_SIZE = 16
LABEL_FONT_SIZE = 9


# Score color tiers (BLOQUE 58.41)
SCORE_RED = (220, 30, 35)       # 100% / 99% blood red
SCORE_RED_BRIGHT = (255, 40, 50)  # 100% extra-saturated
SCORE_YELLOW = (240, 200, 60)   # 49% threshold
SCORE_WHITE = (240, 240, 240)    # <20%
GOLD_BORDER = (255, 200, 80)     # 100% gold border


def score_color_for_ratio(ratio: float) -> tuple[int, int, int]:
    """BLOQUE 58.41: compute the score color based on kill ratio.

    Returns the RGB tuple for the score number.
    """
    r = max(0.0, min(1.0, ratio))
    if r >= 1.0:
        return SCORE_RED_BRIGHT
    if r >= 0.99:
        return SCORE_RED
    if r >= 0.49:
        # Interpolate YELLOW (0.49) → RED (0.99) as ratio increases
        # t=0 → yellow (at 49%), t=1 → red (at 99%)
        t = (r - 0.49) / (0.99 - 0.49)
        return (
            int(SCORE_YELLOW[0] + (SCORE_RED[0] - SCORE_YELLOW[0]) * t),
            int(SCORE_YELLOW[1] + (SCORE_RED[1] - SCORE_YELLOW[1]) * t),
            int(SCORE_YELLOW[2] + (SCORE_RED[2] - SCORE_YELLOW[2]) * t),
        )
    if r >= 0.20:
        # Interpolate WHITE (0.20) → YELLOW (0.49) as ratio increases
        # t=0 → white (at 20%), t=1 → yellow (at 49%)
        t = (r - 0.20) / (0.49 - 0.20)
        return (
            int(SCORE_WHITE[0] + (SCORE_YELLOW[0] - SCORE_WHITE[0]) * t),
            int(SCORE_WHITE[1] + (SCORE_YELLOW[1] - SCORE_WHITE[1]) * t),
            int(SCORE_WHITE[2] + (SCORE_YELLOW[2] - SCORE_WHITE[2]) * t),
        )
    return SCORE_WHITE


def score_has_glow(ratio: float) -> bool:
    """BLOQUE 58.41: 100% → glow + gold border. 99% → red without extras."""
    return ratio >= 1.0


class HUD:
    """BLOQUE 58.41: minimalist HUD with HP, overheat, missiles, score."""

    def __init__(self) -> None:
        self.font_label: Optional[pygame.font.Font] = None
        self.font_value: Optional[pygame.font.Font] = None
        self.font_score: Optional[pygame.font.Font] = None
        self.initialized: bool = False

    def _ensure_fonts(self) -> None:
        if self.initialized:
            return
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            self.font_label = pygame.font.SysFont("consolas", LABEL_FONT_SIZE, bold=False)
            self.font_value = pygame.font.SysFont("consolas", LABEL_FONT_SIZE, bold=True)
            self.font_score = pygame.font.SysFont("consolas", SCORE_FONT_SIZE, bold=True)
        except pygame.error:
            self.font_label = None
            self.font_value = None
            self.font_score = None
        self.initialized = True

    def draw(
        self,
        target: pygame.Surface,
        player: Player,
        weapon: WeaponSystem,
        scoring: ScoringSystem,
        t: float = 0.0,
        kill_ratio: float = 1.0,
    ) -> None:
        self._ensure_fonts()
        # Stack: HP, overheat (left column)
        y = HUD_MARGIN
        y = self._draw_hp_bar(target, player, y, t)
        y = self._draw_overheat_bar(target, player, y, t)
        y = self._draw_missiles(target, player, y, t)
        # Right column: score
        self._draw_score(target, scoring, kill_ratio, t)

    def _draw_hp_bar(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        """BLOQUE 58.41: HP bar minimalist (no value text, smaller)."""
        x = HUD_MARGIN
        ratio = max(0.0, player.hp / max(1, player.hp_max))
        # Color tier
        if ratio > 0.6:
            color = (80, 220, 100)
            outline = (160, 200, 180)
        elif ratio > 0.3:
            color = (255, 220, 80)
            outline = (200, 200, 170)
        else:
            pulse = 0.5 + 0.5 * math.sin(t * 8.0)
            r = int(255 * (0.7 + 0.3 * pulse))
            g = int(40 * (1.0 - pulse))
            color = (r, g, 40)
            outline = (200, 180, 160)
        bar_y = y + (ROW_H - HP_BAR_H) // 2
        # Critical HP outer glow (subtle)
        if ratio <= 0.3 and int(t * 8) % 2 == 0:
            glow = pygame.Surface((HP_BAR_W + 4, HP_BAR_H + 4), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 60, 40, 90), (0, 0, HP_BAR_W + 4, HP_BAR_H + 4), 2)
            target.blit(glow, (x - 2, bar_y - 2))
        # Frame
        pygame.draw.rect(target, outline, (x - 1, bar_y - 1, HP_BAR_W + 2, HP_BAR_H + 2), 1)
        # Empty background
        pygame.draw.rect(target, (30, 20, 30), (x, bar_y, HP_BAR_W, HP_BAR_H))
        # Fill
        fill = int(HP_BAR_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (x, bar_y, fill, HP_BAR_H))
        # Segment dividers
        seg_w = HP_BAR_W // HP_BAR_SEGMENTS
        for i in range(1, HP_BAR_SEGMENTS):
            sx = x + i * seg_w
            pygame.draw.line(target, (10, 10, 15), (sx, bar_y), (sx, bar_y + HP_BAR_H), 1)
        return y + ROW_H

    def _draw_overheat_bar(self, target: pygame.Surface, player: Player,
                            y: int, t: float) -> int:
        """BLOQUE 58.41: overheat bar minimalist (no label, no state text)."""
        from src.core.settings import (
            PLAYER_DASH_HEAT_MAX, PLAYER_DASH_HEAT_RESUME_THRESHOLD,
        )
        x = HUD_MARGIN
        bar_y = y + (ROW_H - HEAT_BAR_H) // 2
        ratio = max(0.0, min(1.0, player.dash_heat / PLAYER_DASH_HEAT_MAX))
        # Color tier: cyan (cool) -> yellow (warm) -> red (overheat)
        if ratio < 0.5:
            color = (80, 220, 240)
            outline = (140, 200, 220)
        elif ratio < 0.85:
            color = (255, 220, 80)
            outline = (200, 200, 140)
        else:
            pulse = 0.5 + 0.5 * math.sin(t * 12.0)
            r = int(220 + 35 * pulse)
            g = int(50 * (1.0 - pulse))
            color = (r, g, 50)
            outline = (200, 100, 80)
        # Frame + bg + fill
        pygame.draw.rect(target, outline, (x - 1, bar_y - 1, HEAT_BAR_W + 2, HEAT_BAR_H + 2), 1)
        pygame.draw.rect(target, (30, 20, 30), (x, bar_y, HEAT_BAR_W, HEAT_BAR_H))
        fill = int(HEAT_BAR_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (x, bar_y, fill, HEAT_BAR_H))
        # Threshold marker
        th_x = x + int(HEAT_BAR_W * PLAYER_DASH_HEAT_RESUME_THRESHOLD
                       / PLAYER_DASH_HEAT_MAX)
        pygame.draw.line(target, (180, 180, 200),
                          (th_x, bar_y - 1), (th_x, bar_y + HEAT_BAR_H + 1), 1)
        return y + ROW_H

    def _draw_missiles(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        """BLOQUE 58.41: minimalist missile icons (replaces bomb rounds).

        Each icon is a tiny vertical missile silhouette: pointed nose,
        thin body, two small fins. Ready missiles pulse warm yellow with
        a faint engine glow. Spent missiles are dark silhouettes.
        """
        x = HUD_MARGIN
        bombs = player.bombs
        max_bombs = player.bombs_max
        icon_cy = y + ROW_H // 2
        for i in range(max_bombs):
            bx = x + i * (ICON_SIZE + 3)
            is_ready = i < bombs
            self._draw_missile_icon(target, bx, icon_cy, ready=is_ready, t=t, idx=i)
        return y + ROW_H

    def _draw_missile_icon(self, target: pygame.Surface, x: int, y: int,
                            ready: bool, t: float, idx: int) -> None:
        """BLOQUE 58.41: draw a single minimalist missile silhouette.

        Vertical orientation. Pointed nose at top, body, two small fins at
        the bottom, optional engine glow when ready.
        """
        # Missile geometry (6 px tall, 4 px wide)
        body_x = x
        body_y = y - 2  # center vertically in the row
        body_w = 4
        body_h = 5
        # Color palette
        if ready:
            pulse = 0.7 + 0.3 * math.sin(t * 4.0 + idx * 0.6)
            body_col = (int(220 * pulse), int(200 * pulse), int(120 * pulse))
            nose_col = (255, 180, 100)
            fin_col = (200, 130, 60)
            engine_col = (255, 220, 140)
        else:
            body_col = (50, 50, 60)
            nose_col = (60, 60, 70)
            fin_col = (40, 40, 50)
            engine_col = (40, 40, 50)
        # Nose (pointed triangle on top)
        pygame.draw.polygon(target, nose_col, [
            (body_x + body_w // 2, body_y - 1),       # tip
            (body_x + body_w, body_y + 1),           # right base
            (body_x, body_y + 1),                    # left base
        ])
        # Body (rectangle)
        pygame.draw.rect(target, body_col, (body_x, body_y + 1, body_w, body_h - 2))
        # Body outline (darker edge for definition)
        pygame.draw.rect(target, (max(0, body_col[0] - 50), max(0, body_col[1] - 50),
                                    max(0, body_col[2] - 50)),
                          (body_x, body_y + 1, body_w, body_h - 2), 1)
        # Wings / fins (small triangles at the bottom)
        pygame.draw.polygon(target, fin_col, [
            (body_x, body_y + body_h - 1),
            (body_x - 1, body_y + body_h + 1),
            (body_x + 1, body_y + body_h - 1),
        ])
        pygame.draw.polygon(target, fin_col, [
            (body_x + body_w, body_y + body_h - 1),
            (body_x + body_w + 1, body_y + body_h + 1),
            (body_x + body_w - 1, body_y + body_h - 1),
        ])
        # Engine glow (small dot below when ready)
        if ready:
            glow = pygame.Surface((6, 3), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*engine_col, 180), (0, 0, 6, 3))
            target.blit(glow, (body_x - 1, body_y + body_h))

    def _draw_score(self, target: pygame.Surface, scoring: ScoringSystem,
                    kill_ratio: float, t: float) -> None:
        """BLOQUE 58.41: score with dynamic color + 100% glow + gold border.

        Color tiers (based on kill_ratio = kills / enemies_spawned):
          * 100%:  blood red + bright glow halo + gold border (extra-pumped)
          * 99% :  blood red, no extras
          * 99→49%: red → yellow gradient
          * 49→20%: yellow → white gradient
          * <20%:   white
        """
        if self.font_score is None:
            return
        score_text = f"{scoring.score:06d}"
        col = score_color_for_ratio(kill_ratio)
        # 100% perk: glow halo + gold border around the number
        if score_has_glow(kill_ratio):
            # Pulsing glow (intensity breathes 0.85 → 1.0)
            pulse = 0.85 + 0.15 * math.sin(t * 4.0)
            # Layer 1: outer red glow (soft)
            outer_glow = self.font_score.render(score_text, True, (255, 60, 80))
            outer_glow.set_alpha(int(140 * pulse))
            text_w = outer_glow.get_width()
            text_h = outer_glow.get_height()
            ox = INTERNAL_W - HUD_MARGIN - text_w
            oy = HUD_MARGIN
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                target.blit(outer_glow, (ox + dx, oy + dy))
            # Layer 2: gold border (drawn behind the main text)
            border_col = GOLD_BORDER
            text_main = self.font_score.render(score_text, True, col)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                           (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                border = self.font_score.render(score_text, True, border_col)
                target.blit(border, (ox + dx, oy + dy))
            # Layer 3: bright red core text
            target.blit(text_main, (ox, oy))
        else:
            # Plain text in the tier color
            text = self.font_score.render(score_text, True, col)
            text_w = text.get_width()
            target.blit(text, (INTERNAL_W - HUD_MARGIN - text_w, HUD_MARGIN))


# ---------------------------------------------------------------------------
# DamagePopup — floating score popup (per GDD §10)
# ---------------------------------------------------------------------------
class DamagePopup:
    """Single floating score popup. Pool-friendly."""

    def __init__(self) -> None:
        self.active: bool = False
        self.x: float = 0.0
        self.y: float = 0.0
        self.vy: float = -30.0
        self.text: str = ""
        self.color: tuple[int, int, int] = (255, 255, 255)
        self.life: float = 0.0
        self.max_life: float = 1.0
        self.size: int = 12

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
            font = pygame.font.SysFont("consolas", 11)
        except pygame.error:
            return
        for p in self._pool:
            if not p.active:
                continue
            alpha = int(255 * max(0, p.life / p.max_life))
            text_surf = font.render(p.text, True, p.color)
            text_surf.set_alpha(alpha)
            target.blit(text_surf, (int(p.x), int(p.y)))

    def release_all(self) -> None:
        self._pool.release_all()
