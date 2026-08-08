"""Tests for src.systems.screen_shake (BLOQUE 5)."""
from __future__ import annotations

import pytest

from src.core.settings import SHAKE_MAX_PX, TRAUMA_DECAY
from src.systems.screen_shake import ScreenShake


def test_initial_trauma_zero() -> None:
    s = ScreenShake()
    assert s.trauma == 0.0
    assert s.get_offset() == (0.0, 0.0)


def test_add_trauma_clamps_to_one() -> None:
    s = ScreenShake()
    s.add_trauma(5.0)
    assert s.trauma == 1.0


def test_add_trauma_clamps_to_zero() -> None:
    s = ScreenShake()
    s.trauma = 0.5
    s.add_trauma(-1.0)
    assert s.trauma == 0.0


def test_update_decays_trauma() -> None:
    """decay=0.88, after 1s trauma should drop substantially."""
    s = ScreenShake()
    s.trauma = 1.0
    s.update(1.0)
    # 1.0 - 0.88*1 = 0.12 (clamped to 0 if negative)
    assert 0.0 <= s.trauma < 1.0


def test_decay_88_in_10_updates() -> None:
    """Per spec: decay=0.88 → trauma baja a 0.12 en 10 updates."""
    s = ScreenShake()
    s.trauma = 1.0
    for _ in range(10):
        s.update(1.0)  # dt=1 each time, decays fast
    # 1.0 - 10*0.88 = -7.8, clamped to 0
    assert s.trauma == 0.0


def test_offset_at_max_trauma_within_max_px() -> None:
    s = ScreenShake()
    s.trauma = 1.0
    s.update(0.001)
    ox, oy = s.get_offset()
    assert -SHAKE_MAX_PX <= ox <= SHAKE_MAX_PX
    assert -SHAKE_MAX_PX <= oy <= SHAKE_MAX_PX


def test_offset_at_half_trauma_is_smaller() -> None:
    """trauma²: half trauma → quarter max offset."""
    s = ScreenShake()
    s.trauma = 0.5
    s.update(0.001)
    ox, oy = s.get_offset()
    # max for trauma=0.5 is 0.25 * 8 = 2.0 px
    assert abs(ox) <= 2.0
    assert abs(oy) <= 2.0


def test_zero_dt_noop() -> None:
    s = ScreenShake()
    s.trauma = 0.5
    s.update(0.0)
    assert s.trauma == 0.5


def test_10_shakes_clamped_to_max_one() -> None:
    """10 add_trauma(0.5) → 5.0 → clamped to 1.0."""
    s = ScreenShake()
    for _ in range(10):
        s.add_trauma(0.5)
    assert s.trauma == 1.0


def test_reset_clears_state() -> None:
    s = ScreenShake()
    s.trauma = 0.5
    s.reset()
    assert s.trauma == 0.0
    assert s.get_offset() == (0.0, 0.0)


def test_max_px_is_8_per_spec() -> None:
    """GDD: SHAKE_MAX_PX escalated 4→8."""
    assert SHAKE_MAX_PX == 8.0


def test_decay_matches_setting() -> None:
    s = ScreenShake()
    assert s.decay == TRAUMA_DECAY
    assert TRAUMA_DECAY == 0.88
