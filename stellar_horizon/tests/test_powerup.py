# stellar_horizon/tests/test_powerup.py
import pygame
import pytest

from stellar_horizon.entities.powerup import (
    ENEMY_DROP_RATE_GOLD,
    ENEMY_DROP_RATE_SILVER,
    PowerUp,
    PowerUpKind,
    roll_enemy_drop,
)


class FakePlayer:
    def __init__(self, x=200, y=135):
        self.x, self.y = x, y


def test_powerup_kind_constants():
    assert PowerUpKind.SILVER == "silver"
    assert PowerUpKind.GOLD == "gold"


def test_powerup_starts_dead():
    p = PowerUp()
    assert p.alive is False


def test_powerup_spawn_sets_alive():
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.SILVER, 0.0)
    assert p.alive is True
    assert p.kind == PowerUpKind.SILVER


def test_powerup_spawn_stores_position():
    p = PowerUp()
    p.spawn(123, 45, PowerUpKind.GOLD, 1.5)
    assert p.x == 123
    assert p.y == 45
    assert p.spawn_time == 1.5


def test_powerup_magneto_pickup():
    """Player inside PICKUP_RADIUS -> picked up."""
    p = PowerUp()
    p.spawn(200, 135, PowerUpKind.SILVER, 0.0)
    player = FakePlayer(x=210, y=140)  # ~11.2 px away
    picked = p.update(0.01, player, 0.01)
    assert picked is True
    assert p.alive is False


def test_powerup_outside_pickup_radius_survives():
    """Player outside PICKUP_RADIUS -> survives."""
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.SILVER, 0.0)
    player = FakePlayer(x=300, y=200)  # way outside
    picked = p.update(0.01, player, 0.01)
    assert picked is False
    assert p.alive is True


def test_powerup_expires_after_lifetime():
    """After LIFETIME + FADE the ring becomes dead."""
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.SILVER, 0.0)
    p.update(0.01, FakePlayer(x=500, y=500),
             PowerUp.LIFETIME_S + PowerUp.FADE_DURATION_S + 0.1)
    assert p.alive is False


def test_powerup_alpha_full_during_lifetime():
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.SILVER, 0.0)
    assert p.current_alpha(5.0) == 255


def test_powerup_alpha_fades_during_tail():
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.SILVER, 0.0)
    # Mid-fade: should be between 0 and 255.
    mid = p.current_alpha(PowerUp.LIFETIME_S + PowerUp.FADE_DURATION_S * 0.5)
    assert 0 < mid < 255


def test_powerup_alpha_zero_after_full_fade():
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.SILVER, 0.0)
    a = p.current_alpha(PowerUp.LIFETIME_S + PowerUp.FADE_DURATION_S + 0.1)
    assert a == 0


def test_roll_enemy_drop_distribution():
    """Over 10000 rolls, gold ~5% and silver ~10% (total ~15%)."""
    import random
    rng = random.Random(42)
    gold = 0
    silver = 0
    for _ in range(10000):
        kind = roll_enemy_drop(rng)
        if kind == PowerUpKind.GOLD:
            gold += 1
        elif kind == PowerUpKind.SILVER:
            silver += 1
    # Allow generous band for randomness.
    assert 350 <= gold <= 650, f"gold={gold}"
    assert 800 <= silver <= 1200, f"silver={silver}"


def test_roll_enemy_drop_seeded_deterministic():
    """Same seed = same sequence (helps with replay testing)."""
    import random
    rng1 = random.Random(123)
    rng2 = random.Random(123)
    a = [roll_enemy_drop(rng1) for _ in range(50)]
    b = [roll_enemy_drop(rng2) for _ in range(50)]
    assert a == b


def test_roll_enemy_drop_rates():
    """Sanity check on the constants themselves."""
    assert ENEMY_DROP_RATE_GOLD == 0.05
    assert ENEMY_DROP_RATE_SILVER == 0.10


def test_powerup_hitbox_size():
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.SILVER, 0.0)
    hb = p.hitbox()
    assert hb.width == 10
    assert hb.height == 10


def test_powerup_draw_does_not_crash():
    """Smoke test that the render path doesn't throw on dummy
    surface (no display).
    """
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.GOLD, 0.0)
    surf = pygame.Surface((480, 270), pygame.SRCALPHA)
    p.draw(surf, 5.0)
    # No exception = pass.


def test_powerup_draw_skips_dead():
    p = PowerUp()
    p.spawn(100, 50, PowerUpKind.SILVER, 0.0)
    p.alive = False
    surf = pygame.Surface((480, 270), pygame.SRCALPHA)
    p.draw(surf, 5.0)
    # No exception = pass.
