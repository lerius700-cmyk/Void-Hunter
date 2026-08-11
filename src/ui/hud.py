"""HUD — BLOQUE 58.16 minimalist.

User feedback: "quita todo los datos innecesarios del hud,
dejo minimalista y simbolico."

Final design: only TWO elements on the screen.

  - Top-left: HP bar (color-coded: green > yellow > red).
              Critical HP pulses red and shows a brief outer glow.
              No text label, no section headers, no value numbers.
              The visual fill IS the information.
  - Top-right: Score. Just the number, right-aligned.
              Big enough to read at a glance, no "SCORE" header.

Everything else is gone:
  - No section headers (VITALS / LOADOUT / TACTICAL)
  - No "BOMBS 3/3", "WEAPON L1 PLASMA 8/10", "MULT x4"
  - No dash heat bar, no gold rings, no tech icons
  - No "RINGS", "TECH", "DASH" labels

The player can SEE what's happening in the game. The HUD is for
passive ambient information, not a dashboard.
"""
from __future__ import annotations

import math
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.entities.player import Player
from src.systems.scoring_system import ScoringSystem
from src.systems.weapon_system import WeaponSystem


# Layout — minimum viable HUD
HUD_MARGIN = 4
HP_BAR_W = 100
HP_BAR_H = 6
HP_BAR_SEGMENTS = 10
SCORE_FONT_SIZE = 18


class HUD:
    """BLOQUE 58.16: minimalist HUD. Just HP + score."""

    def __init__(self) -> None:
        self.font_score: Optional[pygame.font.Font] = None
        self.initialized: bool = False

    def _ensure_fonts(self) -> None:
        if self.initialized:
            return
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            self.font_score = pygame.font.SysFont("consolas", SCORE_FONT_SIZE, bold=True)
        except pygame.error:
            self.font_score = None
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
        # Just the HP bar (top-left)
        self._draw_hp_bar(target, player, t)
        # Just the score (top-right)
        self._draw_score(target, scoring)

    def _draw_hp_bar(self, target: pygame.Surface, player: Player, t: float) -> None:
        """Minimalist HP bar — color tells the state, no text."""
        x = HUD_MARGIN
        y = HUD_MARGIN
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

    def _draw_score(self, target: pygame.Surface, scoring: ScoringSystem) -> None:
        """Score number, right-aligned, no header."""
        if self.font_score is None:
            return
        text = self.font_score.render(f"{scoring.score:06d}", True, (255, 220, 100))
        right = INTERNAL_W - HUD_MARGIN
        target.blit(text, (right - text.get_width(), HUD_MARGIN))


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
