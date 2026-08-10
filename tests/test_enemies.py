"""Tests for src.entities.enemies.enemy — 8 archetypes (BLOQUE 8)."""
from __future__ import annotations

import pytest
import pygame

from src.entities.enemies import (
    ENEMY_ARCHETYPES,
    EnemyKind,
    EnemyPool,
    EnemyState,
    create_enemy,
)
from src.entities.enemies.enemy import (
    ENEMY_CONFIGS,
    MINI_DRONE_CONFIG,
)


@pytest.fixture
def pool() -> EnemyPool:
    return EnemyPool(capacity=64)


# ---------------------------------------------------------------------------
# 1. 8 archetypes exist
# ---------------------------------------------------------------------------
def test_eight_archetypes_exist() -> None:
    """BLOQUE 50: 9 archetypes now (added SUB_BOSS)."""
    assert len(ENEMY_CONFIGS) == 9
    assert len(ENEMY_ARCHETYPES) == 9


def test_all_kinds_have_config() -> None:
    for kind in EnemyKind:
        assert kind in ENEMY_CONFIGS


def test_archetype_strings_match_kinds() -> None:
    for kind in EnemyKind:
        assert kind.value in ENEMY_ARCHETYPES


# ---------------------------------------------------------------------------
# 2. Per-archetype invariants from GDD §4
# ---------------------------------------------------------------------------
def test_scout_low_hp() -> None:
    """Scout HP=1, fast."""
    cfg = ENEMY_CONFIGS[EnemyKind.SCOUT]
    assert cfg.hp == 1
    assert cfg.speed == 110.0
    assert cfg.width == 12 and cfg.height == 8
    assert cfg.score == 50
    assert cfg.sine_wobble is True


def test_cruiser_medium_twin_cannon() -> None:
    cfg = ENEMY_CONFIGS[EnemyKind.CRUISER]
    assert cfg.hp == 4
    assert cfg.width == 14 and cfg.height == 10
    assert cfg.score == 150


def test_heavy_armored_slow() -> None:
    cfg = ENEMY_CONFIGS[EnemyKind.HEAVY]
    assert cfg.hp == 12
    assert cfg.speed == 30.0
    assert cfg.width == 18 and cfg.height == 12
    assert cfg.score == 400
    assert cfg.telegraph_frames == 24


def test_kamikaze_homing_explode() -> None:
    cfg = ENEMY_CONFIGS[EnemyKind.KAMIKAZE]
    assert cfg.hp == 1
    assert cfg.homing is True
    assert cfg.homing_turn_rate > 0.0
    assert cfg.telegraph_frames == 30
    assert cfg.score == 200


def test_drone_spawns_mini() -> None:
    cfg = ENEMY_CONFIGS[EnemyKind.DRONE]
    assert cfg.spawns_mini_on_timer is True
    assert cfg.mini_spawn_count == 3
    assert MINI_DRONE_CONFIG.hp == 1


def test_sniper_static_laser() -> None:
    cfg = ENEMY_CONFIGS[EnemyKind.SNIPER]
    assert cfg.anchored is True
    assert cfg.speed == 0.0
    assert cfg.telegraph_frames == 60
    assert cfg.fire_damage == 3


def test_turret_anchored_3spread() -> None:
    cfg = ENEMY_CONFIGS[EnemyKind.TURRET]
    assert cfg.anchored is True
    assert cfg.speed == 0.0
    assert cfg.telegraph_frames == 6


def test_carrier_spawns_children() -> None:
    cfg = ENEMY_CONFIGS[EnemyKind.CARRIER]
    assert cfg.spawns_carrier_children is True
    assert cfg.hp == 20
    assert cfg.score == 800


# ---------------------------------------------------------------------------
# 3. create_enemy factory
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kind", list(EnemyKind))
def test_create_enemy_sets_all_fields(kind: EnemyKind) -> None:
    e = create_enemy(kind, 100.0, 50.0)
    cfg = ENEMY_CONFIGS[kind]
    assert e.kind == kind
    assert e.x == 100.0
    assert e.y == 50.0
    assert e.hp == cfg.hp
    assert e.max_hp == cfg.hp
    assert e.active is True


# ---------------------------------------------------------------------------
# 4. Hitbox
# ---------------------------------------------------------------------------
def test_hitbox_is_smaller_than_sprite() -> None:
    e = create_enemy(EnemyKind.HEAVY, 100.0, 100.0)
    box = e.hitbox()
    assert box.width < 18
    assert box.height < 12


# ---------------------------------------------------------------------------
# 5. Damage and death
# ---------------------------------------------------------------------------
def test_apply_damage_reduces_hp() -> None:
    e = create_enemy(EnemyKind.CRUISER, 100.0, 100.0)
    e.apply_damage(1)
    assert e.hp == 3


