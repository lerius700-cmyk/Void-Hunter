"""BLOQUE 63: tests for MINE-ASTEROID enemy.

Adds ``EnemyKind.MINE_ASTEROID`` — a stealth enemy that uses the asteroid
aesthetic as camouflage. When in the ``closed`` state it is visually
identical to a regular asteroid (``Assets/sprites/asteroids/round.png`` is
reused for the closed frame). When its y crosses the
``OPENING_Y_THRESHOLD`` (200 = upper playfield), it transitions through
``opening`` (0.5s) → ``open`` (0.3s, fires 3 bullets in a fan) → ``closing``
(0.5s) → ``closed`` (with ``has_opened=True``, no re-open). The closed
state is immune to player bullets but vulnerable to player collision.

Test count: 25.
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

from src.entities.enemies.enemy import (
    OPENING_Y_THRESHOLD,
    Enemy,
    EnemyKind,
    EnemyState,
    create_enemy,
)
from src.systems.projectile import (
    BULLET_ENEMY_MINE,
    OWNER_ENEMY,
    Projectile,
    ProjectilePool,
)
from src.entities.asteroid import PowerupKind


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MINE_ASTEROID_SPRITES_DIR = ROOT / "Assets" / "sprites" / "enemies" / "mine_asteroid"
ASTEROID_ROUND_PNG = ROOT / "Assets" / "sprites" / "asteroids" / "round.png"


# =====================================================================
# Enum + constants (5 tests)
# =====================================================================
class TestEnumAndConstants:
    def test_mine_asteroid_kind_in_enum(self) -> None:
        """EnemyKind.MINE_ASTEROID exists with value 'mine_asteroid'."""
        assert hasattr(EnemyKind, "MINE_ASTEROID"), "MINE_ASTEROID missing from EnemyKind"
        assert EnemyKind.MINE_ASTEROID.value == "mine_asteroid"

    def test_opening_y_threshold_constant_200(self) -> None:
        """OPENING_Y_THRESHOLD is exactly 200 (upper playfield, per spec)."""
        assert OPENING_Y_THRESHOLD == 200

    def test_mine_asteroid_in_archetypes(self) -> None:
        """ENEMY_ARCHETYPES tuple includes 'mine_asteroid'."""
        from src.entities.enemies.enemy import ENEMY_ARCHETYPES
        assert "mine_asteroid" in ENEMY_ARCHETYPES

    def test_mine_asteroid_default_state_closed(self) -> None:
        """A freshly-spawned MINE_ASTEROID has mine_state='closed' (string)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert e.mine_state == "closed"
        assert e.mine_state not in ("open", "opening", "closing")

    def test_mine_asteroid_default_has_opened_false(self) -> None:
        """A fresh MINE_ASTEROID has has_opened=False (no cycle yet)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert e.has_opened is False
        assert e.state_timer == 0.0


# =====================================================================
# State machine (5 tests)
# =====================================================================
class TestStateMachine:
    def test_state_transitions_on_y_threshold(self) -> None:
        """Crossing y < OPENING_Y_THRESHOLD triggers closed -> opening."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        # Above the threshold (small y) should trigger
        e.y = OPENING_Y_THRESHOLD - 10
        e.update(0.016, player_x=160.0, player_y=400.0)
        assert e.mine_state == "opening"
        # Below the threshold (large y) should NOT trigger
        e2 = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e2.y = OPENING_Y_THRESHOLD + 50
        e2.update(0.016, player_x=160.0, player_y=400.0)
        assert e2.mine_state == "closed"

    def test_opening_to_open_after_0_5s(self) -> None:
        """After 0.5s in 'opening' state, transitions to 'open'."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD - 10
        e.update(0.016, player_x=160.0, player_y=400.0)
        assert e.mine_state == "opening"
        # Advance 0.4s — still in opening
        e.update(0.4, player_x=160.0, player_y=400.0)
        assert e.mine_state == "opening"
        # Advance 0.1s more (total 0.5s+) — now open
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open"

    def test_open_to_closing_after_0_3s(self) -> None:
        """After 0.3s in 'open' state, transitions to 'closing'.

        Note: the state machine uses a tick-relative model — a single
        large tick can chain through multiple states. The test uses
        small ticks (0.016s) so each tick advances at most one state.
        """
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD - 10
        # First tick: closed -> opening (0.016s elapsed, not enough to advance)
        e.update(0.016, player_x=160.0, player_y=400.0)
        assert e.mine_state == "opening"
        # Advance to 'open' (total 0.5s in opening)
        e.update(0.5, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open"
        # 0.2s later — still open
        e.update(0.2, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open"
        # 0.1s more (total 0.3s) — now closing
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "closing"

    def test_closing_to_closed_after_0_5s(self) -> None:
        """After 0.5s in 'closing' state, transitions back to 'closed' (with has_opened=True)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD - 10
        # Advance through opening + open (0.5 + 0.3 = 0.8s) with small ticks
        e.update(0.016, player_x=160.0, player_y=400.0)  # closed -> opening
        e.update(0.5, player_x=160.0, player_y=400.0)  # opening -> open
        e.update(0.3, player_x=160.0, player_y=400.0)  # open -> closing
        assert e.mine_state == "closing"
        # 0.4s later — still closing
        e.update(0.4, player_x=160.0, player_y=400.0)
        assert e.mine_state == "closing"
        # 0.1s more (total 0.5s) — back to closed, has_opened=True
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "closed"
        assert e.has_opened is True

    def test_has_opened_prevents_reopen(self) -> None:
        """After a full cycle, the MINE-ASTEROID does NOT re-open.

        The y threshold check is performed AFTER the per-tick drift
        update, so we set y close to 0 (well above the threshold)
        and run enough ticks to cover the full 1.3s cycle plus
        extra drift time. After the cycle, has_opened=True so the
        mine_state stays at 'closed' even if y crosses the threshold
        again.
        """
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 0.0)
        # Run a full cycle: 0.5 + 0.3 + 0.5 = 1.3s. Use small ticks
        # so the state machine transitions one state per tick.
        for _ in range(20):  # 20 * 0.1 = 2.0s of updates
            e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "closed"
        assert e.has_opened is True
        # Now update again — should stay in closed (no re-trigger)
        for _ in range(10):
            e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "closed"


