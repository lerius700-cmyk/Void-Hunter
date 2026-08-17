"""HUD: top bar (lives, score, wave, boss HP) + bottom bar (weapon selector, enemies).

The bottom bar is the new bit: 10 weapon icons in a row, with the
active one highlighted, plus the weapon name to the left and the
enemy counter to the right. The icons come from the single-frame
laser sprite cache passed in by GameplayScene (laser_01..10), so the
HUD stays in sync with whichever weapon the player is holding.
"""
from __future__ import annotations

import pygame

from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


class Hud:
    TOP_BAR_H = 16
    BOTTOM_BAR_H = 22
    COLOR_BG = (10, 15, 31)
    COLOR_BG_DARK = (6, 9, 20)
    COLOR_BORDER = (40, 50, 80)
    COLOR_TEXT = (240, 240, 240)
    COLOR_TEXT_DIM = (160, 160, 180)
    COLOR_HEART = (230, 70, 90)
    COLOR_HP = (90, 220, 90)
    COLOR_HP_BG = (40, 60, 40)
    COLOR_BOSS_HP = (220, 80, 80)
    COLOR_WAVE = (255, 220, 100)
    COLOR_ENEMIES = (180, 180, 220)
    COLOR_ACCENT = (255, 240, 100)
    COLOR_WEAPON_BG = (24, 28, 50)
    COLOR_WEAPON_ACTIVE_BORDER = (255, 240, 100)
    COLOR_WEAPON_ACTIVE_BG = (60, 55, 30)
    WEAPON_KEYS_LABEL = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")

    def __init__(self) -> None:
        self.player = None
        self.score: int = 0
        self.wave_n: int = 0
        self.wave_total: int = 0
        self.boss = None
        self.enemies_n: int = 0
        self.enemies_total: int = 0
        self.current_weapon: int = 0
        # Dict of laser_NN -> pygame.Surface (single-frame, NOT
        # animated). The GameplayScene's _laser_sprites dict is
        # passed in via set_weapon_catalog() so the HUD shows the
        # exact same sprite as the bullet currently in flight.
        self._weapon_sprites: dict = {}
        self._weapon_names: tuple = ()
        self._font = None
        self._small_font = None
        self._tiny_font = None

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

    def set_weapon_catalog(self, weapon_sprites: dict, names: tuple,
                           current: int) -> None:
        """Wire the HUD to the single-frame laser sprite cache the
        scene uses, plus the human-readable weapon names. Called from
        GameplayScene.on_enter.

        `weapon_sprites` maps `laser_NN` -> pygame.Surface. The HUD
        blits these directly (no animation) since the per-weapon VFX
        is applied in the bullet draw code, not in the selector strip.
        """
        self._weapon_sprites = weapon_sprites
        self._weapon_names = names
        self.current_weapon = current

    def set_current_weapon(self, idx: int) -> None:
        self.current_weapon = idx

    def _ensure_fonts(self) -> None:
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", 12, bold=True)
            self._small_font = pygame.font.SysFont("monospace", 9, bold=True)
            self._tiny_font = pygame.font.SysFont("monospace", 7)

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        self._draw_top_bar(surface)
        self._draw_bottom_bar(surface)

    # ------------------------------------------------------------------
    # Top bar: lives, score, wave, boss HP
    # ------------------------------------------------------------------
    def _draw_top_bar(self, surface: pygame.Surface) -> None:
        # Solid background + bottom border for separation.
        top_rect = pygame.Rect(0, 0, INTERNAL_W, self.TOP_BAR_H)
        pygame.draw.rect(surface, self.COLOR_BG, top_rect)
        pygame.draw.line(surface, self.COLOR_BORDER,
                         (0, self.TOP_BAR_H), (INTERNAL_W, self.TOP_BAR_H), 1)
        if self.player is not None:
            self._draw_lives(surface)
        self._draw_score(surface)
        if self.wave_total > 0:
            self._draw_wave(surface)
        if self.boss is not None and self.boss.alive:
            self._draw_boss_hp(surface)

    def _draw_lives(self, surface: pygame.Surface) -> None:
        # Heart icons (small filled circles in a row).
        for i in range(self.player.lives):
            cx = 5 + i * 9
            cy = self.TOP_BAR_H // 2
            # Soft glow ring.
            pygame.draw.circle(surface, (255, 100, 120), (cx, cy), 4)
            pygame.draw.circle(surface, self.COLOR_HEART, (cx, cy), 3)

    def _draw_score(self, surface: pygame.Surface) -> None:
        # "PTS 000000" centered. Slightly larger font + dim "PTS" label.
        label = self._small_font.render("PTS", False, self.COLOR_TEXT_DIM)
        num = self._font.render(f"{self.score:06d}", False, self.COLOR_TEXT)
        total_w = label.get_width() + 4 + num.get_width()
        x = INTERNAL_W // 2 - total_w // 2
        surface.blit(label, (x, self.TOP_BAR_H // 2 - label.get_height() // 2))
        surface.blit(num, (x + label.get_width() + 4,
                           self.TOP_BAR_H // 2 - num.get_height() // 2))

    def _draw_wave(self, surface: pygame.Surface) -> None:
        wave_surf = self._small_font.render(
            f"WAVE {self.wave_n}/{self.wave_total}", False, self.COLOR_WAVE,
        )
        surface.blit(wave_surf, (INTERNAL_W // 2 + 50, 3))

    def _draw_boss_hp(self, surface: pygame.Surface) -> None:
        bar_w = 84
        bar_h = 8
        bar_x = INTERNAL_W - bar_w - 4
        bar_y = 4
        # Label
        label = self._tiny_font.render("BOSS", False, self.COLOR_BOSS_HP)
        surface.blit(label, (bar_x, bar_y - 1))
        # Background
        pygame.draw.rect(surface, self.COLOR_HP_BG,
                         (bar_x, bar_y + 7, bar_w, bar_h))
        pct = max(0.0, self.boss.hp / self.boss.max_hp)
        pygame.draw.rect(surface, self.COLOR_BOSS_HP,
                         (bar_x, bar_y + 7, int(bar_w * pct), bar_h))
        # Ticks on the bar for readability.
        for t in range(1, 4):
            tx = bar_x + int(bar_w * t / 4)
            pygame.draw.line(surface, self.COLOR_HP_BG,
                             (tx, bar_y + 7), (tx, bar_y + 7 + bar_h), 1)

    # ------------------------------------------------------------------
    # Bottom bar: weapon selector (10 icons) + enemy counter
    # ------------------------------------------------------------------
    def _draw_bottom_bar(self, surface: pygame.Surface) -> None:
        bot_y = INTERNAL_H - self.BOTTOM_BAR_H
        bot_rect = pygame.Rect(0, bot_y, INTERNAL_W, self.BOTTOM_BAR_H)
        pygame.draw.rect(surface, self.COLOR_BG, bot_rect)
        pygame.draw.line(surface, self.COLOR_BORDER,
                         (0, bot_y), (INTERNAL_W, bot_y), 1)
        # Weapon name on the left (e.g. "PINK HEART").
        if self._weapon_names and self.player is not None:
            self._draw_weapon_name(surface, bot_y)
        # 10-icon selector in the center.
        if self._weapon_sprites is not None:
            self._draw_weapon_strip(surface, bot_y)
        # Enemy counter on the right.
        if self.enemies_total > 0:
            self._draw_enemy_counter(surface, bot_y)

    def _draw_weapon_name(self, surface: pygame.Surface, bot_y: int) -> None:
        idx = min(self.current_weapon, len(self._weapon_names) - 1)
        name = self._weapon_names[idx]
        label = self._small_font.render(name, False, self.COLOR_ACCENT)
        surface.blit(label, (6, bot_y + self.BOTTOM_BAR_H // 2
                            - label.get_height() // 2))

    def _draw_weapon_strip(self, surface: pygame.Surface, bot_y: int) -> None:
        # 10 icons in a centered row, each 14x14 with 2px gaps.
        icon_size = 14
        gap = 2
        total_w = 10 * icon_size + 9 * gap
        x0 = INTERNAL_W // 2 - total_w // 2
        y0 = bot_y + (self.BOTTOM_BAR_H - icon_size) // 2
        for i in range(10):
            ix = x0 + i * (icon_size + gap)
            iy = y0
            active = (i == self.current_weapon)
            # Background slot.
            slot_color = (self.COLOR_WEAPON_ACTIVE_BG if active
                          else self.COLOR_WEAPON_BG)
            pygame.draw.rect(surface, slot_color,
                             (ix, iy, icon_size, icon_size))
            # Border (bright yellow when active, dim otherwise).
            border = (self.COLOR_WEAPON_ACTIVE_BORDER if active
                      else self.COLOR_BORDER)
            pygame.draw.rect(surface, border,
                             (ix, iy, icon_size, icon_size), 1)
            # Icon: single-frame laser_NN, scaled up to fit the slot.
            weapon_name = f"laser_{i + 1:02d}"
            src = self._weapon_sprites.get(weapon_name)
            if src is not None:
                if src.get_width() != icon_size or src.get_height() != icon_size:
                    src = pygame.transform.scale(src, (icon_size, icon_size))
                # Center the sprite in the slot.
                bx = ix + (icon_size - src.get_width()) // 2
                by = iy + (icon_size - src.get_height()) // 2
                surface.blit(src, (bx, by))
            # Key label below (1-9, 0) when active.
            if active:
                key_label = self._tiny_font.render(
                    self.WEAPON_KEYS_LABEL[i], False, self.COLOR_ACCENT,
                )
                surface.blit(key_label,
                             (ix + icon_size // 2 - key_label.get_width() // 2,
                              iy + icon_size + 1))

    def _draw_enemy_counter(self, surface: pygame.Surface, bot_y: int) -> None:
        en_surf = self._small_font.render(
            f"ENEMIES {self.enemies_n}/{self.enemies_total}",
            False, self.COLOR_ENEMIES,
        )
        surface.blit(
            en_surf,
            (INTERNAL_W - en_surf.get_width() - 6,
             bot_y + self.BOTTOM_BAR_H // 2 - en_surf.get_height() // 2),
        )
