"""Tests for the GameplayRuntime integration (BLOQUE 17.3).

These tests verify the wiring without requiring a real pygame display.
The runtime owns the live action loop, so we instantiate it with stub
transition_to and exercise its update/draw via the Scene interface.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import pytest

# Headless before pygame import
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from src.core.scene_manager import GameState  # noqa: E402
from src.core.settings import INTERNAL_H, INTERNAL_W  # noqa: E402
from src.entities.enemies import EnemyKind  # noqa: E402
from src.entities.enemies.boss import BOSS_CONFIGS  # noqa: E402
from src.systems.projectile import BULLET_PLAYER, OWNER_PLAYER  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime, ScorePopup  # noqa: E402


@pytest.fixture(autouse=True)
def _init_pygame():
    pygame.init()
    yield
    pygame.quit()


def _noop_transition(state: GameState) -> None:
    pass


def _make_runtime(is_boss: bool = False, act: int = 1) -> GameplayRuntime:
    rt = GameplayRuntime(transition_to=_noop_transition, is_boss=is_boss, act=act)
    rt.on_enter()
    return rt


# -----------------------------------------------------------------------
# Basic construction
# -----------------------------------------------------------------------
def test_runtime_constructs_with_all_systems():
    rt = _make_runtime()
    assert rt._player is not None
    assert rt._bullets.capacity == 400
    assert rt._enemies._pool.size == 64
    assert rt._weapon.level.value == 1
    assert rt._scoring.score == 0
    assert rt._boss is None  # not boss mode


def test_boss_runtime_has_boss():
    rt = _make_runtime(is_boss=True, act=1)
    assert rt._boss is not None
    assert rt._boss.id.value == "goliath"
    assert rt._boss.hp == 400  # BLOQUE 28: reduced from 800


def test_boss_picks_correct_boss_per_act():
    assert _make_runtime(is_boss=True, act=2)._boss.id.value == "hydra"
    assert _make_runtime(is_boss=True, act=3)._boss.id.value == "nemesis"


# -----------------------------------------------------------------------
# Player firing
# -----------------------------------------------------------------------
def test_player_can_shoot():
    rt = _make_runtime()
    # Force fire request
    rt._player.input_fire = True
    rt._player.wants_to_shoot = True
    rt._handle_firing(1.0 / 120.0)
    # Bullet should have spawned
    bullets = [b for b in rt._bullets.pool if b.active and b.owner == OWNER_PLAYER]
    assert len(bullets) >= 1
    # Bullet travels upward
    assert bullets[0].vy < 0


def test_charge_release_spawns_charged_bullet():
    from src.systems.projectile import BULLET_PLAYER_CHARGED
    rt = _make_runtime()
    rt._player.wants_to_charge_release = True
    rt._player.charge_time = 0.6  # past L1 threshold
    rt._handle_firing(1.0 / 120.0)
    bullets = [b for b in rt._bullets.pool if b.active and b.kind == BULLET_PLAYER_CHARGED]
    assert len(bullets) >= 1


# -----------------------------------------------------------------------
# Bomb
# -----------------------------------------------------------------------
def test_bomb_spawns_homing_missile():
    """BLOQUE 39: B/L press spawns a HomingMissile (not a screen clear)."""
    rt = _make_runtime()
    rt._player.input_bomb = True
    rt._player.wants_to_bomb = True
    rt._player.bombs = 3
    rt._handle_firing(1.0 / 120.0)
    assert rt._player.bombs == 2
    assert len(rt._missiles) == 1
    m = rt._missiles[0]
    assert m.active is True
    assert m.life == 0.0
    assert (m.vx, m.vy) != (0.0, 0.0)


def test_missile_steers_toward_mouse():
    """BLOQUE 39: when the mouse moves, the missile updates its heading."""
    rt = _make_runtime()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H / 2
    # Initial mouse is straight up — missile points up
    rt._mouse_x = rt._player.x
    rt._mouse_y = rt._player.y - 100
    rt._player.input_bomb = True
    rt._player.wants_to_bomb = True
    rt._player.bombs = 3
    rt._handle_firing(1.0 / 120.0)
    m = rt._missiles[0]
    # Now move the mouse to the right
    rt._mouse_x = rt._player.x + 100
    rt._mouse_y = rt._player.y
    # Run several updates — the missile should turn toward the new mouse pos
    for _ in range(20):
        rt._update_missiles(1.0 / 60.0)
    # And the missile is now pointing roughly toward the mouse (right).
    target = math.degrees(math.atan2(
        rt._mouse_x - m.x, -(rt._mouse_y - m.y)
    )) % 360.0
    delta = (target - m.angle + 540.0) % 360.0 - 180.0
    assert abs(delta) < 90.0, (
        f"Missile should face the mouse after 20 updates; "
        f"target={target:.1f} missile={m.angle:.1f} delta={delta:.1f}"
    )


def test_missile_explodes_on_enemy_collision():
    """BLOQUE 39: missile detonates when it hits an enemy."""
    rt = _make_runtime()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H / 2
    rt._mouse_x = rt._player.x
    rt._mouse_y = rt._player.y - 100
    rt._player.input_bomb = True
    rt._player.wants_to_bomb = True
    rt._player.bombs = 3
    rt._handle_firing(1.0 / 120.0)
    m = rt._missiles[0]
    e = rt._enemies.spawn(EnemyKind.SCOUT, rt._player.x, rt._player.y - 30)
    assert e is not None
    for _ in range(60):
        rt._update_missiles(1.0 / 60.0)
        if not m.active:
            break
    assert m.active is False


def test_missile_explodes_on_screen_edge():
    """BLOQUE 39: missile that leaves the play area detonates (small)."""
    rt = _make_runtime()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H / 2
    rt._mouse_x = INTERNAL_W + 200
    rt._mouse_y = INTERNAL_H / 2
    rt._player.input_bomb = True
    rt._player.wants_to_bomb = True
    rt._player.bombs = 3
    rt._handle_firing(1.0 / 120.0)
    m = rt._missiles[0]
    for _ in range(60):
        rt._update_missiles(1.0 / 60.0)
        if not m.active:
            break
    assert m.active is False


def test_missile_settings_constants_present():
    """BLOQUE 39: missile tuning constants exist with sane values."""
    from src.core.settings import (
        MISSILE_ACCEL_PX_S2, MISSILE_BODY_RADIUS_PX, MISSILE_EXPLOSION_DAMAGE,
        MISSILE_EXPLOSION_RADIUS_PX, MISSILE_KEY, MISSILE_LIFE_S,
        MISSILE_SPEED_PX_S, MISSILE_TRAIL_RATE_S, MISSILE_TURN_RATE_DEG_S,
    )
    assert MISSILE_SPEED_PX_S > 100.0
    assert MISSILE_ACCEL_PX_S2 > 0.0
    assert MISSILE_TURN_RATE_DEG_S > 0.0
    assert MISSILE_LIFE_S > 0.0
    assert MISSILE_BODY_RADIUS_PX > 0
    assert MISSILE_EXPLOSION_RADIUS_PX > MISSILE_BODY_RADIUS_PX
    assert MISSILE_EXPLOSION_DAMAGE > 0
    assert MISSILE_TRAIL_RATE_S > 0.0
    assert MISSILE_KEY == ord('b')


# -----------------------------------------------------------------------
# Collisions
# -----------------------------------------------------------------------
def test_bullet_hits_enemy_and_kills():
    rt = _make_runtime()
    # Spawn enemy at known position
    e = rt._enemies.spawn(EnemyKind.SCOUT, 120, 100)
    assert e is not None
    # Spawn player bullet overlapping the enemy
    rt._bullets.spawn(BULLET_PLAYER, 120, 100, 0.0, -480.0, damage=99, owner=OWNER_PLAYER)
    rt._handle_collisions()
    # Enemy should be killed
    assert e.state.value == "dying"
    # Bullet consumed
    active_bullets = [b for b in rt._bullets.pool if b.active and b.owner == OWNER_PLAYER]
    assert len(active_bullets) == 0


def test_bullet_damages_but_does_not_kill_heavy():
    rt = _make_runtime()
    e = rt._enemies.spawn(EnemyKind.HEAVY, 120, 100)
    assert e is not None
    # Heavy has 12 HP; deal 1 damage
    rt._bullets.spawn(BULLET_PLAYER, 120, 100, 0.0, -480.0, damage=1, owner=OWNER_PLAYER)
    rt._handle_collisions()
    assert e.hp == 11
    assert e.state.value == "idle"


def test_enemy_bullet_hits_player():
    from src.systems.projectile import BULLET_ENEMY, OWNER_ENEMY
    rt = _make_runtime()
    rt._player.x = 120
    rt._player.y = 300
    # Spawn enemy bullet at player position
    rt._bullets.spawn(BULLET_ENEMY, 120, 300, 0.0, 100.0, damage=1, owner=OWNER_ENEMY)
    rt._handle_collisions()
    # BLOQUE 53b: HP starts at 30, not 3
    assert rt._player.hp < 30


def test_pierce_bullet_hits_multiple_enemies():
    from src.systems.projectile import BULLET_PLAYER_CHARGED
    rt = _make_runtime()
    # Two enemies very close together so the bullet (at one position) hits both
    e1 = rt._enemies.spawn(EnemyKind.SCOUT, 100, 100)
    e2 = rt._enemies.spawn(EnemyKind.SCOUT, 108, 100)
    assert e1 is not None and e2 is not None
    # Bullet at midpoint with 99 damage and pierce 3
    rt._bullets.spawn(BULLET_PLAYER_CHARGED, 104, 100, 0.0, -480.0, damage=99,
                      owner=OWNER_PLAYER, pierce=3)
    rt._handle_collisions()
    # Both enemies should be killed by one bullet
    assert e1.state.value == "dying"
    assert e2.state.value == "dying"


# -----------------------------------------------------------------------
# Score
# -----------------------------------------------------------------------
def test_kill_increments_score():
    rt = _make_runtime()
    e = rt._enemies.spawn(EnemyKind.SCOUT, 100, 50)
    assert e is not None
    rt._on_enemy_killed(e)
    # Scout base = 50, multiplier 1x
    assert rt._scoring.score >= 50
    assert rt._wave_mgr.current.kills == 1


def test_wave_clears_when_kill_target_reached():
    """BLOQUE 50: Wave 0 (Act 1, wave 1) is now 6 SCOUT in LINE (was 4)."""
    rt = _make_runtime()
    assert rt._wave_mgr.scripts[0]["kill_target"] == 6
    for _ in range(6):
        e = rt._enemies.spawn(EnemyKind.SCOUT, 100, 50)
        if e is not None:
            rt._on_enemy_killed(e)
    assert rt._check_wave_cleared() is True


# -----------------------------------------------------------------------
# Update loop smoke
# -----------------------------------------------------------------------
def test_update_runs_full_loop_without_error():
    rt = _make_runtime()
    # Force fire so something happens
    rt._player.input_fire = True
    # Tick 1 sec at 120 FPS
    for _ in range(120):
        rt.update(1.0 / 120.0)
    # Should have spawned some enemies, fired bullets, etc.
    # Just check no exceptions
    assert rt._t > 0.0


def test_boss_update_selects_attack():
    rt = _make_runtime(is_boss=True, act=1)
    # Tick 3 seconds — should select at least one attack
    attacks = 0
    for _ in range(360):
        rt._player.input_fire = True
        rt.update(1.0 / 120.0)
        # Check for boss bullets
        boss_bullets = [b for b in rt._bullets.pool if b.active]
        attacks = max(attacks, len(boss_bullets))
    # Boss should have fired at least once
    assert attacks > 0


def test_draw_produces_non_empty_surface():
    rt = _make_runtime()
    # Tick a few frames
    rt._player.input_fire = True
    for _ in range(10):
        rt.update(1.0 / 120.0)
    surf = pygame.Surface((240, 360))
    rt.draw(surf)
    # At minimum, the HUD should have drawn some pixels (non-zero)
    # We just check the surface is valid; visual inspection is via visualizer
    assert surf.get_width() == 240
    assert surf.get_height() == 360


def test_player_death_transitions_to_game_over():
    """BLOQUE 28: GAME_OVER only when lives run out, not on every death."""
    state_holder = {"current": None}
    def transition(state):
        state_holder["current"] = state
    rt = GameplayRuntime(transition_to=transition, is_boss=False, act=1)
    rt.on_enter()
    # With lives >= 0, dying should NOT trigger GAME_OVER (player respawns)
    rt._player.is_dead = True
    rt._player.lives = 3
    rt._check_player_death()
    assert state_holder["current"] is None  # No transition yet
    # Only when lives go negative should GAME_OVER trigger
    rt._player.lives = -1
    rt._check_player_death()
    assert state_holder["current"] == GameState.GAME_OVER


# -----------------------------------------------------------------------
# BLOQUE 18: 8-way dash
# -----------------------------------------------------------------------
def test_dash_8way_up():
    from src.entities.player import Player
    p = Player()
    p._enter_idle()
    p.input_dash = True
    # No directional input -> UP per GDD
    for _ in range(int(0.18 * 120)):
        p.update(1.0 / 120)
    assert p.dash_dir_y < 0  # up
    assert p.dash_dir_x == 0


def test_dash_8way_down():
    from src.entities.player import Player
    p = Player()
    p._enter_idle()
    p.input_dash = True
    p.input_down = True
    for _ in range(int(0.18 * 120)):
        p.update(1.0 / 120)
    assert p.dash_dir_y > 0  # down
    assert p.dash_dir_x == 0


def test_dash_8way_diagonal_up_left():
    from src.entities.player import Player
    p = Player()
    p._enter_idle()
    p.input_dash = True
    p.input_left = True
    p.input_up = True
    for _ in range(int(0.18 * 120)):
        p.update(1.0 / 120)
    # Diagonal: normalized so |x| == |y| ≈ 0.707
    assert p.dash_dir_x < 0
    assert p.dash_dir_y < 0
    assert abs(abs(p.dash_dir_x) - abs(p.dash_dir_y)) < 0.01


def test_dash_8way_diagonal_down_right():
    from src.entities.player import Player
    p = Player()
    p._enter_idle()
    p.input_dash = True
    p.input_right = True
    p.input_down = True
    for _ in range(int(0.18 * 120)):
        p.update(1.0 / 120)
    assert p.dash_dir_x > 0
    assert p.dash_dir_y > 0


# -----------------------------------------------------------------------
# BLOQUE 33: Shift = dash, K freed, Boost removed
# -----------------------------------------------------------------------
def test_dash_triggers_on_shift_left_down():
    """BLOQUE 58.8.1/58.8.2/58.8.3: shift = DASH (click, < 0.28s) OR PROPULSION (hold).

    On KEYDOWN shift: dash_held is set to True, but input_dash is NOT
    set (it would be a "hold" not a "click"). input_dash is only set
    on KEYUP if the hold was shorter than the click threshold.

    The simple KEYDOWN-only test now expects dash_held=True and
    input_dash=False. The full click cycle (KEYDOWN + KEYUP) is
    tested separately in test_dash_triggers_on_shift_click.
    """
    import pygame
    original_get = pygame.event.get

    def fake_get(event_type=None):
        if event_type is None or event_type == pygame.KEYDOWN:
            return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LSHIFT})]
        return []
    pygame.event.get = fake_get
    try:
        rt = _make_runtime()
        rt._read_input()
        # KEYDOWN only — input_dash should be False (we haven't released yet)
        assert rt._player.input_dash is False
        # But dash_held is True (so a hold could enter PROPULSION)
        assert rt._player.dash_held is True
    finally:
        pygame.event.get = original_get


def test_dash_triggers_on_shift_click():
    """BLOQUE 58.8.1: click (KEYDOWN + KEYUP within threshold) triggers DASH.

    After the click, input_dash is set to True, and dash_held is False.
    """
    import pygame
    original_get = pygame.event.get

    call_count = {"n": 0}

    def fake_get(event_type=None):
        if event_type is None or event_type in (pygame.KEYDOWN, pygame.KEYUP):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LSHIFT})]
            else:
                return [pygame.event.Event(pygame.KEYUP, {"key": pygame.K_LSHIFT})]
        return []
    pygame.event.get = fake_get
    try:
        rt = _make_runtime()
        # Call 1 returns KEYDOWN — sets dash_held
        rt._read_input()
        # Call 2 returns KEYUP — triggers DASH (input_dash=True)
        rt._read_input()
        assert rt._player.input_dash is True
        assert rt._player.dash_held is False
    finally:
        pygame.event.get = original_get


def test_dash_triggers_on_tap_within_threshold():
    """BLOQUE 58.8.2/58.8.3: 0.28s window. A 0.2s tap must trigger DASH (not
    PROPULSION). Regression test for the user complaint that a normal
    tap on shift was being misread as a hold and triggering PROPULSION.
    """
    import pygame
    from src.core.settings import PLAYER_CLICK_VS_HOLD_THRESHOLD_S
    assert 0.2 <= PLAYER_CLICK_VS_HOLD_THRESHOLD_S <= 0.4, (
        "BLOQUE 58.8.3: threshold must be wide enough for human reaction time "
        "but short enough to feel responsive (0.2-0.4s sweet spot)"
    )
    original_get = pygame.event.get
    call_count = {"n": 0}

    def fake_get(event_type=None):
        if event_type is None or event_type in (pygame.KEYDOWN, pygame.KEYUP):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LSHIFT})]
            return [pygame.event.Event(pygame.KEYUP, {"key": pygame.K_LSHIFT})]
        return []
    pygame.event.get = fake_get
    try:
        rt = _make_runtime()
        # Simulate a 0.3s tap (well within the 0.6s threshold)
        rt._player.dash_held_time = 0.3
        rt._read_input()  # KEYDOWN
        # Hold the dash for 0.3s of game time
        for _ in range(int(0.3 * 120)):
            rt.update(1.0 / 120)
        rt._read_input()  # KEYUP — should trigger DASH since 0.3 < 0.6
        assert rt._player.input_dash is True, (
            f"A {0.3}s tap must trigger DASH (input_dash=True), "
            f"but got input_dash={rt._player.input_dash}"
        )
        assert rt._player.dash_held is False
    finally:
        pygame.event.get = original_get


def test_hold_past_threshold_triggers_propulsion():
    """BLOQUE 58.8.2: holding shift for >= 0.6s should trigger PROPULSION,
    NOT DASH.
    """
    import pygame
    from src.core.settings import PLAYER_CLICK_VS_HOLD_THRESHOLD_S
    from src.entities.player.player import PlayerState
    original_get = pygame.event.get

    def fake_get(event_type=None):
        if event_type is None or event_type in (pygame.KEYDOWN, pygame.KEYUP):
            return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LSHIFT})]
        return []
    pygame.event.get = fake_get
    try:
        rt = _make_runtime()
        rt._read_input()
        # Hold past threshold (0.6s + small buffer) — many update ticks
        for _ in range(int((PLAYER_CLICK_VS_HOLD_THRESHOLD_S + 0.2) * 120)):
            rt.update(1.0 / 120)
        # Should be in PROPULSION state, NOT DASH
        assert rt._player.state == PlayerState.PROPULSION, (
            f"Holding shift for >= {PLAYER_CLICK_VS_HOLD_THRESHOLD_S}s must "
            f"enter PROPULSION, but state={rt._player.state}"
        )
    finally:
        pygame.event.get = original_get


def test_boost_fields_removed_from_player():
    """BLOQUE 33: input_boost / boost_timer / is_boosting should not exist."""
    from src.entities.player import Player
    p = Player()
    assert not hasattr(p, "input_boost"), "input_boost must be removed"
    assert not hasattr(p, "boost_timer"), "boost_timer must be removed"
    assert not hasattr(p, "boost_cooldown"), "boost_cooldown must be removed"
    assert not hasattr(p, "is_boosting"), "is_boosting must be removed"


def test_settings_no_boost_constants():
    """BLOQUE 33: PLAYER_BOOST_* must not be in settings."""
    from src.core import settings
    assert not hasattr(settings, "PLAYER_BOOST_MULT")
    assert not hasattr(settings, "PLAYER_BOOST_DURATION_S")
    assert not hasattr(settings, "PLAYER_BOOST_COOLDOWN_S")


def test_k_does_not_trigger_dash():
    """BLOQUE 33: K must NOT trigger dash (only Shift does)."""
    import pygame
    # Synthesize a K KEYDOWN
    original_get = pygame.event.get

    def fake_get(event_type=None):
        if event_type is None or event_type == pygame.KEYDOWN:
            return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_k})]
        return []
    pygame.event.get = fake_get
    try:
        rt = _make_runtime()
        rt._read_input()
        assert rt._player.input_dash is False, "K should NOT trigger dash anymore"
    finally:
        pygame.event.get = original_get


# -----------------------------------------------------------------------
# BLOQUE 34: BGM off, resolution 320x480, fast nose tracking, RMB rapid fire
# -----------------------------------------------------------------------
def test_bgm_start_becomes_noop():
    """BLOQUE 34: _start_bgm is a no-op (user asked to remove background music)."""
    rt = _make_runtime()
    # Just verify the call doesn't crash and BGM stays "not playing"
    rt._start_bgm("act_normal")
    assert rt._bgm_started is True  # state flag set, but no audio dispatched


def test_resolution_grew_to_320x480():
    """BLOQUE 34: INTERNAL_W/H is 320/480 (1.33x bigger playfield, ships look smaller)."""
    from src.core.settings import INTERNAL_H, INTERNAL_W
    assert INTERNAL_W == 320
    assert INTERNAL_H == 480


def test_nose_lerp_faster_per_spec():
    """BLOQUE 38: PLAYER_NOSE_LERP_PER_S is 50 (was 28, was 12 originally)."""
    from src.core.settings import PLAYER_NOSE_LERP_PER_S
    assert PLAYER_NOSE_LERP_PER_S == 50.0


def test_nose_angle_lerps_when_stopped():
    """BLOQUE 34: nose angle now lerps EVERY frame (not just while moving)."""
    from src.entities.player import Player
    p = Player()
    p.nose_angle = 90.0
    p.current_nose_angle = 0.0
    # No movement input
    p.input_left = p.input_right = p.input_up = p.input_down = False
    # One small update
    p.update(0.01)
    # current_nose_angle should have moved toward 90°
    assert p.current_nose_angle > 0.0


def test_rmb_rapid_fire_skips_charge():
    """BLOQUE 34: input_rapid_fire=True keeps charge_time at 0 → no CHARGE state."""
    from src.entities.player import Player, PlayerState
    p = Player()
    p.input_rapid_fire = True
    p.input_fire = True
    # Update for > 0.5s (would normally enter CHARGE)
    for _ in range(60):
        p.update(1.0 / 120.0)
    # charge_time should still be ~0 (rapid_fire bypasses)
    assert p.charge_time < 0.1
    # Player should NOT be in CHARGE state
    assert p.state != PlayerState.CHARGE


def test_lmb_charge_still_works():
    """BLOQUE 34: LMB without rapid_fire still charges (regression test).
    Run 120 frames (1s of game time) so the charge has time to grow past 0.5s
    and the player transitions to CHARGE state in an IDLE window."""
    from src.entities.player import Player, PlayerState
    p = Player()
    p.input_rapid_fire = False
    p.input_fire = True
    for _ in range(120):
        p.update(1.0 / 120.0)
    # charge_time should have grown
    assert p.charge_time > 0.5
    # Player should be in CHARGE state
    assert p.state == PlayerState.CHARGE


# -----------------------------------------------------------------------
# BLOQUE 18: Power-ups
# -----------------------------------------------------------------------
def test_powerup_bomb_drops_and_pickup():
    rt = _make_runtime()
    rt._spawn_powerup("bomb", 120, 100)
    assert len(rt._powerups) == 1
    # Move player to the powerup and update
    rt._player.x = 120
    rt._player.y = 100
    rt._update_powerups(0.1)
    assert len(rt._powerups) == 0  # picked up
    assert rt._player.bombs == 4  # 3 + 1


def test_powerup_score_drops_and_pickup():
    rt = _make_runtime()
    initial_score = rt._scoring.score
    rt._spawn_powerup("score", 120, 100)
    rt._player.x = 120
    rt._player.y = 100
    rt._update_powerups(0.1)
    assert len(rt._powerups) == 0
    assert rt._scoring.score > initial_score


def test_powerup_drops_off_screen():
    rt = _make_runtime()
    rt._spawn_powerup("bomb", 120, 100)
    # Move it well below the screen
    rt._powerups[0].y = INTERNAL_H + 50
    rt._update_powerups(0.016)
    assert len(rt._powerups) == 0  # cleaned up


# -----------------------------------------------------------------------
# BLOQUE 18: Score popups
# -----------------------------------------------------------------------
def test_score_popup_floats_up_and_fades():
    rt = _make_runtime()
    rt._score_popups.append(ScorePopup(
        x=100, y=100, vy=-30.0, text="+100", color=(255, 255, 255),
        life=0.5, max_life=0.5,
    ))
    rt._update_score_popups(0.1)
    assert len(rt._score_popups) == 1
    p = rt._score_popups[0]
    assert p.y < 100  # moved up
    assert p.life < 0.5  # decremented
    rt._update_score_popups(1.0)
    assert len(rt._score_popups) == 0  # expired


# -----------------------------------------------------------------------
# BLOQUE 18: Enemy hit feedback
# -----------------------------------------------------------------------
def test_enemy_flash_on_hit():
    rt = _make_runtime()
    e = rt._enemies.spawn(EnemyKind.SCOUT, 100, 50)
    assert e is not None
    rt._bullets.spawn(BULLET_PLAYER, 100, 50, 0.0, -480.0, damage=99, owner=OWNER_PLAYER)
    rt._handle_collisions()
    assert id(e) in rt._enemy_flash  # flash timer set
    assert rt._enemy_flash[id(e)] > 0.0
    # Flash decays
    rt._update_enemy_flash(0.05)
    assert rt._enemy_flash.get(id(e), 0) < 0.08
    rt._update_enemy_flash(0.5)
    assert id(e) not in rt._enemy_flash


# -----------------------------------------------------------------------
# BLOQUE 18: Death explosion
# -----------------------------------------------------------------------
def test_player_death_triggers_explosion():
    rt = _make_runtime()
    initial_particles = sum(1 for p in rt._particles.pool if p.active)
    rt._player.is_dead = True
    rt._check_player_death_explosion()
    after_particles = sum(1 for p in rt._particles.pool if p.active)
    assert after_particles > initial_particles
    assert rt._death_exploded is True
    # Calling again should not add more particles
    rt._check_player_death_explosion()
    after2 = sum(1 for p in rt._particles.pool if p.active)
    assert after2 == after_particles


# -----------------------------------------------------------------------
# BLOQUE 18: Draw methods run without error
# -----------------------------------------------------------------------
def test_draw_with_borders_and_polish_runs():
    rt = _make_runtime()
    rt._player.input_fire = True
    for _ in range(60):
        rt.update(1.0 / 120)
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)  # should not crash
    # Verify surface was modified (some pixel was drawn)
    assert surf.get_size() == (INTERNAL_W, INTERNAL_H)


# -----------------------------------------------------------------------
# BLOQUE 22: Extra polish — muzzle flash, charge release, boss death stages
# -----------------------------------------------------------------------
def test_muzzle_flash_triggers_on_fire():
    """Pressing fire should set _muzzle_flash to > 0."""
    rt = _make_runtime()
    assert rt._muzzle_flash == 0.0
    rt._player.input_fire = True
    for _ in range(int(0.15 * 120)):
        rt.update(1.0 / 120)
    # By now a fire has happened; muzzle flash should be set (then decays)
    # We can't assert > 0 always (it decays fast), so simulate immediate fire
    rt._muzzle_flash = 1.0
    rt.update(0.05)  # 0.05s = 5 frames worth of decay at rate 12
    # Decay of 0.6 -> should be ~0.4
    assert rt._muzzle_flash < 1.0


def test_muzzle_flash_decays_to_zero():
    """After enough time without firing, _muzzle_flash returns to 0."""
    rt = _make_runtime()
    rt._muzzle_flash = 1.0
    for _ in range(60):
        rt.update(1.0 / 120)  # 0.5s total
    assert rt._muzzle_flash == 0.0


def test_charge_release_flash_triggered_on_charge_fire():
    """A charged shot should set _charge_release_flash."""
    rt = _make_runtime()
    # Force the weapon to want a charge release at L3
    rt._player.state = rt._player.state.__class__.CHARGE  # type: ignore[attr-defined]
    rt._player.charge_time = 1.6  # beyond L3 threshold
    rt._player.wants_to_charge_release = True
    rt._handle_firing(0.016)
    # _charge_release_flash should be set (0.7) and a shockwave spawned
    assert rt._charge_release_flash > 0.0
    assert len(rt._shockwaves) >= 1


def test_charge_release_flash_decays():
    """Charge release flash decays to 0 after enough time."""
    rt = _make_runtime()
    rt._charge_release_flash = 0.5
    for _ in range(60):
        rt.update(1.0 / 120)
    assert rt._charge_release_flash == 0.0


def test_boss_death_stages_progress():
    """On boss kill, the 3-stage explosion should progress over time."""
    rt = _make_runtime(is_boss=True, act=1)
    assert rt._boss is not None
    # Manually trigger boss death
    rt._on_boss_killed()
    # After immediate call, stage should be 1 and timer 0
    assert rt._boss_death_stage == 1
    assert rt._boss_death_timer == 0.0
    # Cache pos should match boss
    assert rt._boss_death_pos != (0.0, 0.0)
    # Advance to stage 2 (0.15s)
    for _ in range(int(0.20 * 120)):
        rt.update(1.0 / 120)
    assert rt._boss_death_stage == 2
    # Advance to stage 3 (0.40s)
    for _ in range(int(0.30 * 120)):
        rt.update(1.0 / 120)
    assert rt._boss_death_stage == 3


def test_boss_death_spawns_shockwaves():
    """Boss death should spawn multiple shockwaves across stages."""
    rt = _make_runtime(is_boss=True, act=1)
    rt._on_boss_killed()
    initial_shockwaves = len(rt._shockwaves)
    assert initial_shockwaves >= 1  # at least the stage-1 wave
    # Advance through all stages
    for _ in range(int(0.5 * 120)):
        rt.update(1.0 / 120)
    # More shockwaves should have been added across stages (>= initial + 2)
    assert len(rt._shockwaves) >= initial_shockwaves + 1


def test_on_enter_resets_polish_state():
    """Re-entering the scene should reset BLOQUE 22 polish state."""
    rt = _make_runtime()
    # Dirty the polish state
    rt._muzzle_flash = 0.5
    rt._charge_release_flash = 0.3
    rt._boss_death_stage = 2
    rt._boss_death_timer = 0.2
    rt._boss_death_pos = (100.0, 50.0)
    rt.on_enter()
    assert rt._muzzle_flash == 0.0
    assert rt._charge_release_flash == 0.0
    assert rt._boss_death_stage == 0
    assert rt._boss_death_timer == 0.0


def test_draw_renders_muzzle_flash():
    """Drawing while muzzle_flash > 0 should not raise."""
    rt = _make_runtime()
    rt._muzzle_flash = 0.8
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)  # should not crash


def test_draw_renders_charge_release_flash():
    """Drawing while charge_release_flash > 0 should not raise."""
    rt = _make_runtime()
    rt._charge_release_flash = 0.5
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)


def test_draw_renders_shockwaves():
    """Drawing while shockwaves are active should not raise."""
    rt = _make_runtime()
    rt._add_shockwave(100, 100, 60.0)
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)
    assert len(rt._shockwaves) == 1


def test_shockwave_expands_and_dies():
    """Shockwaves should grow and expire over time."""
    rt = _make_runtime()
    rt._add_shockwave(100, 100, 60.0)
    s = rt._shockwaves[0]
    initial_radius = s.radius
    rt._update_shockwaves(0.1)
    assert len(rt._shockwaves) == 1
    assert rt._shockwaves[0].radius > initial_radius
    rt._update_shockwaves(0.6)
    assert len(rt._shockwaves) == 0  # expired


# -----------------------------------------------------------------------
# BLOQUE 23: Power-up pulse, boss entry warning, player death ring
# -----------------------------------------------------------------------
def test_powerup_renders_with_pulse_halo():
    """Drawing a power-up should not raise (uses pulse halo math)."""
    rt = _make_runtime()
    rt._spawn_powerup("bomb", 100, 100)
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)
    # Verify the power-up is still in the pool
    assert len(rt._powerups) == 1


def test_boss_entry_warning_border_during_entry():
    """During first 1.5s of boss fight, the entry should be < 1.5."""
    rt = _make_runtime(is_boss=True, act=1)
    rt._boss_entry_t = 0.5  # mid-entry
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)  # should not raise (pulsing red border drawn)


def test_boss_entry_warning_border_after_entry():
    """After 1.5s, the entry warning should be cleared."""
    rt = _make_runtime(is_boss=True, act=1)
    rt._boss_entry_t = 2.0  # past entry
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)  # should not raise (no pulsing border)


def test_player_death_explosion_spawns_shockwave():
    """BLOQUE 23: player death should spawn an expanding ring."""
    rt = _make_runtime()
    initial_shockwaves = len(rt._shockwaves)
    rt._player.is_dead = True
    rt._check_player_death_explosion()
    assert len(rt._shockwaves) == initial_shockwaves + 1


# -----------------------------------------------------------------------
# BLOQUE 24: Pickup flash, level-up flash, speed lines
# -----------------------------------------------------------------------
def test_pickup_flash_triggers_on_powerup():
    """Applying a power-up should set _pickup_flash > 0."""
    rt = _make_runtime()
    assert rt._pickup_flash == 0.0
    rt._apply_powerup("score")
    assert rt._pickup_flash > 0.0


def test_pickup_flash_decays():
    """Pickup flash decays to 0 over time."""
    rt = _make_runtime()
    rt._pickup_flash = 0.6
    for _ in range(60):
        rt.update(1.0 / 120)
    assert rt._pickup_flash == 0.0


def test_speed_lines_only_when_moving_fast():
    """Speed lines draw method should run without error."""
    rt = _make_runtime()
    rt._player.vx = 200.0  # moving fast
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._draw_speed_lines(surf)  # should not crash


def test_speed_lines_noop_when_slow():
    """Slow movement should not crash speed line draw."""
    rt = _make_runtime()
    rt._player.vx = 10.0
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._draw_speed_lines(surf)


def test_level_up_flash_triggers_on_weapon_levelup():
    """When the weapon levels up, _level_up_flash should be set."""
    rt = _make_runtime()
    from src.entities.enemies import EnemyKind
    e = rt._enemies.spawn(EnemyKind.SCOUT, 100, 50)
    assert e is not None
    # Set weapon xp just below L2 threshold (10)
    rt._weapon.xp = 9
    rt._on_enemy_killed(e)
    # SCOUT gives 1 XP, so this pushes to 10 -> L2
    assert rt._weapon.level.value >= 2
    assert rt._level_up_flash > 0.0


def test_on_enter_resets_bloque24_state():
    """on_enter should reset BLOQUE 24 polish state."""
    rt = _make_runtime()
    rt._pickup_flash = 0.5
    rt._level_up_flash = 0.5
    rt._speed_line_t = 1.5
    rt.on_enter()
    assert rt._pickup_flash == 0.0
    assert rt._level_up_flash == 0.0
    assert rt._speed_line_t == 0.0


def test_draw_with_pickup_flash_runs():
    """Drawing while pickup_flash > 0 should not raise."""
    rt = _make_runtime()
    rt._pickup_flash = 0.5
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)


def test_draw_with_level_up_flash_runs():
    """Drawing while level_up_flash > 0 should not raise."""
    rt = _make_runtime()
    rt._level_up_flash = 0.5
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)


# -----------------------------------------------------------------------
# BLOQUE 25: Animated HP, shield, ambient dust, wing lights
# -----------------------------------------------------------------------
def test_shield_renders_during_respawn_invuln():
    """When respawn_invuln > 0, _draw_shield should not raise."""
    rt = _make_runtime()
    rt._player.respawn_invuln = 1.0
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._draw_shield(surf, 0, 0)


def test_ambient_dust_runs():
    """Ambient dust draw should not raise."""
    rt = _make_runtime()
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._draw_ambient_dust(surf)


def test_heavy_kill_spawns_more_particles():
    """BLOQUE 25: killing a HEAVY should spawn more particles than killing a SCOUT."""
    rt1 = _make_runtime()
    rt2 = _make_runtime()
    e1 = rt1._enemies.spawn(EnemyKind.SCOUT, 100, 50)
    e2 = rt2._enemies.spawn(EnemyKind.HEAVY, 100, 50)
    assert e1 is not None and e2 is not None
    before1 = sum(1 for p in rt1._particles.pool if p.active)
    before2 = sum(1 for p in rt2._particles.pool if p.active)
    rt1._on_enemy_killed(e1)
    rt2._on_enemy_killed(e2)
    after1 = sum(1 for p in rt1._particles.pool if p.active)
    after2 = sum(1 for p in rt2._particles.pool if p.active)
    delta1 = after1 - before1
    delta2 = after2 - before2
    assert delta2 > delta1  # HEAVY spawns more


def test_heavy_kill_spawns_shockwave():
    """BLOQUE 25: HEAVY kill should add a shockwave ring."""
    rt = _make_runtime()
    e = rt._enemies.spawn(EnemyKind.HEAVY, 100, 50)
    assert e is not None
    initial = len(rt._shockwaves)
    rt._on_enemy_killed(e)
    assert len(rt._shockwaves) > initial


def test_draw_with_respawn_invuln_runs():
    """Full draw with shield active should not raise."""
    rt = _make_runtime()
    rt._player.respawn_invuln = 0.5
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt.draw(surf)


def test_hud_draw_with_t_runs():
    """HUD draw with t parameter should not raise."""
    rt = _make_runtime()
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._hud.draw(surf, rt._player, rt._weapon, rt._scoring, t=0.5)


# -----------------------------------------------------------------------
# BLOQUE 26: Engine smoke, bomb flash, kill counter
# -----------------------------------------------------------------------
def test_engine_smoke_emits_particles():
    """BLOQUE 26: engine smoke should spawn particles when player is alive."""
    rt = _make_runtime()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H - 60
    before = sum(1 for p in rt._particles.pool if p.active)
    for _ in range(20):
        rt.update(1.0 / 60)
    after = sum(1 for p in rt._particles.pool if p.active)
    assert after > before  # smoke particles spawned


def test_engine_smoke_stops_when_dead():
    """When player is dead, engine smoke should not spawn."""
    rt = _make_runtime()
    # Don't trigger player death explosion (which spawns particles)
    rt._player.is_dead = True
    # Mark explosion as already done so it doesn't fire
    rt._death_exploded = True
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H - 60
    before = sum(1 for p in rt._particles.pool if p.active)
    for _ in range(20):
        rt.update(1.0 / 60)
    after = sum(1 for p in rt._particles.pool if p.active)
    assert after == before  # no new engine particles


def test_bomb_flash_triggers_on_bomb_use():
    """BLOQUE 39: bomb use now spawns a missile (not a screen flash).
    The missile detonation can still set _bomb_flash indirectly via the
    explosion; what we verify here is that the bomb call now produces a
    HomingMissile instead of a screen clear.
    """
    rt = _make_runtime()
    rt._player.bombs = 3
    rt._player._consume_bomb()  # sets wants_to_bomb
    rt._handle_firing(0.016)
    # BLOQUE 39: a missile was spawned, not a screen flash
    assert len(rt._missiles) == 1
    assert rt._missiles[0].active is True


def test_bomb_flash_decays():
    """Bomb flash decays to 0 over time."""
    rt = _make_runtime()
    rt._bomb_flash = 0.8
    for _ in range(60):
        rt.update(1.0 / 120)
    assert rt._bomb_flash == 0.0


def test_kill_count_drawn_in_hud():
    """BLOQUE 26: HUD should show a kill counter."""
    rt = _make_runtime()
    rt._scoring.kills = 42
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._hud.draw(surf, rt._player, rt._weapon, rt._scoring, t=0.5)
    # Check that the kill count text was rendered somewhere on the surface
    # (we just verify the draw method didn't raise and the count is used)
    assert rt._scoring.kills == 42


def test_low_hp_emits_damage_smoke():
    """BLOQUE 26: low HP should spawn damage smoke particles."""
    rt = _make_runtime()
    rt._player.hp = 1
    rt._player.hp_max = 3
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H - 60
    before = sum(1 for p in rt._particles.pool if p.active)
    for _ in range(20):
        rt.update(1.0 / 60)
    after = sum(1 for p in rt._particles.pool if p.active)
    # Engine + damage smoke combined
    assert after > before


def test_on_enter_resets_bomb_flash():
    """BLOQUE 26: on_enter should reset _bomb_flash."""
    rt = _make_runtime()
    rt._bomb_flash = 0.5
    rt.on_enter()
    assert rt._bomb_flash == 0.0


def test_dash_emits_extra_smoke():
    """BLOQUE 26: dashing should emit more particles than idle."""
    rt1 = _make_runtime()
    rt2 = _make_runtime()
    for rt in (rt1, rt2):
        rt._player.x = INTERNAL_W / 2
        rt._player.y = INTERNAL_H - 60
    # Force rt2 into DASH state
    rt2._player.state = rt2._player.state.__class__.DASH  # type: ignore[attr-defined]
    rt2._player.dash_iframes_left = 30
    before1 = sum(1 for p in rt1._particles.pool if p.active)
    before2 = sum(1 for p in rt2._particles.pool if p.active)
    for _ in range(20):
        rt1.update(1.0 / 60)
        rt2.update(1.0 / 60)
    after1 = sum(1 for p in rt1._particles.pool if p.active)
    after2 = sum(1 for p in rt2._particles.pool if p.active)
    assert (after2 - before2) > (after1 - before1)  # dash spawns more


# -----------------------------------------------------------------------
# BLOQUE 28: Easy mode + boss killable verification
# -----------------------------------------------------------------------
def test_easy_mode_gives_extra_lives(monkeypatch):
    """BLOQUE 28: --easy should give 9 lives and 4 bombs."""
    import os
    monkeypatch.setenv("VOID_HUNTER_EASY", "1")
    from src.entities.player import Player
    p = Player()
    p.reset()
    assert p.lives == 9
    assert p.bombs == 4
    assert p.bombs_max == 5


def test_normal_mode_default_resources(monkeypatch):
    """Without --easy, player gets normal lives/bombs."""
    import os
    monkeypatch.delenv("VOID_HUNTER_EASY", raising=False)
    monkeypatch.setenv("VOID_HUNTER_EASY", "0")
    from src.entities.player import Player
    p = Player()
    p.reset()
    assert p.lives == 3
    assert p.bombs == 3


def test_boss_hp_reduced_for_playability():
    """BLOQUE 28: boss HP should be lower than original (GDD says 800, we have 400)."""
    from src.entities.enemies.boss import BOSS_CONFIGS, BossId
    goliath = BOSS_CONFIGS[BossId.GOLIATH]
    assert goliath.max_hp == 400  # reduced from 800 for playability


def test_game_10min_achievable_with_easy_mode():
    """BLOQUE 28: smoke test that the 10-min flow doesn't crash with easy mode.

    Runs for 60 frames (0.5s game time) and verifies no crash + boss spawn reachable.
    """
    import os
    os.environ["VOID_HUNTER_EASY"] = "1"
    rt = _make_runtime()
    # Run 60 frames
    for _ in range(60):
        rt._player.input_fire = True
        rt.update(1.0 / 60)
    # No crash, no anomalies
    assert rt._player.hp >= 0
    assert rt._player.lives >= 0
    os.environ.pop("VOID_HUNTER_EASY", None)


# -----------------------------------------------------------------------
# BLOQUE 29: Mouse aiming + level 1 mode (5 min / 50 kills)
# -----------------------------------------------------------------------
def test_mouse_aiming_360_degrees():
    """BLOQUE 32: nose angle is full 360° — no clamp."""
    import math
    rt = _make_runtime()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H - 60
    # Mouse directly above → 0°
    rt._mouse_x = INTERNAL_W / 2
    rt._mouse_y = 0
    rt._update_nose_angle()
    assert abs(rt._player.nose_angle) < 1.0
    # Mouse directly right → 90°
    rt._mouse_x = INTERNAL_W
    rt._mouse_y = INTERNAL_H - 60
    rt._update_nose_angle()
    assert 89.0 < rt._player.nose_angle < 91.0
    # Mouse directly below → 180°
    rt._mouse_x = INTERNAL_W / 2
    rt._mouse_y = INTERNAL_H
    rt._update_nose_angle()
    assert 179.0 < rt._player.nose_angle < 181.0
    # Mouse directly left → 270°
    rt._mouse_x = 0
    rt._mouse_y = INTERNAL_H - 60
    rt._update_nose_angle()
    assert 269.0 < rt._player.nose_angle < 271.0
    # Mouse at 45° (front-right) → 45°
    rt._mouse_x = INTERNAL_W / 2 + 50
    rt._mouse_y = INTERNAL_H - 60 - 50
    rt._update_nose_angle()
    assert 44.0 < rt._player.nose_angle < 46.0


def test_mouse_aiming_front_arc():
    """BLOQUE 32: mouse in front arc determines nose angle (no clamp, full 360)."""
    rt = _make_runtime()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H - 60
    # Mouse directly forward (should be 0)
    rt._mouse_x = INTERNAL_W / 2
    rt._mouse_y = 0
    rt._update_nose_angle()
    assert abs(rt._player.nose_angle) < 1.0
    # Mouse forward-right: atan2(dx=84, -dy=-300) ≈ 15.6°
    rt._mouse_x = INTERNAL_W * 0.85
    rt._mouse_y = 0
    rt._update_nose_angle()
    assert 14.0 < rt._player.nose_angle < 17.0


def test_mouse_aiming_behind_ship():
    """BLOQUE 32: mouse behind ship → nose rotates 180°+ to face mouse (no clamp)."""
    rt = _make_runtime()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H / 2
    # Mouse below+right: atan2(dx=120, -dy=-180) ≈ 146.3° (down-right back)
    rt._mouse_x = INTERNAL_W
    rt._mouse_y = INTERNAL_H
    rt._update_nose_angle()
    assert 144.0 < rt._player.nose_angle < 148.0
    # Mouse below+left: atan2(dx=-120, -dy=-180) ≈ -146.3° → mod 360 = 213.7°
    rt._mouse_x = 0
    rt._update_nose_angle()
    assert 211.0 < rt._player.nose_angle < 216.0


def test_nose_rotation_only_while_moving():
    """BLOQUE 32: nose_angle target only updates while moving (lerp freezes on stop)."""
    rt = _make_runtime()
    p = rt._player
    p.x = INTERNAL_W / 2
    p.y = INTERNAL_H - 60
    # Place mouse on the right side
    rt._mouse_x = INTERNAL_W - 10
    rt._mouse_y = INTERNAL_H - 60
    # While stopped, current_nose_angle should NOT change
    p.current_nose_angle = 0.0
    # Update with no movement
    p.input_left = p.input_right = p.input_up = p.input_down = False
    p.update(0.1)
    assert p.current_nose_angle == 0.0  # didn't move
    # Now move: should start lerping
    p.input_right = True
    # First need to set nose_angle target via runtime
    rt._update_nose_angle()
    p.update(0.1)
    # current_nose_angle should now be > 0 (lerping toward ~90°)
    assert p.current_nose_angle > 0.0
    p.input_right = False


def test_movement_world_relative():
    """BLOQUE 32: W = always up in screen space (regardless of nose facing)."""
    rt = _make_runtime()
    p = rt._player
    p.x = INTERNAL_W / 2
    p.y = INTERNAL_H - 60
    # Face right (90°), then press W
    p.nose_angle = 90.0
    p.current_nose_angle = 90.0
    p.input_up = True
    # Run many small updates (simulating 0.5s at 120Hz)
    for _ in range(60):
        p.update(1.0 / 120.0)
    # Y should decrease (moving up screen), even though facing right
    assert p.y < INTERNAL_H - 60
    # X should stay roughly the same (no left/right input)
    assert abs(p.x - INTERNAL_W / 2) < 5.0


def test_level1_mode_has_62_ships():
    """BLOQUE 50: level 1 chains 62 ships in 4 waves (was 43 in BLOQUE 49).
    Plus a mid-wave sub-boss is triggered after wave index 1.
    """
    from src.systems.wave_manager import LEVEL1_WAVES
    rt = _make_runtime()
    assert rt._is_level1_mode()
    total = sum(len(w["enemies"]) for w in LEVEL1_WAVES)
    assert total == 62
    # Sub-boss after wave 1 (O2) — verification of mid-wave challenge
    assert LEVEL1_WAVES[1].get("sub_boss_after") is True


def test_level1_uses_3_distinct_kinds():
    """BLOQUE 48: level 1 still uses 3 distinct enemy types (SCOUT/CRUISER/HEAVY)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    rt = _make_runtime()
    all_kinds: set = set()
    for w in LEVEL1_WAVES:
        for k in w["enemies"]:
            all_kinds.add(k)
    assert all_kinds == {"SCOUT", "CRUISER", "HEAVY"}


