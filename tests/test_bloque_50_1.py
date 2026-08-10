"""BLOQUE 50.1: regression test for the SUB_BOSS_INTRO loop bug.

Bug: when the SUB_BOSS_INTRO scene transitioned back to GAMEPLAY,
on_enter() reset the level1 chain to O1, which immediately re-triggered
the sub_boss_after condition and looped the yellow warning forever.

Fix: on_enter() detects "resume from SUB_BOSS_INTRO" via
chain.sub_boss_pending and skips the chain reset.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()


def _noop_transition(_state: object) -> None:
    pass


def _make_runtime(is_boss: bool = False, act: int = 1):
    """Match the test_gameplay_runtime helper."""
    from src.ui.gameplay_runtime import GameplayRuntime
    rt = GameplayRuntime(transition_to=_noop_transition, is_boss=is_boss, act=act)
    rt.on_enter()
    return rt


def test_on_enter_does_not_reset_chain_when_sub_boss_pending() -> None:
    """Regression: on_enter from SUB_BOSS_INTRO must NOT clear the chain."""
    from src.systems.wave_manager import WaveChain
    rt = _make_runtime()
    assert rt._level1_chain is not None
    chain: WaveChain = rt._level1_chain
    # Simulate state right before SUB_BOSS_INTRO: O2 just finished, pending=True,
    # current_wave_idx=2 (post-O2)
    chain.current_wave_idx = 2
    chain._sub_boss_pending = True
    pre_wave_idx = chain.current_wave_idx
    pre_pending = chain.sub_boss_pending
    assert pre_pending is True
    assert pre_wave_idx == 2
    # Simulate SUB_BOSS_INTRO transitioning back to GAMEPLAY (which calls on_enter)
    rt.on_enter()
    # The chain must NOT be reset
    assert chain.current_wave_idx == pre_wave_idx, (
        f"chain was reset: was {pre_wave_idx}, now {chain.current_wave_idx}"
    )
    assert chain.sub_boss_pending == pre_pending, (
        f"pending was reset: was {pre_pending}, now {chain.sub_boss_pending}"
    )
    # Sub-boss is not yet alive (will be spawned by _update_enemies)
    assert rt._sub_boss_alive is False
    # Intro is considered "done" (we just came back from it)
    assert rt._sub_boss_intro_done is True


def test_on_enter_does_reset_chain_on_fresh_start() -> None:
    """Sanity: a fresh start (no sub_boss_pending) DOES reset the chain."""
    rt = _make_runtime()
    assert rt._level1_chain is not None
    # Simulate chain being mid-wave (NOT pending)
    rt._level1_chain.current_wave_idx = 3
    rt._level1_chain._sub_boss_pending = False
    # Do a "fresh" on_enter
    rt.on_enter()
    chain = rt._level1_chain
    assert chain is not None
    # Chain should be reset
    assert chain.current_wave_idx == 0
    assert chain.sub_boss_pending is False
    # Sub-boss state should be fresh
    assert rt._sub_boss_alive is False
    assert rt._sub_boss_intro_done is False


def test_sub_boss_spawns_after_resume() -> None:
    """After resume from SUB_BOSS_INTRO, _update_enemies should spawn the sub-boss."""
    from src.entities.enemies.enemy import EnemyKind
    rt = _make_runtime()
    assert rt._level1_chain is not None
    # Mark chain as pending sub-boss and at wave 3
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    # Resume from sub-boss intro
    rt.on_enter()
    # First update should spawn the sub-boss
    rt.update(1.0 / 60.0)
    assert rt._sub_boss_alive is True
    # And the spawned enemy should be a SUB_BOSS
    found = False
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            found = True
            break
    assert found, "SUB_BOSS not spawned after resume"


def test_killing_sub_boss_clears_pending_and_resumes_chain() -> None:
    """Killing the sub-boss should clear pending and let the chain continue."""
    from src.entities.enemies.enemy import EnemyKind
    rt = _make_runtime()
    assert rt._level1_chain is not None
    # Set up the resume state
    rt._level1_chain.current_wave_idx = 2
    rt._level1_chain._sub_boss_pending = True
    rt.on_enter()
    rt.update(1.0 / 60.0)  # spawn sub-boss
    assert rt._sub_boss_alive is True
    # Find and "kill" the sub-boss
    sub = None
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            sub = e
            break
    assert sub is not None
    rt._on_enemy_killed(sub)
    # Now pending should be cleared
    assert rt._level1_chain.sub_boss_pending is False
    assert rt._sub_boss_alive is False
