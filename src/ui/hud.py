"""HUD — BLOQUE 58.19 minimalist with 4 elements.

User feedback (BLOQUE 58.19): "agrega solo la barra de overheat,
los 3 ranuras de los anillos para aumentar la vida y recuperar la
misma, tambien agrega un contador de cuantas bombas tengo."

The HUD now has 5 elements total:

  - Top-left: HP bar (color-coded: green > yellow > red)
  - Below HP: Overheat bar (dash heat) with state text (OK/WARM/HOT)
  - Below overheat: 3 gold ring slots (collected/empty)
  - Below rings: Bomb counter (3-4 bomb icons + value)
  - Top-right: Score (large number, no header)

Everything else is gone: no section headers, no weapon info,
no multiplier, no tech icons, no "BOMBS 3/3" label.
"""
from __future__ import annotations

import math
from typing import Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.entities.player import Player
from src.systems.scoring_system import ScoringSystem
from src.systems.weapon_system import WeaponSystem


# Layout — BLOQUE 58.19
HUD_MARGIN = 4
ROW_H = 14
ICON_SIZE = 8
GOLD_RING_ICON_SIZE = 6
HP_BAR_W = 100
HP_BAR_H = 6
HP_BAR_SEGMENTS = 10
HEAT_BAR_W = 80
HEAT_BAR_H = 5
SCORE_FONT_SIZE = 18
LABEL_FONT_SIZE = 10


