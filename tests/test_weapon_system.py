"""Tests for src.systems.weapon_system — 3 paths × 3 levels (BLOQUE 7)."""
from __future__ import annotations

import pytest

from src.systems.weapon_system import (
    ELEMENT_BONUS_TARGETS,
    PLASMA_SPECS,
    SHOCK_SPECS,
    ION_SPECS,
    SPECIAL_NAMES,
    SPECS_BY_PATH,
    XP_PER_KILL,
    XP_PER_KILL_ELEMENT_BONUS,
    XP_THRESHOLD_L2,
    XP_THRESHOLD_L3,
    XP_THRESHOLD_SPECIAL,
    WeaponLevel,
    WeaponPath,
    WeaponSystem,
)


@pytest.fixture
def weapon() -> WeaponSystem:
    return WeaponSystem()


# ---------------------------------------------------------------------------
# 1. Defaults
# ---------------------------------------------------------------------------
def test_default_path_is_plasma(weapon: WeaponSystem) -> None:
    assert weapon.path == WeaponPath.PLASMA


def test_default_level_is_l1(weapon: WeaponSystem) -> None:
    assert weapon.level == WeaponLevel.L1


def test_default_no_special_unlocked(weapon: WeaponSystem) -> None:
    assert weapon.special_unlocked is False


def test_default_xp_zero(weapon: WeaponSystem) -> None:
    assert weapon.xp == 0


def test_default_bombs_full(weapon: WeaponSystem) -> None:
    assert weapon.bombs == weapon.bombs_max == 4


# ---------------------------------------------------------------------------
# 2. 3 paths exist
# ---------------------------------------------------------------------------
def test_three_paths_exist() -> None:
    assert len(SPECS_BY_PATH) == 3
    assert WeaponPath.PLASMA in SPECS_BY_PATH
    assert WeaponPath.ION in SPECS_BY_PATH
    assert WeaponPath.SHOCK in SPECS_BY_PATH


def test_three_levels_per_path() -> None:
    for path in WeaponPath:
        assert len(SPECS_BY_PATH[path]) == 3
        for level in WeaponLevel:
            assert level in SPECS_BY_PATH[path]


def test_special_names_per_path() -> None:
    assert SPECIAL_NAMES[WeaponPath.PLASMA] == "INFERNO"
    assert SPECIAL_NAMES[WeaponPath.ION] == "CHAIN_LIGHTNING"
    assert SPECIAL_NAMES[WeaponPath.SHOCK] == "QUAKE"


# ---------------------------------------------------------------------------
# 3. Damage scales with level
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path,specs", [
    (WeaponPath.PLASMA, PLASMA_SPECS),
    (WeaponPath.ION, ION_SPECS),
    (WeaponPath.SHOCK, SHOCK_SPECS),
])
def test_damage_1_2_3_per_level(path: WeaponPath, specs: dict) -> None:
    """Per GDD §3: damage 1/2/3 at L1/L2/L3."""
    assert specs[WeaponLevel.L1].damage == 1
    assert specs[WeaponLevel.L2].damage == 2
    assert specs[WeaponLevel.L3].damage == 3


# ---------------------------------------------------------------------------
# 4. Bullet count scales
# ---------------------------------------------------------------------------
def test_plasma_bullets_1_2_3() -> None:
    assert PLASMA_SPECS[WeaponLevel.L1].count == 1
    assert PLASMA_SPECS[WeaponLevel.L2].count == 2
    assert PLASMA_SPECS[WeaponLevel.L3].count == 3


def test_ion_bullets_1_2_3() -> None:
    assert ION_SPECS[WeaponLevel.L1].count == 1
    assert ION_SPECS[WeaponLevel.L2].count == 2
    assert ION_SPECS[WeaponLevel.L3].count == 3


def test_shock_bullets_1_2_1() -> None:
    """Shock is single-shot slow heavy at L3 (knockback focus)."""
    assert SHOCK_SPECS[WeaponLevel.L1].count == 1
    assert SHOCK_SPECS[WeaponLevel.L2].count == 2
    assert SHOCK_SPECS[WeaponLevel.L3].count == 1


# ---------------------------------------------------------------------------
# 5. Pierce on ion
# ---------------------------------------------------------------------------
def test_ion_pierce_1_2_3() -> None:
    assert ION_SPECS[WeaponLevel.L1].pierce == 1
    assert ION_SPECS[WeaponLevel.L2].pierce == 2
    assert ION_SPECS[WeaponLevel.L3].pierce == 3


def test_plasma_no_pierce() -> None:
    for level in WeaponLevel:
        assert PLASMA_SPECS[level].pierce == 0


def test_shock_no_pierce() -> None:
    for level in WeaponLevel:
        assert SHOCK_SPECS[level].pierce == 0


# ---------------------------------------------------------------------------
# 6. Speed differences
# ---------------------------------------------------------------------------
def test_shock_slower_than_plasma_ion() -> None:
    """Shock is the slow path per GDD §3."""
    for level in WeaponLevel:
        assert SHOCK_SPECS[level].speed_mult < PLASMA_SPECS[level].speed_mult
        assert SHOCK_SPECS[level].speed_mult < ION_SPECS[level].speed_mult


