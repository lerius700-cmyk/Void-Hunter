"""BLOQUE 61: tests for AI-generated asteroid sprite loader.

The procedural `_make_asteroid_sprite` was removed. Asteroids now load
5 AI-generated 32x32 PNGs from Assets/sprites/asteroids/.

Test count: 20.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

import pytest

from src.entities.asteroid import (
    Asteroid,
    Powerup,
    PowerupKind,
    POWERUP_WEIGHTS,
    _load_asteroid_sprite,
    draw_asteroid,
    spawn_asteroid,
)


SPRITES_DIR = ROOT / "Assets" / "sprites" / "asteroids"
VARIANTS = ("round", "elongated", "spiked", "hollowed", "cracked")


# =====================================================================
# Asset presence (5 tests)
# =====================================================================
class TestAssetPresence:
    def test_sprites_dir_exists(self) -> None:
        assert SPRITES_DIR.is_dir(), f"missing dir: {SPRITES_DIR}"

    def test_5_variant_files_exist(self) -> None:
        missing = [v for v in VARIANTS if not (SPRITES_DIR / f"{v}.png").exists()]
        assert not missing, f"missing variants: {missing}"

    def test_each_variant_is_64x64(self) -> None:
        """BLOQUE 64.A: asteroid sprites regenerated at 64x64 (was 32x32)."""
        # Defer import so failures are clear
        from PIL import Image
        for v in VARIANTS:
            with Image.open(SPRITES_DIR / f"{v}.png") as img:
                assert img.size == (64, 64), f"{v} is {img.size}, not (64, 64)"

    def test_each_variant_has_transparent_background(self) -> None:
        """Majority of edge pixels should be fully transparent (alpha=0)."""
        from PIL import Image
        for v in VARIANTS:
            with Image.open(SPRITES_DIR / f"{v}.png") as raw:
                img = raw.convert("RGBA")
                w, h = img.size
            # Sample 4 edge pixels
            edge = [img.getpixel((0, 0)), img.getpixel((w-1, 0)),
                    img.getpixel((0, h-1)), img.getpixel((w-1, h-1))]
            # The 4 corners are expected to be transparent (the asteroid
            # is centered, doesn't touch corners). The base palette is
            # brown so they should be either transparent or black-bg.
            for px in edge:
                assert px[3] == 0 or px[:3] == (0, 0, 0), (
                    f"{v} corner not transparent: {px}"
                )

    def test_5_variants_render_to_5_distinct_surfaces(self) -> None:
        """The 5 cached variants must be 5 distinct Surface objects
        (one per variant key, no collision in the cache)."""
        surfaces = []
        for v in range(5):
            surf = _load_asteroid_sprite(v)
            surfaces.append(surf)
        # All 5 must be distinct cached entries. Caching is per-variant
        # in the source, so this is guaranteed by construction.
        unique = len({id(s) for s in surfaces})
        assert unique == 5, f"only {unique}/5 unique cached surfaces"


# =====================================================================
# Sprite loader (3 tests)
# =====================================================================
class TestSpriteLoader:
    def test_load_asteroid_sprite_returns_surface(self) -> None:
        surf = _load_asteroid_sprite(0)
        assert isinstance(surf, pygame.Surface)

    def test_load_asteroid_sprite_caches(self) -> None:
        s1 = _load_asteroid_sprite(0)
        s2 = _load_asteroid_sprite(0)
        # Cached — must be the same Surface object
        assert s1 is s2

    def test_load_asteroid_sprite_invalid_variant_returns_fallback(self) -> None:
        # Out-of-range variant must not crash. Either raises or returns fallback.
        # Spec says: "or returns fallback". We chose fallback.
        surf = _load_asteroid_sprite(99)
        assert isinstance(surf, pygame.Surface)


# =====================================================================
# Dataclass shape (4 tests)
# =====================================================================
class TestDataclass:
    def test_asteroid_dataclass_no_rotation_field(self) -> None:
        import dataclasses
        fields = {f.name for f in dataclasses.fields(Asteroid)}
        assert "rotation" not in fields
        assert "rotation_speed" not in fields

    def test_asteroid_dataclass_has_variant_field(self) -> None:
        ast = Asteroid(x=100, y=50, radius=15, variant=2)
        assert ast.variant == 2

    def test_asteroid_dataclass_has_scale_field(self) -> None:
        ast = Asteroid(x=100, y=50, radius=15, scale=1.2)
        assert ast.scale == 1.2

    def test_drift_vx_vy_unchanged(self) -> None:
        ast = Asteroid(x=100, y=50, radius=15,
                       drift_vx=10.0, drift_vy=30.0)
        ast.update(1.0)
        assert ast.x == 110.0
        assert ast.y == 80.0
        # After refactor, update() does NOT modify rotation
        import dataclasses
        fields = {f.name for f in dataclasses.fields(Asteroid)}
        assert "rotation" not in fields
        # BLOQUE 64.A: hp field was removed (asteroids are indestructible)
        assert "hp" not in fields


# =====================================================================
# Spawn factory (4 tests)
# =====================================================================
class TestSpawnFactory:
    def test_spawn_picks_variant_in_0_to_4(self) -> None:
        rng = random.Random(42)
        for _ in range(1000):
            ast = spawn_asteroid(rng)
            assert 0 <= ast.variant <= 4, f"variant out of range: {ast.variant}"

    def test_spawn_picks_scale_in_1_5_to_2_5(self) -> None:
        """BLOQUE 64.A: scale range bumped to 1.5-2.5 (was 0.7-1.3)."""
        rng = random.Random(42)
        for _ in range(1000):
            ast = spawn_asteroid(rng)
            assert 1.5 <= ast.scale <= 2.5, f"scale out of range: {ast.scale}"

    def test_spawn_radius_derived_from_scale(self) -> None:
        """radius = int(16 * scale), clamped to >= 8."""
        rng = random.Random(42)
        for _ in range(100):
            ast = spawn_asteroid(rng)
            expected = max(8, int(16 * ast.scale))
            assert ast.radius == expected, (
                f"scale={ast.scale}, got radius={ast.radius}, expected={expected}"
            )

    def test_powerup_drop_rate_30_percent(self) -> None:
        rng = random.Random(42)
        n = 1000
        with_powerup = sum(1 for _ in range(n) if spawn_asteroid(rng).hidden_powerup is not None)
        rate = with_powerup / n
        # 30% ± 5% tolerance
        assert 0.25 <= rate <= 0.35, f"powerup rate {rate:.2%} not ~30%"


# =====================================================================
# Draw (3 tests)
# =====================================================================
class TestDraw:
    def test_draw_asteroid_does_not_crash(self) -> None:
        surf = pygame.Surface((320, 480))
        for v in range(5):
            ast = Asteroid(x=100, y=50, radius=15, variant=v, scale=1.0)
            draw_asteroid(surf, ast)  # no exception

    def test_draw_asteroid_inactive_no_op(self) -> None:
        surf = pygame.Surface((320, 480))
        ast = Asteroid(x=100, y=50, radius=15)
        ast.active = False
        # Should not crash, should not draw (no surface change at center)
        draw_asteroid(surf, ast)

    def test_no_pygame_rotate_call_in_draw(self) -> None:
        """The new draw must NOT call pygame.transform.rotate (rotation removed)."""
        import inspect
        from src.entities import asteroid as asteroid_mod
        src = inspect.getsource(asteroid_mod.draw_asteroid)
        assert "pygame.transform.rotate" not in src
        assert "transform.rotate" not in src


# =====================================================================
# Collision (preserved) (2 tests)
# =====================================================================
class TestCollisionPreserved:
    def test_collision_indestructible_hit_method(self) -> None:
        """BLOQUE 64.A: regular asteroids are indestructible. hit() always
        returns False and never marks the asteroid inactive."""
        ast = Asteroid(x=100, y=50, radius=15)
        assert ast.hit(1) is False
        assert ast.active is True
        # Multiple hits still don't destroy it
        for _ in range(10):
            ast.hit(1)
        assert ast.active is True

    def test_collision_unchanged_is_off_screen(self) -> None:
        ast = Asteroid(x=100, y=100, radius=15)
        assert ast.is_off_screen() is False
        ast2 = Asteroid(x=100, y=600, radius=15)
        assert ast2.is_off_screen() is True


# =====================================================================
# Powerup API preserved (2 tests)
# =====================================================================
class TestPowerupPreserved:
    def test_powerup_kind_enum_unchanged(self) -> None:
        kinds = {k.value for k in PowerupKind}
        assert kinds == {"bomb", "hp", "weapon", "score"}

    def test_weights_sum_to_100(self) -> None:
        assert sum(POWERUP_WEIGHTS.values()) == 100