class HUD:
    """BLOQUE 58.19: minimalist HUD with HP, overheat, rings, bombs, score."""

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
    ) -> None:
        self._ensure_fonts()
        # Stack: HP, overheat, rings, bombs (left column)
        y = HUD_MARGIN
        y = self._draw_hp_bar(target, player, y, t)
        y = self._draw_overheat_bar(target, player, y, t)
        y = self._draw_gold_rings(target, player, y, t)
        y = self._draw_bombs(target, player, y, t)
        # Right column: score
        self._draw_score(target, scoring)

    def _draw_hp_bar(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        """HP bar with color tier (green/yellow/red)."""
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
        # Value text (28/30) right of the bar
        if self.font_value:
            value = self.font_value.render(
                f"{player.hp}/{player.hp_max}", True, (255, 240, 200)
            )
            value_y = y + (ROW_H - value.get_height()) // 2
            target.blit(value, (x + HP_BAR_W + 6, value_y))
        return y + ROW_H

    def _draw_overheat_bar(self, target: pygame.Surface, player: Player,
                            y: int, t: float) -> int:
        """BLOQUE 58.19: overheat (dash heat) bar with state text."""
        from src.core.settings import (
            PLAYER_DASH_HEAT_MAX, PLAYER_DASH_HEAT_RESUME_THRESHOLD,
        )
        x = HUD_MARGIN
        # Label + bar + state text on one row
        if self.font_label:
            label = self.font_label.render("HEAT", True, (180, 200, 220))
            label_y = y + (ROW_H - label.get_height()) // 2
            target.blit(label, (x, label_y))
            label_w = label.get_width()
        else:
            label_w = 30
        bar_x = x + label_w + 4
        bar_y = y + (ROW_H - HEAT_BAR_H) // 2
        ratio = max(0.0, min(1.0, player.dash_heat / PLAYER_DASH_HEAT_MAX))
        # Color tier: cyan (cool) -> yellow (warm) -> red (overheat)
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
        pygame.draw.rect(target, outline, (bar_x - 1, bar_y - 1, HEAT_BAR_W + 2, HEAT_BAR_H + 2), 1)
        pygame.draw.rect(target, (30, 20, 30), (bar_x, bar_y, HEAT_BAR_W, HEAT_BAR_H))
        fill = int(HEAT_BAR_W * ratio)
        if fill > 0:
            pygame.draw.rect(target, color, (bar_x, bar_y, fill, HEAT_BAR_H))
        # Threshold marker (where dash becomes available again)
        th_x = bar_x + int(HEAT_BAR_W * PLAYER_DASH_HEAT_RESUME_THRESHOLD
                            / PLAYER_DASH_HEAT_MAX)
        pygame.draw.line(target, (180, 180, 200),
                          (th_x, bar_y - 1), (th_x, bar_y + HEAT_BAR_H + 1), 1)
        # State text (OK / WARM / HOT)
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
            target.blit(text, (bar_x + HEAT_BAR_W + 6, text_y))
        return y + ROW_H

    def _draw_gold_rings(self, target: pygame.Surface, player: Player,
                          y: int, t: float) -> int:
        """BLOQUE 58.19: 3 gold ring slots (collected/empty)."""
        x = HUD_MARGIN
        if self.font_label:
            label = self.font_label.render("RINGS", True, (180, 200, 220))
            label_y = y + (ROW_H - label.get_height()) // 2
            target.blit(label, (x, label_y))
            label_w = label.get_width()
        else:
            label_w = 30
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

    def _draw_bombs(self, target: pygame.Surface, player: Player, y: int, t: float) -> int:
        """BLOQUE 58.19 + 58.39: bomb counter (3-4 bomb icons + numeric value).

        BLOQUE 58.39: bombs are now drawn as actual bomb silhouettes
        (round body + neck + cap + lit fuse), not just circles. Makes the
        HUD read more like a real shmup inventory.
        """
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
            self._draw_bomb_icon(target, bx, icon_cy, ready=is_ready, t=t, idx=i)
        # Count value to the right
        if self.font_value:
            value = self.font_value.render(
                f"{bombs}/{max_bombs}", True, (255, 220, 120)
            )
            value_x = slots_x + max_bombs * (ICON_SIZE + 3) + 4
            value_y = y + (ROW_H - value.get_height()) // 2
            target.blit(value, (value_x, value_y))
        return y + ROW_H

    def _draw_bomb_icon(self, target: pygame.Surface, x: int, y: int,
                        ready: bool, t: float, idx: int) -> None:
        """BLOQUE 58.39: draw a single bomb silhouette (round body + neck + fuse).

        Ready bombs pulse warm yellow with a glowing fuse. Spent bombs are
        a dim grey silhouette (no fuse spark).
        """
        if ready:
            pulse = 0.7 + 0.3 * math.sin(t * 4.0 + idx * 0.6)
            body_col = (int(255 * pulse), int(200 * pulse), int(80 * pulse))
            cap_col = (140, 110, 60)
            fuse_col = (255, 200, 100)
            spark_col = (255, 255, 200)
        else:
            body_col = (50, 50, 60)
            cap_col = (35, 35, 40)
            fuse_col = (40, 40, 50)
            spark_col = (40, 40, 50)
        # Bomb body (sphere, 5px diameter)
        body_cx = x + 3
        body_cy = y + 1
        # Bottom shadow
        pygame.draw.circle(target, (max(0, body_col[0] - 60), max(0, body_col[1] - 60),
                                     max(0, body_col[2] - 60)),
                           (body_cx, body_cy + 1), 3)
        # Main body
        pygame.draw.circle(target, body_col, (body_cx, body_cy), 3)
        # Highlight (top-left of sphere, gives 3D feel)
        if ready:
            pygame.draw.circle(target, (255, 255, 220), (body_cx - 1, body_cy - 1), 1)
        # Neck (small rectangle on top)
        pygame.draw.rect(target, cap_col, (body_cx - 1, body_cy - 4, 2, 2))
        # Cap (top of neck)
        pygame.draw.rect(target, cap_col, (body_cx - 2, body_cy - 5, 4, 1))
        # Fuse (curves up-right from cap)
        fuse_x = body_cx + 2
        fuse_y = body_cy - 5
        pygame.draw.line(target, fuse_col, (fuse_x, fuse_y),
                         (fuse_x + 2, fuse_y - 2), 1)
        # Fuse spark (only when ready, animated)
        if ready:
            spark_phase = (t * 8.0 + idx * 1.3) % 1.0
            spark_x = int(fuse_x + 2 + math.cos(spark_phase * 6.28) * 1)
            spark_y = int(fuse_y - 2 + math.sin(spark_phase * 6.28) * 1)
            # Tiny spark glow
            halo = pygame.Surface((6, 6), pygame.SRCALPHA)
            halo_a = int(180 * (1.0 - spark_phase * 0.4))
            pygame.draw.circle(halo, (*spark_col, halo_a), (3, 3), 2)
            target.blit(halo, (spark_x - 3, spark_y - 3))
            pygame.draw.circle(target, (255, 255, 255), (spark_x, spark_y), 1)

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
