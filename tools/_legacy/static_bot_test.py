"""Static-position test: bot stays at center, fires constantly, dashes when in danger.

This isolates the question "can the player kill enemies by just firing
up from the bottom?". If yes, the game is mechanically working.
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
    game.scenes.transition_to(GameState.ACT_INTRO)
    game.scenes.transition_to(GameState.GAMEPLAY)
    game.scenes.scenes[GameState.GAMEPLAY].on_enter()

    # Track metrics
    history = []
    # Run for 60s
    for frame in range(60 * 120):
        scene = game.scenes.scenes.get(game.scenes.current_state)
        if scene is None or not hasattr(scene, "_rt"):
            if game.scenes.current_state == GameState.GAME_OVER:
                print("Player died. Test ending.")
                break
            continue
        rt = scene._rt
        rt._read_input = lambda: None
        # Force player to center, fire constantly, dash only if bullet imminent
        rt._player.x = 120
        # Just fire
        rt._player.input_fire = True
        # Dash if bullet very close
        imminent = False
        for p in rt._bullets.pool:
            if p.active and p.owner in (1, 2):
                if abs(p.x - 120) < 6 and abs(p.y - rt._player.y) < 6:
                    imminent = True
                    break
        rt._player.input_dash = imminent
        # Bomb if 2+ enemies close
        live = sum(1 for e in rt._enemies.pool if e.active and e.state.name != "DEAD")
        if live >= 3 and rt._player.bombs > 0 and rt._player.wants_to_bomb == False:
            rt._player.input_bomb = True
            rt._player.wants_to_bomb = True
        else:
            rt._player.input_bomb = False

        rt.update(1.0 / 120.0)
        t = frame / 120.0
        if frame % 120 == 0:
            history.append((
                t,
                rt._player.hp,
                rt._scoring.score,
                rt._wave_mgr.current.kills,
                sum(1 for e in rt._enemies.pool if e.active),
                rt._player.bombs,
            ))

    print(f"\n{'t':>5s}  {'hp':>3s}  {'score':>6s}  {'kills':>5s}  {'enemies':>7s}  {'bombs':>5s}")
    for t, hp, score, kills, enemies, bombs in history:
        print(f"{t:5.1f}  {hp:>3d}  {score:>6d}  {kills:>5d}  {enemies:>7d}  {bombs:>5d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
