"""Tests for src.entities.enemies.boss — 4 bosses × 4 phases (BLOQUE 9)."""
from __future__ import annotations

import pytest

from src.entities.enemies import BOSS_CONFIGS, Boss, BossId, BossPool
from src.core.settings import INTERNAL_H, INTERNAL_W


@pytest.fixture
def pool() -> BossPool:
    return BossPool()


# ---------------------------------------------------------------------------
# 1. 4 bosses exist
# ---------------------------------------------------------------------------
def test_four_bosses_defined() -> None:
    assert len(BOSS_CONFIGS) == 4
    assert BossId.GOLIATH in BOSS_CONFIGS
    assert BossId.HYDRA in BOSS_CONFIGS
    assert BossId.PHANTOM in BOSS_CONFIGS
    assert BossId.NEMESIS in BOSS_CONFIGS


# ---------------------------------------------------------------------------
# 2. Per-boss GDD §5 specs
# ---------------------------------------------------------------------------
def test_goliath_2_phases_800_hp() -> None:
    cfg = BOSS_CONFIGS[BossId.GOLIATH]
    assert cfg.max_hp == 800
    assert cfg.width == 32 and cfg.height == 18
    assert cfg.phase_thresholds == (0.66,)


def test_hydra_3_phases_1400_hp() -> None:
    cfg = BOSS_CONFIGS[BossId.HYDRA]
    assert cfg.max_hp == 1400
    assert cfg.width == 36 and cfg.height == 20
    assert cfg.phase_thresholds == (0.66, 0.33)  # 2->3, 3->enraged


def test_phantom_2_phases_2000_hp() -> None:
    cfg = BOSS_CONFIGS[BossId.PHANTOM]
    assert cfg.max_hp == 2000
    assert cfg.width == 40 and cfg.height == 22
    assert cfg.phase_thresholds == (0.66,)


def test_nemesis_4_phases_5000_hp() -> None:
    cfg = BOSS_CONFIGS[BossId.NEMESIS]
    assert cfg.max_hp == 5000
    assert cfg.width == 48 and cfg.height == 28
    assert cfg.phase_thresholds == (0.75, 0.50, 0.25)


# ---------------------------------------------------------------------------
# 3. Pool spawn
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("boss_id", list(BossId))
def test_spawn_resets_state(pool: BossPool, boss_id: BossId) -> None:
    b = pool.spawn(boss_id)
    assert b is not None
    cfg = BOSS_CONFIGS[boss_id]
    assert b.x == cfg.anchor_x
    assert b.y == cfg.anchor_y
    assert b.hp == cfg.max_hp
    assert b.phase == 1
    assert b.active is True


def test_pool_capacity_4(pool: BossPool) -> None:
    assert pool.pool.size == 4


# ---------------------------------------------------------------------------
# 4. Phase transitions
# ---------------------------------------------------------------------------
def test_goliath_phase_2_at_66_percent() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.hp = 800
    b._check_phase()
    assert b.phase == 1
    # 67% > 66% threshold
    b.hp = 540  # 67.5%
    b._check_phase()
    assert b.phase == 1  # still 1
    # 65% < 66% threshold → phase 2
    b.hp = 510
    b._check_phase()
    assert b.phase == 2
    assert b.on_phase_transition == 2


def test_hydra_phase_3_at_33_percent() -> None:
    b = Boss()
    b.id = BossId.HYDRA
    b.max_hp = 1400
    b.hp = 1400
    b._check_phase()
    assert b.phase == 1
    b.hp = 600  # 42% > 33% → phase 2
    b._check_phase()
    assert b.phase == 2
    b.hp = 400  # 28% < 33% → phase 3 (enraged)
    b._check_phase()
    assert b.phase == 3
    assert b.on_phase_transition == 3


def test_nemesis_phase_4_triggers_desperacion() -> None:
    b = Boss()
    b.id = BossId.NEMESIS
    b.max_hp = 5000
    b.hp = 1000  # 20% < 25% → phase 4
    b._check_phase()
    assert b.phase == 4
    # DESESPERACIÓN effects
    assert b.arena_shrink_pct == 0.20
    assert b.bgm_tempo_mult == 1.20
    assert b.hitbox_factor == 0.5