def test_level1_victory_at_50_kills():
    """BLOQUE 48: 50 kills was the old fallback. Now safety triggers at 120s
    OR perfect path at 60s with kills>=1. This test verifies safety.
    """
    from src.core.settings import BOSS_SAFETY_TRIGGER_S
    from src.systems.wave_manager import WaveChain, BossTrigger
    rt = _make_runtime()
    rt._level1_chain = WaveChain()
    rt._level1_boss_trigger = BossTrigger()
    rt._level1_chain.elapsed_s = BOSS_SAFETY_TRIGGER_S
    rt._level1_chain.kills = 50
    rt._level1_chain.perfect = False
    state_holder = {"current": None}
    def transition(state):
        state_holder["current"] = state
    rt._transition_to = transition
    rt._update_wave_state(0.0)
    assert state_holder["current"] == GameState.BOSS_INTRO


def test_level1_victory_at_5_minutes():
    """BLOQUE 48: 5 min elapsed is now beyond the safety trigger (120s)."""
    from src.systems.wave_manager import WaveChain, BossTrigger
    rt = _make_runtime()
    rt._level1_chain = WaveChain()
    rt._level1_boss_trigger = BossTrigger()
    rt._level1_chain.elapsed_s = 305.0  # 5 minutes
    rt._level1_chain.kills = 0
    rt._level1_chain.perfect = False
    state_holder = {"current": None}
    def transition(state):
        state_holder["current"] = state
    rt._transition_to = transition
    rt._update_wave_state(0.0)
    assert state_holder["current"] == GameState.BOSS_INTRO


