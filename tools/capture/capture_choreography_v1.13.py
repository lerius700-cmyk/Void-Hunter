"""BLOQUE 58.13: Capture 8 PNGs of the 4 bezier patterns (early + mid).

Run from project root:
    python tools/capture/capture_choreography_v1.13.py

Outputs:
    tools/playtest_out/choreography_v1.13_<pattern>_<phase>.png
"""
from __future__ import annotations

import os
import random
import sys

# Use dummy SDL drivers so the script can run headless
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.entities.enemies.enemy import EnemyKind, EnemyPool
from src.systems.wave_patterns.bezier_sweep import BezierSweepPattern
from src.systems.wave_patterns.oscillating_butterfly import OscillatingButterflyPattern
from src.systems.wave_patterns.leader_chain import LeaderFollowerChainPattern
from src.systems.wave_patterns.pincer_cross import PincerCrossPattern
from src.systems.wave_patterns.runtime import spawn_pattern_wave


PATTERNS = [
    ("bezier_sweep", BezierSweepPattern()),
    ("butterfly", OscillatingButterflyPattern()),
    ("leader_chain", LeaderFollowerChainPattern()),
    ("pincer_cross", PincerCrossPattern()),
]

PHASES = [
    ("early", 1.0),
    ("mid", 3.0),
]


def main() -> None:
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    out_dir = os.path.join(PROJECT_ROOT, "tools", "playtest_out")
    os.makedirs(out_dir, exist_ok=True)

    for pattern_name, pattern in PATTERNS:
        print(f"Capturing {pattern_name}...")
        for phase_name, phase_t in PHASES:
            pool = EnemyPool(capacity=32)
            rng = random.Random(42)
            result = pattern.generate(rng, level=5)
            runtime = spawn_pattern_wave(pool, result)

            surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
            surf.fill((8, 8, 16))
            # EnemyPool wraps an inner Pool that supports __iter__ over all items.
            active = [e for e in pool.pool if e.active]
            for spawned, enemy in zip(result.ships, active):
                if enemy.path_follower is None:
                    continue
                enemy.path_follower.reset()
                for _ in range(int(phase_t * 60)):
                    enemy.path_follower.update(1.0 / 60.0)
                pos = enemy.path_follower.path.position_at(enemy.path_follower.t)
                cx, cy = int(pos.x), int(pos.y)
                color = spawned.color or (255, 255, 255)
                pygame.draw.circle(surf, color, (cx, cy), 6)

            out_path = os.path.join(
                out_dir, f"choreography_v1.13_{pattern_name}_{phase_name}.png"
            )
            big = pygame.transform.scale(surf, (INTERNAL_W * 2, INTERNAL_H * 2))
            pygame.image.save(big, out_path)
            print(f"  -> {out_path}")

    pygame.quit()
    print("\nDone. 8 PNGs written to tools/playtest_out/")


if __name__ == "__main__":
    main()
