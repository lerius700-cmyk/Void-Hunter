"""BLOQUE 63 + 65: tests for MINE-ASTEROID enemy.

Adds ``EnemyKind.MINE_ASTEROID`` — a stealth enemy that uses the asteroid
aesthetic as camouflage. When in the ``closed`` state it is visually
identical to a regular asteroid (``Assets/sprites/asteroids/round.png`` is
reused for the closed frame). When its y crosses the
``OPENING_Y_THRESHOLD`` (200 = upper playfield), it transitions through
``open1`` (0.2s) → ``open2`` (0.2s) → ``open3`` (terminal, fires 3 bullets
in a fan, HP=3 while vulnerable). The 4-state cycle is ONE-WAY: the mine
never returns to closed after opening. The closed state is immune to
player bullets but vulnerable to player collision.

BLOQUE 65 update: 4-frame state machine replaces the legacy
5-frame cycle (closed/opening/open/closing). Per-state durations:
open1=0.2s, open2=0.2s, open3=indefinite. Total opening animation
0.6s. The terminal state (open3) reuses the new ship reference
sprite from BLOQUE 65 (replacing the BLOQUE 63 `open/frame_00.png`).
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
    MINE_OPEN1_DURATION_S,
    MINE_OPEN2_DURATION_S,
    MINE_OPEN_DURATION_S,
    MINE_FIRE_INTERVAL_S,
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
        """BLOQUE 69: OPENING_Y_THRESHOLD is exactly 120 (first quarter, paired with yellow line)."""
        assert OPENING_Y_THRESHOLD == 120

    def test_mine_asteroid_in_archetypes(self) -> None:
        """ENEMY_ARCHETYPES tuple includes 'mine_asteroid'."""
        from src.entities.enemies.enemy import ENEMY_ARCHETYPES
        assert "mine_asteroid" in ENEMY_ARCHETYPES

    def test_mine_asteroid_default_state_closed(self) -> None:
        """A freshly-spawned MINE_ASTEROID has mine_state='closed' (string)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert e.mine_state == "closed"
        # BLOQUE 65: the legacy 5-state cycle (closed/opening/open/closing)
        # is replaced with a 4-state cycle (closed/open1/open2/open3).
        assert e.mine_state not in ("open", "opening", "closing", "open1", "open2", "open3")

    def test_mine_asteroid_default_has_opened_false(self) -> None:
        """A fresh MINE_ASTEROID has has_opened=False (no cycle yet)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        assert e.has_opened is False
        assert e.state_timer == 0.0


# =====================================================================
# State machine (BLOQUE 65: 4-state cycle) — 6 tests
# =====================================================================
class TestStateMachine:
    def test_state_transitions_on_y_threshold(self) -> None:
        """BLOQUE 69: crossing the yellow-line trigger (y >= 120) opens the mine.

        The check is `y > 0 AND y >= OPENING_Y_THRESHOLD` (>=, not >) — the
        mine must have entered the screen (y > 0) AND reached the yellow
        line at OPENING_Y_THRESHOLD (120). The check uses >= so the
        mine opens the moment of crossing.

        History:
        - BLOQUE 63: `y < 200` (broken: opened off-screen).
        - BLOQUE 68: `y > 0 AND y < 200` (worked but no visual cue).
        - BLOQUE 69: `y > 0 AND y >= 120` (paired with visible yellow
          line at the same y).
        """
        # Case 1: y = OPENING_Y_THRESHOLD + 10 (130) — well below the
        # yellow line, mine has crossed → must open.
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD + 10  # 130
        e.update(0.016, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open1", (
            f"Mine at y=130 (below the yellow line) must open, "
            f"got mine_state={e.mine_state}"
        )
        # BLOQUE 68: off-screen above (y < 0) should NOT trigger.
        e2 = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e2.y = -50
        e2.update(0.016, player_x=160.0, player_y=400.0)
        assert e2.mine_state == "closed", (
            "Mine at y=-50 (off-screen above) must not open — it "
            "needs to enter the screen (y > 0) first"
        )
        # BLOQUE 69: y=119 (just ABOVE the line) should NOT trigger.
        # The mine is in the "warning" zone — visible on screen but
        # still above the line (not yet crossed). The check `y >= 120`
        # is FALSE (119 < 120) so the mine stays closed.
        e3 = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e3.y = 119
        e3.update(0.016, player_x=160.0, player_y=400.0)
        assert e3.mine_state == "closed", (
            "Mine at y=119 (just above the yellow line) must stay closed — "
            "the threshold check is `y >= 120`, not `y > 120`"
        )
        # BLOQUE 69: y=120 (AT the line) should trigger.
        # This is the moment of crossing. The check `y >= 120` is TRUE
        # (120 >= 120) so the mine transitions to open1.
        e4 = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e4.y = 120
        e4.update(0.016, player_x=160.0, player_y=400.0)
        assert e4.mine_state == "open1", (
            "Mine at y=120 (crossing the yellow line) must open — "
            "the threshold check is `y >= 120` so the moment of "
            "crossing triggers the open transition"
        )

    def test_open1_to_open2_after_0_2s(self) -> None:
        """After 0.2s in 'open1' state, transitions to 'open2'."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD + 10  # BLOQUE 69: 130 (above the yellow line)
        e.update(0.016, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open1"
        # Advance 0.1s — still in open1
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open1"
        # Advance 0.1s more (total 0.2s) — now open2
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open2"

    def test_open2_to_open3_after_0_2s(self) -> None:
        """After 0.2s in 'open2' state, transitions to 'open3' (terminal)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD + 10  # BLOQUE 69: 130 (above the yellow line)
        # closed -> open1 -> open2 (0.016 + 0.2 = 0.216s)
        e.update(0.016, player_x=160.0, player_y=400.0)
        e.update(0.2, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open2"
        # 0.1s later — still in open2
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open2"
        # 0.1s more (total 0.2s in open2) — now open3
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open3"
        # has_opened=True (BLOQUE 63 invariant preserved)
        assert e.has_opened is True

    def test_open3_stays_terminal(self) -> None:
        """BLOQUE 65: open3 is the TERMINAL state — no transition out.

        After reaching open3, the mine stays there indefinitely until
        destroyed (HP=0). The cycle is ONE-WAY.
        """
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD + 10  # BLOQUE 69: 130 (above the yellow line)
        # Full cycle: 0.016 + 0.2 + 0.2 = 0.416s
        e.update(0.016, player_x=160.0, player_y=400.0)
        e.update(0.2, player_x=160.0, player_y=400.0)
        e.update(0.2, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open3"
        # Run for 5 more seconds — should stay in open3
        for _ in range(50):
            e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open3"

    def test_open3_fires_every_1_second(self) -> None:
        """BLOQUE 67: MINE-ASTEROID fires 1 fan per second in open3.

        User's absolute requirement: the open mine must fire forward
        at 1Hz, not just once. After the first fire (on entry to
        open3), the mine must keep firing every MINE_FIRE_INTERVAL_S
        (1.0s) until destroyed.

        Test: enter open3, reset on_fire (caller responsibility),
        advance time in 0.1s ticks for 2.5s. Verify on_fire is set
        True approximately 2-3 times during that span (1Hz ± noise).
        """
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD + 10  # BLOQUE 69: 130 (above the yellow line)
        e.update(0.016, player_x=160.0, player_y=400.0)
        e.update(0.2, player_x=160.0, player_y=400.0)
        e.update(0.2, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open3"
        # Entry fire: on_fire was set True. Caller resets it.
        e.on_fire = False
        # Track how many times on_fire flips to True over 2.5s
        fire_count = 0
        for _ in range(25):
            was_firing = e.on_fire
            e.update(0.1, player_x=160.0, player_y=400.0)
            if not was_firing and e.on_fire:
                fire_count += 1
        # Expected: ~2 fires (at t=1.0 and t=2.0) in 2.5s of post-entry
        # open3 time. Allow a tolerance of [1, 3] for tick noise.
        assert 1 <= fire_count <= 3, (
            f"Expected 1-3 fires in 2.5s of open3 time, got {fire_count}. "
            f"This means the mine is not firing at 1Hz as required."
        )

    def test_open3_fire_interval_is_one_second(self) -> None:
        """BLOQUE 67: MINE_FIRE_INTERVAL_S is exactly 1.0s.

        Required so the mine fires "1 time per second" as specified.
        """
        assert MINE_FIRE_INTERVAL_S == 1.0

    def test_closed_open1_open2_do_not_fire(self) -> None:
        """BLOQUE 67: only open3 fires. closed/open1/open2 are silent.

        While in 'asteroid mode' (closed), the mine is silent and
        indestructible. While opening (open1/open2), the mine is
        vulnerable but not yet firing. The first fire is on entry
        to open3, then every 1s thereafter.
        """
        # Spawn above the threshold so the mine stays closed while
        # we verify it doesn't fire. BLOQUE 69: y must be < 120 (above
        # the yellow line on screen) to stay closed.
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        # closed (above threshold — no transition)
        e.update(0.5, player_x=160.0, player_y=400.0)
        assert e.mine_state == "closed"
        assert e.on_fire is False
        # open1 (move into the trigger zone, y >= 120)
        e.y = OPENING_Y_THRESHOLD + 10  # BLOQUE 69: 130 (below the yellow line)
        e.update(0.05, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open1"
        assert e.on_fire is False
        # open2 (0.2s in open1)
        e.update(0.2, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open2"
        assert e.on_fire is False
        # open3 (0.2s in open2) — on_fire is set True on ENTRY only
        e.update(0.2, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open3"
        assert e.on_fire is True

    def test_has_opened_set_when_reaching_open3(self) -> None:
        """BLOQUE 65: has_opened=True is set at the open2->open3 transition.

        This is the same invariant from BLOQUE 63 (no re-open) but
        moved to the open3 transition since there's no closing state.
        """
        # BLOQUE 69: spawn at y=130 (above the yellow line) so the
        # mine opens on the first update.
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 130.0)
        assert e.has_opened is False
        # Run a full cycle
        e.update(0.016, player_x=160.0, player_y=400.0)  # closed -> open1
        e.update(0.2, player_x=160.0, player_y=400.0)    # open1 -> open2
        e.update(0.2, player_x=160.0, player_y=400.0)    # open2 -> open3
        assert e.mine_state == "open3"
        assert e.has_opened is True

    def test_mine_drifts_down_with_velocity(self) -> None:
        """BLOQUE 68: MINE-ASTEROID has drift velocity (vx, vy != 0).

        The bug: previously spawn_obstacle returned only {x, y} for the
        MINE_ASTEROID payload. The enemy was created with vx=vy=0
        (dataclass defaults) and never moved. The mine stayed at the
        spawn y (off-screen) and never reached OPENING_Y_THRESHOLD,
        so it never opened. Result: 'asteroids are static, they don't
        open' in gameplay.

        This test asserts the spawn_obstacle payload now includes
        drift_vx and drift_vy, and that an enemy created from this
        payload actually moves when update() is called.
        """
        from src.entities.enemies.enemy import spawn_obstacle
        # Find a payload that is a MINE_ASTEROID (try a few seeds)
        import random
        payload = None
        for seed in range(100):
            rng = random.Random(seed)
            if rng.random() < 0.25:  # MINE_SPAWN_FRACTION
                kind, p = spawn_obstacle(rng)
                if kind == "mine_asteroid":
                    payload = p
                    break
        assert payload is not None, "could not sample a MINE_ASTEROID payload"
        # The payload MUST include drift_vx and drift_vy (not just x, y)
        assert "drift_vx" in payload, (
            f"MINE_ASTEROID payload missing drift_vx (was the static-asteroid bug)"
        )
        assert "drift_vy" in payload, (
            f"MINE_ASTEROID payload missing drift_vy (was the static-asteroid bug)"
        )
        # The drift velocity should be non-zero (mimics asteroid drift)
        assert payload["drift_vy"] > 0, (
            f"drift_vy should be positive (downward), got {payload['drift_vy']}"
        )
        # End-to-end: an enemy with these vx/vy actually moves
        e = create_enemy(
            EnemyKind.MINE_ASTEROID,
            payload["x"], payload["y"],
        )
        e.vx = payload["drift_vx"]
        e.vy = payload["drift_vy"]
        e.y = -40  # above the playfield like a real spawn
        e.update(1.0, player_x=160.0, player_y=400.0)
        # After 1s of drift, the mine should have moved noticeably
        assert e.y > -40, (
            f"After 1s, mine y should have increased (moved down), "
            f"got y={e.y}. This means the mine is static and will "
            f"never reach OPENING_Y_THRESHOLD to open."
        )

    def test_mine_culled_when_off_screen_bottom(self) -> None:
        """BLOQUE 68: MINE-ASTEROID is culled when y > INTERNAL_H + 32.

        The bug: the off-screen cull was at the bottom of
        _update_mine_asteroid but every state branch returned before
        reaching it. So mines that drifted past the bottom of the
        screen were never marked DEAD and accumulated in the pool.

        The cull is now at the top of the function, before the state
        branches. This test verifies it.
        """
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 100.0)
        e.vy = 100.0  # fast downward
        e.y = 1000  # way off the bottom of the 480-tall playfield
        e.update(0.016, player_x=160.0, player_y=400.0)
        # The mine should now be marked DEAD
        assert e.state == EnemyState.DEAD, (
            f"Mine at y=1000 should be culled (DEAD), got state={e.state}"
        )


# =====================================================================
# State timer (2 tests)
# =====================================================================
class TestStateTimer:
    def test_state_timer_resets_on_transition(self) -> None:
        """state_timer resets to 0.0 each time the state changes."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD + 10  # BLOQUE 69: 130 (above the yellow line)
        e.update(0.016, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open1"
        assert e.state_timer == 0.0  # reset on transition
        e.update(0.1, player_x=160.0, player_y=400.0)
        # Timer should now have accumulated (still in 'open1')
        assert e.mine_state == "open1"
        assert e.state_timer > 0.0
        # 0.1s more -> transitions to 'open2', timer resets to 0
        e.update(0.1, player_x=160.0, player_y=400.0)
        assert e.mine_state == "open2"
        assert e.state_timer == 0.0

    def test_state_timer_advances_in_each_state(self) -> None:
        """state_timer advances inside each non-closed state."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD + 10  # BLOQUE 69: 130 (above the yellow line)
        e.update(0.0, player_x=160.0, player_y=400.0)
        e.update(0.1, player_x=160.0, player_y=400.0)
        t1 = e.state_timer
        e.update(0.1, player_x=160.0, player_y=400.0)
        t2 = e.state_timer
        assert t2 > t1  # advancing in 'open1'
        assert t2 < 0.2  # not yet at threshold (open1=0.2s)


# =====================================================================
# Firing pattern (2 tests)
# =====================================================================
class TestFiring:
    def _make_mine_in_open3(self) -> Enemy:
        """BLOQUE 65: advance the MINE-ASTEROID to open3 (the firing state)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.y = OPENING_Y_THRESHOLD + 10  # BLOQUE 69: 130 (above the yellow line)
        # Use small ticks to control state transitions
        e.update(0.016, player_x=160.0, player_y=400.0)  # closed -> open1
        e.update(0.2, player_x=160.0, player_y=400.0)     # open1 -> open2
        e.update(0.2, player_x=160.0, player_y=400.0)     # open2 -> open3 (fires)
        assert e.mine_state == "open3"
        return e

    def test_fire_spawns_3_bullets(self) -> None:
        """_fire_mine_bullets spawns 3 BULLET_ENEMY_MINE bullets in the pool."""
        pool = ProjectilePool(capacity=64)
        e = self._make_mine_in_open3()
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
        e = self._make_mine_in_open3()
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

    def test_open3_vulnerable_to_bullets(self) -> None:
        """BLOQUE 64.A: HP=3, so 3 hits destroy the MINE_ASTEROID.

        BLOQUE 65: the vulnerable terminal state is 'open3' (was 'open'
        in BLOQUE 63/64.5).
        """
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        # Force into 'open3' state directly
        e.mine_state = "open3"
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

    def test_open1_vulnerable_to_bullets(self) -> None:
        """BLOQUE 65: open1 is vulnerable (only closed is immune)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_state = "open1"
        e.hp = 3
        # 3 hits to destroy
        e.apply_damage(1)
        e.apply_damage(1)
        result = e.apply_damage(1)
        assert result is True

    def test_open2_vulnerable_to_bullets(self) -> None:
        """BLOQUE 65: open2 is vulnerable (only closed is immune)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_state = "open2"
        e.hp = 3
        # 3 hits to destroy
        e.apply_damage(1)
        e.apply_damage(1)
        result = e.apply_damage(1)
        assert result is True


# =====================================================================
# Sprite assets (BLOQUE 65: 4-state cycle, 4 dirs)
# =====================================================================
class TestSprites:
    def test_4_states_exist(self) -> None:
        """BLOQUE 65: closed/open1/open2/open/death directories all exist.

        The legacy 5-state cycle (closed/opening/open/closing) is
        replaced with a 4-state cycle (closed/open1/open2/open3).
        open3 reuses the legacy `open/` directory.
        """
        for sub in ("closed", "open1", "open2", "open", "death"):
            d = MINE_ASTEROID_SPRITES_DIR / sub
            assert d.is_dir(), f"missing dir: {d}"

    def test_open1_sprite_is_64x64(self) -> None:
        """BLOQUE 65: open1 sprite is 64x64 (matches the asteroid size)."""
        from PIL import Image
        f = MINE_ASTEROID_SPRITES_DIR / "open1" / "frame_00.png"
        assert f.is_file(), f"missing open1 frame: {f}"
        with Image.open(f) as img:
            assert img.size == (64, 64), f"open1 size {img.size}, expected (64, 64)"

    def test_open2_sprite_is_64x64(self) -> None:
        """BLOQUE 65: open2 sprite is 64x64 (matches the asteroid size)."""
        from PIL import Image
        f = MINE_ASTEROID_SPRITES_DIR / "open2" / "frame_00.png"
        assert f.is_file(), f"missing open2 frame: {f}"
        with Image.open(f) as img:
            assert img.size == (64, 64), f"open2 size {img.size}, expected (64, 64)"

    def test_open3_sprite_uses_new_reference(self) -> None:
        """BLOQUE 65: open3 sprite (open/frame_00.png) is the user's new ship reference.

        The new reference image was processed and saved to
        `open/frame_00.png` (replacing the legacy BLOQUE 63 sprite).
        The new image is a different visual from the legacy one
        (different dimensions / different ship with gun).
        """
        from PIL import Image
        f = MINE_ASTEROID_SPRITES_DIR / "open" / "frame_00.png"
        assert f.is_file(), f"missing open frame: {f}"
        with Image.open(f) as img:
            # BLOQUE 65: 64x64 (was 32x32 in BLOQUE 63 to match asteroid size)
            assert img.size == (64, 64), f"open3 size {img.size}, expected (64, 64)"

    def test_closed_uses_round_png(self) -> None:
        """The closed frame is byte-equal to Assets/sprites/asteroids/round.png.

        BLOQUE 65: the perfect-camo invariant from BLOQUE 63 is preserved.
        """
        import hashlib
        assert ASTEROID_ROUND_PNG.is_file(), f"missing asteroid round: {ASTEROID_ROUND_PNG}"
        closed_path = MINE_ASTEROID_SPRITES_DIR / "closed" / "frame_00.png"
        assert closed_path.is_file(), f"missing closed frame: {closed_path}"
        with open(ASTEROID_ROUND_PNG, "rb") as f:
            h1 = hashlib.md5(f.read()).hexdigest()
        with open(closed_path, "rb") as f:
            h2 = hashlib.md5(f.read()).hexdigest()
        assert h1 == h2, "closed frame must be byte-equal to asteroid round.png (perfect camo)"

    def test_opening_directory_removed(self) -> None:
        """BLOQUE 65: opening/ directory moved to _backup_pre_bloque_65/.

        The 4-state cycle doesn't need a 'opening' state.
        """
        d = MINE_ASTEROID_SPRITES_DIR / "opening"
        assert not d.is_dir(), f"opening/ should be removed (moved to backup)"

    def test_closing_directory_removed(self) -> None:
        """BLOQUE 65: closing/ directory moved to _backup_pre_bloque_65/.

        The 4-state cycle doesn't need a 'closing' state — the mine
        never closes after opening.
        """
        d = MINE_ASTEROID_SPRITES_DIR / "closing"
        assert not d.is_dir(), f"closing/ should be removed (moved to backup)"

    def test_death_frame_count(self) -> None:
        """death has 10 frames."""
        for i in range(10):
            f = MINE_ASTEROID_SPRITES_DIR / "death" / f"frame_{i:02d}.png"
            assert f.is_file(), f"missing death frame: {f}"

    # ------------------------------------------------------------------
    # BLOQUE 66: variant-aware closed state. The closed sprite is one of
    # 5 variants matching the regular asteroid sprites (round, elongated,
    # spiked, hollowed, cracked). mine_variant is set at spawn time by
    # gameplay_runtime.py to a random 0-4.
    # ------------------------------------------------------------------
    def test_closed_loads_variant_0_path(self) -> None:
        """BLOQUE 66: mine_variant=0 loads closed/frame_00.png (round)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_variant = 0
        e.mine_state = "closed"
        assert e.animation_path == "enemies/mine_asteroid/closed/frame_00.png"

    def test_closed_loads_variant_4_path(self) -> None:
        """BLOQUE 66: mine_variant=4 loads closed/frame_04.png (cracked)."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_variant = 4
        e.mine_state = "closed"
        assert e.animation_path == "enemies/mine_asteroid/closed/frame_04.png"

    def test_closed_clamps_out_of_range_variant(self) -> None:
        """BLOQUE 66: variant > 4 clamps to 4 (cracked) — safety net."""
        e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
        e.mine_variant = 99
        e.mine_state = "closed"
        assert e.animation_path == "enemies/mine_asteroid/closed/frame_04.png"

    def test_open1_open2_open3_ignore_variant(self) -> None:
        """BLOQUE 66: only closed uses mine_variant. Other states use frame_00.

        The intermediate and terminal states are hand-designed composites
        (open1: thin crack, open2: wider gap with gun, open3: full ship).
        These are not per-variant — the same composite is reused for any
        mine_variant because the reveal animation is the same regardless
        of which asteroid variant was being mimicked.
        """
        for v in (0, 2, 4):
            e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
            e.mine_variant = v
            for st in ("open1", "open2"):
                e.mine_state = st
                assert e.animation_path == f"enemies/mine_asteroid/{st}/frame_00.png"
            e.mine_state = "open3"
            assert e.animation_path == "enemies/mine_asteroid/open/frame_00.png"

    def test_closed_5_variants_all_exist(self) -> None:
        """BLOQUE 66: 5 closed variant frames all exist on disk.

        Required for variant-aware camouflage: each mine_variant 0..4
        must have a sprite. If any variant is missing, the camo is
        broken (the closed state would show a missing texture).
        """
        names = ("round", "elongated", "spiked", "hollowed", "cracked")
        for i, name in enumerate(names):
            f = MINE_ASTEROID_SPRITES_DIR / "closed" / f"frame_{i:02d}.png"
            assert f.is_file(), f"missing closed variant {i} ({name}): {f}"
            # Sanity: each variant is byte-equal to its asteroid source
            import hashlib
            src = ROOT / "Assets" / "sprites" / "asteroids" / f"{name}.png"
            assert src.is_file(), f"missing asteroid source: {src}"
            with open(f, "rb") as fp:
                h_closed = hashlib.md5(fp.read()).hexdigest()
            with open(src, "rb") as fp:
                h_src = hashlib.md5(fp.read()).hexdigest()
            assert h_closed == h_src, (
                f"closed/frame_{i:02d}.png must be byte-equal to "
                f"asteroids/{name}.png (perfect camo)"
            )


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
        """spawn_obstacle produces ~1/4 MINE_ASTEROID (BLOQUE 64.5: 1/8 → 1/4)."""
        from src.entities.enemies.enemy import spawn_obstacle
        rng = random.Random(0xCAFE)
        results = {"asteroid": 0, "mine_asteroid": 0}
        for _ in range(2000):
            kind, _payload = spawn_obstacle(rng)
            results[kind] = results.get(kind, 0) + 1
        # ~1/4 should be mine_asteroid, ~3/4 should be asteroid
        ratio = results.get("mine_asteroid", 0) / 2000
        assert 0.20 <= ratio <= 0.30, f"mine_asteroid ratio {ratio} not in [0.20, 0.30] (expected ~0.25)"

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