# =====================================================================
# State timer (2 tests)
# =====================================================================
class TestStateTimer:
    def test_state_timer_resets_on_transition(self) -> None:
        """state_timer resets to 0.0 each time the state changes."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD - 10
        e.update(0.016, player_x=160.0, player_y=400.0)
        assert e.mine_state == "opening"
        assert e.state_timer == 0.0  # reset on transition
        e.update(0.1, player_x=160.0, player_y=400.0)
        # Timer should now have accumulated (still in 'opening')
        assert e.mine_state == "opening"
        assert e.state_timer > 0.0
        # 0.4s more -> transitions to 'open', timer resets to 0
        e.update(0.4, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open"
        assert e.state_timer == 0.0

    def test_state_timer_advances_in_each_state(self) -> None:
        """state_timer advances inside each non-closed state."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD - 10
        e.update(0.0, player_x=160.0, player_y=400.0)
        e.update(0.1, player_x=160.0, player_y=400.0)
        t1 = e.state_timer
        e.update(0.1, player_x=160.0, player_y=400.0)
        t2 = e.state_timer
        assert t2 > t1  # advancing in 'opening'
        assert t2 < 0.5  # not yet at threshold


# =====================================================================
# Firing pattern (2 tests)
# =====================================================================
class TestFiring:
    def _make_mine_in_open(self) -> Enemy:
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD - 10
        # Use small ticks to control state transitions
        e.update(0.016, player_x=160.0, player_y=400.0)  # closed -> opening
        e.update(0.5, player_x=160.0, player_y=400.0)    # opening -> open
        assert e.mine_state == "open"
        return e

    def test_fire_spawns_3_bullets(self) -> None:
        """_fire_mine_bullets spawns 3 BULLET_ENEMY_MINE bullets in the pool."""
        pool = ProjectilePool(capacity=64)
        e = self._make_mine_in_open()
        e._fire_mine_bullets(pool)
        active = [p for p in pool.pool if p.active]
        assert len(active) == 3
        # All bullets are BULLET_ENEMY_MINE
        assert all(b.kind == BULLET_ENEMY_MINE for b in active)
        # All bullets are owned by ENEMY
        assert all(b.owner == OWNER_ENEMY for b in active)

    def test_fire_bullets_fan_pattern(self) -> None:
        """The 3 bullets fire at 0°, +15°, -15° from straight down."""
        import math
        pool = ProjectilePool(capacity=64)
        e = self._make_mine_in_open()
        e._fire_mine_bullets(pool)
        active = [p for p in pool.pool if p.active]
        assert len(active) == 3
        # Sort by vx so we have left, center, right
        active.sort(key=lambda b: b.vx)
        # All bullets have the same speed (80 px/s)
        speed = math.hypot(active[0].vx, active[0].vy)
        assert abs(speed - 80.0) < 0.001
        # Center bullet: vx=0, vy=80 (straight down)
        center = active[1]
        assert abs(center.vx) < 0.001
        assert abs(center.vy - 80.0) < 0.001
        # Left bullet: vx < 0
        assert active[0].vx < 0
        # Right bullet: vx > 0
        assert active[2].vx > 0
        # Angles: 15° from down
        # 15° from straight down (positive y) means vx/vy = tan(15°)
        tan15 = math.tan(math.radians(15))
        ratio_left = abs(active[0].vx / active[0].vy) if active[0].vy != 0 else 0
        ratio_right = abs(active[2].vx / active[2].vy) if active[2].vy != 0 else 0
        assert abs(ratio_left - tan15) < 0.01
        assert abs(ratio_right - tan15) < 0.01


