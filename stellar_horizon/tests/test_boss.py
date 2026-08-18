# stellar_horizon/tests/test_boss.py
import pytest

from stellar_horizon.entities.boss import Boss, BossPhase, BossAction


class FakePlayer:
    def __init__(self, x=200, y=135):
        self.x, self.y = x, y


def test_boss_phase_constants():
    assert BossPhase.ENTERING == "entering"
    assert BossPhase.PHASE_1 == "phase_1"
    assert BossPhase.PHASE_2 == "phase_2"
    assert BossPhase.DYING == "dying"
    assert BossPhase.DEAD == "dead"


def test_boss_action_constants():
    assert BossAction.IDLE_PATROL == "idle_patrol"
    assert BossAction.TELEGRAPH == "telegraph"
    assert BossAction.CHARGE == "charge"
    assert BossAction.RETREAT == "retreat"
    assert BossAction.COOLDOWN == "cooldown"


def test_boss_starts_entering():
    b = Boss()
    assert b.phase == BossPhase.ENTERING
    assert b.alive is True
    # New: 10x HP = 600.
    assert b.hp == 600
    assert b.max_hp == 600


def test_boss_transitions_to_phase_1_after_entry():
    b = Boss()
    for _ in range(600):
        b.update(1 / 120, FakePlayer())
    assert b.phase == BossPhase.PHASE_1


def test_boss_takes_damage_in_phase_1():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.take_damage(10)
    assert b.hp == 590
    assert b.alive is True


def test_boss_transitions_to_phase_2_at_300_hp():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.take_damage(300)
    assert b.phase == BossPhase.PHASE_2


def test_boss_transitions_to_dying_at_0_hp():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.take_damage(600)
    assert b.phase == BossPhase.DYING


def test_boss_hitbox_is_48x48():
    b = Boss()
    b.x, b.y = 350.0, 135.0
    hb = b.hitbox()
    assert hb.width == 48
    assert hb.height == 48


def test_boss_phase_1_attacks_aimed():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.action = BossAction.TELEGRAPH
    b.bullet_cd = 0.0
    new_bullets = b.update(0.01, FakePlayer(x=200, y=80))
    assert len(new_bullets) >= 1
    # Boss bullets deal 2 damage (DAMAGE_TO_PLAYER).
    assert new_bullets[0].damage == 2


def test_boss_bullets_deal_two_damage():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.action = BossAction.TELEGRAPH
    b.bullet_cd = 0.0
    new_bullets = b.update(0.01, FakePlayer(x=200, y=80))
    assert len(new_bullets) >= 1
    for nb in new_bullets:
        assert nb.damage == Boss.DAMAGE_TO_PLAYER == 2


def test_boss_action_cycle_advances_after_telegraph():
    """Telegraph action timer expires -> next action is CHARGE."""
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.action = BossAction.TELEGRAPH
    b.action_timer = 0.01  # almost expired
    b.update(0.02, FakePlayer())
    assert b.action == BossAction.CHARGE


def test_boss_action_cycle_full_sequence():
    """Boss cycles through TELEGRAPH -> CHARGE -> RETREAT -> COOLDOWN
    -> IDLE_PATROL within a few seconds.
    """
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.action = BossAction.TELEGRAPH
    b.action_timer = 0.01
    seen = set()
    # Run a generous number of frames; we should see every action.
    for _ in range(600):
        b.update(1 / 60, FakePlayer())
        seen.add(b.action)
        if len(seen) == 5:
            break
    assert BossAction.TELEGRAPH in seen
    assert BossAction.CHARGE in seen
    assert BossAction.RETREAT in seen
    assert BossAction.COOLDOWN in seen
    assert BossAction.IDLE_PATROL in seen


def test_boss_stays_in_arena_bounds():
    """Boss never leaves the arena rectangle even after long updates."""
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.action = BossAction.IDLE_PATROL
    b.action_timer = 0.0
    b._enter_action(BossAction.IDLE_PATROL)
    for _ in range(1200):
        b.update(1 / 60, FakePlayer(x=10, y=10))
        assert b.x >= Boss.ARENA_X_MIN
        assert b.x <= Boss.ARENA_X_MAX
        assert b.y >= Boss.ARENA_Y_MIN
        assert b.y <= Boss.ARENA_Y_MAX


def test_boss_charge_captures_player_position():
    """On entering CHARGE, the boss records a target; during CHARGE
    it moves toward that target, not a live-tracked player.
    """
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.action = BossAction.TELEGRAPH
    b.action_timer = 0.01
    # First update: TELEGRAPH -> CHARGE transition (no capture yet).
    b.update(0.02, FakePlayer(x=150, y=140))
    assert b.action == BossAction.CHARGE
    # Second update: enter CHARGE branch and capture the target.
    b.update(0.02, FakePlayer(x=150, y=140))
    assert b.charge_target_x > 0
    assert b.charge_target_y > 0


def test_boss_dying_ends_in_dead():
    b = Boss()
    b.phase = BossPhase.DYING
    b.x, b.y = 350.0, 135.0
    b.dying_timer = 1.5
    b.update(0.1, FakePlayer())
    for _ in range(20):
        b.update(0.1, FakePlayer())
    assert b.phase == BossPhase.DEAD


# ------------------------------------------------------------------
# Hit-streak + ring drop tests (Checkpoint 3 wired in via boss API).
# ------------------------------------------------------------------

def test_boss_hit_streak_starts_at_zero():
    b = Boss()
    assert b.hit_streak == 0


def test_boss_hit_streak_increments_with_damage():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    for _ in range(5):
        b.take_damage(1)
    assert b.hit_streak == 5


def test_boss_should_not_drop_ring_below_threshold():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    for _ in range(19):
        b.take_damage(1)
    assert not b.should_drop_ring()


def test_boss_should_drop_ring_at_threshold_within_window():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    # Simulate 20 fast hits within the 7s window. We don't have
    # access to update() from here, so we just advance the boss's
    # internal _now clock by hand.
    b._now = 1.0
    for _ in range(20):
        b.take_damage(1)
    assert b.hit_streak == 20
    assert b.should_drop_ring() is True


def test_boss_should_not_drop_ring_outside_window():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b._now = 0.0
    for _ in range(20):
        b.take_damage(1)
    # Push _now past the 7s window without a new hit.
    b._now = 8.0
    assert b.should_drop_ring() is False


def test_boss_on_player_damaged_resets_streak():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b._now = 0.0
    for _ in range(10):
        b.take_damage(1)
    assert b.hit_streak == 10
    b.on_player_damaged()
    assert b.hit_streak == 0


def test_boss_consume_ring_drop_50_percent():
    """Over 1000 trials, the drop fires ~500 times (±5%)."""
    drops = 0
    for _ in range(1000):
        b = Boss()
        b.phase = BossPhase.PHASE_1
        b._now = 0.0
        for _ in range(20):
            b.take_damage(1)
        if b.consume_ring_drop():
            drops += 1
    # Expect ~500 (allow generous band for RNG).
    assert 400 <= drops <= 600
