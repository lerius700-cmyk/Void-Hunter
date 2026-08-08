"""Quick visual inspector: dumps frames of each game state in sequence."""
from __future__ import annotations
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
from src.core.game import Game
from src.core.scene_manager import GameState

pygame.init()
g = Game()
out_dir = "tools/playtest_out/state_frames"
os.makedirs(out_dir, exist_ok=True)

# Force each state in order
states = [
    GameState.TITLE, GameState.ACT_INTRO, GameState.GAMEPLAY,
    GameState.BOSS_INTRO, GameState.BOSS_FIGHT, GameState.ACT_CLEARED,
    GameState.GAME_OVER, GameState.VICTORY, GameState.CREDITS,
]
for st in states:
    try:
        g.scenes.transition_to(st)
    except Exception as e:
        print(f"  skip {st.value}: {e}")
        continue
    g.scenes.draw(g.internal)
    path = f"{out_dir}/{st.value}.png"
    pygame.image.save(g.internal, path)
    print(f"  saved {path}")

print("Done.")
