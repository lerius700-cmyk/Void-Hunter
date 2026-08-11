"""HUD — redesigned for clarity, pedagogy, and organization (BLOQUE 58.14).

Layout (320x480, 8px grid):

    ┌─ VITALS ──────────────┐                ┌─ SCORE ──────┐
    │ ▓▓▓▓▓▓▓▓▓▓░░░  30/30  │  HP            │   000042     │
    │ ◯ ◯ ◯  ⚙ ⚙ ⚙          │  RINGS TECH    │   KILLS 0023 │
    ├─ LOADOUT ─────────────┤                └──────────────┘
    │ ⊕ ⊕ ⊕  3/3           │  BOMBS
    │ PATH L1 ▓▓▓▓░░  8/10 │  WEAPON+XP
    ├─ TACTICAL ────────────┤
    │ ▓▓▓▓▓▓▓▓░░  DASH OK   │  HEAT
    │ ×2  ● ● ● ●           │  MULTIPLIER
    └───────────────────────┘

Design principles:
  - Section headers (VITALS, LOADOUT, TACTICAL, SCORE) so each group
    is self-explanatory.
  - All elements use the same 4px margin and 4px row height.
  - Labels are written in plain text so the HUD teaches the player
    what each value means (HP, BOMBS, DASH, etc.).
  - Each section has a 1px top divider for visual separation.
  - No element extends past x=316 (INTERNAL_W - HUD_MARGIN) or below
    y=110 (so the gameplay area below stays uncluttered).
  - All font sizes use the same fixed-size family so labels don't
    get truncated at different DPI / scale factors.

BLOQUE 58.14: complete rewrite from BLOQUE 53b/53c/53d/58.8 layouts.
The previous HUD had overlapping labels and inconsistent margins; the
new layout is didactic, organized, and pixel-aligned.
"""
from __future__ import annotations

import math
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.entities.player import Player
from src.systems.scoring_system import ScoringSystem
from src.systems.weapon_system import WeaponLevel, WeaponSystem


# HUD layout constants — every element snaps to this 4px grid so the
# borders align with the window edges and with each other.
HUD_MARGIN = 4
SECTION_GAP = 6        # vertical gap between sections
ROW_GAP = 2            # vertical gap between rows inside a section
LABEL_FONT_SIZE = 10   # default label font (small, fits 320 width)
VALUE_FONT_SIZE = 11   # value text font (slightly larger for readability)
HEADER_FONT_SIZE = 9   # section header font (uppercase, dim)
HP_BAR_W = 100
HP_BAR_H = 8
HP_BAR_SEGMENTS = 10
DASH_BAR_W = 80
DASH_BAR_H = 6
XP_BAR_W = 60
XP_BAR_H = 4
ICON_SIZE = 8
GOLD_RING_ICON_SIZE = 6
TECH_ICON_SIZE = 6


