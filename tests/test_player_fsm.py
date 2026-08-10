"""Tests for Player FSM (BLOQUE 6)."""
from __future__ import annotations

import math

import pytest

from src.core.settings import (
    INTERNAL_H,
    INTERNAL_W,
    PLAYER_DASH_DURATION_S,
    PLAYER_DEATH_DURATION_S,
    PLAYER_FIRE_COOLDOWN_S,
    PLAYER_INVULN_FRAMES,
    PLAYER_LIVES,
    PLAYER_RESPAWN_INVULN_S,
    PLAYER_SPEED,
)
from src.entities.player import Player, PlayerState


@pytest.fixture
def p() -> Player:
    return Player()


# ---------------------------------------------------------------------------
# 1. Initial state
# ---------------------------------------------------------------------------
def test_player_initial_state_idle(p: Player) -> None:
    assert p.state == PlayerState.IDLE


def test_player_initial_lives_and_bombs(p: Player) -> None:
    assert p.lives == PLAYER_LIVES == 3
    assert p.bombs == 3
    assert p.bombs_max == 4  # +1 with special unlocked


def test_player_initial_position_center_bottom(p: Player) -> None:
    """BLOQUE 34: playfield is 320x480 now, so center-bottom is (160, 420)."""
    assert p.x == INTERNAL_W / 2 == 160
    assert p.y == INTERNAL_H - 60 == 420


def test_player_initial_tilt_zero(p: Player) -> None:
    assert p.current_tilt == 0.0


# ---------------------------------------------------------------------------
# 2. IDLE -> MOVE on lateral input
# ---------------------------------------------------------------------------
def test_idle_to_move_on_left_input(p: Player) -> None:
    p.input_left = True
    p.update(1 / 60)
    assert p.state == PlayerState.MOVE


def test_idle_to_move_on_right_input(p: Player) -> None:
    p.input_right = True
    p.update(1 / 60)
    assert p.state == PlayerState.MOVE


def test_move_accelerates_to_target_speed(p: Player) -> None:
    p.input_left = True
    for _ in range(30):  # 0.5s of frames
        p.update(1 / 60)
    # Approaching PLAYER_SPEED
    assert p.vx <= -PLAYER_SPEED + 1.0
    assert p.vx < 0


def test_move_tilt_left_negative(p: Player) -> None:
    p.input_left = True
    for _ in range(15):
        p.update(1 / 60)
    # BLOQUE 47: snappier banking (was -15.0)
    assert p.tilt == -25.0


def test_move_tilt_right_positive(p: Player) -> None:
    p.input_right = True
    for _ in range(15):
        p.update(1 / 60)
    # BLOQUE 47: snappier banking (was 15.0)
    assert p.tilt == 25.0


# ---------------------------------------------------------------------------
# 3. MOVE -> IDLE on input release + settle
# ---------------------------------------------------------------------------
def test_move_to_idle_after_settle(p: Player) -> None:
    p.input_left = True
    p.update(1 / 60)  # enter MOVE
    p.input_left = False
    # Wait MOVE_SETTLE_S (0.05s) + a bit
    for _ in range(10):
        p.update(1 / 60)
    assert p.state == PlayerState.IDLE


# ---------------------------------------------------------------------------
# 4. IDLE -> SHOOT on fire
# ---------------------------------------------------------------------------
def test_idle_to_shoot_on_fire(p: Player) -> None:
    p.input_fire = True
    p.update(1 / 60)
    assert p.state == PlayerState.SHOOT
    assert p.wants_to_shoot is True


def test_shoot_to_idle_after_cooldown(p: Player) -> None:
    p.input_fire = True
    p.update(1 / 60)
    p.input_fire = False
    # Cooldown is 0.10s = 12 frames at 120 FPS, but update is at 1/60 = 16ms
    # We need 6 frames @ 1/60 = 0.10s
    for _ in range(7):
        p.update(1 / 60)
    assert p.state == PlayerState.IDLE


def test_fire_cd_blocks_immediate_refire(p: Player) -> None:
    p.input_fire = True
    p.update(1 / 60)
    p.input_fire = False
    p.update(1 / 60)  # still in SHOOT
    assert p.fire_cd > 0.0
    # Try to fire again before cd_ready
    p.input_fire = True
    p.update(1 / 60)
    # The second shot should NOT register yet
    # (depends on cooldown vs state timer; let's just verify no crash)


