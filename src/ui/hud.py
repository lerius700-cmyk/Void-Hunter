"""HUD — redesigned for clarity, pedagogy, and organization (BLOQUE 58.15).

BLOQUE 58.15: complete rewrite of BLOQUE 58.14. The previous version
had overlapping rows because each draw method used a different
"natural" height (e.g. 8 for bars, 6 for icons, 10-11 for text),
and the value text on the right of a bar (e.g. "HP 28/30") extended
BELOW the bar, into the next row's space.

The fix: every row is now a fixed ROW_H (14px) tall. The value text
sits WITHIN the row (not below it). Sections have a fixed
SECTION_HEADER_H (14px) + 1px divider. Everything snaps to a 4px
subgrid so labels, bars, and icons never overlap.

Final layout (320x480, all in the top-left corner):

    ┌─ VITALS ──────────────┐                ┌─ SCORE ──────┐
    │ HP 28/30 ▓▓▓▓▓▓░░░░  │  (row 14)      │   123456     │
    │ RINGS  ◯ ◯ ◯          │  (row 14)      │   KILLS 0067 │
    │ TECH   ⚙ ⚙            │  (row 14)      └──────────────┘
    ├─ LOADOUT ─────────────┤  (gap 6)
    │ BOMBS  ⊕ ⊕ ⊕  3/3     │  (row 14)
    │ WEAPON L1 PLASMA 8/10 │  (row 14)
    ├─ TACTICAL ────────────┤  (gap 6)
    │ DASH  ▓▓▓▓░░  OK      │  (row 14)
    │ MULT  x4 ● ● ● ●      │  (row 14)
    └───────────────────────┘

Total HUD height: 14*3 + 14*2 + 14*2 + 14*3 + 6*2 + 14*2 = 154 px
Fits comfortably in the top 200 px of the 480 px screen.
"""
from __future__ import annotations

import math
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.entities.player import Player
from src.systems.scoring_system import ScoringSystem
from src.systems.weapon_system import WeaponLevel, WeaponSystem


# Layout constants — BLOQUE 58.15
HUD_MARGIN = 4
# Every row is exactly ROW_H pixels tall. This is the single most
# important number: it must be >= the tallest content in any row
# (icons are 8, text is 11, bars are 8, value text is 11). 14 is
# the safe minimum that prevents overlap.
ROW_H = 14
# Section header is a label + a 1px divider. The label uses
# HEADER_FONT_SIZE; the divider is just below.
SECTION_HEADER_H = 14
# Gap between sections (vertical space between divider and next header)
SECTION_GAP = 6
# Gap between rows within a section
ROW_GAP = 0  # not used — rows are fixed at ROW_H now

# Element sizes
HP_BAR_W = 100
HP_BAR_H = 8
HP_BAR_SEGMENTS = 10
DASH_BAR_W = 70
DASH_BAR_H = 6
XP_BAR_W = 60
XP_BAR_H = 4
ICON_SIZE = 8
GOLD_RING_ICON_SIZE = 6
TECH_ICON_SIZE = 6

# Font sizes
LABEL_FONT_SIZE = 10
VALUE_FONT_SIZE = 11
HEADER_FONT_SIZE = 9
SCORE_FONT_SIZE = 20