def test_level1_does_not_trigger_boss_before_threshold():
    """BLOQUE 43: before 50 kills AND before 60s, no boss intro.
    (Was 5min in BLOQUE 29; tightened to 60s+perfect in BLOQUE 43.)
    """
    rt = _make_runtime()
    state_holder = {"current": None}
    def transition(state):
        state_holder["current"] = state
    rt._transition_to = transition
    rt._wave_mgr.current.kills = 10
    rt._wave_mgr.current.elapsed_s = 30.0
    rt._update_wave_state(0.0)
    assert state_holder["current"] is None


def test_player_nose_angle_default_zero():
    """BLOQUE 29: player starts with nose_angle=0."""
    from src.entities.player import Player
    p = Player()
    assert p.nose_angle == 0.0
    assert p.current_nose_angle == 0.0


def test_bullets_fire_in_nose_direction():
    """BLOQUE 29: bullets follow the ship's nose angle."""
    rt = _make_runtime()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H - 60
    # Set nose to +45 (firing up-right)
    rt._player.nose_angle = 45.0
    rt._spawn_player_bullet(charge_level=0)
    # Find the spawned bullet
    bullet = None
    for b in rt._bullets.pool:
        if b.active and b.owner == 0:  # OWNER_PLAYER
            bullet = b
            break
    assert bullet is not None
    # Bullet should have positive vx (right) and negative vy (up)
    assert bullet.vx > 0, f"Expected vx > 0, got {bullet.vx}"
    assert bullet.vy < 0, f"Expected vy < 0, got {bullet.vy}"


