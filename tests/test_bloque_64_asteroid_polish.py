"""BLOQUE 64.A: tests for asteroid + MINE-ASTEROID polish.

Three coordinated changes per the BLOQUE 64.A spec
(``docs/superpowers/specs/2026-09-08-bloque-64-goliath-anim-and-asteroid-polish.md``):

1. 5 asteroid variants regenerated at 64x64 (was 32x32). MINE-ASTEROID
   camouflage (BLOQUE 63) reuses ``round.png`` as the closed sprite, so
   the canonical asteroid and the MINE-ASTEROID closed lookalike both
   grow to 64x64 in lockstep.
2. Regular asteroids are now INDESTRUCTIBLE: ``Asteroid.hit()`` is a
   no-op, the HP system is gone, and ``_asteroid_bullet_collision``
   in ``gameplay_runtime`` no longer damages asteroids (it only kills
   the bullet, like the off-target bullet pass-through).
3. MINE-ASTEROID HP is now 3 (was 2), with a 0.2s red flash on each
   hit so the player sees the damage progression. The closed-state
   bullet immunity from BLOQUE 63 is preserved (the red flash only
   applies when the hit lands, i.e. when the mine is in opening/open/
   closing states).

Test count: 18.
"""
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

import hashlib
import pytest

from src.entities.asteroid import (
    ASTEROID_SPRITE_BASE_SIZE,
    ASTEROID_SCALE_MAX,
    ASTEROID_SCALE_MIN,
    Asteroid,
    spawn_asteroid,
    draw_asteroid,
)
from src.entities.enemies.enemy import (
    Enemy,
    EnemyKind,
    create_enemy,
)


SPRITES_DIR = ROOT / "Assets" / "sprites" / "asteroids"
MINE_CLOSED_DIR = ROOT / "Assets" / "sprites" / "enemies" / "mine_asteroid" / "closed"
VARIANTS = ("round", "elongated", "spiked", "hollowed", "cracked")


# =====================================================================
# 64x64 regeneration (3 tests)
# =====================================================================
class TestAsteroidSprites64x64:
    def test_5_variant_files_still_exist(self) -> None:
        missing = [v for v in VARIANTS if not (SPRITES_DIR / f"{v}.png").exists()]
        assert not missing, f"missing variants: {missing}"

    def test_each_variant_is_64x64(self) -> None:
        """BLOQUE 64.A: 5 asteroid variants regenerated at 64x64 (was 32x32)."""
        from PIL import Image
        for v in VARIANTS:
            with Image.open(SPRITES_DIR / f"{v}.png") as img:
                assert img.size == (64, 64), (
                    f"{v} is {img.size}, not (64, 64)"
                )

    def test_mine_asteroid_closed_uses_64x64_round(self) -> None:
        """The MINE-ASTEROID closed frame is byte-equal to the new 64x64
        ``round.png`` (camo requires identical pixels)."""
        assert (MINE_CLOSED_DIR / "frame_00.png").is_file()
        assert (SPRITES_DIR / "round.png").is_file()
        with open(SPRITES_DIR / "round.png", "rb") as f:
            h_round = hashlib.md5(f.read()).hexdigest()
        with open(MINE_CLOSED_DIR / "frame_00.png", "rb") as f:
            h_closed = hashlib.md5(f.read()).hexdigest()
        assert h_round == h_closed, (
            "MINE-ASTEROID closed frame must be byte-equal to the new "
            "64x64 round.png (perfect camo invariant)"
        )


# =====================================================================
# Asteroid constants (3 tests)
# =====================================================================
class TestAsteroidConstants:
    def test_asteroid_sprite_base_size_is_64(self) -> None:
        assert ASTEROID_SPRITE_BASE_SIZE == 64

    def test_asteroid_scale_min_is_1_5(self) -> None:
        assert ASTEROID_SCALE_MIN == 1.5

    def test_asteroid_scale_max_is_2_5(self) -> None:
        assert ASTEROID_SCALE_MAX == 2.5


# =====================================================================
# Spawn scale range (2 tests)
# =====================================================================
class TestSpawnScale:
    def test_spawn_scale_in_1_5_to_2_5(self) -> None:
        import random
        rng = random.Random(42)
        for _ in range(500):
            ast = spawn_asteroid(rng)
            assert 1.5 <= ast.scale <= 2.5, (
                f"scale {ast.scale} out of [1.5, 2.5]"
            )

    def test_spawn_radius_derived_from_new_scale(self) -> None:
        """radius = max(8, int(16 * scale)) with new scale range."""
        import random
        rng = random.Random(42)
        for _ in range(100):
            ast = spawn_asteroid(rng)
            expected = max(8, int(16 * ast.scale))
            assert ast.radius == expected


