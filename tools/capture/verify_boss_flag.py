"""BLOQUE 73.5: verify --boss goliath actually lands in a GOLIATH fight
with the restored 60-frame animation set running.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
sys.path.insert(0, ".")

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from src.core.game import Game
from src.core.scene_manager import GameState
from src.ui.scenes import BossFightScene

g = Game()
g.scenes.register_scene(
    GameState.BOSS_FIGHT,
    BossFightScene(
        g.scenes.transition_to,
        act=1,
        audio=g.audio,
        get_session_score=g._get_session_score,
        set_session_score=g._set_session_score,
    ),
)
for st in (GameState.ACT_INTRO, GameState.GAMEPLAY, GameState.BOSS_INTRO, GameState.BOSS_FIGHT):
    g.scenes.transition_to(st)

sc = g.scenes.scenes[GameState.BOSS_FIGHT]
rt = sc._rt
b = rt._boss

print(f"estado final       : {g.scenes.current_state.name}")
print(f"boss               : {b.id}")
print(f"hp                 : {b.hp}")
print(f"anim inicial       : {b.animation_state} frame={b.animation_frame}")

seen = set()
for _ in range(120 * 6):  # 6 seconds at 120Hz
    rt.update(1.0 / 120.0)
    seen.add((b.animation_state, b.animation_frame))

states = sorted({s for s, _ in seen})
frames_by_state: dict[str, set[int]] = {}
for s, f in seen:
    frames_by_state.setdefault(s, set()).add(f)

print()
print("anims vistas en 6s de pelea:")
for s in states:
    fr = sorted(frames_by_state[s])
    print(f"  {s:<16} frames {fr}")
print()
print(f"total de poses distintas: {len(seen)}")