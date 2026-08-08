"""Capture gameplay frames during a successful kill sequence.

Bot: aim at nearest enemy, fire, don't move when aligned, dodge if needed.
This produces a more representative playthrough than the dumb bot.
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

OUT = ROOT / "tools" / "playtest_out" / "real_run"
OUT.mkdir(parents=True, exist_ok=True)


def find_nearest(rt):
    px, py = rt._player.x, rt._player.y
    best = None
    best_d = 9999
    for e in rt._enemies.pool:
        if e.active and e.state.name != "DEAD":
            d = abs(e.x - px)
            if d < best_d:
                best_d = d
                best = (e.x, e.y)
    if rt._boss is not None and rt._boss.active:
        d = abs(rt._boss.x - px)
        if d < best_d:
            best = (rt._boss.x, rt._boss.y)
    return best


def main() -> int:
    pygame.init()
    game = Game()
    game.scenes.transition_to(GameState.ACT_INTRO)
    game.scenes.transition_to(GameState.GAMEPLAY)
    game.scenes.scenes[GameState.GAMEPLAY].on_enter()

    last_shot = 0
    last_frame_save = -1
    frames_captured = 0
    initial_kills = 0

    for frame in range(60 * 120):  # 60s
        t = frame / 120.0
        scene = game.scenes.scenes.get(game.scenes.current_state)
        if scene is None or not hasattr(scene, "_rt"):
            if game.scenes.current_state == GameState.GAME_OVER:
                break
            continue
        rt = scene._rt
        rt._read_input = lambda: None
        # Aim
        nearest = find_nearest(rt)
        if nearest is not None:
            ex, ey = nearest
            if ex < rt._player.x - 6:
                rt._player.input_left = True
                rt._player.input_right = False
            elif ex > rt._player.x + 6:
                rt._player.input_left = False
                rt._player.input_right = True
            else:
                rt._player.input_left = False
                rt._player.input_right = False
        # Fire
        rt._player.input_fire = True
        # Dash when needed
        for p in rt._bullets.pool:
            if p.active and p.owner in (1, 2):
                fut_x = p.x + p.vx * 0.1
                fut_y = p.y + p.vy * 0.1
                if abs(fut_x - rt._player.x) < 8 and abs(fut_y - rt._player.y) < 8:
                    if t - last_shot > 0.8:
                        rt._player.input_dash = True
                        last_shot = t
                    break
        # Bomb if low HP
        if rt._player.hp <= 1 and rt._player.bombs > 0:
            rt._player.input_bomb = True
            rt._player.wants_to_bomb = True

        rt.update(1.0 / 120.0)

        # Capture frames around kills
        current_kills = rt._wave_mgr.current.kills
        if current_kills > initial_kills:
            initial_kills = current_kills
            for f in range(3):  # capture 3 frames around each kill
                game.internal.fill((0, 0, 0))
                rt.draw(game.internal)
                pygame.image.save(game.internal, str(OUT / f"kill_{initial_kills:02d}_frame{f}.png"))
                frames_captured += 1
        # Also capture a frame every 2 seconds
        if int(t) % 2 == 0 and int(t) != last_frame_save:
            last_frame_save = int(t)
            game.internal.fill((0, 0, 0))
            rt.draw(game.internal)
            pygame.image.save(game.internal, str(OUT / f"t{int(t):03d}s.png"))
            frames_captured += 1

    print(f"Captured {frames_captured} frames in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