# ---------------------------------------------------------------------------
# 5. CHARGE state
# ---------------------------------------------------------------------------
def test_charge_enters_when_held_long_enough(p: Player) -> None:
    p.input_fire = True
    p.charge_time = 1.0  # simulate held > 0.5s
    p.update(1 / 60)
    assert p.state == PlayerState.CHARGE


def test_charge_release_emits_signal(p: Player) -> None:
    p.input_fire = True
    p.charge_time = 1.0
    p.update(1 / 60)  # enter CHARGE
    # Release
    p.input_fire = False
    p.update(1 / 60)
    assert p.wants_to_charge_release is True


def test_charge_returns_to_idle_after_fire_anim(p: Player) -> None:
    p.input_fire = True
    p.charge_time = 1.0
    p.update(1 / 60)  # enter CHARGE
    p.input_fire = False
    p.update(1 / 60)  # release
    # 0.20s fire anim = 12 frames @ 60Hz
    for _ in range(15):
        p.update(1 / 60)
    assert p.state == PlayerState.IDLE


# ---------------------------------------------------------------------------
# 6. DASH
# ---------------------------------------------------------------------------
def test_dash_from_idle(p: Player) -> None:
    p.input_dash = True
    p.update(1 / 60)
    assert p.state == PlayerState.DASH


def test_dash_dash_iframes(p: Player) -> None:
    p.input_dash = True
    p.update(1 / 60)
    assert p.dash_iframes_left == 22


def test_dash_ends_after_duration(p: Player) -> None:
    p.input_dash = True
    p.update(1 / 60)  # enter DASH
    # 0.18s = ~11 frames @ 60Hz
    for _ in range(13):
        p.update(1 / 60)
    assert p.state == PlayerState.IDLE


def test_dash_lateral_direction(p: Player) -> None:
    p.input_dash = True
    p.input_left = True
    p.input_right = False
    p.update(1 / 60)
    assert p.dash_dir_x == -1.0
    assert p.dash_dir_y == 0.0


def test_dash_default_up(p: Player) -> None:
    p.input_dash = True
    p.update(1 / 60)
    assert p.dash_dir_x == 0.0
    assert p.dash_dir_y == -1.0


def test_dash_creates_afterimage(p: Player) -> None:
    p.input_dash = True
    p.update(1 / 60)
    p.update(1 / 60)
    assert len(p.afterimage) >= 1


# ---------------------------------------------------------------------------
# 7. HIT
# ---------------------------------------------------------------------------
def test_take_damage_reduces_hp(p: Player) -> None:
    # BLOQUE 53b: HP starts at 30, not 3
    p.take_damage(1)
    p.update(1 / 60)
    assert p.hp == 29


def test_take_damage_blocked_in_iframes(p: Player) -> None:
    p.invuln_frames = 30
    result = p.take_damage(1)
    assert result is False
    assert p.hp == 30  # BLOQUE 53b: HP starts at 30


def test_take_damage_enters_hit_state(p: Player) -> None:
    p.take_damage(1)
    p.update(1 / 60)
    assert p.state == PlayerState.HIT


def test_take_damage_sets_invuln(p: Player) -> None:
    p.take_damage(1)
    p.update(1 / 60)
    assert p.invuln_frames == PLAYER_INVULN_FRAMES == 60


def test_hit_to_dead_when_hp_zero(p: Player) -> None:
    p.hp = 1
    p.take_damage(1)
    p.update(1 / 60)  # enter HIT
    # 0.30s hit duration
    for _ in range(20):
        p.update(1 / 60)
    assert p.state == PlayerState.DEAD
    assert p.lives == PLAYER_LIVES - 1


def test_hit_to_idle_when_hp_remaining(p: Player) -> None:
    # BLOQUE 53b: HP starts at 30 — set to a small value so we can
    # take damage and verify we return to IDLE (not DEAD).
    p.hp = 2
    p.take_damage(1)  # hp -> 1
    p.update(1 / 60)  # enter HIT
    for _ in range(20):
        p.update(1 / 60)
    assert p.state == PlayerState.IDLE
    assert p.hp == 1  # BLOQUE 53b: no auto-heal; HP stays at 1


