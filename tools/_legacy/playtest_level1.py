"""Play through level 1 myself (BLOQUE 58.5) and capture frames.

BLOQUE 58.5: I run the game headless with --roguelike 42, advance through
~20 seconds of gameplay, and save key frames so I can verify the sprite
orientation fix + find any other visual/mechanics issues.

Captures 4 frames at t=2s, 6s, 12s, 18s covering:
  - Early waves (SCOUT, CRUISER arriving)
  - Mid waves (HEAVY, KAMIKAZE, SNIPER, DRONE)
  - Pre-sub-boss (TURRET, mixed)
  - Sub-boss spawn (the Star Wolf V ship)

Output: tools/playtest_out/polish_48_playthrough_*.png
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_EASY"] = "1"
os.environ["VOID_HUNTER_INVULN"] = "1"
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
from src.core.game import Game
from src.core.scene_manager import GameState
from src.roguelike.integration import enable_roguelike

OUT_DIR = ROOT / "tools" / "playtest_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Force a specific seed for reproducibility
enable_roguelike(seed=42)
print("[playtest] using seed=42")

pygame.init()
game = Game()
# Skip the title — go straight to gameplay
game.scenes.transition_to(GameState.ACT_INTRO)
game.scenes.transition_to(GameState.GAMEPLAY)
game.scenes.scenes[GameState.GAMEPLAY].on_enter()

# Find the gameplay scene and its runtime
gp = game.scenes.scenes[GameState.GAMEPLAY]
rt = gp.runtime if hasattr(gp, "runtime") else gp
print(f"[playtest] runtime type: {type(rt).__name__}")

# Capture times (seconds)
CAPTURE_TIMES = [2.0, 6.0, 12.0, 22.0, 28.0]
CAPTURE_LABELS = ["t=2s_early_wave", "t=6s_mid_wave", "t=12s_late_wave", "t=22s_sub_boss", "t=28s_final_boss"]

# Advance time and capture
start_wall = time.perf_counter()
sim_time = 0.0
dt = 1.0 / 60.0
frame_count = 0
last_capture_idx = -1
captures = []

print(f"[playtest] running for ~35s, capturing at {CAPTURE_TIMES}")

while sim_time < 35.0:
    # Update the game
    game.scenes.update(dt)
    sim_time += dt
    frame_count += 1
    # Draw the game (this is what was missing — scene.draw renders to internal)
    game.scenes.draw(game.internal)
    # Check if we should capture
    for i, t in enumerate(CAPTURE_TIMES):
        if sim_time >= t and i > last_capture_idx:
            # Capture the current internal surface
            try:
                internal = game.internal if hasattr(game, "internal") else None
                if internal is not None:
                    out = OUT_DIR / f"polish_48_playthrough_{CAPTURE_LABELS[i]}.png"
                    pygame.image.save(internal, str(out))
                    print(f"[playtest] captured {out.name}")
                    captures.append(out.name)
                    last_capture_idx = i
                    break
            except Exception as e:
                print(f"[playtest] capture failed at t={sim_time:.1f}: {e}")
    # Safety: stop early if game over
    if hasattr(game, "_running") and not game._running:
        print(f"[playtest] game stopped at t={sim_time:.1f}")
        break

elapsed = time.perf_counter() - start_wall
print(f"[playtest] done: {frame_count} frames in {elapsed:.2f}s wall time")
print(f"[playtest] state at end: {game.scenes.current_state.name}")
if hasattr(rt, "_player"):
    p = rt._player
    print(f"[playtest] player: hp={p.hp}/{p.hp_max} lives={p.lives} bombs={p.bombs} score={p.score}")
if hasattr(rt, "_enemies"):
    active = sum(1 for e in rt._enemies.pool if e.active and e.state.name != "DEAD")
    print(f"[playtest] active enemies at end: {active}")
if hasattr(rt, "_wave_idx"):
    print(f"[playtest] wave_idx at end: {rt._wave_idx}")
if hasattr(rt, "_wave_mgr") and hasattr(rt._wave_mgr, "current"):
    print(f"[playtest] wave_mgr state: kills={rt._wave_mgr.current.kills} target={rt._wave_mgr.current.kill_target}")
