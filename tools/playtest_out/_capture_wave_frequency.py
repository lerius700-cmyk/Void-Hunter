"""Capture visual proof of the wave frequency change (BLOQUE 58.next item #2).

Spawns N waves at the given interval and renders the playfield at
6 timestamps. Same seed for both intervals — the difference is the
NUMBER of waves that have started by each timestamp.

Output: tools/playtest_out/wave_freq_<interval>s.png — 6 panels
showing the playfield at t=0, 2, 4, 6, 8, 10 seconds.
"""
import os
import sys
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import random
import pygame

from src.core.settings import INTERNAL_W, INTERNAL_H


def render_at_timestamps(spawn_interval: float, timestamps=(0, 2, 4, 6, 8, 10)) -> list[pygame.Surface]:
    """Simulate N=10 waves at the given interval, return playfield surfaces at each timestamp.

    Correctly counts visible waves per timestamp (not snapshots of the
    pre-allocated 128-slot EnemyPool). Each timestamp renders the ships
    that have been spawned AND whose age < wave_duration_s.
    """
    from src.entities.enemies.enemy import EnemyPool
    from src.systems.wave_patterns.v_formation import VFormationPattern
    from src.systems.wave_patterns.runtime import spawn_pattern_wave

    pool = EnemyPool(capacity=128)
    surfaces = []
    rng = random.Random(42)

    # Phase 1: spawn 10 waves and record (spawn_time, spawn_y, spawn_x)
    # for each ship. The pool pre-allocates 128 Enemy objects, so we
    # CAN'T snapshot `pool.pool` per wave (all snapshots see the same
    # final set). Instead, we record the spawn position + time so the
    # render phase can replay positions at any timestamp.
    spawn_records: list[tuple[float, float, float]] = []  # (t_spawn, x, y)
    wave_duration_s = 6.0
    for wave_idx in range(10):
        t_spawn = wave_idx * spawn_interval
        result = VFormationPattern().generate(rng, level=3)
        # Capture ship positions BEFORE spawn_pattern_wave resets the
        # pool indices, then record the new ships' spawn positions.
        spawned_now: list[tuple[float, float]] = []
        for ship in result.ships:
            spawned_now.append((ship.spawn_x, ship.spawn_y))
        spawn_pattern_wave(pool, result, current_wave_idx=0)
        for x, y in spawned_now:
            spawn_records.append((t_spawn, x, y))

    # Phase 2: render at each timestamp. Count visible ships based on
    # age = t - t_spawn (in [0, wave_duration_s)). Apply a simple
    # downward motion: y += 60 px/s × age.
    for t in timestamps:
        surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
        surf.fill((0, 0, 0))
        n_visible = 0
        for t_spawn, x, y0 in spawn_records:
            age = t - t_spawn
            if 0 <= age < wave_duration_s:
                n_visible += 1
                y = y0 + 60 * age
                if 0 <= y < INTERNAL_H:
                    pygame.draw.circle(
                        surf, (180, 180, 200), (int(x), int(y)), 4
                    )
        # Count text in the corner
        font = pygame.font.SysFont("Consolas", 14, bold=True)
        count_surf = font.render(f"t={t:2d}s  ships={n_visible}", True, (255, 255, 100))
        surf.blit(count_surf, (4, 4))
        surfaces.append(surf)
    return surfaces


def main() -> int:
    pygame.init()
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(exist_ok=True)
    for interval in (4.0, 2.0):
        panels = render_at_timestamps(interval)
        panel_w, panel_h = INTERNAL_W, INTERNAL_H
        label_h = 20
        # 3 cols x 2 rows
        cols, rows = 3, 2
        mosaic = pygame.Surface((panel_w * cols, (panel_h + label_h) * rows))
        mosaic.fill((20, 20, 20))
        font = pygame.font.SysFont("Consolas", 14, bold=True)
        for i, surf in enumerate(panels):
            col = i % cols
            row = i // cols
            x = col * panel_w
            y = row * (panel_h + label_h) + label_h
            pygame.draw.rect(mosaic, (60, 60, 60), (x, y, panel_w, panel_h), 2)
            mosaic.blit(surf, (x, y))
        title = font.render(
            f"spawn_interval={interval}s — 6 timestamps, same seed", True, (255, 255, 255)
        )
        mosaic.blit(title, (4, 2))
        out_path = out_dir / f"wave_freq_{interval:.1f}s.png"
        pygame.image.save(mosaic, str(out_path))
        print(f"saved -> {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