class HUD:
    """BLOQUE 58.14: didactic, organized, pixel-aligned HUD.

    Sections (top-to-bottom, left column):
      - VITALS: HP bar (with label), gold rings, tech icons
      - LOADOUT: bombs (with count), weapon path+level+XP
      - TACTICAL: dash heat (with label), multiplier (with chain dots)

    Right column:
      - SCORE: large score, kills counter below
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
            # Fixed font size for consistent layout. The default pygame
            # font is deterministic in width per character, so text never
            # overflows the section's allocated width.
            self.font_label = pygame.font.SysFont("consolas", LABEL_FONT_SIZE, bold=False)
            self.font_value = pygame.font.SysFont("consolas", VALUE_FONT_SIZE, bold=True)
            self.font_header = pygame.font.SysFont("consolas", HEADER_FONT_SIZE, bold=True)
            self.font_score = pygame.font.SysFont("consolas", 20, bold=True)
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
        # Section 1: VITALS (HP bar, gold rings, tech icons)
        y = HUD_MARGIN
        y = self._draw_section_header(target, "VITALS", y)
        y = self._draw_hp_bar(target, player, y, t)
        y += ROW_GAP
        y = self._draw_gold_rings(target, player, y, t)
        y += ROW_GAP
        y = self._draw_tech_icons(target, player, y)
        y += SECTION_GAP
        # Section 2: LOADOUT (bombs, weapon)
        y = self._draw_section_header(target, "LOADOUT", y)
        y = self._draw_bombs(target, player, y, t)
        y += ROW_GAP
        y = self._draw_weapon(target, weapon, y)
        y += SECTION_GAP
        # Section 3: TACTICAL (dash heat, multiplier)
        y = self._draw_section_header(target, "TACTICAL", y)
        y = self._draw_dash_heat(target, player, y, t)
        y += ROW_GAP
        y = self._draw_multiplier(target, scoring, y, t)
        # Right column: SCORE (large) + kills (small)
        self._draw_score_panel(target, scoring, t)

    # ------------------------------------------------------------------
    # Section header
    # ------------------------------------------------------------------
    def _draw_section_header(self, target: pygame.Surface, name: str, y: int) -> int:
        """Draw a small uppercase section header. Returns the next y."""
        if self.font_header:
            surf = self.font_header.render(name, True, (140, 160, 200))
            target.blit(surf, (HUD_MARGIN, y))
        # Thin divider line under the header (1px, dim)
        pygame.draw.line(
            target, (50, 60, 90),
            (HUD_MARGIN, y + HEADER_FONT_SIZE + 1),
            (HUD_MARGIN + 100, y + HEADER_FONT_SIZE + 1),
            1,
        )
        return y + HEADER_FONT_SIZE + 3  # header + divider + small gap

    # ------------------------------------------------------------------
    # HP bar
    # ------------------------------------------------------------------
    def _draw_hp_bar(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        """Segmented HP bar with the numeric value on the right.

        Didactic: the value `30/30` is shown next to the bar so the
        player can see the exact HP at a glance, not just the visual
        fill level.
        """
        x = HUD_MARGIN
        ratio = max(0.0, player.hp / max(1, player.hp_max))
        # Color tier — green > yellow > red
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
            glow = pygame.Surface((HP_BAR_W + 6, HP_BAR_H + 6), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 60, 40, 100), (0, 0, HP_BAR_W + 6, HP_BAR_H + 6), 2)
            target.blit(glow, (x - 3, y - 3))
        # Frame
        pygame.draw.rect(target, outline, (x - 1, y - 1, HP_BAR_W + 2, HP_BAR_H + 2), 1)
        # Empty background
        pygame.draw.rect(target, (30, 20, 30), (x, y, HP_BAR_W, HP_BAR_H))
        # Fill
        fill = int(HP_BAR_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (x, y, fill, HP_BAR_H))
        # Segment dividers
        seg_w = HP_BAR_W // HP_BAR_SEGMENTS
        for i in range(1, HP_BAR_SEGMENTS):
            sx = x + i * seg_w
            pygame.draw.line(target, (10, 10, 15), (sx, y), (sx, y + HP_BAR_H), 1)
        # HP label on the right (numeric value)
        if self.font_label and self.font_value:
            label = self.font_label.render("HP", True, (160, 200, 220))
            target.blit(label, (x + HP_BAR_W + 6, y - 1))
            value = self.font_value.render(
                f"{player.hp}/{player.hp_max}", True, (255, 240, 200)
            )
            target.blit(value, (x + HP_BAR_W + 6, y + 8))
        return y + HP_BAR_H

    # ------------------------------------------------------------------
    # Gold rings
    # ------------------------------------------------------------------
    def _draw_gold_rings(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        x = HUD_MARGIN
        if self.font_label:
            label = self.font_label.render("RINGS", True, (180, 200, 220))
            target.blit(label, (x, y))
            label_w = label.get_width()
        else:
            label_w = 30
        # 3 ring slots to the right of the label
        slots_x = x + label_w + 4
        for i in range(3):
            cx = slots_x + i * (GOLD_RING_ICON_SIZE + 4)
            cy = y + GOLD_RING_ICON_SIZE // 2
            if i < player.gold_rings and not player.hp_doubled:
                pygame.draw.circle(target, (255, 220, 80), (cx, cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)
                pygame.draw.circle(target, (255, 200, 60), (cx, cy),
                                   GOLD_RING_ICON_SIZE // 2 - 1, 1)
            elif player.hp_doubled:
                pygame.draw.circle(target, (255, 240, 160), (cx, cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)
                pygame.draw.line(target, (255, 255, 200),
                                  (cx - 2, cy), (cx - 1, cy + 1), 1)
                pygame.draw.line(target, (255, 255, 200),
                                  (cx - 1, cy + 1), (cx + 2, cy - 1), 1)
            else:
                pygame.draw.circle(target, (80, 80, 100), (cx, cy),
                                   GOLD_RING_ICON_SIZE // 2, 1)
        return y + GOLD_RING_ICON_SIZE

    # ------------------------------------------------------------------
    # Tech upgrade icons
    # ------------------------------------------------------------------
    def _draw_tech_icons(self, target: pygame.Surface, player: Player, y: int) -> int:
        x = HUD_MARGIN
        if self.font_label:
            label = self.font_label.render("TECH", True, (180, 200, 220))
            target.blit(label, (x, y))
            label_w = label.get_width()
        else:
            label_w = 30
        slots_x = x + label_w + 4
        for i, upgrade_id in enumerate(player.tech_upgrades):
            ix = slots_x + i * (TECH_ICON_SIZE + 3)
            if upgrade_id == "HP_BOOST_10":
                color = (120, 255, 180)
            elif upgrade_id == "GOLIATH_SUMMON":
                color = (255, 200, 100)
            else:
                color = (200, 200, 220)
            pygame.draw.rect(target, color, (ix, y, TECH_ICON_SIZE, TECH_ICON_SIZE))
            pygame.draw.rect(target, (40, 40, 60), (ix, y, TECH_ICON_SIZE, TECH_ICON_SIZE), 1)
        return y + TECH_ICON_SIZE

    # ------------------------------------------------------------------
    # Bombs
    # ------------------------------------------------------------------
    def _draw_bombs(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        x = HUD_MARGIN
        bombs = player.bombs
        max_bombs = player.bombs_max
        if self.font_label:
            label = self.font_label.render("BOMBS", True, (180, 200, 220))
            target.blit(label, (x, y + 1))
            label_w = label.get_width()
        else:
            label_w = 30
        # 3 bomb slots to the right of the label
        slots_x = x + label_w + 4
        for i in range(max_bombs):
            bx = slots_x + i * (ICON_SIZE + 3)
            is_ready = i < bombs
            if is_ready:
                pulse = 0.7 + 0.3 * math.sin(t * 4.0 + i * 0.6)
                color = (int(255 * pulse), int(200 * pulse), int(80 * pulse))
            else:
                color = (60, 60, 80)
            # Bomb icon: circle + cross
            pygame.draw.circle(target, color, (bx + ICON_SIZE // 2, y + ICON_SIZE // 2), 3)
            if is_ready:
                cx_b, cy_b = bx + ICON_SIZE // 2, y + ICON_SIZE // 2
                pygame.draw.line(target, (255, 240, 180),
                                  (cx_b - 2, cy_b), (cx_b + 2, cy_b), 1)
                pygame.draw.line(target, (255, 240, 180),
                                  (cx_b, cy_b - 2), (cx_b, cy_b + 2), 1)
        # Count value at the far right
        if self.font_value:
            value = self.font_value.render(
                f"{bombs}/{max_bombs}", True, (255, 220, 120)
            )
            target.blit(value, (slots_x + max_bombs * (ICON_SIZE + 3) + 4, y))
        return y + ICON_SIZE

    # ------------------------------------------------------------------
    # Weapon path + level + XP
    # ------------------------------------------------------------------
    def _draw_weapon(self, target: pygame.Surface, weapon: WeaponSystem, y: int) -> int:
        x = HUD_MARGIN
        path_name = weapon.path.value.upper()
        level = weapon.level.value
        # Color by level
        if level >= 3:
            label_color = (255, 240, 200)
        elif level >= 2:
            label_color = (220, 230, 255)
        else:
            label_color = (220, 200, 100)
        if self.font_label:
            label = self.font_label.render("WEAPON", True, (180, 200, 220))
            target.blit(label, (x, y))
        if self.font_value:
            text = self.font_value.render(f"{path_name} L{level}", True, label_color)
            target.blit(text, (x + 50, y))
        # XP bar
        xp_needed = 10 if weapon.level == WeaponLevel.L1 else (
            25 if weapon.level == WeaponLevel.L2 else 50
        )
        xp_clamped = min(weapon.xp, xp_needed)
        ratio = xp_clamped / max(1, xp_needed)
        bar_y = y + 4
        pygame.draw.rect(target, (200, 200, 220), (x, bar_y, XP_BAR_W + 2, XP_BAR_H + 2), 1)
        fill = int(XP_BAR_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, (255, 220, 100), (x + 1, bar_y + 1, fill, XP_BAR_H))
        # XP value text
        if self.font_label:
            value = self.font_label.render(
                f"{xp_clamped}/{xp_needed}", True, (200, 200, 220)
            )
            target.blit(value, (x + XP_BAR_W + 6, y))
        return y + 4 + XP_BAR_H

    # ------------------------------------------------------------------
    # Dash heat
    # ------------------------------------------------------------------
    def _draw_dash_heat(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        from src.core.settings import (
            PLAYER_DASH_HEAT_MAX, PLAYER_DASH_HEAT_RESUME_THRESHOLD,
        )
        x = HUD_MARGIN
        if self.font_label:
            label = self.font_label.render("DASH", True, (180, 200, 220))
            target.blit(label, (x, y))
            label_w = label.get_width()
        else:
            label_w = 30
        bar_x = x + label_w + 4
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
        # Frame + bg + fill
        pygame.draw.rect(target, outline, (bar_x - 1, y - 1, DASH_BAR_W + 2, DASH_BAR_H + 2), 1)
        pygame.draw.rect(target, (30, 20, 30), (bar_x, y, DASH_BAR_W, DASH_BAR_H))
        fill = int(DASH_BAR_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (bar_x, y, fill, DASH_BAR_H))
        # Threshold marker
        th_x = bar_x + int(DASH_BAR_W * PLAYER_DASH_HEAT_RESUME_THRESHOLD
                            / PLAYER_DASH_HEAT_MAX)
        pygame.draw.line(target, (180, 180, 200),
                          (th_x, y - 1), (th_x, y + DASH_BAR_H + 1), 1)
        # State text (cool / warm / overheat)
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
            target.blit(text, (bar_x + DASH_BAR_W + 6, y))
        return y + DASH_BAR_H

    # ------------------------------------------------------------------
    # Multiplier
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
        if self.font_label:
            label = self.font_label.render("MULT", True, (180, 200, 220))
            target.blit(label, (x, y))
        if self.font_value:
            text = self.font_value.render(f"x{mult}", True, color)
            target.blit(text, (x + 40, y - 1))
        # Chain progress dots (next 8 multipliers)
        if self.font_label and mult < 16:
            dots_x = x + 70
            for i in range(min(8, scoring.streak_count)):
                pygame.draw.circle(target, color, (dots_x + i * 4, y + 4), 1)
        return y + 6

    # ------------------------------------------------------------------
    # Score panel (top-right)
    # ------------------------------------------------------------------
    def _draw_score_panel(self, target: pygame.Surface, scoring: ScoringSystem,
                           t: float) -> None:
        # Right-anchored, so use INTERNAL_W - margin as the right edge
        right = INTERNAL_W - HUD_MARGIN
        # Section header
        if self.font_header:
            surf = self.font_header.render("SCORE", True, (140, 160, 200))
            # Right-align the header text
            target.blit(surf, (right - surf.get_width(), HUD_MARGIN))
        # Score (large, right-aligned)
        if self.font_score:
            text = self.font_score.render(f"{scoring.score:06d}", True, (255, 220, 100))
            target.blit(text, (right - text.get_width(), HUD_MARGIN + HEADER_FONT_SIZE + 2))
        # Kills counter (small, right-aligned, below score)
        y_kills = HUD_MARGIN + HEADER_FONT_SIZE + 2 + 22
        if self.font_label:
            k_text = self.font_label.render(f"KILLS {scoring.kills:05d}", True, (180, 200, 220))
            target.blit(k_text, (right - k_text.get_width(), y_kills))


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