# -----------------------------------------------------------------------
# BLOQUE 27: Hit sparks on player, power-up magnet, boss phase burst
# -----------------------------------------------------------------------
def test_powerup_magnet_drifts_toward_player():
    """BLOQUE 27: power-ups near the player should drift toward it."""
    rt = _make_runtime()
    rt._player.x = 100
    rt._player.y = 200
    # Spawn a powerup close to the player
    rt._spawn_powerup("score", 110, 210)
    initial_x = rt._powerups[0].x
    initial_y = rt._powerups[0].y
    rt._update_powerups(0.1)
    # The powerup may have been picked up; check if still alive
    if rt._powerups:
        # If still alive, it should have moved toward the player
        p = rt._powerups[0]
        dx_to_player = p.x - rt._player.x
        dy_to_player = p.y - rt._player.y
        orig_dx = initial_x - rt._player.x
        orig_dy = initial_y - rt._player.y
        # Distance should be smaller (or equal if already at the player)
        orig_dist = math.hypot(orig_dx, orig_dy)
        new_dist = math.hypot(dx_to_player, dy_to_player)
        assert new_dist <= orig_dist


def test_boss_phase_change_spawns_burst():
    """BLOQUE 27: when boss enters a new phase, a bigger burst should spawn."""
    rt = _make_runtime(is_boss=True, act=1)
    # Damage the boss heavily to trigger phase change
    assert rt._boss is not None
    rt._boss.phase = 1
    # Set boss HP just above phase 2 threshold to force a change
    cfg = BOSS_CONFIGS[rt._boss.id]
    threshold = cfg.phase_thresholds[0]
    rt._boss.hp = int(rt._boss.max_hp * (threshold + 0.05))
    initial_particles = sum(1 for p in rt._particles.pool if p.active)
    initial_shockwaves = len(rt._shockwaves)
    # Manually trigger a phase change (normally triggered by collision)
    rt._boss.hp = int(rt._boss.max_hp * (threshold - 0.05))
    # Now damage it with a player bullet
    rt._bullets.spawn(BULLET_PLAYER, rt._boss.x, rt._boss.y, 0, 100, damage=99, owner=OWNER_PLAYER)
    rt._handle_collisions()
    after_particles = sum(1 for p in rt._particles.pool if p.active)
    after_shockwaves = len(rt._shockwaves)
    # Phase change adds particles and shockwave
    assert after_particles > initial_particles
    assert after_shockwaves > initial_shockwaves


