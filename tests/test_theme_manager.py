"""Tests for src.systems.theme_manager (BLOQUE 12)."""
from __future__ import annotations

import pytest

from src.systems.theme_manager import THEME_FADE_FRAMES, ThemeManager
from src.utils.palette import THEME_NAMES


@pytest.fixture
def tm() -> ThemeManager:
    return ThemeManager()


# ---------------------------------------------------------------------------
# 1. 6 themes
# ---------------------------------------------------------------------------
def test_six_themes_available() -> None:
    assert len(THEME_NAMES) == 6


def test_all_expected_themes_present() -> None:
    assert "blue_void" in THEME_NAMES
    assert "pink_void" in THEME_NAMES
    assert "mars" in THEME_NAMES
    assert "teal" in THEME_NAMES
    assert "purple_dusk" in THEME_NAMES
    assert "gold_amber" in THEME_NAMES


# ---------------------------------------------------------------------------
# 2. Fade is 30 frames
# ---------------------------------------------------------------------------
def test_fade_duration_is_30_frames() -> None:
    assert THEME_FADE_FRAMES == 30


# ---------------------------------------------------------------------------
# 3. Initial state
# ---------------------------------------------------------------------------
def test_initial_theme_is_blue_void(tm: ThemeManager) -> None:
    assert tm.current_name == "blue_void"
    assert tm.target_name == "blue_void"
    assert tm.fading is False


# ---------------------------------------------------------------------------
# 4. set_theme
# ---------------------------------------------------------------------------
def test_set_theme_starts_fade(tm: ThemeManager) -> None:
    tm.set_theme("mars")
    assert tm.fading is True
    assert tm.target_name == "mars"
    assert tm.current_name == "blue_void"  # not yet committed


def test_set_theme_to_unknown_noop(tm: ThemeManager) -> None:
    tm.set_theme("nonexistent")
    assert tm.fading is False


def test_set_theme_to_same_noop(tm: ThemeManager) -> None:
    tm.set_theme("blue_void")
    assert tm.fading is False


# ---------------------------------------------------------------------------
# 5. Fade progress
# ---------------------------------------------------------------------------
def test_fade_completes_after_30_frames(tm: ThemeManager) -> None:
    tm.set_theme("mars")
    for _ in range(THEME_FADE_FRAMES):
        tm.update()
    assert tm.fading is False
    assert tm.current_name == "mars"
    assert tm.target_name == "mars"


def test_fade_progress_advances(tm: ThemeManager) -> None:
    tm.set_theme("mars")
    for _ in range(15):
        tm.update()
    assert 0.4 < tm.progress < 0.6  # ~50% through


def test_fade_progress_full_when_not_fading(tm: ThemeManager) -> None:
    assert tm.progress == 1.0


# ---------------------------------------------------------------------------
# 6. Reset
# ---------------------------------------------------------------------------
def test_reset_returns_to_blue_void(tm: ThemeManager) -> None:
    tm.set_theme("mars")
    for _ in range(THEME_FADE_FRAMES):
        tm.update()
    tm.reset()
    assert tm.current_name == "blue_void"
    assert tm.fading is False


# ---------------------------------------------------------------------------
# 7. Theme data accessors
# ---------------------------------------------------------------------------
def test_get_current_returns_theme_dict(tm: ThemeManager) -> None:
    theme = tm.get_current()
    assert "bg" in theme
    assert "nebula" in theme
    assert "accent" in theme


def test_get_target_during_fade(tm: ThemeManager) -> None:
    tm.set_theme("mars")
    target = tm.get_target()
    assert target["accent"] == (255, 180, 80)  # mars accent


# ---------------------------------------------------------------------------
# 8. Theme change is observable during fade
# ---------------------------------------------------------------------------
def test_fade_state_persists_until_complete(tm: ThemeManager) -> None:
    tm.set_theme("teal")
    for _ in range(10):
        tm.update()
    # Mid-fade: still blue_void → teal in progress
    assert tm.fading is True
    assert tm.current_name == "blue_void"
    assert tm.target_name == "teal"
    # Complete
    for _ in range(THEME_FADE_FRAMES):
        tm.update()
    assert tm.fading is False
    assert tm.current_name == "teal"