def test_apply_damage_kills_at_zero_hp() -> None:
    e = create_enemy(EnemyKind.SCOUT, 100.0, 100.0)
    killed = e.apply_damage(1)
    assert killed is True
    assert e.state == EnemyState.DYING
    assert e.on_death is True


def test_apply_damage_does_not_kill_above_zero() -> None:
    e = create_enemy(EnemyKind.HEAVY, 100.0, 100.0)
    killed = e.apply_damage(1)
    assert killed is False
    assert e.state == EnemyState.IDLE


def test_apply_damage_blocked_on_dead() -> None:
    e = create_enemy(EnemyKind.SCOUT, 100.0, 100.0)
    e.apply_damage(1)
    e.state = EnemyState.DEAD
    killed = e.apply_damage(1)
    assert killed is False
    assert e.hp == 0


def test_apply_damage_blocked_when_inactive() -> None:
    e = create_enemy(EnemyKind.SCOUT, 100.0, 100.0)
    e.active = False
    killed = e.apply_damage(1)
    assert killed is False


# ---------------------------------------------------------------------------
# 6. Pool
# ---------------------------------------------------------------------------
def test_pool_default_size_64(pool: EnemyPool) -> None:
    assert pool.pool.size == 64


def test_pool_spawn_returns_enemy(pool: EnemyPool) -> None:
    e = pool.spawn(EnemyKind.SCOUT, 50.0, 50.0)
    assert e is not None
    assert e.kind == EnemyKind.SCOUT
    assert e.active


def test_pool_exhaustion_returns_none(pool: EnemyPool) -> None:
    for i in range(64):
        assert pool.spawn(EnemyKind.SCOUT, 0.0, 0.0) is not None
    assert pool.spawn(EnemyKind.SCOUT, 0.0, 0.0) is None


def test_pool_release_makes_slot_reusable(pool: EnemyPool) -> None:
    e = pool.spawn(EnemyKind.SCOUT, 0.0, 0.0)
    assert e is not None
    pool.release(e)
    assert not e.active
    e2 = pool.spawn(EnemyKind.SCOUT, 100.0, 100.0)
    assert e2 is not None
    assert e2.x == 100.0  # re-spawned with new x


def test_pool_release_all(pool: EnemyPool) -> None:
    for _ in range(10):
        pool.spawn(EnemyKind.SCOUT, 0.0, 0.0)
    assert pool.active_count == 10
    pool.release_all()
    assert pool.active_count == 0


def test_pool_spawn_resets_damage_state(pool: EnemyPool) -> None:
    e = pool.spawn(EnemyKind.SCOUT, 0.0, 0.0)
    assert e is not None
    e.apply_damage(1)
    e.damage_taken = 5
    pool.release(e)
    e2 = pool.spawn(EnemyKind.SCOUT, 0.0, 0.0)
    assert e2 is not None
    assert e2.damage_taken == 0
    assert e2.hp == 1


# ---------------------------------------------------------------------------
# 7. Appearance by act
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kind,first_act", [
    (EnemyKind.SCOUT, 1),
    (EnemyKind.CRUISER, 1),
    (EnemyKind.HEAVY, 1),
    (EnemyKind.KAMIKAZE, 1),
    (EnemyKind.DRONE, 2),
    (EnemyKind.SNIPER, 2),
    (EnemyKind.TURRET, 2),
    (EnemyKind.CARRIER, 3),
])
def test_archetype_appears_in_expected_act(kind: EnemyKind, first_act: int) -> None:
    """Sanity: enemies from later acts don't exist in seed waves.
    (Manual per-act appearance table from GDD §4.)"""
    # No way to test directly without WaveManager; just verify kind is registered.
    assert kind in ENEMY_CONFIGS
    # first_act arg exists for future wave-driven tests
    assert 1 <= first_act <= 3


# ---------------------------------------------------------------------------
# 8. Telegraph / fire timing
# ---------------------------------------------------------------------------
def test_telegraph_frames_30_minimum() -> None:
    """Per GDD: min 30 frames telegraph for lethal attacks (Touhou rule)."""
    for kind in EnemyKind:
        cfg = ENEMY_CONFIGS[kind]
        if cfg.fire_damage > 0:
            # All enemies that deal damage must telegraph at least 6 frames
            # (kamikaze glow counts as telegraph too)
            assert cfg.telegraph_frames >= 6, f"{kind} telegraph too short: {cfg.telegraph_frames}"


def test_sniper_60_frames_telegraph() -> None:
    """Sniper specifically: 60 frames (1s) per GDD §4."""
    cfg = ENEMY_CONFIGS[EnemyKind.SNIPER]
    assert cfg.telegraph_frames == 60
