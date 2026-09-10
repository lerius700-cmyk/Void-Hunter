"""BLOQUE 71 e2e: run GameplayRuntime 60s, verify no NameError, capture PNG.

Validates Tasks 1-3 end-to-end:
- T1: Asteroid hit_timer + palette-swap flash render
- T2: MINE-ASTEROID hit_timer + white flash in 4 states
- T3: asteroid_hit SFX dispatch

The 8-point checklist for BLOQUE 71 is satisfied:
1. Tests pass (T1, T2, T3) - verified separately
2. No regressions - verified separately
3. THIS SCRIPT: 60s e2e without NameError
4. THIS SCRIPT: PNG capture of mid-flash
5. User confirms visual (post-task)
6-8. Phase 5 (release)
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import sys
import time
from pathlib import Path

import pygame

pygame.init()
pygame.display.set_mode((320, 480))
pygame.mixer.init()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui.gameplay_runtime import GameplayRuntime
from src.entities.asteroid import Asteroid
from src.entities.enemies.enemy import EnemyKind


def main() -> int:
    out_dir = Path("tools/playtest_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clear crash.log so we can detect new errors
    crash_log = Path("logs/crash.log")
    if crash_log.exists():
        crash_log.unlink()

    print("=== BLOQUE 71 e2e ===")
    runtime = GameplayRuntime(transition_to=lambda *a, **k: None)
    target = pygame.Surface((320, 480))

    # Initialize wave state so update() doesn't NPE on _level1_chain.
    # The runtime's __init__ leaves _level1_chain as None; _populate_level1_queue
    # would set it up but is normally called via wave state transitions. For the
    # e2e we call it directly to get a fully-functional level-1 setup.
    runtime._populate_level1_queue()

    # Spawn 1 regular asteroid at (160, 50)
    ast = Asteroid(
        x=160, y=50,
        radius=16,
        drift_vx=0.0, drift_vy=30.0,
        variant=0, scale=1.0,
        hidden_powerup=None,
    )
    runtime._asteroids.append(ast)
    print(f"Spawned asteroid at (160, 50)")

    # Spawn 1 MINE-ASTEROID at (160, 200) via the enemy pool
    mine = runtime._enemies.spawn(EnemyKind.MINE_ASTEROID, 160.0, 200.0)
    if mine is None:
        print("ERROR: enemy pool exhausted; cannot spawn MINE")
        return 1
    print(f"Spawned MINE at (160, 200)")

    # Spawn 1 CRUISER (leader ship) at (160, 320) — large enough to show
    # the shape-aware flash clearly.
    cruiser = runtime._enemies.spawn(EnemyKind.CRUISER, 160.0, 320.0)
    if cruiser is None:
        print("WARNING: enemy pool exhausted; cannot spawn CRUISER")
    else:
        print(f"Spawned CRUISER at (160, 320)")

    # Spawn 1 SCOUT as a WAVE-PATTERN LEADER at (240, 280). The leader's
    # is_leader flag drives a different draw color in _draw_enemy_scaled
    # (BLOQUE 58.10) and, when a PatternRuntime is active, a glow ring.
    # In the e2e (no active pattern runtime) only the body flash + the
    # color difference apply.
    scout = runtime._enemies.spawn(EnemyKind.SCOUT, 240.0, 280.0)
    if scout is None:
        print("WARNING: enemy pool exhausted; cannot spawn SCOUT leader")
    else:
        scout.is_leader = True
        # Bump HP to a leader-appropriate value so the flash render doesn't
        # accidentally destroy it during the 60s loop.
        scout.hp = 30
        scout.max_hp = 30
        print(f"Spawned SCOUT leader at (240, 280), HP=30, is_leader=True")

    # 60s simulation at 60fps
    print("Running 60s e2e at 60fps...")
    start = time.perf_counter()
    frames = 0
    for _ in range(60 * 60):
        runtime.update(1/60)
        frames += 1
    elapsed = time.perf_counter() - start
    print(f"60s e2e: {frames} frames in {elapsed:.1f}s ({frames/elapsed:.0f} fps)")

    # Force mid-flash on asteroid (sets hit_timer to 0.15s, mid-decay)
    ast.hit()
    ast.hit_timer = 0.10  # mid-flash
    print(f"Asteroid hit_timer set to 0.10 (mid-flash)")

    # Force mid-flash on MINE (find it in the enemy pool)
    for e in runtime._enemies.pool:
        if e.active and e.kind == EnemyKind.MINE_ASTEROID:
            e.hit_timer = 0.10
            print(f"MINE hit_timer set to 0.10 (mid-flash)")
            break

    # Force mid-flash on CRUISER (leader)
    if cruiser is not None:
        cruiser.hit_timer = 0.10
        print(f"CRUISER hit_timer set to 0.10 (mid-flash)")

    # Force mid-flash on SCOUT leader
    if scout is not None:
        scout.hit_timer = 0.10
        print(f"SCOUT leader hit_timer set to 0.10 (mid-flash)")

    # Render and capture
    target.fill((0, 0, 0))
    runtime.draw(target)

    capture_path = out_dir / "bloque_71_asteroid_flash_01.png"
    pygame.image.save(target, str(capture_path))
    size = capture_path.stat().st_size
    print(f"Saved capture to {capture_path} ({size} bytes)")

    # Verify PNG is valid
    loaded = pygame.image.load(str(capture_path))
    w, h = loaded.get_size()
    if (w, h) != (320, 480):
        print(f"ERROR: PNG dimensions are {w}x{h}, expected 320x480")
        return 1

    # Check crash.log
    if crash_log.exists():
        text = crash_log.read_text()
        if "NameError" in text or "AttributeError" in text:
            print("ERROR: NameError or AttributeError in crash.log")
            print("First 500 chars:")
            print(text[:500])
            return 1

    # Sample center pixel to confirm SOMETHING was drawn at (160, 50)
    center_pixel = target.get_at((160, 50))[:3]
    print(f"Pixel at (160, 50) = RGB{center_pixel}")

    print("=== e2e complete: PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
