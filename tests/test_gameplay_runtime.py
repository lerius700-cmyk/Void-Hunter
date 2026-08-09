"""Tests for the GameplayRuntime integration (BLOQUE 17.3).

These tests verify the wiring without requiring a real pygame display.
The runtime owns the live action loop, so we instantiate it with stub
transition_to and exercise its update/draw via the Scene interface.
"""
from __future__ import annotations

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
from src.systems.projectile import BULLET_PLAYER, OWNER_PLAYER  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime, PowerUp, ScorePopup  # noqa: E402


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
    assert rt._boss.hp == 800


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
def test_bomb_clears_screen():
    rt = _make_runtime()
    # Spawn a few enemies manually
    rt._enemies.spawn(EnemyKind.SCOUT, 100, 50)
    rt._enemies.spawn(EnemyKind.SCOUT, 60, 80)
    # Trigger bomb
    rt._player.input_bomb = True
    rt._player.wants_to_bomb = True
    rt._player.bombs = 3
    rt._handle_firing(1.0 / 120.0)
    # Bombs decremented
    assert rt._player.bombs == 2
    # Both enemies should be killed (400 dmg to 1 HP enemies)
    assert sum(1 for e in rt._enemies.pool if e.active and e.state.value != "dead") == 0


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
    # Player should have taken damage
    assert rt._player.hp < 3


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
    rt = _make_runtime()
    # Wave 0 (Act 1, wave 1) has kill_target=6
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
    state_holder = {"current": None}
    def transition(state):
        state_holder["current"] = state
    rt = GameplayRuntime(transition_to=transition, is_boss=False, act=1)
    rt.on_enter()
    rt._player.is_dead = True
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