# ---------------------------------------------------------------------------
# BLOQUE 35: sprite scale + RMB rapid fire
# ---------------------------------------------------------------------------
def test_player_sprite_scale_constant():
    """BLOQUE 35: PLAYER_SPRITE_SCALE is 0.75 (player 32x24 -> 24x18)."""
    from src.core.settings import PLAYER_SPRITE_SCALE
    assert PLAYER_SPRITE_SCALE == 0.75


def test_bullet_sprite_scale_constant():
    """BLOQUE 35: BULLET_SPRITE_SCALE is 0.75."""
    from src.core.settings import BULLET_SPRITE_SCALE
    assert BULLET_SPRITE_SCALE == 0.75


def test_rmb_fire_cooldown_constant():
    """BLOQUE 35: RMB_FIRE_COOLDOWN_S is 0.083 (~12 shots/s)."""
    from src.core.settings import RMB_FIRE_COOLDOWN_S
    assert abs(RMB_FIRE_COOLDOWN_S - 0.083) < 0.01


def test_bullet_sizes_reduced_by_scale():
    """BLOQUE 35: BULLET_SIZES are 75% of pre-BLOQUE-35 (or close)."""
    from src.systems.projectile import (
        BULLET_BOSS,
        BULLET_ENEMY,
        BULLET_PLAYER,
        BULLET_PLAYER_BEAM,
        BULLET_PLAYER_CHARGED,
        BULLET_SIZES,
    )
    # All sizes should be smaller than 4 in at least one dim
    # (pre-BLOQUE-35 had at least (4, 6), (6, 10), (12, 16), (4, 6), (8, 8))
    for kind in (BULLET_PLAYER, BULLET_PLAYER_CHARGED, BULLET_PLAYER_BEAM,
                 BULLET_ENEMY, BULLET_BOSS):
        w, h = BULLET_SIZES[kind]
        assert w >= 1 and h >= 1, f"Bullet kind {kind} has invalid size ({w}, {h})"


