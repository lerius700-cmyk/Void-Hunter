"""Tests for BLOQUE 58.8.3: click-vs-hold 0.28s + P_WAKE delayed afterglow.

Covers:
  - PLAYER_CLICK_VS_HOLD_THRESHOLD_S == 0.28s (was 0.6s).
  - P_WAKE kind is registered in KIND_CONFIG (kind 18).
  - Particle.delay_s field is honored: a particle with delay_s > 0
    is invisible (alpha = 0) and frozen (no position change) for the
    delay window, then becomes active.
  - P_WAKE with delay_s=1.0 stays invisible for ~1 second of
    simulated time, then becomes visible and fades.
  - The propulsion wake emission uses PLAYER_PROPULSION_WAKE_DELAY_S.
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
# 1) Click-vs-hold threshold is 0.28s
# -----------------------------------------------------------------------
def test_click_hold_threshold_is_028():
    """BLOQUE 58.8.3: tightened from 0.6s to 0.28s. Sweet spot for
    human reaction time + responsive propulsion start.
    """
    from src.core.settings import PLAYER_CLICK_VS_HOLD_THRESHOLD_S
    assert PLAYER_CLICK_VS_HOLD_THRESHOLD_S == 0.28, (
        f"Expected 0.28s, got {PLAYER_CLICK_VS_HOLD_THRESHOLD_S}"
    )


def test_wake_constants_exist():
    """BLOQUE 58.8.3: wake/destello constants must be defined."""
    from src.core import settings
    assert hasattr(settings, "PLAYER_PROPULSION_WAKE_DELAY_S")
    assert hasattr(settings, "PLAYER_PROPULSION_WAKE_LIFE_S")
    assert hasattr(settings, "PLAYER_PROPULSION_WAKE_INTERVAL_S")
    assert settings.PLAYER_PROPULSION_WAKE_DELAY_S == 1.0
    assert settings.PLAYER_PROPULSION_WAKE_LIFE_S == 0.8
    assert 0.02 <= settings.PLAYER_PROPULSION_WAKE_INTERVAL_S <= 0.08


# -----------------------------------------------------------------------
# 2) P_WAKE kind is registered
# -----------------------------------------------------------------------
def test_p_wake_kind_registered():
    """BLOQUE 58.8.3/58.8.4: P_WAKE = 18. The base color is a neon
    magenta-pink (BLOQUE 58.8.4) and the base surface is a soft
    radial gradient (4 concentric circles). The actual on-screen
    appearance is a 3-particle layered burst (P_GLOW halo + P_WAKE
    body + P_SPARK core) for the "spectral neon" feel.
    """
    from src.systems.particle_engine import (
        P_WAKE, P_KIND_COUNT, KIND_CONFIG,
    )
    assert P_WAKE == 18
    assert P_KIND_COUNT == 19
    assert P_WAKE in KIND_CONFIG
    # Neon magenta-pink palette (BLOQUE 58.8.4: changed from pure
    # orange to magenta-pink for the spectral feel).
    r, g, b = KIND_CONFIG[P_WAKE].base_color
    assert r > 200 and b > 150, (
        f"P_WAKE should be neon magenta-pink (high R, high B). "
        f"Got ({r}, {g}, {b})"
    )
    # Base size should be 16 (the radial gradient is 16x16)
    assert KIND_CONFIG[P_WAKE].base_size == 16, (
        f"P_WAKE base size should be 16 for the soft gradient, got "
        f"{KIND_CONFIG[P_WAKE].base_size}"
    )


def test_player_no_longer_has_wake_timer():
    """BLOQUE 58.11: removed propulsion_wake_timer. The Tron trail
    replaces the delayed wake and is managed by the engine, not the
    Player.
    """
    from src.entities.player import Player
    p = Player()
    assert not hasattr(p, "propulsion_wake_timer"), (
        "propulsion_wake_timer should be removed in BLOQUE 58.11"
    )


# -----------------------------------------------------------------------
# 3) Particle.delay_s field behavior
# -----------------------------------------------------------------------
def test_particle_delay_keeps_invisible():
    """A particle with delay_s > 0 should be invisible and frozen for
    that duration.
    """
    from src.systems.particle_engine import (
        P_SPARK, ParticleEngine,
    )
    eng = ParticleEngine(pool_size=64)
    p = eng.emit(P_SPARK, 100.0, 100.0, vx=50.0, vy=50.0,
                 life=0.5, delay_s=1.0)
    assert p is not None
    assert p.delay_s == 1.0
    # Initial alpha is 0 (invisible) while in the delay window
    assert p._alpha == 0
    # Tick 0.4s — still in delay window
    eng.update(0.4)
    assert p.delay_s > 0.0
    assert p._alpha == 0
    # Position MUST NOT have moved (frozen during delay)
    assert p.x == 100.0
    assert p.y == 100.0
    # Velocity has not been applied either
    assert p.vx == 50.0
    assert p.vy == 50.0


def test_particle_delay_expires_correctly():
    """After delay_s reaches 0, the particle becomes visible and
    runs its normal life cycle.
    """
    from src.systems.particle_engine import (
        P_SPARK, ParticleEngine,
    )
    eng = ParticleEngine(pool_size=64)
    p = eng.emit(P_SPARK, 100.0, 100.0, vx=50.0, vy=50.0,
                 life=2.0, delay_s=0.5)
    assert p is not None
    # Tick 0.3s — still in delay window
    eng.update(0.3)
    assert p.delay_s > 0.0
    assert p._alpha == 0
    assert p.x == 100.0 and p.y == 100.0  # frozen during delay
    # Tick 0.3s more — delay just expired, particle now active
    eng.update(0.3)
    assert p.delay_s == 0.0
    assert p._alpha > 0  # visible (not necessarily 255 if fade kicked in)
    # The position should now start to update (the velocity is applied)
    # on the same frame the delay expires
    assert p.x != 100.0 or p.y != 100.0


def test_p_wake_full_lifecycle():
    """P_WAKE with 1.0s delay should stay invisible for ~1 second
    of simulated time, then appear and fade out.
    """
    from src.systems.particle_engine import P_WAKE, ParticleEngine
    eng = ParticleEngine(pool_size=64)
    p = eng.emit(P_WAKE, 50.0, 50.0,
                 life=5.0, delay_s=1.0)  # long life so fade is gradual
    assert p is not None
    assert p.kind == P_WAKE
    assert p.delay_s == 1.0
    assert p._alpha == 0  # invisible during delay
    # 0.9s of delay — still invisible
    eng.update(0.9)
    assert p.delay_s > 0.0
    assert p._alpha == 0
    # 0.2s more — delay expired, particle now active
    eng.update(0.2)
    assert p.delay_s == 0.0
    assert p._alpha > 0  # visible (full alpha with long life)
    # No motion (vx=vy=0, gravity=0)
    assert p.x == 50.0 and p.y == 50.0
    # After more time, fade should reduce alpha
    eng.update(2.0)
    assert 0 < p._alpha < 255, f"Expected fading alpha, got {p._alpha}"


# -----------------------------------------------------------------------
# 4) End-to-end: player propulsion emits the wake
# -----------------------------------------------------------------------
def test_propulsion_emits_p_wake_particle_REMOVED():
    """BLOQUE 58.11: the delayed wake emission was REMOVED. The
    Tron-style light trail replaces it. The _emit_propulsion_trail
    now only emits the main yellow/cyan thruster sparks (BLOQUE 58.8.1).

    This test is intentionally a no-op — it documents the removal.
    For the Tron trail, see tests/test_bloque_58_11.py.
    """
    from src.ui import gameplay_runtime as gpr
    import inspect
    src = inspect.getsource(gpr.GameplayRuntime._emit_propulsion_trail)
    # The wake emission was removed — P_WAKE should not be in the
    # propulsion trail source anymore.
    assert "P_WAKE" not in src, (
        "P_WAKE wake emission should be REMOVED from _emit_propulsion_trail "
        "in BLOQUE 58.11 (only Tron trail now)"
    )


# -----------------------------------------------------------------------
# 5) Regression: main propulsion trail still emits yellow sparks
# -----------------------------------------------------------------------
def test_main_trail_still_emits_sparks():
    """The main propulsion trail (yellow/cyan) must still work after
    adding the wake (BLOQUE 58.8.3 must not break BLOQUE 58.8.1).
    """
    from src.ui import gameplay_runtime as gpr
    from src.entities.player import Player
    from src.entities.player.player import PlayerState
    from src.systems.particle_engine import P_SPARK

    rt = gpr.GameplayRuntime.__new__(gpr.GameplayRuntime)
    rt._t = 0.0
    rt._player = Player()
    rt._player.state = PlayerState.PROPULSION
    rt._player.x = 100.0
    rt._player.y = 200.0
    rt._player.propulsion_trail_timer = 999.0
    rt._player.propulsion_wake_timer = 999.0

    class _RecordingEngine:
        def __init__(self) -> None:
            self.calls = []
        def emit(self, kind, x, y, **kwargs):
            self.calls.append({"kind": kind, **kwargs})
            return None
    eng = _RecordingEngine()
    rt._particles = eng

    rt._emit_propulsion_trail(1.0 / 60.0)

    # The main trail must still produce P_SPARK particles
    spark_calls = [c for c in eng.calls if c["kind"] == P_SPARK]
    assert len(spark_calls) >= 1, (
        "Main propulsion trail must still emit P_SPARK particles"
    )