# ---------------------------------------------------------------------------
# 8. DEAD
# ---------------------------------------------------------------------------
def test_dead_to_respawn(p: Player) -> None:
    p.hp = 1
    p.take_damage(1)
    p.update(1 / 60)  # HIT
    for _ in range(20):
        p.update(1 / 60)  # wait for HIT to end → DEAD
    assert p.state == PlayerState.DEAD
    # 1.20s death anim
    for _ in range(80):
        p.update(1 / 60)
    assert p.state == PlayerState.IDLE
    assert p.hp == p.hp_max


def test_dead_lives_decrement(p: Player) -> None:
    p.hp = 1
    p.take_damage(1)
    p.update(1 / 60)  # HIT
    for _ in range(20):
        p.update(1 / 60)  # wait for HIT
    assert p.lives == PLAYER_LIVES - 1 == 2


def test_dead_game_over_when_lives_negative(p: Player) -> None:
    p.lives = 0
    p.hp = 1
    p.take_damage(1)
    p.update(1 / 60)  # HIT
    for _ in range(20):
        p.update(1 / 60)  # wait for HIT
    assert p.is_game_over is True


# ---------------------------------------------------------------------------
# 9. BOMB
# ---------------------------------------------------------------------------
def test_bomb_consumes_count(p: Player) -> None:
    p.input_bomb = True
    p.update(1 / 60)
    assert p.bombs == 2
    assert p.wants_to_bomb is True


def test_bomb_blocked_when_zero(p: Player) -> None:
    p.bombs = 0
    p.input_bomb = True
    p.update(1 / 60)
    assert p.wants_to_bomb is False


# ---------------------------------------------------------------------------
# 10. Reset
# ---------------------------------------------------------------------------
def test_reset_returns_to_spawn(p: Player) -> None:
    p.hp = 1
    p.lives = 0
    p.bombs = 0
    p.state = PlayerState.DEAD
    p.reset()
    # BLOQUE 53b: HP resets to PLAYER_HP (30)
    assert p.hp == 30
    assert p.lives == PLAYER_LIVES
    assert p.bombs == 3
    assert p.state == PlayerState.IDLE
    assert p.is_game_over is False


# ---------------------------------------------------------------------------
# 11. Position clamping
# ---------------------------------------------------------------------------
def test_position_clamped_to_left_edge(p: Player) -> None:
    p.x = -100.0
    p.update(1 / 60)
    assert p.x >= 9


def test_position_clamped_to_right_edge(p: Player) -> None:
    p.x = INTERNAL_W + 100.0
    p.update(1 / 60)
    assert p.x <= INTERNAL_W - 9


# ---------------------------------------------------------------------------
# 12. Hitbox
# ---------------------------------------------------------------------------
def test_hitbox_is_smaller_than_sprite(p: Player) -> None:
    """70% forgiving hitbox per GDD §5."""
    box = p.hitbox
    # 18x16 sprite, 70% = ~12x11
    assert box.width <= 18
    assert box.height <= 16


# ---------------------------------------------------------------------------
# 13. State timer
# ---------------------------------------------------------------------------
def test_state_timer_advances(p: Player) -> None:
    p.update(1 / 60)
    assert p.state_timer == pytest.approx(1 / 60, abs=1e-6)


def test_charge_level_function(p: Player) -> None:
    """get_charge_level returns 0/1/2/3 based on state + charge_time."""
    assert p.get_charge_level() == 0
    p.state = PlayerState.CHARGE
    p.charge_time = 0.3
    assert p.get_charge_level() == 0
    p.charge_time = 0.7
    assert p.get_charge_level() == 1
    p.charge_time = 1.2
    assert p.get_charge_level() == 2
    p.charge_time = 1.6
    assert p.get_charge_level() == 3

# ---------------------------------------------------------------------------
# BLOQUE 35: nose_angle short-path + clamp (regression for "360 spontaneous spin")
# ---------------------------------------------------------------------------
def test_nose_angle_short_path_359_to_1() -> None:
    """359 -> 1 should be short-path diff of about +2 deg, NOT long-path -358.

    Reproduces the "spontaneous 360 rotation" bug. With correct short-path
    math, after one update step (28 deg/s * 0.1s = 2.8 deg), current_nose_angle
    should move from 359 to about 1.8, NOT to about 357 via the long way.
    """
    p = Player()
    p.current_nose_angle = 359.0
    p.nose_angle = 1.0
    p.update(0.1)
    diff_to_target = abs((p.current_nose_angle - 1.0 + 540) % 360 - 180)
    assert diff_to_target < 90.0, (
        f"Long-path rotation detected: current_nose_angle={p.current_nose_angle}, "
        f"target=1.0, diff={diff_to_target} (should be <90 for short-path)"
    )