# ---------------------------------------------------------------------------
# 7. Level-up progression
# ---------------------------------------------------------------------------
def test_10_kills_advance_to_l2(weapon: WeaponSystem) -> None:
    for _ in range(10):
        weapon.on_kill("scout")  # not element bonus
    assert weapon.level == WeaponLevel.L2


def test_25_kills_advance_to_l3(weapon: WeaponSystem) -> None:
    for _ in range(25):
        weapon.on_kill("scout")
    assert weapon.level == WeaponLevel.L3


def test_50_kills_unlock_special(weapon: WeaponSystem) -> None:
    for _ in range(50):
        weapon.on_kill("scout")
    assert weapon.special_unlocked is True
    assert weapon.level == WeaponLevel.L3


def test_element_bonus_kill_grants_extra_xp(weapon: WeaponSystem) -> None:
    weapon.on_kill("heavy")  # plasma bonus target
    assert weapon.xp == XP_PER_KILL_ELEMENT_BONUS


def test_non_bonus_kill_grants_normal_xp(weapon: WeaponSystem) -> None:
    weapon.on_kill("scout")
    assert weapon.xp == XP_PER_KILL


# ---------------------------------------------------------------------------
# 8. Element bonus targets
# ---------------------------------------------------------------------------
def test_plasma_bonus_targets_heavy_cruiser_turret_carrier() -> None:
    targets = ELEMENT_BONUS_TARGETS[WeaponPath.PLASMA]
    assert "heavy" in targets
    assert "cruiser" in targets
    assert "turret" in targets
    assert "carrier" in targets


def test_ion_bonus_targets_scout_drone_sniper() -> None:
    targets = ELEMENT_BONUS_TARGETS[WeaponPath.ION]
    assert "scout" in targets
    assert "drone" in targets
    assert "sniper" in targets


def test_shock_bonus_targets_kamikaze_sniper_heavy() -> None:
    targets = ELEMENT_BONUS_TARGETS[WeaponPath.SHOCK]
    assert "kamikaze" in targets
    assert "sniper" in targets
    assert "heavy" in targets


# ---------------------------------------------------------------------------
# 9. Fire request
# ---------------------------------------------------------------------------
def test_request_fire_sets_pending(weapon: WeaponSystem) -> None:
    weapon.request_fire()
    assert weapon.pending_fire is True


def test_consume_pending_returns_and_clears(weapon: WeaponSystem) -> None:
    weapon.request_fire(charge_level=2)
    fire, special, level = weapon.consume_pending()
    assert fire is True
    assert special is False
    assert level == 2
    # Cleared
    assert weapon.pending_fire is False
    assert weapon.pending_charge_level == 0


# ---------------------------------------------------------------------------
# 10. Special
# ---------------------------------------------------------------------------
def test_special_blocked_when_not_unlocked(weapon: WeaponSystem) -> None:
    assert weapon.request_special() is False


def test_special_blocked_when_no_bomb(weapon: WeaponSystem) -> None:
    weapon.special_unlocked = True
    weapon.bombs = 0
    assert weapon.request_special() is False


def test_special_consumes_bomb(weapon: WeaponSystem) -> None:
    weapon.special_unlocked = True
    weapon.bombs = 3
    result = weapon.request_special()
    assert result is True
    assert weapon.bombs == 2
    assert weapon.pending_special is True


# ---------------------------------------------------------------------------
# 11. set_path resets state
# ---------------------------------------------------------------------------
def test_set_path_resets_level_and_xp(weapon: WeaponSystem) -> None:
    weapon.level = WeaponLevel.L3
    weapon.xp = 50
    weapon.special_unlocked = True
    weapon.set_path(WeaponPath.ION)
    assert weapon.path == WeaponPath.ION
    assert weapon.level == WeaponLevel.L1
    assert weapon.xp == 0
    assert weapon.special_unlocked is False


# ---------------------------------------------------------------------------
# 12. Reset
# ---------------------------------------------------------------------------
def test_reset_returns_to_default(weapon: WeaponSystem) -> None:
    weapon.xp = 50
    weapon.level = WeaponLevel.L3
    weapon.special_unlocked = True
    weapon.bombs = 1
    weapon.reset()
    assert weapon.xp == 0
    assert weapon.level == WeaponLevel.L1
    assert weapon.special_unlocked is False
    assert weapon.bombs == weapon.bombs_max
    assert weapon.total_kills == 0


# ---------------------------------------------------------------------------
# 13. XP thresholds
# ---------------------------------------------------------------------------
def test_xp_thresholds_match_spec() -> None:
    assert XP_THRESHOLD_L2 == 10
    assert XP_THRESHOLD_L3 == 25
    assert XP_THRESHOLD_SPECIAL == 50
    assert XP_PER_KILL == 1
    assert XP_PER_KILL_ELEMENT_BONUS == 2
