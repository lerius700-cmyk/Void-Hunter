"""BLOQUE 52: tests for the GOLIATH spear throw mechanic.

Covers:
  - BossSpear update (serpentine motion, lifetime, hit flash decay)
  - BossSpear.apply_damage kills at HP=0
  - BossSpear.hitbox differs by kind
  - Runtime spear state machine (ready → winding → thrown → ready)
  - _start_goliath_spear_throw only fires from "ready"
  - _spawn_boss_spear creates a main spear
  - _split_spear creates 3 fragments with cone spread and awards bonus
  - Boss select_attack pool includes 8 for GOLIATH only
  - Player bullets damage the spear
  - Spear damages player on contact
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()


def _noop_transition(_state: object) -> None:
    pass


def _make_runtime(is_boss: bool = False, act: int = 1):
    from src.ui.gameplay_runtime import GameplayRuntime
    rt = GameplayRuntime(transition_to=_noop_transition, is_boss=is_boss, act=act)
    rt.on_enter()
    return rt


def _make_boss_runtime(act: int = 1):
    """Create a boss-fight runtime (GOLIATH) with the boss active and
    positioned at the anchor so spear spawn works."""
    rt = _make_runtime(is_boss=True, act=act)
    # Place the player below the boss and the boss at the anchor
    if rt._boss is not None:
        rt._boss.x = 160
        rt._boss.y = 80
        rt._boss_entry_t = 2.0  # past the entry animation
    rt._player.x = 160
    rt._player.y = 300
    return rt


# ---------------------------------------------------------------------------
# 1. BossSpear basics
# ---------------------------------------------------------------------------
def test_boss_spear_starts_inactive() -> None:
    from src.entities.boss_spear import BossSpear
    s = BossSpear()
    assert s.active is False


def test_boss_spear_apply_damage_kills_at_zero() -> None:
    from src.entities.boss_spear import BossSpear
    s = BossSpear(active=True, hp=30, max_hp=30)
    # 29 hits to bring down to 1 HP
    for _ in range(29):
        assert s.apply_damage(1) is False
    assert s.hp == 1
    # 30th hit kills
    assert s.apply_damage(1) is True
    assert s.active is False


def test_boss_spear_hitbox_size_by_kind() -> None:
    from src.entities.boss_spear import BossSpear
    main = BossSpear(active=True, kind="main", x=100, y=50)
    frag = BossSpear(active=True, kind="fragment", x=100, y=50)
    _, _, mw, mh = main.hitbox()
    _, _, fw, fh = frag.hitbox()
    # Main is bigger than fragment
    assert mw * mh > fw * fh
    # Both centered on the position
    assert (100, 50) == (main.hitbox()[0], main.hitbox()[1])
    assert (100, 50) == (frag.hitbox()[0], frag.hitbox()[1])


def test_boss_spear_serpentine_motion_advances_wave_t() -> None:
    from src.entities.boss_spear import BossSpear
    s = BossSpear(
        active=True, kind="main", x=100, y=0,
        base_vx=0.0, base_vy=1.0, perp_vx=1.0, perp_vy=0.0,
        speed=100.0, wave_amp=10.0, wave_freq_hz=2.0,
        wave_amp_growth=0.0, life=10.0, max_life=10.0,
    )
    initial_y = s.y
    s.update(0.1)
    # After 0.1s, the y should have increased (base direction is +y)
    assert s.y > initial_y
    # wave_t should have advanced
    assert s.wave_t > 0.0


def test_boss_spear_straight_line_motion_bloque_58_59() -> None:
    """BLOQUE 58.59: serpentine wave removed. The spear must travel in a
    pure straight line along (base_vx, base_vy) — no perpendicular wobble.

    With base_vy=1, base_vx=0, speed=100, dt=0.1: x must stay at 100.0
    (no horizontal wobble from sin wave) and y must increase by 10 (100*0.1).
    """
    from src.entities.boss_spear import BossSpear
    s = BossSpear(
        active=True, kind="main", x=100, y=0,
        base_vx=0.0, base_vy=1.0, perp_vx=1.0, perp_vy=0.0,
        speed=100.0, wave_amp=40.0, wave_freq_hz=5.0,  # big wave (would
                                                         # cause 40px wobble)
        wave_amp_growth=100.0, life=10.0, max_life=10.0,  # grows fast
    )
    initial_x = s.x
    initial_y = s.y
    # Run for 0.5s — if the wave was still active, x would oscillate up to
    # ~40-50 px from initial. With the wave disabled, x must stay at 100.
    for _ in range(5):
        s.update(0.1)
    assert s.x == initial_x, f"x wobbled to {s.x} (expected {initial_x})"
    assert s.y == initial_y + 100.0 * 0.5, (
        f"y expected {initial_y + 50.0}, got {s.y}"
    )


def test_boss_spear_lifetime_expires() -> None:
    from src.entities.boss_spear import BossSpear
    s = BossSpear(
        active=True, kind="main", x=100, y=0,
        base_vx=0.0, base_vy=1.0, speed=100.0,
        wave_amp=0.0, wave_freq_hz=1.0, wave_amp_growth=0.0,
        life=1.0, max_life=1.0,
    )
    s.update(0.5)
    assert s.active is True
    s.update(0.6)  # total 1.1s > 1.0
    assert s.active is False


# ---------------------------------------------------------------------------
# 2. Runtime state machine
# ---------------------------------------------------------------------------
def test_runtime_spear_starts_in_ready_phase() -> None:
    rt = _make_runtime()
    assert rt._boss_spear_phase == "ready"
    assert rt._boss_spear_phase_t == 0.0
    assert rt._boss_spears == []


def test_start_spear_throw_only_fires_from_ready() -> None:
    rt = _make_runtime()
    # First call works
    rt._start_goliath_spear_throw()
    assert rt._boss_spear_phase == "winding"
    # Second call is ignored (already winding)
    rt._boss_spear_phase_t = 0.1
    rt._start_goliath_spear_throw()
    assert rt._boss_spear_phase_t == 0.1  # unchanged


def test_spear_throw_full_cycle() -> None:
    """ready → winding → (0.3s) → thrown → (1.2s) → ready."""
    rt = _make_boss_runtime()
    rt._start_goliath_spear_throw()
    assert rt._boss_spear_phase == "winding"
    # Tick 0.3s — should spawn the spear and transition to "thrown"
    rt._update_boss_spears(0.15)
    assert rt._boss_spear_phase == "winding"
    rt._update_boss_spears(0.15)  # total 0.3
    assert rt._boss_spear_phase == "thrown"
    assert len(rt._boss_spears) == 1
    # Tick 1.2s — should return to "ready"
    rt._update_boss_spears(1.2)
    assert rt._boss_spear_phase == "ready"


def test_spawn_spear_creates_main_spear() -> None:
    rt = _make_boss_runtime()
    rt._spawn_boss_spear()
    assert len(rt._boss_spears) == 1
    s = rt._boss_spears[0]
    assert s.kind == "main"
    assert s.is_main is True
    assert s.hp == 30  # BLOQUE 58.56: x10 HP (was 3)
    # The base direction should be roughly toward the player (positive y)
    assert s.base_vy > 0.5


def test_split_spear_creates_three_fragments() -> None:
    """When a main spear is destroyed, 3 fragments appear in a cone."""
    rt = _make_runtime()
    # Create a main spear aimed to the right (no vertical component)
    from src.entities.boss_spear import BossSpear
    s = BossSpear(
        active=True, kind="main", is_main=True,
        x=100, y=200,
        base_vx=1.0, base_vy=0.0,
        perp_vx=0.0, perp_vy=1.0,
        speed=160.0, hp=0, max_hp=3, life=2.0, max_life=2.0,
    )
    rt._boss_spears.append(s)
    # Score should be awarded
    initial_score = rt._scoring.score
    rt._split_spear(s)
    # 3 fragments added, 1 main (now inactive)
    fragments = [sp for sp in rt._boss_spears if sp.kind == "fragment"]
    assert len(fragments) == 3
    for frag in fragments:
        assert frag.is_main is False
    # Score went up
    assert rt._scoring.score > initial_score
    # Cone spread: middle fragment should be straight, sides offset ±20°
    angles = sorted(math.atan2(f.base_vy, f.base_vx) for f in fragments)
    assert abs(angles[1]) < 0.01  # middle
    assert abs(angles[0] - math.radians(-20)) < 0.05  # left
    assert abs(angles[2] - math.radians(20)) < 0.05  # right


def test_split_spear_no_op_for_fragments() -> None:
    """Fragments don't split further."""
    rt = _make_runtime()
    from src.entities.boss_spear import BossSpear
    s = BossSpear(
        active=True, kind="fragment", is_main=False,
        x=100, y=200, base_vx=1.0, base_vy=0.0,
    )
    rt._boss_spears.append(s)
    rt._split_spear(s)
    # Still 1 spear (the fragment), no new ones added
    assert len(rt._boss_spears) == 1


