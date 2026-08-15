"""BLOQUE 58.7ab: simulate the full level 1 wave flow and check sub-boss."""
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
pygame.display.set_mode((320, 480))


def _noop(_state):
    pass


def test_full_wave_flow_triggers_sub_boss():
    """Run the wave flow and verify sub_boss_pending becomes True after O2."""
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.enemies.enemy import EnemyKind
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    chain = rt._level1_chain
    assert chain is not None
    print(f"Start: current_wave={chain.current_wave_idx}, sub_boss_pending={chain.sub_boss_pending}")
    print(f"_sub_boss_after_waves: {chain._sub_boss_after_waves}")
    # BLOQUE 58.11: doubled ships, so 100s no longer covers all 4 waves
    # (O1+O2 = 36+48 = 84s minimum). Extended to 200s.
    transitions = []
    real_transition = rt._transition_to
    def capture(state):
        transitions.append((rt._t, state))
    rt._transition_to = capture
    for i in range(12000):  # 200 seconds at 60fps
        rt.update(1.0 / 60.0)
        if i % 1200 == 0:
            print(f"t={rt._t:.1f}s wave={chain.current_wave_idx} sub_boss_pending={chain.sub_boss_pending} enemies_alive={sum(1 for e in rt._enemies.pool if e.active)}")
    rt._transition_to = real_transition
    # Print all transitions
    print(f"\nTransitions ({len(transitions)}):")
    from src.core.scene_manager import GameState
    for t, s in transitions:
        name = s.name if hasattr(s, "name") else str(s)
        print(f"  t={t:.1f}s -> {name}")
    # Check if SUB_BOSS_INTRO was triggered
    sub_boss_intros = [t for t, s in transitions if s == GameState.SUB_BOSS_INTRO]
    print(f"\nSUB_BOSS_INTRO triggered {len(sub_boss_intros)} times")
    assert len(sub_boss_intros) >= 1, "SUB_BOSS_INTRO was never triggered!"


if __name__ == "__main__":
    test_full_wave_flow_triggers_sub_boss()