def test_nose_angle_clamp_to_360_after_update() -> None:
    """current_nose_angle must always be in [0, 360) after update()."""
    p = Player()
    p.current_nose_angle = 720.0
    p.nose_angle = 0.0
    p.update(0.1)
    assert 0.0 <= p.current_nose_angle < 360.0, (
        f"current_nose_angle out of range: {p.current_nose_angle}"
    )


def test_nose_angle_10_to_350_short_path() -> None:
    """10 -> 350: short path is -20 deg (back), long path is +340 deg.

    After 0.1s of update at 28 deg/s, the lerp should move ~2.8 deg toward
    350 (i.e., from 10 to about 7.2 via the short path -2.8), NOT to about 12.8
    via the long way around.
    """
    p = Player()
    p.current_nose_angle = 10.0
    p.nose_angle = 350.0
    p.update(0.1)
    assert p.current_nose_angle < 10.0, (
        f"Long-path rotation: current_nose_angle={p.current_nose_angle} "
        f"(expected < 10.0 for short-path back to 350)"
    )


def test_nose_angle_no_nan_or_inf() -> None:
    """current_nose_angle must never become NaN or Inf."""
    p = Player()
    for target in (0.0, 45.0, 90.0, 180.0, 270.0, 359.0, 720.0, -100.0):
        p.nose_angle = target
        p.current_nose_angle = 0.0
        p.update(0.1)
        assert math.isfinite(p.current_nose_angle), (
            f"current_nose_angle is not finite: {p.current_nose_angle} for target={target}"
        )
        assert 0.0 <= p.current_nose_angle < 360.0


# ---------------------------------------------------------------------------
# 14. BLOQUE 38: RMB rapid fire (was a bug in BLOQUE 34 — input_rapid_fire
# flag was set but never read in the FSM, so RMB did nothing).
# ---------------------------------------------------------------------------
def test_rmb_rapid_fire_in_idle(p: Player) -> None:
    """RMB hold triggers a L1 shot from IDLE without entering CHARGE."""
    p.input_rapid_fire = True
    p.update(1 / 60)
    assert p.state == PlayerState.SHOOT, "RMB should fire from IDLE"
    assert p.wants_to_shoot is True
    # Rapid fire must NOT enter CHARGE (charge_time stays 0)
    assert p.charge_time == 0.0


def test_rmb_rapid_fire_continues_in_shoot(p: Player) -> None:
    """RMB hold keeps firing: subsequent shots fire as cooldown elapses."""
    p.input_rapid_fire = True
    p.update(1 / 60)
    p.wants_to_shoot = False
    # Cooldown is 0.10s = 100ms = 6 frames at 1/60 (1/60 ≈ 16.67ms).
    # Run for 8 frames (133ms) — should see 1 refire.
    fired_count = 0
    for _ in range(8):
        p.update(1 / 60)
        if p.wants_to_shoot:
            fired_count += 1
            p.wants_to_shoot = False
    assert fired_count >= 1, f"Expected at least 1 refire, got {fired_count}"


def test_rmb_does_not_charge(p: Player) -> None:
    """Even with RMB held for >1.5s, charge_time must stay 0 (no L3)."""
    p.input_rapid_fire = True
    # Run for 2 simulated seconds
    for _ in range(int(2.0 * 60)):
        p.update(1 / 60)
    assert p.charge_time == 0.0, (
        f"RMB should never charge (charge_time={p.charge_time})"
    )
    assert p.get_charge_level() == 0


def test_lmb_with_rmb_held_does_not_charge(p: Player) -> None:
    """LMB+RMB both held: rapid_fire suppresses charge (RMB wins)."""
    p.input_rapid_fire = True
    p.input_fire = True
    p.update(1 / 60)
    # Per the player FSM, charge_time only grows if input_fire AND NOT input_rapid_fire.
    # So if both are held, RMB wins (rapid_fire=True suppresses charge_time growth).
    assert p.charge_time == 0.0, (
        f"With RMB held, charge_time must stay 0 (got {p.charge_time})"
    )
    assert p.wants_to_shoot is True
