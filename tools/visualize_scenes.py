"""VOID HUNTER scene visualizer.

Sets SDL_VIDEODRIVER=dummy to run headless, then renders each game scene
to a PNG file. I (the agent) read these PNGs to "see" what the game
looks like and find visual bugs.

Usage:
    python tools/visualize_scenes.py
    # outputs to tools/visualize_out/
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

# Display needs to be initialized for font rendering
pygame.init()
pygame.display.set_mode((960, 1440))

OUT = ROOT / "tools" / "visualize_out"
OUT.mkdir(parents=True, exist_ok=True)

from src.core.game import Game
from src.core.scene_manager import GameState
from src.core.settings import FIXED_DT, INTERNAL_H, INTERNAL_W


def render_and_save(game: Game, name: str, ticks: int = 30) -> None:
    """Run `ticks` updates, then render the current scene to PNG."""
    for _ in range(ticks):
        game.scenes.update(FIXED_DT)
    print(f"    state={game.scenes.current_state.name}  internal={game.internal.get_size()}")
    # Clear internal surface
    game.internal.fill((0, 0, 0))
    # Draw to 240x360 internal surface
    game.scenes.draw(game.internal)
    # Save the 240x360 internal (what the user would see scaled 4x on a real display)
    out = OUT / f"{name}.png"
    pygame.image.save(game.internal, str(out))
    print(f"  -> {out}")


def main() -> int:
    game = Game()

    # 01 — TITLE
    print("Rendering TITLE...")
    render_and_save(game, "01_title", ticks=60)

    # 02 — ACT_INTRO
    print("Rendering ACT_INTRO...")
    game.scenes.transition_to(GameState.ACT_INTRO)
    render_and_save(game, "02_act_intro", ticks=30)

    # 03 — GAMEPLAY (idle player, no movement)
    print("Rendering GAMEPLAY (idle)...")
    game.scenes.transition_to(GameState.GAMEPLAY)
    render_and_save(game, "03_gameplay_idle", ticks=30)

    # 04 — GAMEPLAY (player firing and moving)
    print("Rendering GAMEPLAY (combat)...")
    gp = game.scenes.scenes[GameState.GAMEPLAY]
    # Monkey-patch input reader so we can control inputs
    gp._rt._read_input = lambda: None
    # Place player at right edge to show wall indicator + fire
    gp._rt._player.x = INTERNAL_W - 12
    gp._rt._player.y = INTERNAL_H - 60
    gp._rt._player.input_fire = True
    for _ in range(180):  # 1.5 seconds
        gp._rt._player.input_fire = True
        gp.update(FIXED_DT)
    game.internal.fill((0, 0, 0))
    game.scenes.draw(game.internal)
    pygame.image.save(game.internal, str(OUT / "04_gameplay_moving.png"))
    print(f"  -> {OUT / '04_gameplay_moving.png'}")
    gp._rt._player.input_fire = False

    # 05 — BOSS_INTRO (animated)
    print("Rendering BOSS_INTRO...")
    game.scenes.transition_to(GameState.BOSS_INTRO)
    render_and_save(game, "05_boss_intro", ticks=180)  # ~1.5s for slide-in

    # 06 — BOSS_FIGHT (real boss with attacks)
    print("Rendering BOSS_FIGHT...")
    game.scenes.transition_to(GameState.BOSS_FIGHT)
    bf = game.scenes.scenes[GameState.BOSS_FIGHT]
    bf._rt._read_input = lambda: None
    # Set player at a survivable position to capture a clean combat frame
    bf._rt._player.x = 60
    bf._rt._player.y = 300
    bf._rt._player.invuln_frames = 99999  # invulnerable for the capture
    # Tick ~1.5s to let boss fire some attacks
    for _ in range(180):
        bf._rt._player.input_fire = True
        bf.update(FIXED_DT)
        if bf._rt._boss is None or not bf._rt._boss.active:
            break
    game.internal.fill((0, 0, 0))
    game.scenes.draw(game.internal)
    pygame.image.save(game.internal, str(OUT / "06_boss_fight.png"))
    print(f"  -> {OUT / '06_boss_fight.png'}")
    bf._rt._player.input_fire = False

    # 07 — ACT_CLEARED
    print("Rendering ACT_CLEARED...")
    game.scenes.transition_to(GameState.ACT_CLEARED)
    render_and_save(game, "07_act_cleared", ticks=30)

    # 08 — VICTORY
    print("Rendering VICTORY...")
    game.scenes.transition_to(GameState.VICTORY)
    render_and_save(game, "08_victory", ticks=30)

    # 09 — CREDITS
    print("Rendering CREDITS...")
    game.scenes.transition_to(GameState.CREDITS)
    render_and_save(game, "09_credits", ticks=30)

    # 10 — PAUSE overlay on top of GAMEPLAY
    print("Rendering PAUSE overlay...")
    game2 = Game()
    game2.scenes.transition_to(GameState.ACT_INTRO)
    game2.scenes.transition_to(GameState.GAMEPLAY)
    for _ in range(30):
        game2.scenes.update(FIXED_DT)
    game2.scenes.push_overlay(game2.scenes.scenes[GameState.PAUSE])
    game2.internal.fill((0, 0, 0))
    game2.scenes.draw(game2.internal)
    pygame.image.save(game2.internal, str(OUT / "10_pause_overlay.png"))
    print(f"  -> {OUT / '10_pause_overlay.png'}")

    pygame.quit()
    print("\nDone. Inspect tools/visualize_out/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