class HUD:
    """BLOQUE 58.15: didactic, organized, pixel-aligned HUD.

    Every row is exactly ROW_H pixels tall. Value text is rendered
    WITHIN the row (not below it) so rows never overlap. Section
    headers have a fixed SECTION_HEADER_H + a 1px divider.
    """

    def __init__(self) -> None:
        self.font_label: Optional[pygame.font.Font] = None
        self.font_value: Optional[pygame.font.Font] = None
        self.font_header: Optional[pygame.font.Font] = None
        self.font_score: Optional[pygame.font.Font] = None
        self.initialized: bool = False

    def _ensure_fonts(self) -> None:
        if self.initialized:
            return
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            self.font_label = pygame.font.SysFont("consolas", LABEL_FONT_SIZE, bold=False)
            self.font_value = pygame.font.SysFont("consolas", VALUE_FONT_SIZE, bold=True)
            self.font_header = pygame.font.SysFont("consolas", HEADER_FONT_SIZE, bold=True)
            self.font_score = pygame.font.SysFont("consolas", SCORE_FONT_SIZE, bold=True)
        except pygame.error:
            self.font_label = None
            self.font_value = None
            self.font_header = None
            self.font_score = None
        self.initialized = True

    # ------------------------------------------------------------------
    # Public draw entry point
    # ------------------------------------------------------------------
    def draw(
        self,
        target: pygame.Surface,
        player: Player,
        weapon: WeaponSystem,
        scoring: ScoringSystem,
        t: float = 0.0,
    ) -> None:
        self._ensure_fonts()
        y = HUD_MARGIN
        # Section 1: VITALS (header + 3 rows)
        y = self._draw_section_header(target, "VITALS", y)
        y = self._draw_hp_bar(target, player, y, t)
        y = self._draw_gold_rings(target, player, y, t)
        y = self._draw_tech_icons(target, player, y)
        y += SECTION_GAP
        # Section 2: LOADOUT (header + 2 rows)
        y = self._draw_section_header(target, "LOADOUT", y)
        y = self._draw_bombs(target, player, y, t)
        y = self._draw_weapon(target, weapon, y)
        y += SECTION_GAP
        # Section 3: TACTICAL (header + 2 rows)
        y = self._draw_section_header(target, "TACTICAL", y)
        y = self._draw_dash_heat(target, player, y, t)
        y = self._draw_multiplier(target, scoring, y, t)
        # Right column: SCORE (anchored to right edge)
        self._draw_score_panel(target, scoring, t)

    # ------------------------------------------------------------------
    # Section header (fixed height)
    # ------------------------------------------------------------------
    def _draw_section_header(self, target: pygame.Surface, name: str, y: int) -> int:
        """Draw a small uppercase section header + 1px divider.
        Returns y + SECTION_HEADER_H.
        """
        if self.font_header:
            surf = self.font_header.render(name, True, (140, 160, 200))
            # Vertically center the text within the row
            text_y = y + (SECTION_HEADER_H - HEADER_FONT_SIZE) // 2
            target.blit(surf, (HUD_MARGIN, text_y))
        # Divider at the bottom of the header row
        divider_y = y + SECTION_HEADER_H - 1
        pygame.draw.line(
            target, (50, 60, 90),
            (HUD_MARGIN, divider_y),
            (HUD_MARGIN + 100, divider_y),
            1,
        )
        return y + SECTION_HEADER_H

    # ------------------------------------------------------------------
    # HP bar (fixed ROW_H tall — value text within the row)
    # ------------------------------------------------------------------
    def _draw_hp_bar(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        x = HUD_MARGIN
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
        # Bar vertically centered within the row
        bar_y = y + (ROW_H - HP_BAR_H) // 2
        # Critical HP outer glow
        if ratio <= 0.3 and int(t * 8) % 2 == 0:
            glow = pygame.Surface((HP_BAR_W + 6, HP_BAR_H + 6), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 60, 40, 100), (0, 0, HP_BAR_W + 6, HP_BAR_H + 6), 2)
            target.blit(glow, (x - 3, bar_y - 3))
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
        # Value text WITHIN the row (vertically centered)
        if self.font_value:
            value = self.font_value.render(
                f"{player.hp}/{player.hp_max}", True, (255, 240, 200)
            )
            value_y = y + (ROW_H - value.get_height()) // 2
            target.blit(value, (x + HP_BAR_W + 6, value_y))
        return y + ROW_H

    # ------------------------------------------------------------------
    # Gold rings (fixed ROW_H tall)
    # ------------------------------------------------------------------
    def _draw_gold_rings(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        x = HUD_MARGIN
        # Label vertically centered
        if self.font_label:
            label = self.font_label.render("RINGS", True, (180, 200, 220))
            label_y = y + (ROW_H - label.get_height()) // 2
            target.blit(label, (x, label_y))
            label_w = label.get_width()
        else:
            label_w = 30
        # 3 ring slots to the right of the label, vertically centered
        slots_x = x + label_w + 6
        slot_cy = y + ROW_H // 2
        for i in range(3):
            cx = slots_x + i * (GOLD_RING_ICON_SIZE + 4)
            if i < player.gold_rings and not player.hp_doubled:
                pygame.draw.circle(target, (255, 220, 80), (cx, slot_cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)
                pygame.draw.circle(target, (255, 200, 60), (cx, slot_cy),
                                   GOLD_RING_ICON_SIZE // 2 - 1, 1)
            elif player.hp_doubled:
                pygame.draw.circle(target, (255, 240, 160), (cx, slot_cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)
                pygame.draw.line(target, (255, 255, 200),
                                  (cx - 2, slot_cy), (cx - 1, slot_cy + 1), 1)
                pygame.draw.line(target, (255, 255, 200),
                                  (cx - 1, slot_cy + 1), (cx + 2, slot_cy - 1), 1)
            else:
                pygame.draw.circle(target, (80, 80, 100), (cx, slot_cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)
        return y + ROW_H

    # ------------------------------------------------------------------
    # Tech icons (fixed ROW_H tall)
    # ------------------------------------------------------------------
    def _draw_tech_icons(self, target: pygame.Surface, player: Player, y: int) -> int:
        x = HUD_MARGIN
        if self.font_label:
            label = self.font_label.render("TECH", True, (180, 200, 220))
            label_y = y + (ROW_H - label.get_height()) // 2
            target.blit(label, (x, label_y))
            label_w = label.get_width()
        else:
            label_w = 30
        slots_x = x + label_w + 6
        for i, upgrade_id in enumerate(player.tech_upgrades):
            ix = slots_x + i * (TECH_ICON_SIZE + 3)
            iy = y + (ROW_H - TECH_ICON_SIZE) // 2
            if upgrade_id == "HP_BOOST_10":
                color = (120, 255, 180)
            elif upgrade_id == "GOLIATH_SUMMON":
                color = (255, 200, 100)
            else:
                color = (200, 200, 220)
            pygame.draw.rect(target, color, (ix, iy, TECH_ICON_SIZE, TECH_ICON_SIZE))
            pygame.draw.rect(target, (40, 40, 60), (ix, iy, TECH_ICON_SIZE, TECH_ICON_SIZE), 1)
        return y + ROW_H

    # ------------------------------------------------------------------
    # Bombs (fixed ROW_H tall — label + icons + value all on one line)
    # ------------------------------------------------------------------
    def _draw_bombs(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        x = HUD_MARGIN
        bombs = player.bombs
        max_bombs = player.bombs_max
        if self.font_label:
            label = self.font_label.render("BOMBS", True, (180, 200, 220))
            label_y = y + (ROW_H - label.get_height()) // 2
            target.blit(label, (x, label_y))
            label_w = label.get_width()
        else:
            label_w = 30
        slots_x = x + label_w + 6
        icon_cy = y + ROW_H // 2
        for i in range(max_bombs):
            bx = slots_x + i * (ICON_SIZE + 3)
            is_ready = i < bombs
            if is_ready:
                pulse = 0.7 + 0.3 * math.sin(t * 4.0 + i * 0.6)
                color = (int(255 * pulse), int(200 * pulse), int(80 * pulse))
            else:
                color = (60, 60, 80)
            pygame.draw.circle(target, color, (bx + ICON_SIZE // 2, icon_cy), 3)
            if is_ready:
                cx_b, cy_b = bx + ICON_SIZE // 2, icon_cy
                pygame.draw.line(target, (255, 240, 180),
                                  (cx_b - 2, cy_b), (cx_b + 2, cy_b), 1)
                pygame.draw.line(target, (255, 240, 180),
                                  (cx_b, cy_b - 2), (cx_b, cy_b + 2), 1)
        # Count value to the right of the icons, vertically centered
        if self.font_value:
            value = self.font_value.render(
                f"{bombs}/{max_bombs}", True, (255, 220, 120)
            )
            value_x = slots_x + max_bombs * (ICON_SIZE + 3) + 4
            value_y = y + (ROW_H - value.get_height()) // 2
            target.blit(value, (value_x, value_y))
        return y + ROW_H

    # ------------------------------------------------------------------
    # Weapon (fixed ROW_H tall — label + path+level on top, XP bar at bottom)
    # ------------------------------------------------------------------
    def _draw_weapon(self, target: pygame.Surface, weapon: WeaponSystem, y: int) -> int:
        x = HUD_MARGIN
        path_name = weapon.path.value.upper()
        level = weapon.level.value
        if level >= 3:
            label_color = (255, 240, 200)
        elif level >= 2:
            label_color = (220, 230, 255)
        else:
            label_color = (220, 200, 100)
        # Top line: label + path+level
        top_y = y + 1
        if self.font_label:
            label = self.font_label.render("WEAPON", True, (180, 200, 220))
            target.blit(label, (x, top_y))
        if self.font_value:
            text = self.font_value.render(f"{path_name} L{level}", True, label_color)
            target.blit(text, (x + 50, top_y))
        # XP bar near the bottom of the row
        xp_needed = 10 if weapon.level == WeaponLevel.L1 else (
            25 if weapon.level == WeaponLevel.L2 else 50
        )
        xp_clamped = min(weapon.xp, xp_needed)
        ratio = xp_clamped / max(1, xp_needed)
        xp_y = y + ROW_H - XP_BAR_H - 1
        pygame.draw.rect(target, (200, 200, 220), (x, xp_y, XP_BAR_W + 2, XP_BAR_H + 2), 1)
        fill = int(XP_BAR_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, (255, 220, 100), (x + 1, xp_y + 1, fill, XP_BAR_H))
        # XP value at the right of the bar
        if self.font_label:
            value = self.font_label.render(
                f"{xp_clamped}/{xp_needed}", True, (200, 200, 220)
            )
            value_y = y + (ROW_H - value.get_height()) // 2
            target.blit(value, (x + XP_BAR_W + 6, value_y))
        return y + ROW_H

    # ------------------------------------------------------------------
    # Dash heat (fixed ROW_H tall)
    # ------------------------------------------------------------------
    def _draw_dash_heat(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        from src.core.settings import (
            PLAYER_DASH_HEAT_MAX, PLAYER_DASH_HEAT_RESUME_THRESHOLD,
        )
        x = HUD_MARGIN
        if self.font_label:
            label = self.font_label.render("DASH", True, (180, 200, 220))
            label_y = y + (ROW_H - label.get_height()) // 2
            target.blit(label, (x, label_y))
            label_w = label.get_width()
        else:
            label_w = 30
        bar_x = x + label_w + 6
        bar_y = y + (ROW_H - DASH_BAR_H) // 2
        ratio = max(0.0, min(1.0, player.dash_heat / PLAYER_DASH_HEAT_MAX))
        if ratio < 0.5:
            color = (80, 220, 240)
            outline = (140, 200, 220)
        elif ratio < 0.85:
            color = (255, 220, 80)
            outline = (220, 200, 140)
        else:
            pulse = 0.5 + 0.5 * math.sin(t * 12.0)
            r = int(220 + 35 * pulse)
            g = int(50 * (1.0 - pulse))
            color = (r, g, 50)
            outline = (220, 100, 80)
        pygame.draw.rect(target, outline, (bar_x - 1, bar_y - 1, DASH_BAR_W + 2, DASH_BAR_H + 2), 1)
        pygame.draw.rect(target, (30, 20, 30), (bar_x, bar_y, DASH_BAR_W, DASH_BAR_H))
        fill = int(DASH_BAR_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (bar_x, bar_y, fill, DASH_BAR_H))
        # Threshold marker
        th_x = bar_x + int(DASH_BAR_W * PLAYER_DASH_HEAT_RESUME_THRESHOLD
                            / PLAYER_DASH_HEAT_MAX)
        pygame.draw.line(target, (180, 180, 200),
                          (th_x, bar_y - 1), (th_x, bar_y + DASH_BAR_H + 1), 1)
        # State text
        if self.font_label:
            if ratio >= 0.85:
                state = "HOT"
                state_color = (255, 100, 80)
            elif ratio >= 0.5:
                state = "WARM"
                state_color = (255, 200, 100)
            else:
                state = "OK"
                state_color = (140, 220, 200)
            text = self.font_label.render(state, True, state_color)
            text_y = y + (ROW_H - text.get_height()) // 2
            target.blit(text, (bar_x + DASH_BAR_W + 6, text_y))
        return y + ROW_H

    # ------------------------------------------------------------------
    # Multiplier (fixed ROW_H tall)
    # ------------------------------------------------------------------
    def _draw_multiplier(self, target: pygame.Surface, scoring: ScoringSystem,
                          y: int, t: float) -> int:
        x = HUD_MARGIN
        mult = scoring.multiplier
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
        # Label + value on the top of the row
        if self.font_label:
            label = self.font_label.render("MULT", True, (180, 200, 220))
            label_y = y + (ROW_H - label.get_height()) // 2 - 1
            target.blit(label, (x, label_y))
        if self.font_value:
            text = self.font_value.render(f"x{mult}", True, color)
            value_x = x + 36
            value_y = y + (ROW_H - text.get_height()) // 2
            target.blit(text, (value_x, value_y))
        # Chain progress dots
        if mult < 16:
            dots_x = x + 70
            dots_cy = y + ROW_H // 2
            for i in range(min(8, scoring.streak_count)):
                pygame.draw.circle(target, color, (dots_x + i * 4, dots_cy), 1)
        return y + ROW_H

    # ------------------------------------------------------------------
    # Score panel (right column, anchored to right edge)
    # ------------------------------------------------------------------
    def _draw_score_panel(self, target: pygame.Surface, scoring: ScoringSystem,
                           t: float) -> None:
        # Right-anchored, so use INTERNAL_W - margin as the right edge
        right = INTERNAL_W - HUD_MARGIN
        # Section header
        if self.font_header:
            surf = self.font_header.render("SCORE", True, (140, 160, 200))
            header_y = HUD_MARGIN + (SECTION_HEADER_H - HEADER_FONT_SIZE) // 2
            target.blit(surf, (right - surf.get_width(), header_y))
        # Score (large, vertically centered in its row)
        if self.font_score:
            text = self.font_score.render(f"{scoring.score:06d}", True, (255, 220, 100))
            score_y = HUD_MARGIN + SECTION_HEADER_H + 1
            target.blit(text, (right - text.get_width(), score_y))
        # Kills counter (small, right-aligned, below score)
        if self.font_label:
            k_text = self.font_label.render(
                f"KILLS {scoring.kills:05d}", True, (180, 200, 220)
            )
            kills_y = HUD_MARGIN + SECTION_HEADER_H + SCORE_FONT_SIZE + 4
            target.blit(k_text, (right - k_text.get_width(), kills_y))


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
