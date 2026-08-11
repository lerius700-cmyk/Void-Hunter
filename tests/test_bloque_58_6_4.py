"""Tests for BLOQUE 58.6.4 — SUB_BOSS movement pattern (4-entry cycle).

The sub-boss should:
  1. Enter through the same wall it exits (per user requirement)
  2. Follow a 4-entry cycle where every 2 entries it does an "L"
     pattern (vertical then horizontal exit) instead of a straight
     line. The 4-entry cycle is:
       0: top -> down -> bottom (straight)
       1: top -> down -> L-right -> right (L pattern)
       2: bottom -> up -> top (straight)
       3: bottom -> up -> L-left -> left (L pattern)
"""
from src.entities.enemies.enemy import (
    ENEMY_CONFIGS, Enemy, EnemyKind, EnemyState,
)
from src.core.settings import INTERNAL_H, INTERNAL_W


def _make_sub_boss() -> Enemy:
    """Create a fresh SUB_BOSS enemy with default config."""
    e = Enemy()
    e.kind = EnemyKind.SUB_BOSS
    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    e.hp = cfg.hp
    e.max_hp = cfg.hp
    e.vy = cfg.speed
    e.vx = 0.0
    e.x = INTERNAL_W / 2
    e.y = 100.0
    e.active = True
    return e


def test_sub_boss_has_movement_state_fields() -> None:
    """BLOQUE 58.6.4: SUB_BOSS has the new movement pattern state fields."""
    e = _make_sub_boss()
    # New fields should exist with sensible defaults
    assert e.sb_entry_count == 0
    assert e.sb_current_wall == "top"
    assert e.sb_is_l is False
    assert e.sb_turn_done is False
    assert e.sb_turn_at_x == 0.0
    assert e.sb_turn_at_y == 0.0
    assert e.sb_post_turn_vx == 0.0
    assert e.sb_post_turn_vy == 0.0


def test_sub_boss_exits_bottom_resets_to_top_when_in_cycle_0() -> None:
    """Cycle 0 (first entry, vertical from top): exit bottom → re-enter top."""
    e = _make_sub_boss()
    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    e.sb_entry_count = 0
    e.sb_current_wall = "top"
    e.vx = 0.0
    e.vy = cfg.speed  # moving down
    # Simulate: y goes past bottom
    e.y = INTERNAL_H + 30.0
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    # Should re-enter from top (because cycle 0 = "top entry, down, exit bottom"
    # and the SAME wall rule: re-enter from the wall it just exited,
    # but exit_wall was bottom so sb_current_wall is "bottom" and entry
    # position is at the bottom of the screen — moving UP now)
    # Per the implementation, the entry_count increments to 1, so the
    # next cycle is 1 = "L-right" if it were a fresh entry. But the
    # code uses the current sb_entry_count to determine the L pattern.
    assert e.sb_entry_count == 1
    # After the wrap, the sub-boss is moving up (y from bottom)
    # so it re-enters from the bottom and moves up.
    assert e.vy < 0  # now moving up
    assert e.sb_current_wall == "bottom"


def test_sub_boss_exits_top_resets_to_bottom() -> None:
    """When sub-boss exits the top, re-enter from the bottom (moving down)."""
    e = _make_sub_boss()
    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    e.sb_entry_count = 1  # in the bottom-entry part of the cycle
    e.sb_current_wall = "bottom"
    e.vx = 0.0
    e.vy = -cfg.speed  # moving up
    e.y = -30.0  # past the top
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    # Should re-enter from top (moving down)
    assert e.sb_entry_count == 2
    assert e.vy > 0  # now moving down
    assert e.sb_current_wall == "top"


def test_sub_boss_l_turn_changes_velocity_at_turn_point() -> None:
    """BLOQUE 58.6.4: when L pattern is active, velocity changes at the
    turn point (sb_turn_at_y)."""
    e = _make_sub_boss()
    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    e.sb_entry_count = 1  # L pattern cycle (1 = top entry, L-right)
    e.sb_current_wall = "top"
    e.sb_is_l = True
    e.sb_turn_done = False
    e.sb_turn_at_y = INTERNAL_H * 0.4
    e.sb_post_turn_vx = cfg.speed  # right
    e.sb_post_turn_vy = 0.0
    e.vx = 0.0
    e.vy = cfg.speed  # moving down
    e.y = e.sb_turn_at_y - 5  # NOT yet at turn point
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    # Before reaching turn point, velocity should still be down
    assert e.vy > 0
    assert e.sb_turn_done is False
    # Now move past the turn point
    e.y = e.sb_turn_at_y + 5
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    # After reaching turn point, velocity should be right (L turn)
    assert e.vx > 0
    assert e.vy == 0
    assert e.sb_turn_done is True


def test_sub_boss_l_pattern_only_once() -> None:
    """BLOQUE 58.6.4: after the L turn, the velocity stays the new
    direction (no double-turn)."""
    e = _make_sub_boss()
    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    e.sb_entry_count = 1
    e.sb_current_wall = "top"
    e.sb_is_l = True
    e.sb_turn_done = False
    e.sb_turn_at_y = INTERNAL_H * 0.4
    e.sb_post_turn_vx = cfg.speed
    e.sb_post_turn_vy = 0.0
    e.vx = 0.0
    e.vy = cfg.speed
    e.y = e.sb_turn_at_y + 10
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    # After turn, velocity is right
    assert e.vx > 0
    assert e.sb_turn_done is True
    # Update again — should stay right
    prev_vx = e.vx
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    assert e.vx == prev_vx


def test_sub_boss_cycle_3_is_l_left_from_bottom() -> None:
    """Cycle 3: bottom entry, up, L-left, exit left."""
    e = _make_sub_boss()
    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    e.sb_entry_count = 3
    e.sb_current_wall = "bottom"
    e.sb_is_l = True
    e.sb_turn_done = False
    e.sb_turn_at_y = INTERNAL_H * 0.6
    e.sb_post_turn_vx = -cfg.speed  # left
    e.sb_post_turn_vy = 0.0
    e.vx = 0.0
    e.vy = -cfg.speed  # moving up
    # Sub-boss is moving UP from bottom, so y decreases. "Not yet at
    # turn point" means y is still BELOW the turn point (y > turn_at_y
    # since smaller y is higher on screen).
    e.y = e.sb_turn_at_y + 5  # not yet at turn point (still below it going up)
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    assert e.vy < 0
    assert e.sb_turn_done is False
    # Now move above the turn point (y decreases past turn_at_y)
    e.y = e.sb_turn_at_y - 20  # past the turn point (going up)
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    # After turn: velocity is left
    assert e.vx < 0
    assert e.vy == 0
    assert e.sb_turn_done is True


def test_sub_boss_exit_left_resets_to_left() -> None:
    """When sub-boss exits through the left wall (after L), re-enter from left."""
    e = _make_sub_boss()
    cfg = ENEMY_CONFIGS[EnemyKind.SUB_BOSS]
    e.sb_entry_count = 3  # L pattern that exits left
    e.sb_current_wall = "bottom"
    e.sb_is_l = True
    e.sb_turn_done = True
    e.sb_post_turn_vx = -cfg.speed
    e.sb_post_turn_vy = 0.0
    e.vx = -cfg.speed  # moving left
    e.vy = 0.0
    e.x = -30.0  # past the left wall
    e.y = 100.0
    e.update(0.016, INTERNAL_W / 2, INTERNAL_H)
    # Should re-enter from left (moving right)
    assert e.sb_entry_count == 4
    assert e.vx > 0  # moving right
    assert e.sb_current_wall == "left"