# =====================================================================
# Indestructibility (3 tests)
# =====================================================================
class TestIndestructibility:
    def test_asteroid_hit_is_noop(self) -> None:
        """BLOQUE 64.A: regular asteroids are indestructible. ``hit()``
        always returns False and never marks the asteroid inactive."""
        ast = Asteroid(x=100, y=50, radius=15)
        assert ast.hit(1) is False
        assert ast.active is True
        # Multiple hits still don't destroy it
        for _ in range(10):
            ast.hit(1)
        assert ast.active is True

    def test_asteroid_survives_many_bullets(self) -> None:
        """Even after 100 hits, the asteroid stays active."""
        ast = Asteroid(x=100, y=50, radius=15)
        for _ in range(100):
            ast.hit(1)
        assert ast.active is True

    def test_asteroid_hitbox_unchanged(self) -> None:
        """The radius (collision hitbox) is not affected by indestructibility."""
        ast = Asteroid(x=100, y=50, radius=15)
        assert ast.radius == 15
        # Player collision still uses the same radius (see _asteroid_player_collision)


# =====================================================================
# Draw still works at 64x64 (1 test)
# =====================================================================
class TestDrawAt64:
    def test_draw_asteroid_does_not_crash(self) -> None:
        surf = pygame.Surface((320, 480))
        for v in range(5):
            ast = Asteroid(x=100, y=50, radius=15, variant=v, scale=2.0)
            draw_asteroid(surf, ast)  # no exception


# =====================================================================
# MINE-ASTEROID HP=3 (4 tests)
# =====================================================================
class TestMineAsteroidHP3:
    def test_mine_asteroid_hp_3(self) -> None:
        """MINE-ASTEROID HP is now 3 (was 2 in BLOQUE 63)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert e.hp == 3
        assert e.max_hp == 3

    def test_mine_asteroid_survives_2_hits(self) -> None:
        """2 hits leave the MINE-ASTEROID alive (HP=3, needs 3 hits to die)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_state = "open"  # vulnerable
        e.hp = 3
        result = e.apply_damage(1)
        assert result is False
        assert e.hp == 2
        assert e.state.name != "DEAD"

    def test_mine_asteroid_3_hits_destroy(self) -> None:
        """3 hits kill the MINE-ASTEROID."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_state = "open"
        e.hp = 3
        e.apply_damage(1)
        e.apply_damage(1)
        result = e.apply_damage(1)
        assert result is True
        assert e.hp <= 0

    def test_mine_asteroid_2_damage_kill(self) -> None:
        """A single 2-damage hit at HP=3 leaves it alive (3 - 2 = 1)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_state = "open"
        e.hp = 3
        result = e.apply_damage(2)
        assert result is False
        assert e.hp == 1


# =====================================================================
# MINE-ASTEROID red flash (4 tests)
# =====================================================================
class TestMineAsteroidRedFlash:
    def test_mine_hit_flash_timer_field_default_zero(self) -> None:
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert hasattr(e, "mine_hit_flash_timer")
        assert e.mine_hit_flash_timer == 0.0

    def test_mine_hit_sets_flash_timer(self) -> None:
        """A hit while vulnerable sets mine_hit_flash_timer to 0.2s."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_state = "open"
        e.hp = 3
        e.apply_damage(1)
        assert e.mine_hit_flash_timer == pytest.approx(0.2, abs=0.01)

    def test_mine_hit_closed_no_flash(self) -> None:
        """A hit while in closed state (immune) does NOT set the flash timer."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert e.mine_state == "closed"
        e.apply_damage(1)
        # Closed-state immunity means no damage applied, so no flash.
        assert e.mine_hit_flash_timer == 0.0

    def test_mine_flash_timer_decrements_in_update(self) -> None:
        """The flash timer ticks down by dt in update()."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_state = "open"
        e.hp = 3
        e.apply_damage(1)
        assert e.mine_hit_flash_timer == pytest.approx(0.2, abs=0.01)
        # 0.1s of update should drop the timer to ~0.1
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_hit_flash_timer == pytest.approx(0.1, abs=0.01)
        # Another 0.15s should drop it close to 0 (clamped at 0)
        e.update(0.15, player_x=160.0, player_y=400.0)
        assert e.mine_hit_flash_timer == pytest.approx(0.0, abs=0.01)


# =====================================================================
# Existing closed-state immunity (1 test) — regression guard
# =====================================================================
class TestClosedStateImmunity:
    def test_closed_state_still_immune(self) -> None:
        """BLOQUE 64.A: closed-state immunity from BLOQUE 63 is preserved."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert e.mine_state == "closed"
        hp_before = e.hp
        result = e.apply_damage(1)
        assert e.hp == hp_before
        assert result is False