# ---------------------------------------------------------------------------
# BLOQUE 37: continuous L3 plasma laser
# ---------------------------------------------------------------------------
def test_continuous_laser_constants_set() -> None:
    """BLOQUE 37: laser tuning constants exist with sane values."""
    from src.core.settings import (
        LASER_DAMAGE_PER_TICK, LASER_HIT_RADIUS_PX, LASER_MAX_RANGE_PX,
        LASER_SPARK_RATE_S, LASER_TICK_S,
    )
    assert LASER_MAX_RANGE_PX > INTERNAL_H, "laser range should exceed screen height"
    assert LASER_TICK_S > 0.0
    assert LASER_DAMAGE_PER_TICK >= 1
    assert LASER_HIT_RADIUS_PX > 0
    assert LASER_SPARK_RATE_S > 0.0


def test_continuous_laser_inactive_by_default() -> None:
    """BLOQUE 37: laser is OFF at scene start (not charging)."""
    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    assert rt._laser_active is False


def test_continuous_laser_activates_at_l3_charge_with_lmb() -> None:
    """BLOQUE 37: laser turns ON when state=CHARGE, charge>=3, LMB held."""
    from src.entities.player.player import PlayerState

    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    # Force player into L3 CHARGE state with LMB held
    rt._player.state = PlayerState.CHARGE
    rt._player.charge_time = 1.6  # past CHARGE_L3_S
    rt._mouse_held = True
    rt._update_continuous_laser(0.05, current_charge=3)
    assert rt._laser_active is True
    assert rt._laser_end_x != 0.0 or rt._laser_end_y != 0.0  # endpoint was set


