"""Tests for src.roguelike.integration (BLOQUE 57)."""
from __future__ import annotations

import pytest

from src.roguelike.integration import (
    disable_roguelike,
    enable_roguelike,
    generate_procedural_waves,
    get_active_seed,
    inject_roguelike_waves,
    is_roguelike_enabled,
)


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset roguelike state between tests."""
    disable_roguelike()
    yield
    disable_roguelike()


# ---------------------------------------------------------------------------
# 1. Enable / disable
# ---------------------------------------------------------------------------
def test_enable_with_explicit_seed() -> None:
    seed = enable_roguelike(seed=42)
    assert seed == 42
    assert is_roguelike_enabled() is True
    assert get_active_seed() == 42


def test_enable_with_default_seed() -> None:
    seed = enable_roguelike()
    assert seed > 0
    assert is_roguelike_enabled() is True


def test_disable_clears_state() -> None:
    enable_roguelike(seed=99)
    disable_roguelike()
    assert is_roguelike_enabled() is False
    assert get_active_seed() is None


# ---------------------------------------------------------------------------
# 2. Generate procedural waves
# ---------------------------------------------------------------------------
def test_generate_procedural_waves_deterministic() -> None:
    """Same seed -> same procedural waves (the core acceptance demo)."""
    enable_roguelike(seed=42)
    w1 = generate_procedural_waves(level_idx=1, num_waves=3)
    enable_roguelike(seed=42)
    w2 = generate_procedural_waves(level_idx=1, num_waves=3)
    assert w1 == w2
    assert len(w1) == 3


def test_generate_procedural_waves_different_seeds() -> None:
    enable_roguelike(seed=42)
    w1 = generate_procedural_waves(level_idx=1, num_waves=3)
    enable_roguelike(seed=99)
    w2 = generate_procedural_waves(level_idx=1, num_waves=3)
    assert w1 != w2


def test_generate_procedural_waves_format() -> None:
    enable_roguelike(seed=42)
    waves = generate_procedural_waves(level_idx=2, num_waves=4)
    assert len(waves) == 4
    for i, w in enumerate(waves):
        assert w["act"] == 2
        assert w["wave"] == i + 1
        assert w["formation"]["formation_type"] in (
            "line", "v", "arc", "staircase", "spiral",
            "hilera", "x", "diamond", "box",
        )
        assert "kill_target" in w
        assert "time_limit_s" in w


def test_inject_into_wave_manager() -> None:
    """BLOQUE 57: inject_roguelike_waves replaces the WaveManager.scripts list."""
    enable_roguelike(seed=42)

    class FakeWM:
        scripts: list = []

    wm = FakeWM()
    assert inject_roguelike_waves(wm) is True
    assert len(wm.scripts) == 6  # default num_waves


def test_inject_disabled_returns_false() -> None:
    """If roguelike mode is not enabled, inject is a no-op."""
    class FakeWM:
        scripts: list = []

    wm = FakeWM()
    assert inject_roguelike_waves(wm) is False
    assert wm.scripts == []
