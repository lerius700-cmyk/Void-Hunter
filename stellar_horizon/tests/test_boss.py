# stellar_horizon/tests/test_boss.py
import pytest

from stellar_horizon.entities.boss import Boss, BossPhase


class FakePlayer:
    def __init__(self, x=200, y=135):
        self.x, self.y = x, y


def test_boss_phase_constants():
    assert BossPhase.ENTERING == "entering"
    assert BossPhase.PHASE_1 == "phase_1"
    assert BossPhase.PHASE_2 == "phase_2"
    assert BossPhase.DYING == "dying"
    assert BossPhase.DEAD == "dead"


def test_boss_starts_entering():
    b = Boss()
    assert b.phase == BossPhase.ENTERING
    assert b.alive is True
    assert b.hp == 60


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
    assert b.hp == 50
    assert b.alive is True


def test_boss_transitions_to_phase_2_at_30_hp():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.take_damage(30)
    assert b.phase == BossPhase.PHASE_2


def test_boss_transitions_to_dying_at_0_hp():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.take_damage(60)
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
    b.attack_cd = 0.0
    new_bullets = b.update(0.1, FakePlayer(x=200, y=80))
    assert len(new_bullets) >= 1


def test_boss_phase_1_attack_cooldown_resets():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.attack_cd = 0.0
    b.update(0.1, FakePlayer())
    assert b.attack_cd > 0


def test_boss_dying_ends_in_dead():
    b = Boss()
    b.phase = BossPhase.DYING
    b.x, b.y = 350.0, 135.0
    b.dying_timer = 1.5
    b.update(0.1, FakePlayer())
    for _ in range(20):
        b.update(0.1, FakePlayer())
    assert b.phase == BossPhase.DEAD