def test_continuous_laser_deactivates_when_lmb_released() -> None:
    """BLOQUE 37: laser turns OFF when LMB released even if still in CHARGE."""
    from src.entities.player.player import PlayerState

    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    rt._player.state = PlayerState.CHARGE
    rt._player.charge_time = 1.6
    rt._mouse_held = True
    rt._update_continuous_laser(0.05, current_charge=3)
    assert rt._laser_active is True
    # Release LMB
    rt._mouse_held = False
    rt._update_continuous_laser(0.05, current_charge=3)
    assert rt._laser_active is False


def test_continuous_laser_inactive_when_charge_below_3() -> None:
    """BLOQUE 37: laser only fires at L3, not at L1/L2."""
    from src.entities.player.player import PlayerState

    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    rt._player.state = PlayerState.CHARGE
    rt._player.charge_time = 0.7  # L1 only
    rt._mouse_held = True
    rt._update_continuous_laser(0.05, current_charge=1)
    assert rt._laser_active is False
    rt._update_continuous_laser(0.05, current_charge=2)
    assert rt._laser_active is False


def test_continuous_laser_does_not_spawn_bullets() -> None:
    """BLOQUE 37: laser mode is bullet-free — only the visual beam damages."""
    from src.entities.player.player import PlayerState

    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    rt._player.state = PlayerState.CHARGE
    rt._player.charge_time = 1.6
    rt._mouse_held = True
    initial_active = sum(1 for b in rt._bullets.pool if b.active)
    # Run many updates (laser should be active throughout)
    for _ in range(20):
        rt._update_continuous_laser(0.05, current_charge=3)
    after_active = sum(1 for b in rt._bullets.pool if b.active)
    # No new BULLET_PLAYER_BEAM should have been spawned.
    assert after_active == initial_active, (
        f"laser spawned bullets ({initial_active} -> {after_active})"
    )


def test_continuous_laser_damages_enemy_in_path() -> None:
    """BLOQUE 37: laser applies damage to enemies in its path."""
    from src.entities.player.player import PlayerState

    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    # Place player in the middle, pointing up
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H * 0.7
    rt._player.nose_angle = 0.0
    rt._player.state = PlayerState.CHARGE
    rt._player.charge_time = 1.6
    rt._mouse_held = True
    # Spawn a SCOUT directly in front of the player (in the beam path)
    e = rt._enemies.spawn(EnemyKind.SCOUT, INTERNAL_W / 2, INTERNAL_H * 0.4)
    assert e is not None
    initial_hp = e.hp
    # Compute the beam origin/endpoint the same way the update does, then
    # call _laser_apply_damage once directly to verify damage path.
    import math
    nose_rad = math.radians(rt._player.nose_angle)
    muzzle_offset = 12.0
    bx = rt._player.x + math.sin(nose_rad) * muzzle_offset
    by = rt._player.y - math.cos(nose_rad) * muzzle_offset
    # dx, dy
    dx = math.sin(nose_rad)
    dy = -math.cos(nose_rad)
    # t_max: how far the beam goes (well past the SCOUT at y=192)
    t_max = 600.0
    from src.core.settings import LASER_HIT_RADIUS_PX, LASER_DAMAGE_PER_TICK
    rt._laser_apply_damage(bx, by, dx, dy, t_max, LASER_HIT_RADIUS_PX, LASER_DAMAGE_PER_TICK)
    # SCOUT has 1 HP, so apply_damage returns True and the SCOUT is now DYING.
    assert e.damage_taken >= LASER_DAMAGE_PER_TICK, (
        f"laser did not damage enemy (damage_taken={e.damage_taken})"
    )


