"""Tests for src.ui.hud — HUD + damage popup (BLOQUE 15)."""
from __future__ import annotations

import pytest
import pygame

from src.entities.player import Player
from src.systems.scoring_system import ScoringSystem
from src.systems.weapon_system import WeaponPath, WeaponSystem
from src.ui.hud import HUD, DamagePopup, DamagePopupPool


@pytest.fixture
def hud() -> HUD:
    return HUD()


@pytest.fixture
def display() -> pygame.Surface:
    return pygame.Surface((240, 360), pygame.SRCALPHA)


@pytest.fixture
def player() -> Player:
    return Player()


@pytest.fixture
def weapon() -> WeaponSystem:
    return WeaponSystem()


@pytest.fixture
def scoring() -> ScoringSystem:
    return ScoringSystem()


# ---------------------------------------------------------------------------
# 1. HUD draws without crash
# ---------------------------------------------------------------------------
def test_hud_draw_does_not_crash(
    hud: HUD, display: pygame.Surface,
    player: Player, weapon: WeaponSystem, scoring: ScoringSystem,
) -> None:
    hud.draw(display, player, weapon, scoring)


def test_hud_works_with_low_hp(
    hud: HUD, display: pygame.Surface,
    player: Player, weapon: WeaponSystem, scoring: ScoringSystem,
) -> None:
    player.hp = 1
    hud.draw(display, player, weapon, scoring)


def test_hud_works_at_max_multiplier(
    hud: HUD, display: pygame.Surface,
    player: Player, weapon: WeaponSystem, scoring: ScoringSystem,
) -> None:
    for _ in range(10):
        scoring.on_kill(50)
    assert scoring.multiplier == 16
    hud.draw(display, player, weapon, scoring)


# ---------------------------------------------------------------------------
# 2. Damage popup pool
# ---------------------------------------------------------------------------
def test_popup_pool_default_size_32() -> None:
    pool = DamagePopupPool()
    assert pool._pool.size == 32


def test_popup_spawn_returns_popup() -> None:
    pool = DamagePopupPool()
    p = pool.spawn(100.0, 100.0, "+500", (120, 255, 120))
    assert p is not None
    assert p.active
    assert p.x == 100.0
    assert p.text == "+500"


def test_popup_color_by_milestone() -> None:
    pool = DamagePopupPool()
    # White for normal
    p1 = pool.spawn(0, 0, "+50")
    assert p1.color == (255, 255, 255)
    # Green for +500
    p2 = pool.spawn(0, 0, "+500", (120, 255, 120))
    assert p2.color == (120, 255, 120)
    # Gold for +1000+
    p3 = pool.spawn(0, 0, "+1000", (255, 180, 40))
    assert p3.color == (255, 180, 40)


def test_popup_life_decreases() -> None:
    pool = DamagePopupPool()
    p = pool.spawn(0, 0, "+50")
    pool.update(0.5)
    assert p.life == 0.5


def test_popup_expires() -> None:
    pool = DamagePopupPool()
    p = pool.spawn(0, 0, "+50")
    pool.update(2.0)
    assert not p.active


def test_popup_floats_upward() -> None:
    pool = DamagePopupPool()
    p = pool.spawn(100.0, 100.0, "+500")
    initial_y = p.y
    pool.update(0.1)
    assert p.y < initial_y  # floats up


def test_popup_pool_exhaustion() -> None:
    pool = DamagePopupPool(capacity=4)
    for _ in range(4):
        assert pool.spawn(0, 0, "+50") is not None
    assert pool.spawn(0, 0, "+50") is None


def test_popup_pool_release_all() -> None:
    pool = DamagePopupPool()
    for _ in range(5):
        pool.spawn(0, 0, "+50")
    assert pool.active_count == 5
    pool.release_all()
    assert pool.active_count == 0


def test_popup_draw_does_not_crash() -> None:
    pool = DamagePopupPool()
    pool.spawn(50, 50, "+500", (120, 255, 120))
    pool.draw(display := pygame.Surface((240, 360), pygame.SRCALPHA))


# ---------------------------------------------------------------------------
# 3. Multiplier chain colors
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kills,expected_mult", [
    (0, 1),
    (1, 2),
    (2, 4),
    (3, 8),
    (4, 16),
    (10, 16),
])
def test_multiplier_progression(kills: int, expected_mult: int) -> None:
    s = ScoringSystem()
    for _ in range(kills):
        s.on_kill(50)
    assert s.multiplier == expected_mult


# ---------------------------------------------------------------------------
# 4. HUD initialization
# ---------------------------------------------------------------------------
def test_hud_init_lazy_fonts(hud: HUD) -> None:
    """First draw initializes fonts lazily."""
    assert hud.initialized is False
    hud._ensure_fonts()
    assert hud.initialized is True