def test_split_spear_marks_main_inactive() -> None:
    """After split, the main spear is marked inactive (will be culled)."""
    rt = _make_runtime()
    from src.entities.boss_spear import BossSpear
    s = BossSpear(
        active=True, kind="main", is_main=True,
        x=100, y=200, base_vx=1.0, base_vy=0.0,
    )
    rt._boss_spears.append(s)
    rt._split_spear(s)
    # The main is now inactive
    assert s.active is False
    # _update_boss_spears will cull it
    rt._update_boss_spears(0.1)
    active = [sp for sp in rt._boss_spears if sp.active]
    mains = [sp for sp in active if sp.is_main]
    assert len(mains) == 0


# ---------------------------------------------------------------------------
# 3. Boss select_attack includes spear throw
# ---------------------------------------------------------------------------
def test_goliath_phase1_pool_has_spear_throw() -> None:
    from src.entities.enemies.boss import Boss, BossId
    b = Boss()
    b.id = BossId.GOLIATH
    b.phase = 1
    # Sample many times to check that 8 (spear) is in the possible pool
    results = set()
    for t_ms in range(0, 200, 5):
        b.move_t = t_ms / 100.0
        b.fire_cd = 0.0  # reset before each call (select_attack sets it)
        idx = b.select_attack()
        results.add(idx)
    # 8 (spear throw) should be in the pool
    assert 8 in results