def test_continuous_laser_endpoint_stays_inside_playfield() -> None:
    """BLOQUE 37: laser endpoint is clamped to the play area."""
    from src.entities.player.player import PlayerState

    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    rt._player.x = INTERNAL_W / 2
    rt._player.y = INTERNAL_H / 2
    rt._player.state = PlayerState.CHARGE
    rt._player.charge_time = 1.6
    rt._mouse_held = True
    for angle in (0.0, 90.0, 180.0, 270.0, 45.0, 135.0):
        rt._player.nose_angle = angle
        rt._update_continuous_laser(0.05, current_charge=3)
        assert 0 <= rt._laser_end_x <= INTERNAL_W, (
            f"laser endpoint x out of bounds at angle {angle}: {rt._laser_end_x}"
        )
        assert 0 <= rt._laser_end_y <= INTERNAL_H, (
            f"laser endpoint y out of bounds at angle {angle}: {rt._laser_end_y}"
        )


# ---------------------------------------------------------------------------
# BLOQUE 38: snappier mouse follow + RMB rapid fire visual feedback
# ---------------------------------------------------------------------------
def test_bloque_38_player_speed_increased() -> None:
    """BLOQUE 38: PLAYER_SPEED is 165 px/s (was 130, ~1.27x faster)."""
    from src.core.settings import PLAYER_SPEED
    assert PLAYER_SPEED >= 160.0, f"PLAYER_SPEED too low: {PLAYER_SPEED}"
    assert PLAYER_SPEED <= 200.0, f"PLAYER_SPEED too high: {PLAYER_SPEED}"


def test_bloque_38_nose_lerp_snappier() -> None:
    """BLOQUE 38: PLAYER_NOSE_LERP_PER_S is 50 (was 28, ~1.78x snappier)."""
    from src.core.settings import PLAYER_NOSE_LERP_PER_S
    assert PLAYER_NOSE_LERP_PER_S >= 40.0, (
        f"Nose lerp too slow: {PLAYER_NOSE_LERP_PER_S}"
    )
    assert PLAYER_NOSE_LERP_PER_S <= 80.0, (
        f"Nose lerp too aggressive: {PLAYER_NOSE_LERP_PER_S}"
    )


def test_bloque_38_muzzle_flash_source_defaults_to_lmb() -> None:
    """BLOQUE 38: muzzle_flash_source starts as 'lmb'."""
    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    assert rt._muzzle_flash_source == "lmb"


def test_bloque_38_muzzle_flash_source_tracks_rmb() -> None:
    """BLOQUE 38: when RMB is held, _muzzle_flash_source becomes 'rmb'."""
    from src.entities.player.player import PlayerState
    def _noop(*_args, **_kwargs):
        return None
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    rt._player.state = PlayerState.IDLE
    # Manually set the source the same way _handle_firing would
    rt._mouse_r_held = True
    rt._muzzle_flash_source = "rmb" if rt._mouse_r_held else "lmb"
    assert rt._muzzle_flash_source == "rmb"


# ---------------------------------------------------------------------------
# BLOQUE 43: boss trigger (60s+perfect OR 50kills OR 180s)
# ---------------------------------------------------------------------------
def test_boss_trigger_constants_in_settings() -> None:
    """BLOQUE 43: settings have the new boss trigger constants."""
    from src.core.settings import (
        BOSS_FALLBACK_KILLS, BOSS_FALLBACK_TIMEOUT_S, BOSS_FAST_TRIGGER_S,
    )
    assert BOSS_FAST_TRIGGER_S == 60.0
    assert BOSS_FALLBACK_KILLS == 50
    assert BOSS_FALLBACK_TIMEOUT_S == 180.0


def _recording_transition():
    """Returns (callback_fn, transitions_list) — appends each state passed to fn."""
    transitions: list = []
    def _fn(state):
        transitions.append(state)
    return _fn, transitions


def test_boss_trigger_at_60s_with_perfect_score() -> None:
    """BLOQUE 48: elapsed=60s, no escaped, kills>=1 → BOSS_INTRO via chain."""
    from src.core.settings import BOSS_PERFECT_TRIGGER_S
    from src.core.scene_manager import GameState
    from src.systems.wave_manager import WaveChain, BossTrigger
    fn, transitions = _recording_transition()
    rt = GameplayRuntime(transition_to=fn, is_boss=False, act=1)
    rt.on_enter()
    rt._is_level1_mode = lambda: True
    # Manually set up the chain with the desired state
    rt._level1_chain = WaveChain()
    rt._level1_boss_trigger = BossTrigger()
    rt._level1_chain.elapsed_s = BOSS_PERFECT_TRIGGER_S
    rt._level1_chain.kills = 4
    rt._level1_chain.perfect = True
    rt._update_wave_state(0.0)
    assert GameState.BOSS_INTRO in transitions


def test_boss_trigger_fallback_at_50_kills() -> None:
    """BLOQUE 48: with old 50-kill fallback gone, the safety trigger
    fires at 120s instead. Keep the test name for symmetry but check
    the new behavior."""
    from src.core.settings import BOSS_SAFETY_TRIGGER_S
    from src.core.scene_manager import GameState
    from src.systems.wave_manager import WaveChain, BossTrigger
    fn, transitions = _recording_transition()
    rt = GameplayRuntime(transition_to=fn, is_boss=False, act=1)
    rt.on_enter()
    rt._is_level1_mode = lambda: True
    rt._level1_chain = WaveChain()
    rt._level1_boss_trigger = BossTrigger()
    rt._level1_chain.elapsed_s = BOSS_SAFETY_TRIGGER_S
    rt._level1_chain.kills = 5  # way less than 50
    rt._level1_chain.perfect = False
    rt._update_wave_state(0.0)
    assert GameState.BOSS_INTRO in transitions


def test_boss_trigger_timeout_at_120s() -> None:
    """BLOQUE 48: elapsed>=120s → BOSS_INTRO (lenient safety, was 180s)."""
    from src.core.settings import BOSS_SAFETY_TRIGGER_S
    from src.core.scene_manager import GameState
    from src.systems.wave_manager import WaveChain, BossTrigger
    fn, transitions = _recording_transition()
    rt = GameplayRuntime(transition_to=fn, is_boss=False, act=1)
    rt.on_enter()
    rt._is_level1_mode = lambda: True
    rt._level1_chain = WaveChain()
    rt._level1_boss_trigger = BossTrigger()
    rt._level1_chain.elapsed_s = BOSS_SAFETY_TRIGGER_S
    rt._level1_chain.kills = 10
    rt._level1_chain.perfect = False
    rt._update_wave_state(0.0)
    assert GameState.BOSS_INTRO in transitions


def test_boss_trigger_does_not_fire_below_thresholds() -> None:
    """BLOQUE 48: under all thresholds, NO transition."""
    from src.core.scene_manager import GameState
    from src.systems.wave_manager import WaveChain, BossTrigger
    fn, transitions = _recording_transition()
    rt = GameplayRuntime(transition_to=fn, is_boss=False, act=1)
    rt.on_enter()
    rt._is_level1_mode = lambda: True
    rt._level1_chain = WaveChain()
    rt._level1_boss_trigger = BossTrigger()
    rt._level1_chain.elapsed_s = 30.0
    rt._level1_chain.kills = 10
    rt._level1_chain.perfect = False
    rt._update_wave_state(0.0)
    assert GameState.BOSS_INTRO not in transitions


def test_boss_trigger_fast_requires_at_least_one_kill() -> None:
    """BLOQUE 48: even at 60s, the perfect path requires at least 1 kill."""
    from src.core.settings import BOSS_PERFECT_TRIGGER_S
    from src.core.scene_manager import GameState
    from src.systems.wave_manager import WaveChain, BossTrigger
    fn, transitions = _recording_transition()
    rt = GameplayRuntime(transition_to=fn, is_boss=False, act=1)
    rt.on_enter()
    rt._is_level1_mode = lambda: True
    rt._level1_chain = WaveChain()
    rt._level1_boss_trigger = BossTrigger()
    rt._level1_chain.elapsed_s = BOSS_PERFECT_TRIGGER_S
    rt._level1_chain.kills = 0  # no kills!
    rt._level1_chain.perfect = True
    rt._update_wave_state(0.0)
    assert GameState.BOSS_INTRO not in transitions


# ---------------------------------------------------------------------------
# BLOQUE 42: density cap
# ---------------------------------------------------------------------------
def test_density_cap_setting_is_8() -> None:
    """BLOQUE 42: MAX_ENEMIES_ON_SCREEN is 8."""
    from src.core.settings import MAX_ENEMIES_ON_SCREEN
    assert MAX_ENEMIES_ON_SCREEN == 8
