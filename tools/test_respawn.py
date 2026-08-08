"""Clean test of the player respawn sequence (BLOQUE 17.6).

Drives the player through the full 3-lives cycle to verify:
- take_damage actually damages
- HIT state -> DEAD state when HP <= 0
- DEAD state respawns after PLAYER_DEATH_DURATION_S
- Respawn restores HP to hp_max
- 4th death (lives go to -1) triggers GAME_OVER
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
from src.entities.player import PlayerState


def main() -> int:
    pygame.init()
    game = Game()
    game.scenes.transition_to(GameState.ACT_INTRO)
    game.scenes.transition_to(GameState.GAMEPLAY)
    game.scenes.scenes[GameState.GAMEPLAY].on_enter()

    rt = game.scenes.scenes[GameState.GAMEPLAY]._rt
    rt._read_input = lambda: None

    print(f"Initial: hp={rt._player.hp} lives={rt._player.lives} state={rt._player.state.value}")

    # Apply damage the proper way (via take_damage) — wait long enough for invuln
    for life_n in range(6):  # 3 lives + 1 to trigger game over + 2 buffer
        # Kill the player: 3 hits with 0.5s between (matches invuln duration)
        for hit_n in range(4):
            if rt._player.hp <= 0 or rt._player.is_game_over:
                break
            rt._player.take_damage(1)
            # Wait for HIT (0.30s) + invuln (0.50s) = 0.80s
            for _ in range(int(0.85 * 120)):
                rt._player.input_fire = False
                rt._player.input_left = False
                rt._player.input_right = False
                rt._player.input_dash = False
                rt._player.input_bomb = False
                rt.update(1.0 / 120.0)
        # Now should be in DEAD or GAME_OVER
        if rt._player.is_game_over:
            print(f"  After life {life_n + 1}: GAME OVER (expected after 3 lives)")
            break
        if rt._player.state == PlayerState.DEAD:
            print(f"  After life {life_n + 1}: in DEAD state, waiting for respawn...")
        # Wait for respawn (1.20s + safety)
        for _ in range(int(2.0 * 120)):
            rt._player.input_fire = False
            rt._player.input_left = False
            rt._player.input_right = False
            rt._player.input_dash = False
            rt._player.input_bomb = False
            rt.update(1.0 / 120.0)
        # Check respawn
        if rt._player.is_game_over:
            print(f"  After life {life_n + 1}: GAME OVER (lives ran out)")
            break
        if rt._player.state == PlayerState.DEAD:
            print(f"  Life {life_n + 1}: BUG — still in DEAD state after 2.0s wait (respawn didn't fire)")
            print(f"    death_timer={rt._player.death_timer:.2f} is_game_over={rt._player.is_game_over} lives={rt._player.lives}")
            break
        print(f"  Life {life_n + 1} respawned: hp={rt._player.hp}/{rt._player.hp_max} lives={rt._player.lives} state={rt._player.state.value} x={rt._player.x:.0f} y={rt._player.y:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
