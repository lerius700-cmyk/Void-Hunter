"""Verify all state transitions work without errors (BLOQUE 17.6).

Walks through the entire state machine to confirm every transition is valid
and doesn't crash. This is the "is the game actually navigable" check.
"""
from __future__ import annotations
import os, sys
from pathlib import Path
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
from src.core.game import Game
from src.core.scene_manager import GameState


def main() -> int:
    pygame.init()
    game = Game()
    # All valid transitions per the state machine
    valid_chains = [
        # Normal gameplay flow
        [GameState.TITLE, GameState.ACT_INTRO, GameState.GAMEPLAY,
         GameState.PAUSE, GameState.GAMEPLAY,
         GameState.BOSS_INTRO, GameState.BOSS_FIGHT,
         GameState.ACT_CLEARED, GameState.ACT_INTRO, GameState.GAMEPLAY,
         GameState.BOSS_INTRO, GameState.BOSS_FIGHT,
         GameState.ACT_CLEARED, GameState.VICTORY, GameState.CREDITS,
         GameState.TITLE],
        # Game over flow
        [GameState.TITLE, GameState.ACT_INTRO, GameState.GAMEPLAY,
         GameState.GAME_OVER, GameState.TITLE, GameState.CREDITS],
    ]
    issues = 0
    for chain_n, chain in enumerate(valid_chains):
        game2 = Game()
        ok = True
        for i, target in enumerate(chain):
            try:
                game2.scenes.transition_to(target)
                actual = game2.scenes.current_state
                if actual != target:
                    print(f"  Chain {chain_n + 1}, step {i + 1}: expected {target.value}, got {actual.value}")
                    issues += 1
                    ok = False
            except Exception as e:
                print(f"  Chain {chain_n + 1}, step {i + 1}: FAILED to transition to {target.value}: {e}")
                issues += 1
                ok = False
        if ok:
            print(f"  Chain {chain_n + 1}: OK ({len(chain)} transitions)")
    # Test that invalid transitions are rejected
    game3 = Game()
    try:
        game3.scenes.transition_to(GameState.BOSS_FIGHT)  # TITLE -> BOSS_FIGHT invalid
        print(f"  Invalid transition not rejected: TITLE -> BOSS_FIGHT succeeded")
        issues += 1
    except Exception:
        print(f"  Invalid transition rejected: TITLE -> BOSS_FIGHT (OK)")
    print(f"\n{'='*40}\nTotal issues: {issues}")
    return 0 if issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
