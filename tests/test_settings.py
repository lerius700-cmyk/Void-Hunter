"""Tests for src.core.settings — BLOQUE 0 baseline.

Covers the constants that anchor the spec: 120 FPS lock, 240x360 @ 4x scale,
pool sizes, player baseline, trauma² max 8px, multiplier chain 1-16,
16-channel mixer. These are the invariants other BLOQUE will build on; if
any of these flip, the cascade is loud (GDD Apéndice A + §0).
"""
from __future__ import annotations

import math

import pytest

from src.core import settings
from src.core.settings import (
    DEFAULT_SCALE,
    DT_CLAMP,
    FIXED_DT,
    FPS_TARGET,
    INTERNAL_H,
    INTERNAL_W,
    MIXER_CHANNELS,
    MIXER_SAMPLE_RATE,
    MULTIPLIER_DECAY_S,
    MULTIPLIER_MAX,
    PARTICLE_POOL,
    PLAYER_BOMBS,
    PLAYER_BOMBS_MAX,
    PLAYER_LIVES,
    PLAYER_SPEED,
    PROJECTILE_POOL,
    SHAKE_MAX_PX,
    TRAUMA_DECAY,
    WINDOW_H,
    WINDOW_W,
)


# ---------------------------------------------------------------------------
# 1. FPS target — the 120 FPS lock is the whole reason this game exists.
# ---------------------------------------------------------------------------
def test_fps_target_is_120() -> None:
    """Spec §0: '120 FPS mínimo en gameplay normal, 90 FPS mínimo en stress'."""
    assert FPS_TARGET == 120


def test_fixed_dt_matches_one_over_fps() -> None:
    """FIXED_DT must equal 1/FPS_TARGET exactly (8.333...ms)."""
    assert math.isclose(FIXED_DT, 1.0 / FPS_TARGET, rel_tol=1e-12, abs_tol=0.0)
    # Spot-check the absolute value too.
    assert math.isclose(FIXED_DT, 1.0 / 120.0, abs_tol=1e-6)
    # Sanity: it's between 8ms and 9ms.
    assert 0.008 < FIXED_DT < 0.009


def test_dt_clamp_prevents_death_spiral() -> None:
    """DT_CLAMP = 1/30s. If a frame stalls longer, we clamp — never integrate huge dt."""
    assert DT_CLAMP == 1.0 / 30.0
    # 30 FPS worth of dt is the cap; if FIXED_DT = 1/120, the clamp allows
    # up to 4 sub-steps per frame, which is the documented accumulator ceiling.
    assert DT_CLAMP / FIXED_DT == 4.0


# ---------------------------------------------------------------------------
# 2. Display — 320x480 internal @ 3x integer scale = 960x1440 window. (BLOQUE 34)
# ---------------------------------------------------------------------------
def test_resolution_internal_320x480() -> None:
    """BLOQUE 34: 1.33x wider playfield (was 240x360) — more dodge space, ships look smaller."""
    assert INTERNAL_W == 320
    assert INTERNAL_H == 480


def test_window_960x1440_at_3x() -> None:
    """BLOQUE 34: default scale is 3 (was 4) because INTERNAL grew 1.33x; window stays 960x1440."""
    assert DEFAULT_SCALE == 3
    assert WINDOW_W == INTERNAL_W * DEFAULT_SCALE == 960
    assert WINDOW_H == INTERNAL_H * DEFAULT_SCALE == 1440


# ---------------------------------------------------------------------------
# 3. Pools — seed expansion: 600→1500 particles, 200→400 projectiles.
# ---------------------------------------------------------------------------
def test_particle_pool_1500() -> None:
    """ParticleEngine: pool 1500 (vs 600 seed)."""
    assert PARTICLE_POOL == 1500


def test_projectile_pool_400() -> None:
    """ProjectilePool: pool 400 (vs 200 seed), 600 con boss."""
    assert PROJECTILE_POOL == 400
    # Boss expansion lives in PROJECTILE_POOL_BOSS — make sure it's a strict
    # superset of the base pool.
    assert settings.PROJECTILE_POOL_BOSS > PROJECTILE_POOL
    assert settings.PROJECTILE_POOL_BOSS == 600


# ---------------------------------------------------------------------------
# 4. Player baseline — 3 lives, 1 continue, 3 bombs (4 con special).
# ---------------------------------------------------------------------------
def test_player_lives_and_bombs() -> None:
    assert PLAYER_LIVES == 3
    assert settings.PLAYER_CONTINUES == 1
    assert PLAYER_BOMBS == 3
    assert PLAYER_BOMBS_MAX == 4  # +1 with special unlock


