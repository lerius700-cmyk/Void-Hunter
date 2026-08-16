"""HUD: top bar (HP, score, wave, boss HP) + bottom bar (lives, score, enemies)."""
from __future__ import annotations

import pygame

from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


class Hud:
    TOP_BAR_H = 14
    BOTTOM_BAR_H = 14
    COLOR_BG = (10, 15, 31)
    COLOR_TEXT = (240, 240, 240)
    COLOR_HEART = (220, 60, 80)
    COLOR_HP = (90, 220, 90)
    COLOR_HP_BG = (40, 60, 40)
    COLOR_BOSS_HP = (220, 80, 80)
    COLOR_WAVE = (255, 220, 100)
    COLOR_ENEMIES = (180, 180, 220)

    def __init__(self) -> None:
        self.player = None
        self.score: int = 0
        self.wave_n: int = 0
        self.wave_total: int = 0
        self.boss = None
        self.enemies_n: int = 0
        self.enemies_total: int = 0
        self._font = None
        self._small_font = None

    def set_player(self, player) -> None:
        self.player = player

    def set_score(self, n: int) -> None:
        self.score = n

    def set_wave(self, n: int, total: int) -> None:
        self.wave_n = n
        self.wave_total = total

    def set_boss(self, boss) -> None:
        self.boss = boss

    def set_enemies_remaining(self, n: int, total: int) -> None:
        self.enemies_n = n
        self.enemies_total = total

    def _ensure_fonts(self) -> None:
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", 10, bold=True)
            self._small_font = pygame.font.SysFont("monospace", 8)

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        top_rect = pygame.Rect(0, 0, INTERNAL_W, self.TOP_BAR_H)
        pygame.draw.rect(surface, self.COLOR_BG, top_rect)
        if self.player is not None:
            for i in range(self.player.lives):
                cx = 4 + i * 8
                pygame.draw.circle(surface, self.COLOR_HEART, (cx + 3, 7), 3)
        score_surf = self._font.render(f"{self.score:>6}", False, self.COLOR_TEXT)
        surface.blit(score_surf, (INTERNAL_W // 2 - score_surf.get_width() // 2, 2))
        if self.wave_total > 0:
            wave_surf = self._small_font.render(
                f"WAVE {self.wave_n}/{self.wave_total}", False, self.COLOR_WAVE
            )
            surface.blit(wave_surf, (INTERNAL_W // 2 + 40, 3))
        if self.boss is not None and self.boss.alive:
            bar_w = 80
            bar_h = 6
            bar_x = INTERNAL_W - bar_w - 4
            bar_y = 4
            pygame.draw.rect(surface, self.COLOR_HP_BG, (bar_x, bar_y, bar_w, bar_h))
            pct = self.boss.hp / self.boss.max_hp
            pygame.draw.rect(surface, self.COLOR_BOSS_HP,
                             (bar_x, bar_y, int(bar_w * pct), bar_h))
        bot_rect = pygame.Rect(0, INTERNAL_H - self.BOTTOM_BAR_H, INTERNAL_W, self.BOTTOM_BAR_H)
        pygame.draw.rect(surface, self.COLOR_BG, bot_rect)
        if self.player is not None:
            lives_surf = self._small_font.render(
                f"LIVES {self.player.lives}", False, self.COLOR_HEART
            )
            surface.blit(lives_surf, (4, INTERNAL_H - self.BOTTOM_BAR_H + 3))
        if self.enemies_total > 0:
            en_surf = self._small_font.render(
                f"ENEMIES {self.enemies_n}/{self.enemies_total}", False, self.COLOR_ENEMIES
            )
            surface.blit(en_surf, (INTERNAL_W - en_surf.get_width() - 4,
                                   INTERNAL_H - self.BOTTOM_BAR_H + 3))