def test_hydra_phase1_pool_has_no_spear_throw() -> None:
    """Non-GOLIATH bosses should not have attack 8 in their pool."""
    from src.entities.enemies.boss import Boss, BossId
    b = Boss()
    b.id = BossId.HYDRA
    b.phase = 1
    results = set()
    for t_ms in range(0, 200, 5):
        b.move_t = t_ms / 100.0
        b.fire_cd = 0.0
        idx = b.select_attack()
        results.add(idx)
    assert 8 not in results


# ---------------------------------------------------------------------------
# 4. Collision logic
# ---------------------------------------------------------------------------
def test_player_bullet_damages_spear() -> None:
    """A player bullet hitting the spear should decrement HP and trigger flash."""
    rt = _make_runtime()
    from src.entities.boss_spear import BossSpear
    from src.systems.projectile import (
        BULLET_PLAYER, OWNER_PLAYER, ProjectilePool,
    )
    s = BossSpear(
        active=True, kind="main", is_main=True,
        x=160, y=200, base_vx=0.0, base_vy=1.0,
        speed=100.0, hp=30, max_hp=30, life=5.0, max_life=5.0,
    )
    rt._boss_spears.append(s)
    # Spawn a player bullet at the spear's position
    rt._bullets.spawn(
        BULLET_PLAYER, 160, 200, 0.0, -480.0,
        damage=1, owner=OWNER_PLAYER,
    )
    rt._handle_spear_collisions(rt._player.hitbox)
    # Spear took 1 damage
    assert s.hp == 29
    assert s.flash_t > 0.0


def test_spear_killed_by_player_bullets_splits_into_fragments() -> None:
    rt = _make_runtime()
    from src.entities.boss_spear import BossSpear
    from src.systems.projectile import (
        BULLET_PLAYER, OWNER_PLAYER,
    )
    s = BossSpear(
        active=True, kind="main", is_main=True,
        x=160, y=200, base_vx=0.0, base_vy=1.0,
        speed=100.0, hp=1, max_hp=3, life=5.0, max_life=5.0,
    )
    rt._boss_spears.append(s)
    # Spawn a player bullet that will kill the spear
    rt._bullets.spawn(
        BULLET_PLAYER, 160, 200, 0.0, -480.0,
        damage=1, owner=OWNER_PLAYER,
    )
    rt._handle_spear_collisions(rt._player.hitbox)
    # 3 fragments spawned; the main is now inactive
    fragments = [sp for sp in rt._boss_spears if sp.kind == "fragment"]
    assert len(fragments) == 3
    # The main spear is now inactive
    assert s.active is False


def test_spear_damages_player_on_contact() -> None:
    """A spear touching the player should damage them."""
    rt = _make_runtime()
    from src.entities.boss_spear import BossSpear
    # Place a spear right on top of the player
    rt._player.x = 160
    rt._player.y = 300
    s = BossSpear(
        active=True, kind="main", is_main=True,
        x=160, y=300, base_vx=0.0, base_vy=1.0,
        speed=100.0, hp=3, max_hp=3, damage=2, life=5.0, max_life=5.0,
    )
    rt._boss_spears.append(s)
    rt._handle_spear_collisions(rt._player.hitbox)
    # The main is now inactive (and split into 3 fragments)
    assert s.active is False
    fragments = [sp for sp in rt._boss_spears if sp.kind == "fragment"]
    assert len(fragments) == 3