# =====================================================================
# HP + immunity (3 tests)
# =====================================================================
class TestHPAndImmunity:
    def test_hp_starts_at_3(self) -> None:
        """BLOQUE 64.A: MINE_ASTEROID has HP=3 (was 2 in BLOQUE 63).
        3 hits are required to destroy the mine when vulnerable."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert e.hp == 3
        assert e.max_hp == 3

    def test_closed_immune_to_bullets(self) -> None:
        """When mine_state=='closed', hit() returns False (no damage applied)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        # mine_state is closed by default
        assert e.mine_state == "closed"
        # Track HP before
        hp_before = e.hp
        result = e.apply_damage(1)
        # Should NOT have taken damage (immune)
        assert e.hp == hp_before
        # Should NOT have triggered death
        assert result is False

    def test_open_vulnerable_to_bullets(self) -> None:
        """BLOQUE 64.A: HP=3, so 3 hits destroy the MINE_ASTEROID."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        # Force into 'open' state directly
        e.mine_state = "open"
        e.hp = 3
        # 1 hit — alive
        e.apply_damage(1)
        assert e.hp == 2
        # 2nd hit — alive
        e.apply_damage(1)
        assert e.hp == 1
        # 3rd hit — destroyed
        result = e.apply_damage(1)
        assert result is True
        assert e.hp <= 0

    def test_opening_vulnerable_to_bullets(self) -> None:
        """When mine_state=='opening', bullets deal damage (only closed is immune)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_state = "opening"
        e.hp = 3
        # 3 hits to destroy
        e.apply_damage(1)
        e.apply_damage(1)
        result = e.apply_damage(1)
        assert result is True


# =====================================================================
# Sprite assets (3 tests)
# =====================================================================
class TestSprites:
    def test_5_state_directories_exist(self) -> None:
        """closed/opening/open/closing/death directories all exist."""
        for sub in ("closed", "opening", "open", "closing", "death"):
            d = MINE_ASTEROID_SPRITES_DIR / sub
            assert d.is_dir(), f"missing dir: {d}"

    def test_sprite_closed_equals_asteroid_round(self) -> None:
        """The closed frame is byte-equal to Assets/sprites/asteroids/round.png."""
        import hashlib
        assert ASTEROID_ROUND_PNG.is_file(), f"missing asteroid round: {ASTEROID_ROUND_PNG}"
        closed_path = MINE_ASTEROID_SPRITES_DIR / "closed" / "frame_00.png"
        assert closed_path.is_file(), f"missing closed frame: {closed_path}"
        with open(ASTEROID_ROUND_PNG, "rb") as f:
            h1 = hashlib.md5(f.read()).hexdigest()
        with open(closed_path, "rb") as f:
            h2 = hashlib.md5(f.read()).hexdigest()
        assert h1 == h2, "closed frame must be byte-equal to asteroid round.png (perfect camo)"

    def test_opening_frame_count(self) -> None:
        """opening has 3 frames (00, 01, 02)."""
        for i in range(3):
            f = MINE_ASTEROID_SPRITES_DIR / "opening" / f"frame_{i:02d}.png"
            assert f.is_file(), f"missing opening frame: {f}"

    def test_closing_frame_count(self) -> None:
        """closing has 3 frames."""
        for i in range(3):
            f = MINE_ASTEROID_SPRITES_DIR / "closing" / f"frame_{i:02d}.png"
            assert f.is_file(), f"missing closing frame: {f}"

    def test_open_frame_count(self) -> None:
        """open has 1 frame."""
        f = MINE_ASTEROID_SPRITES_DIR / "open" / "frame_00.png"
        assert f.is_file(), f"missing open frame: {f}"

    def test_death_frame_count(self) -> None:
        """death has 10 frames."""
        for i in range(10):
            f = MINE_ASTEROID_SPRITES_DIR / "death" / f"frame_{i:02d}.png"
            assert f.is_file(), f"missing death frame: {f}"


