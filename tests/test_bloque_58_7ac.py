"""BLOQUE 58.7ac: regression test for the sub-boss being killed by
the boss perfect trigger.

Bug: BOSS_PERFECT_TRIGGER_S was 60s, but the sub-boss doesn't fire
until chain.elapsed ~ 95s. On a perfect run, the boss intro would
fire at 60s, the SUB_BOSS_INTRO would fire at 95s, and on the resume
from SUB_BOSS_INTRO the BOSS_INTRO would fire AGAIN on the same
frame the sub-boss spawns, killing the sub-boss before the player
could see it.

Fix: BOSS_PERFECT_TRIGGER_S raised to 100s (after sub-boss). And the
boss trigger check now returns early if sub_boss_pending is True AND
sub_boss_alive is True (sub-boss on-screen being fought).
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
import pygame
pygame.init()
pygame.display.set_mode((320, 480))


@pytest.fixture(autouse=True)
def _ensure_pygame():
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((320, 480))
    yield


def test_boss_trigger_does_not_fire_during_sub_boss_fight():
    """While sub_boss_pending=True and sub_boss_alive=True, the boss
    trigger must NOT fire. This is the bug we just fixed.

    The BOSS_PERFECT_TRIGGER_S is now 100s. But even at 100s with a
    perfect score, if the sub-boss is on-screen the boss intro must
    wait for the sub-boss to die.
    """
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.enemies.enemy import EnemyKind
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    rt.on_enter()
    # Force post-O2 state with sub-boss pending AND alive
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    rt._level1_chain.perfect = True  # would normally trigger boss perfect
    rt._level1_chain.kills = 50
    rt._level1_chain.elapsed_s = 100.0  # at the perfect trigger threshold
    # Spawn the sub-boss manually
    rt._spawn_sub_boss()
    assert rt._sub_boss_alive is True
    # Now run update; the boss trigger should NOT fire because the
    # sub-boss is on-screen.
    transitions = []
    rt._transition_to = lambda s: transitions.append(s)
    rt.update(1.0 / 60.0)
    from src.core.scene_manager import GameState
    boss_intros = [s for s in transitions if s == GameState.BOSS_INTRO]
    assert len(boss_intros) == 0, (
        f"BOSS_INTRO fired {len(boss_intros)} times while sub-boss was alive. "
        f"Sub-boss is at the screen and being fought; boss must wait."
    )


def test_boss_perfect_trigger_at_100s_after_sub_boss_killed():
    """After the sub-boss is killed, the boss perfect trigger CAN fire
    at 100s. This validates the new timing.
    """
    from src.ui.gameplay_runtime import GameplayRuntime
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    rt.on_enter()
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = False  # sub-boss already killed
    rt._level1_chain.perfect = True
    rt._level1_chain.kills = 50
    rt._level1_chain.elapsed_s = 100.0
    rt._sub_boss_alive = False
    transitions = []
    rt._transition_to = lambda s: transitions.append(s)
    rt.update(1.0 / 60.0)
    from src.core.scene_manager import GameState
    boss_intros = [s for s in transitions if s == GameState.BOSS_INTRO]
    # The perfect trigger condition is met, so the boss SHOULD fire.
    assert len(boss_intros) >= 1, (
        f"Expected BOSS_INTRO to fire after sub-boss killed, but got 0. "
        f"Transitions: {transitions}"
    )


def test_boss_perfect_trigger_at_99s_does_not_fire():
    """Just before the perfect trigger (99s), no trigger should fire.
    This validates the boundary.
    """
    from src.systems.wave_manager import BossTrigger
    bt = BossTrigger()
    assert bt.evaluate(elapsed_s=99.0, waves_complete=False, perfect=True, kills=10) is None
    assert bt.evaluate(elapsed_s=100.0, waves_complete=False, perfect=True, kills=10) == "perfect"
