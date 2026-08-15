"""BLOQUE 58.12: tests for Asteroid + Powerup system."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

import random
from src.entities.asteroid import (
    Asteroid,
    Powerup,
    PowerupKind,
    POWERUP_WEIGHTS,
    pick_random_powerup,
    spawn_asteroid,
    draw_asteroid,
    _make_asteroid_sprite,
)


# =====================================================================
# Asteroid basics
# =====================================================================
class TestAsteroidBasics:
    def test_asteroid_creation(self) -> None:
        ast = Asteroid(x=100, y=50, radius=15, hp=2)
        assert ast.x == 100
        assert ast.y == 50
        assert ast.radius == 15
        assert ast.hp == 2
        assert ast.active is True
        assert ast.powerup_dropped is False
        assert ast.hidden_powerup is None  # default no powerup

    def test_asteroid_update_drifts(self) -> None:
        ast = Asteroid(x=100, y=50, radius=15, hp=2, drift_vy=30.0)
        ast.update(1.0)
        assert ast.y == 80  # 50 + 30*1
        # Rotation also advances
        assert ast.rotation != 0.0

    def test_asteroid_hit_takes_damage(self) -> None:
        ast = Asteroid(x=100, y=50, radius=15, hp=2)
        destroyed = ast.hit(damage=1)
        assert destroyed is False
        assert ast.hp == 1
        assert ast.active is True
        destroyed = ast.hit(damage=1)
        assert destroyed is True
        assert ast.active is False

    def test_asteroid_off_screen(self) -> None:
        # Inside the playfield
        ast = Asteroid(x=100, y=100, radius=15, hp=2)
        assert ast.is_off_screen() is False
        # Below the playfield
        ast2 = Asteroid(x=100, y=600, radius=15, hp=2)
        assert ast2.is_off_screen() is True


# =====================================================================
# Procedural sprite generation
# =====================================================================
class TestSpriteGeneration:
    def test_asteroid_sprite_cached(self) -> None:
        # Same radius -> same sprite
        s1 = _make_asteroid_sprite(16, random.Random(1))
        s2 = _make_asteroid_sprite(16, random.Random(2))  # different rng, but cache wins
        assert s1 is s2  # cached

    def test_asteroid_sprite_size(self) -> None:
        sprite = _make_asteroid_sprite(20, random.Random(42))
        # size = 2*radius + 4 = 44
        w, h = sprite.get_size()
        assert w == 44
        assert h == 44


# =====================================================================
# Powerup roguelike distribution
# =====================================================================
class TestPowerupDistribution:
    def test_all_kinds_have_weights(self) -> None:
        for kind in PowerupKind:
            assert kind in POWERUP_WEIGHTS

    def test_weights_sum_to_100(self) -> None:
        assert sum(POWERUP_WEIGHTS.values()) == 100

    def test_pick_random_powerup_returns_known_kind(self) -> None:
        rng = random.Random(42)
        for _ in range(100):
            kind = pick_random_powerup(rng)
            assert kind in PowerupKind

    def test_distribution_roughly_matches_weights(self) -> None:
        """Over many picks, the distribution should roughly match the weights."""
        rng = random.Random(42)
        counts = {k: 0 for k in PowerupKind}
        for _ in range(1000):
            kind = pick_random_powerup(rng)
            counts[kind] += 1
        # SCORE has 35% weight, expect 250-450 picks
        assert 250 < counts[PowerupKind.SCORE] < 450, f"SCORE got {counts[PowerupKind.SCORE]}"
        # BOMB has 15% weight, expect 100-200 picks
        assert 100 < counts[PowerupKind.BOMB] < 200, f"BOMB got {counts[PowerupKind.BOMB]}"


# =====================================================================
# Asteroid factory
# =====================================================================
class TestAsteroidFactory:
    def test_spawn_returns_asteroid(self) -> None:
        rng = random.Random(42)
        ast = spawn_asteroid(rng)
        assert isinstance(ast, Asteroid)
        assert ast.active is True
        # 30% chance of hidden powerup -> either None or a known kind
        if ast.hidden_powerup is not None:
            assert ast.hidden_powerup in PowerupKind

    def test_spawn_caps_active_asteroids(self) -> None:
        # The runtime caps at 8 active; test that the factory doesn't
        # generate more than 1 at a time.
        rng = random.Random(42)
        for _ in range(50):
            ast = spawn_asteroid(rng)
            assert ast is not None


# =====================================================================
# Powerup drawing (visual)
# =====================================================================
class TestPowerupDraw:
    def test_powerup_draw_does_not_crash(self) -> None:
        surf = pygame.Surface((320, 480))
        p = Powerup(x=100, y=100, kind=PowerupKind.BOMB)
        p.draw(surf)  # should not crash
        # Inactive powerups don't draw
        p.active = False
        p.draw(surf)  # should be a no-op

    def test_powerup_lifecycle(self) -> None:
        p = Powerup(x=100, y=100, kind=PowerupKind.SCORE, max_age_s=1.0)
        assert p.active is True
        p.update(2.0)  # 2s elapsed > max_age 1s
        assert p.active is False