# =====================================================================
# Projectile kind (1 test)
# =====================================================================
class TestProjectileKind:
    def test_bullet_kind_registered(self) -> None:
        """BULLET_ENEMY_MINE is registered in projectile module."""
        from src.systems import projectile
        assert hasattr(projectile, "BULLET_ENEMY_MINE")
        # Should be a unique int distinct from existing kinds
        assert BULLET_ENEMY_MINE not in (0, 1, 2, 3, 4, 5)


# =====================================================================
# Powerup drop (2 tests)
# =====================================================================
class TestPowerupDrop:
    def test_powerup_pool_excludes_score(self) -> None:
        """The powerup pool for MINE_ASTEROID excludes SCORE (only BOMB/HP/WEAPON)."""
        # The pool is implemented in a function: pick_mine_powerup
        from src.entities.enemies.enemy import pick_mine_powerup
        # Sample 200 picks — verify all are BOMB/HP/WEAPON
        rng = random.Random(0xBEEF)
        kinds = [pick_mine_powerup(rng) for _ in range(200)]
        for kind in kinds:
            assert kind in (PowerupKind.BOMB, PowerupKind.HP, PowerupKind.WEAPON), \
                f"unexpected kind in pool: {kind}"

    def test_50_percent_powerup_drop(self) -> None:
        """~50% of destroyed MINE_ASTEROIDs drop a powerup."""
        from src.entities.enemies.enemy import should_drop_mine_powerup
        rng = random.Random(0xBEEF)
        drops = sum(1 for _ in range(2000) if should_drop_mine_powerup(rng))
        # Allow ±5% tolerance (47.5% - 52.5%)
        ratio = drops / 2000
        assert 0.45 <= ratio <= 0.55, f"drop rate {ratio} not in [0.45, 0.55]"


# =====================================================================
# Spawn integration (2 tests)
# =====================================================================
class TestSpawnIntegration:
    def test_spawn_mixes_with_asteroids(self) -> None:
        """spawn_obstacle produces ~1/8 MINE_ASTEROID (BLOQUE 63 spec)."""
        from src.entities.enemies.enemy import spawn_obstacle
        rng = random.Random(0xCAFE)
        results = {"asteroid": 0, "mine_asteroid": 0}
        for _ in range(2000):
            kind, _payload = spawn_obstacle(rng)
            results[kind] = results.get(kind, 0) + 1
        # ~1/8 should be mine_asteroid, ~7/8 should be asteroid
        ratio = results.get("mine_asteroid", 0) / 2000
        assert 0.10 <= ratio <= 0.16, f"mine_asteroid ratio {ratio} not in [0.10, 0.16] (expected ~0.125)"

    def test_spawn_obstacle_asteroid_path(self) -> None:
        """spawn_obstacle's 'asteroid' branch returns a valid asteroid dict."""
        from src.entities.enemies.enemy import spawn_obstacle
        rng = random.Random(0xCAFE)
        # Force a bunch until we get an asteroid
        for _ in range(50):
            kind, payload = spawn_obstacle(rng)
            if kind == "asteroid":
                assert "x" in payload and "y" in payload
                assert "variant" in payload
                assert 0 <= payload["variant"] <= 4
                return
        pytest.fail("no asteroid produced in 50 spawns (rng bias?)")