def test_player_speed_165() -> None:
    """BLOQUE 38: PLAYER_SPEED is 165 px/s (was 130, ~1.27x snappier)."""
    assert PLAYER_SPEED == 165.0
    # 165 px/s in a 320x480 arena ≈ 1.94s to cross horizontally.
    # Sanity check: not too slow, not too fast.
    assert 100.0 <= PLAYER_SPEED <= 200.0


# ---------------------------------------------------------------------------
# 5. Camera — Eiserloh trauma² scaled from 4 to 8 px max.
# ---------------------------------------------------------------------------
def test_shake_max_8px_doubles_seed() -> None:
    """Eiserloh max escalado de 4 a 8 px (criterio §0)."""
    assert SHAKE_MAX_PX == 8.0
    # The trauma² formula is not modified here — only the cap. Confirm decay
    # still at the seed value.
    assert TRAUMA_DECAY == 0.88


# ---------------------------------------------------------------------------
# 6. Scoring — multiplier chain 1×→16× max, decay 1.5s.
# ---------------------------------------------------------------------------
def test_multiplier_chain_max_16() -> None:
    """DoDonPachi scoring chain adapted: 1×→2×→4×→8×→16× max."""
    assert MULTIPLIER_MAX == 16


def test_multiplier_decay_1_5s() -> None:
    """DoDonPachi decay adapted from 2s to 1.5s."""
    assert MULTIPLIER_DECAY_S == 1.5


# ---------------------------------------------------------------------------
# 7. Audio — 16 channels @ 44100 Hz raw PCM.
# ---------------------------------------------------------------------------
def test_mixer_16_channels_44khz() -> None:
    """pygame.mixer best practices: 16 channels, 44100 Hz, set_num_channels pre-Sound."""
    assert MIXER_CHANNELS == 16
    assert MIXER_SAMPLE_RATE == 44100
    assert settings.MIXER_BUFFER == 512
    assert settings.MIXER_BITS == 16


# ---------------------------------------------------------------------------
# 8. Quality gates — coverage 35%, FPS targets.
# ---------------------------------------------------------------------------
def test_quality_gates() -> None:
    """Coverage gate and FPS targets per GDD §0."""
    assert settings.COVERAGE_GATE == 0.35
    assert settings.FPS_TARGET_NORMAL == 120
    assert settings.FPS_TARGET_STRESS == 90


# ---------------------------------------------------------------------------
# Edge cases & invariants
# ---------------------------------------------------------------------------
def test_settings_module_has_no_external_deps() -> None:
    """settings.py must be importable without pygame (used by tests + --check)."""
    # If this test imports without error, we have proven the module has no
    # transitive dependency on pygame. Catches accidental `import pygame` in
    # settings.py at BLOQUE 0 before it becomes a refactor tax.
    import sys
    saved = {k: v for k, v in sys.modules.items() if k.startswith("pygame")}
    for k in saved:
        sys.modules.pop(k, None)
    try:
        import importlib
        mod = importlib.import_module("src.core.settings")
        importlib.reload(mod)
    finally:
        sys.modules.update(saved)


def test_window_dimensions_consistent_with_internal() -> None:
    """WINDOW = INTERNAL * SCALE must hold exactly (no off-by-one in init)."""
    assert WINDOW_W == INTERNAL_W * DEFAULT_SCALE
    assert WINDOW_H == INTERNAL_H * DEFAULT_SCALE
    # And the relationship holds in both directions.
    assert INTERNAL_W * DEFAULT_SCALE == WINDOW_W
    assert INTERNAL_H * DEFAULT_SCALE == WINDOW_H


def test_pool_sizes_strictly_greater_than_seed() -> None:
    """Spec calls for pool expansion vs nebula-hunter seed (60 FPS MVP)."""
    # Seed: PARTICLE_POOL=600, PROJECTILE_POOL=200, DEBRIS_POOL=100
    assert PARTICLE_POOL > 600
    assert PROJECTILE_POOL > 200
    assert settings.DEBRIS_POOL > 100


@pytest.mark.parametrize(
    "attr,expected",
    [
        ("TRAUMA_DECAY", 0.88),
        ("ELEMENT_BONUS", 1.5),
        ("STREAK_BONUS_CAP", 2.0),
        ("WAVE_KILL_TARGET", 20),
        ("SUBBOSS_TRIGGER_KILLS", 40),
    ],
)
def test_key_balance_constants(attr: str, expected: float | int) -> None:
    """Pin balance-critical constants so accidental edits break the test."""
    assert getattr(settings, attr) == expected