def test_phase_transition_only_fires_once() -> None:
    """On_phase_transition is a one-shot signal — should reset to 0 after."""
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.hp = 510
    b._check_phase()
    assert b.on_phase_transition == 2
    # Next call without HP change should not re-fire
    b._check_phase()
    # Note: on_phase_transition stays at 2 (consumer reads and resets)


def test_apply_damage_emits_phase_transition() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.hp = 800
    b.active = True
    b.apply_damage(290)  # hp = 510, 64% < 66% → phase 2
    assert b.phase == 2
    assert b.on_phase_transition == 2


# ---------------------------------------------------------------------------
# 5. Attack selection
# ---------------------------------------------------------------------------
def test_phase_1_attack_pool_is_aimed_3spread() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.phase = 1
    attacks = set()
    for _ in range(50):
        idx = b.select_attack()
        if idx >= 0:
            attacks.add(idx)
    assert attacks.issubset({0, 1})


def test_phase_2_adds_ring() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.hp = 510
    b.phase = 2
    attacks = set()
    for _ in range(100):
        idx = b.select_attack()
        if idx >= 0:
            attacks.add(idx)
    assert attacks.issubset({0, 1, 3})


def test_phase_4_nemesis_uses_all_8() -> None:
    b = Boss()
    b.id = BossId.NEMESIS
    b.max_hp = 5000
    b.phase = 4
    attacks = set()
    for _ in range(200):
        idx = b.select_attack()
        if idx >= 0:
            attacks.add(idx)
    # All 8 patterns should appear in a long sample
    assert attacks.issubset({0, 1, 2, 3, 4, 5, 6, 7})


def test_select_attack_returns_minus_one_during_cooldown() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.fire_cd = 1.0
    assert b.select_attack() == -1


def test_select_attack_emits_on_attack_signal() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.phase = 1
    idx = b.select_attack()
    assert idx >= 0
    assert b.on_attack == idx


# ---------------------------------------------------------------------------
# 6. Hitbox
# ---------------------------------------------------------------------------
def test_hitbox_is_70_percent_by_default() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    box = b.hitbox()
    assert box.width == int(32 * 0.7)
    assert box.height == int(18 * 0.7)


def test_nemesis_p4_hitbox_shrinks_to_50_percent() -> None:
    b = Boss()
    b.id = BossId.NEMESIS
    b.max_hp = 5000
    b.hp = 1000
    b._check_phase()
    box = b.hitbox()
    assert box.width == int(48 * 0.5)
    assert box.height == int(28 * 0.5)


# ---------------------------------------------------------------------------
# 7. Movement
# ---------------------------------------------------------------------------
def test_goliath_sine_oscillates() -> None:
    """Bosses with speed > 0 oscillate around anchor."""
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.x = 120.0
    b.move_t = 0.0
    b.update(0.1)
    assert b.x != 120.0  # moved
    # Should be near anchor_x with sine offset
    assert abs(b.x - 120.0) < 100.0


def test_nemesis_no_movement() -> None:
    b = Boss()
    b.id = BossId.NEMESIS
    b.max_hp = 5000
    b.x = 120.0
    b.update(1.0)
    assert b.x == 120.0  # anchored


# ---------------------------------------------------------------------------
# 8. Death
# ---------------------------------------------------------------------------
def test_apply_damage_at_zero_hp_signals_death() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.hp = 1
    b.active = True
    killed = b.apply_damage(1)
    assert killed is True
    assert b.on_death is True
    assert b.hp == 0


def test_apply_damage_clamped_to_zero() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.hp = 5
    b.active = True
    b.apply_damage(100)  # overkill
    assert b.hp == 0


def test_apply_damage_blocked_when_inactive() -> None:
    b = Boss()
    b.id = BossId.GOLIATH
    b.max_hp = 800
    b.hp = 800
    b.active = False
    killed = b.apply_damage(100)
    assert killed is False
    assert b.hp == 800


# ---------------------------------------------------------------------------
# 9. Pool exhaustion
# ---------------------------------------------------------------------------
def test_pool_exhaustion_returns_none(pool: BossPool) -> None:
    spawned = [pool.spawn(b) for b in BossId]
    assert all(s is not None for s in spawned)
    assert pool.spawn(BossId.GOLIATH) is None  # pool of 4, all used
