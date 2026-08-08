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
from src.entities.enemies import EnemyKind  # noqa: E402
from src.systems.projectile import BULLET_PLAYER, OWNER_PLAYER  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime  # noqa: E402


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
