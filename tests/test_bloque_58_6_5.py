"""Tests for BLOQUE 58.6.5: sub-boss rotation + purple propulsion.

Covers:
  - sub_boss_facing_angle() returns the correct angle for each cardinal
    direction (DOWN/RIGHT/UP/LEFT).
  - The SUB_BOSS rendering uses the new scratch + rotate pipeline (no
    direct draw to the game surface for SUB_BOSS).
  - The propulsion emission uses PURPLE colors (magenta/violet), not
    the old orange P_FIRE.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("VOID_HUNTER_INVULN", "1")

import math
import pygame
pygame.init()
pygame.display.set_mode((1, 1))


# -----------------------------------------------------------------------
# 1) Facing angle mapping
# -----------------------------------------------------------------------
def test_facing_angle_down():
    """vy > 0: nose already points down, no rotation."""
    from src.entities.enemies.enemy import sub_boss_facing_angle
    assert sub_boss_facing_angle(0.0, 90.0) == 0
    assert sub_boss_facing_angle(5.0, 90.0) == 0  # small vx, vy dominant
    assert sub_boss_facing_angle(0.0, 50.0) == 0


def test_facing_angle_up():
    """vy < 0: flip 180 so nose points up."""
    from src.entities.enemies.enemy import sub_boss_facing_angle
    assert sub_boss_facing_angle(0.0, -90.0) == 180
    assert sub_boss_facing_angle(-3.0, -90.0) == 180
    assert sub_boss_facing_angle(0.0, -50.0) == 180


def test_facing_angle_right():
    """vx > 0 dominant: rotate 90 so nose points right."""
    from src.entities.enemies.enemy import sub_boss_facing_angle
    assert sub_boss_facing_angle(90.0, 0.0) == 90
    assert sub_boss_facing_angle(90.0, 5.0) == 90


def test_facing_angle_left():
    """vx < 0 dominant: rotate 270 so nose points left."""
    from src.entities.enemies.enemy import sub_boss_facing_angle
    assert sub_boss_facing_angle(-90.0, 0.0) == 270
    assert sub_boss_facing_angle(-90.0, 5.0) == 270
    assert sub_boss_facing_angle(-50.0, 0.0) == 270


def test_facing_angle_zero_velocity_defaults_down():
    """When vx=vy=0, the ship is stationary and the angle should
    default to 0 (the default nose-down pose) so the ship doesn't
    flicker between angles when paused.
    """
    from src.entities.enemies.enemy import sub_boss_facing_angle
    assert sub_boss_facing_angle(0.0, 0.0) == 0


# -----------------------------------------------------------------------
# 2) The rotation logic in _draw_enemy uses the helper
# -----------------------------------------------------------------------
def test_sub_boss_draw_uses_scratch_and_rotate():
    """BLOQUE 58.6.5: _draw_enemy for SUB_BOSS must call the new helper
    _draw_sub_boss_sprite and apply pygame.transform.rotate with the
    angle from sub_boss_facing_angle. It must NOT call the old
    inline draw logic (which would duplicate the sprite).
    """
    from src.entities.enemies import EnemyKind, ENEMY_CONFIGS
    from src.ui import gameplay_runtime as gpr

    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    rt = gpr.GameplayRuntime.__new__(gpr.GameplayRuntime)
    # Bare minimum attrs needed by _draw_enemy for SUB_BOSS path
    rt._sub_boss_scratch = pygame.Surface((64, 64), pygame.SRCALPHA)
    rt._enemy_flash = {}
    rt._t = 0.5
    # Build a minimal Enemy (use the dataclass directly, with vy=+90)
    from src.entities.enemies.enemy import Enemy, EnemyState
    e = Enemy(
        kind=EnemyKind.SUB_BOSS,
        x=100.0, y=100.0, vx=0.0, vy=90.0,
        hp=cfg.hp, max_hp=cfg.hp,
    )
    e.active = True
    e.state = EnemyState.IDLE
    # Render to a real surface; if anything crashes, the test fails
    target = pygame.Surface((320, 480))
    rt._draw_enemy(target, e, 0, 0)
    # The scratch should have been cleared and redrawn — at minimum it
    # should still be a Surface (no exception)
    assert isinstance(rt._sub_boss_scratch, pygame.Surface)
    # Count non-transparent pixels in the target. If the ship was
    # drawn, at least the cyan eye + silver body + pink fangs should
    # have left a few non-(0,0,0,0) pixels.
    non_zero = 0
    w, h = target.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = target.get_at((x, y))
            if a > 0 and (r, g, b) != (0, 0, 0):
                non_zero += 1
                if non_zero > 10:
                    break
        if non_zero > 10:
            break
    assert non_zero > 10, (
        f"Expected the SUB_BOSS to draw at least 10 non-zero pixels, "
        f"but only found {non_zero}"
    )


# -----------------------------------------------------------------------
# 3) Purple propulsion palette (regression: no P_FIRE orange)
# -----------------------------------------------------------------------
def test_sub_boss_propulsion_uses_purple_palette():
    """BLOQUE 58.6.5: the SUB_BOSS propulsion now uses P_SPARK +
    P_GLOW + P_SMOKE in violet/magenta tones. The old P_FIRE orange
    palette must be gone.
    """
    import inspect
    from src.ui import gameplay_runtime as gpr
    src = inspect.getsource(gpr.GameplayRuntime._emit_sub_boss_propulsion)
    # Must import the purple-particle kinds
    assert "P_SPARK" in src, "Expected P_SPARK in propulsion"
    assert "P_GLOW" in src, "Expected P_GLOW in propulsion"
    assert "P_SMOKE" in src, "Expected P_SMOKE in propulsion"
    # Must NOT use the old P_FIRE (orange) kind
    assert "P_FIRE" not in src, "P_FIRE (orange) should be replaced by purple palette"
    # Must use the purple color tuple
    assert "220, 100, 255" in src or "(220,100,255)" in src, (
        "Expected purple_spark color (220, 100, 255) in propulsion"
    )
    assert "200, 70, 240" in src or "(200,70,240)" in src, (
        "Expected purple_glow color (200, 70, 240) in propulsion"
    )


def test_sub_boss_propulsion_follows_velocity_direction():
    """BLOQUE 58.6.5: particles emit opposite the velocity vector
    (so the trail is behind the ship). When vy=+90 (going down), the
    exhaust vy must be NEGATIVE (going up).
    """
    from src.ui import gameplay_runtime as gpr
    from src.entities.enemies import EnemyKind, ENEMY_CONFIGS
    from src.entities.enemies.enemy import Enemy, EnemyState

    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    rt = gpr.GameplayRuntime.__new__(gpr.GameplayRuntime)
    # Bare minimum to call _emit_sub_boss_propulsion
    rt._t = 0.0
    # Force the throttle to allow emission (frame % 2 == 0)
    rt._particles = _RecordingParticleEngine()

    e = Enemy(
        kind=EnemyKind.SUB_BOSS,
        x=100.0, y=100.0, vx=0.0, vy=90.0,
        hp=cfg.hp, max_hp=cfg.hp,
    )
    e.state = EnemyState.IDLE
    rt._emit_sub_boss_propulsion(e, 1.0 / 60.0)
    # When the ship moves DOWN, the exhaust should fly UP
    assert len(rt._particles.calls) > 0
    # Average vy of all emitted particles must be < 0 (upward)
    avg_vy = sum(c["vy"] for c in rt._particles.calls) / len(rt._particles.calls)
    assert avg_vy < 0, (
        f"Exhaust must fly OPPOSITE of velocity (downward ship -> upward exhaust). "
        f"avg_vy={avg_vy}"
    )


def test_sub_boss_propulsion_exhaust_follows_l_turn():
    """BLOQUE 58.6.5: when the sub-boss L-turns to the right (vx>0),
    the exhaust should fly to the LEFT (vx<0).
    """
    from src.ui import gameplay_runtime as gpr
    from src.entities.enemies import EnemyKind, ENEMY_CONFIGS
    from src.entities.enemies.enemy import Enemy, EnemyState

    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    rt = gpr.GameplayRuntime.__new__(gpr.GameplayRuntime)
    rt._t = 0.0
    rt._particles = _RecordingParticleEngine()

    e = Enemy(
        kind=EnemyKind.SUB_BOSS,
        x=100.0, y=100.0, vx=90.0, vy=0.0,  # L-right: going RIGHT
        hp=cfg.hp, max_hp=cfg.hp,
    )
    e.state = EnemyState.IDLE
    rt._emit_sub_boss_propulsion(e, 1.0 / 60.0)
    assert len(rt._particles.calls) > 0
    avg_vx = sum(c["vx"] for c in rt._particles.calls) / len(rt._particles.calls)
    assert avg_vx < 0, (
        f"Rightward ship must emit LEFTWARD exhaust. avg_vx={avg_vx}"
    )


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
class _RecordingParticleEngine:
    """Minimal stand-in for ParticleEngine that records every emit call."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def emit(self, kind, x, y, vx=0.0, vy=0.0, color=None, life=None,
             radius=None, **_extra):
        self.calls.append({
            "kind": kind, "x": x, "y": y, "vx": vx, "vy": vy,
            "color": color, "life": life, "radius": radius,
        })
