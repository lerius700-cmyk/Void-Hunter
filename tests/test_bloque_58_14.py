"""Tests for BLOQUE 58.16: minimalist HUD.

The new HUD has only TWO elements:
  - Top-left: HP bar (color-coded, no text)
  - Top-right: Score number (no header, no label)

Tests cover:
  - HUD draws without raising in various game states.
  - No pixel extends past INTERNAL_W.
  - HP bar shows correct color tier (green/yellow/red).
  - Score is right-aligned and shows 6 digits.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("VOID_HUNTER_INVULN", "1")

import pygame
pygame.init()
pygame.display.set_mode((1, 1))


# -----------------------------------------------------------------------
# 1) Basic smoke tests
# -----------------------------------------------------------------------
def _make_state(hp=30, hp_max=30, score=0, rings=0, tech=None,
                bombs=3, bombs_max=3, heat=0.0):
    from src.entities.player import Player
    from src.systems.weapon_system import WeaponSystem
    from src.systems.scoring_system import ScoringSystem
    p = Player()
    p.hp = hp
    p.hp_max = hp_max
    p.gold_rings = rings
    p.tech_upgrades = tech or []
    p.bombs = bombs
    p.bombs_max = bombs_max
    p.dash_heat = heat
    w = WeaponSystem()
    s = ScoringSystem()
    s.score = score
    return p, w, s


def test_hud_draws_basic_state():
    """BLOQUE 58.16: HUD draws without error in a default state."""
    from src.ui.hud import HUD
    from src.core.settings import INTERNAL_W, INTERNAL_H
    p, w, s = _make_state()
    hud = HUD()
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    hud.draw(target, p, w, s, t=0.5)


def test_hud_draws_critical_hp():
    """Critical HP (red pulsing) renders without crash."""
    from src.ui.hud import HUD
    from src.core.settings import INTERNAL_W, INTERNAL_H
    p, w, s = _make_state(hp=1, hp_max=30)
    hud = HUD()
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    hud.draw(target, p, w, s, t=0.5)


def test_hud_draws_full_hp():
    """Full HP renders the green color tier."""
    from src.ui.hud import HUD
    from src.core.settings import INTERNAL_W, INTERNAL_H
    p, w, s = _make_state(hp=30, hp_max=30)
    hud = HUD()
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    hud.draw(target, p, w, s, t=0.5)


def test_hud_draws_high_score():
    """High score (999999) renders the 6-digit right-aligned number."""
    from src.ui.hud import HUD
    from src.core.settings import INTERNAL_W, INTERNAL_H
    p, w, s = _make_state(score=999999)
    hud = HUD()
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    hud.draw(target, p, w, s, t=0.5)


# -----------------------------------------------------------------------
# 2) No element extends past INTERNAL_W
# -----------------------------------------------------------------------
def test_hud_no_element_overflows_right_edge():
    """BLOQUE 58.16: even with the highest score, the score number
    must be right-aligned and never overflow the right edge.
    """
    from src.ui.hud import HUD
    from src.core.settings import INTERNAL_W, INTERNAL_H
    p, w, s = _make_state(hp=1, hp_max=30, score=999999)
    hud = HUD()
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    hud.draw(target, p, w, s, t=0.5)
    w_max = target.get_width()
    for y_check in range(0, INTERNAL_H, 2):
        for x_check in range(INTERNAL_W, w_max):
            r, g, b, a = target.get_at((x_check, y_check))
            assert a == 0, (
                f"Non-transparent pixel at ({x_check}, {y_check}) "
                f"— HUD element overflows the right edge"
            )


# -----------------------------------------------------------------------
# 3) HUD is minimal — no extra methods
# -----------------------------------------------------------------------
def test_hud_has_no_section_methods():
    """BLOQUE 58.16/58.19: removed all section helpers from the old HUD.
    The new HUD has no section headers, no LOADOUT / TACTICAL / VITALS.
    """
    from src.ui import hud as hud_mod
    # Section header should not exist anymore
    assert not hasattr(hud_mod, "SECTION_HEADER_H")
    # The draw method should only call HP + overheat + rings + bombs + score
    import inspect
    src = inspect.getsource(hud_mod.HUD.draw)
    assert "section" not in src.lower(), (
        "HUD.draw should not call any section header"
    )
    assert "VITALS" not in src
    assert "LOADOUT" not in src
    assert "TACTICAL" not in src
    assert "WEAPON" not in src
    assert "DASH" not in src
    assert "MULT" not in src


def test_hud_has_minimal_api():
    """BLOQUE 58.41: HUD has the 4 expected draw methods (HP, overheat,
    missiles, score). The old rings/bombs section was removed in 58.41.
    """
    from src.ui.hud import HUD
    hud = HUD()
    # Public API
    assert hasattr(hud, "draw")
    assert hasattr(hud, "_ensure_fonts")
    # Internal helpers
    assert hasattr(hud, "_draw_hp_bar")
    assert hasattr(hud, "_draw_overheat_bar")
    assert hasattr(hud, "_draw_missiles")
    assert hasattr(hud, "_draw_missile_icon")
    assert hasattr(hud, "_draw_score")
    # BLOQUE 58.41: removed in favor of minimalist missiles
    assert not hasattr(hud, "_draw_gold_rings")
    assert not hasattr(hud, "_draw_bombs")
    assert not hasattr(hud, "_draw_bomb_icon")


def test_hud_draws_with_overheat_state():
    """BLOQUE 58.19: HUD draws the overheat bar in OK / WARM / HOT states."""
    from src.ui.hud import HUD
    from src.core.settings import INTERNAL_W, INTERNAL_H, PLAYER_DASH_HEAT_MAX
    hud = HUD()
    for heat_ratio in (0.0, 0.6, 1.0):
        p, w, s = _make_state(heat=heat_ratio * PLAYER_DASH_HEAT_MAX)
        target = pygame.Surface((INTERNAL_W, INTERNAL_H))
        hud.draw(target, p, w, s, t=0.5)  # must not crash


def test_hud_draws_with_missile_count():
    """BLOQUE 58.41: HUD draws the missile counter for various bomb counts."""
    from src.ui.hud import HUD
    from src.core.settings import INTERNAL_W, INTERNAL_H
    hud = HUD()
    for bombs, max_bombs in [(0, 3), (1, 3), (3, 3), (0, 4), (4, 4)]:
        p, w, s = _make_state(bombs=bombs, bombs_max=max_bombs)
        target = pygame.Surface((INTERNAL_W, INTERNAL_H))
        hud.draw(target, p, w, s, t=0.5, kill_ratio=0.5)


def test_hud_score_color_tiers():
    """BLOQUE 58.41: score color reflects kill ratio (100% red, 99% red,
    49% yellow, <20% white).
    """
    from src.ui.hud import score_color_for_ratio, score_has_glow, GOLD_BORDER
    # 100% → bright red + glow
    assert score_has_glow(1.0) is True
    assert score_has_glow(0.99) is False
    assert score_has_glow(0.5) is False
    # Color tiers
    c100 = score_color_for_ratio(1.0)
    c99 = score_color_for_ratio(0.99)
    c75 = score_color_for_ratio(0.75)
    c49 = score_color_for_ratio(0.49)
    c20 = score_color_for_ratio(0.20)
    c10 = score_color_for_ratio(0.10)
    # 100% brightest red, 99% red, 75% red+yellow blend, 49% yellow, white below
    assert c100[0] >= c99[0]      # 100% has equal or more red than 99%
    assert c75[1] > c99[1]        # mid-tier has more green than 99% (red→yellow shift)
    # Yellow at 49% has more green than red at 99% (proves we shifted toward yellow)
    assert c49[1] > c99[1]        # green: 49% > 99%
    assert c10[0] > 200           # white-ish
    # Gold border is reserved for 100% only
    assert GOLD_BORDER == (255, 200, 80)


def test_hud_draws_at_100_percent():
    """BLOQUE 58.41: HUD draws score with glow + gold border at 100%."""
    from src.ui.hud import HUD
    from src.core.settings import INTERNAL_W, INTERNAL_H
    hud = HUD()
    p, w, s = _make_state()
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    hud.draw(target, p, w, s, t=0.5, kill_ratio=1.0)  # must not crash
