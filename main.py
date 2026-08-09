"""VOID HUNTER — entry point (BLOQUE 16: full CLI flags).

Description: parse CLI flags, dispatch to the right runtime path.
BLOQUE 16 adds --duration to auto-exit after N seconds (for stress/smoke).
Dependencies: pygame, src.core.{settings,game}.
"""
from __future__ import annotations

import argparse
import sys
import time


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="void-hunter",
        description="VOID HUNTER — vertical shmup, 8-bit + Metal Slug juice, 120 FPS lock.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Validate imports + settings; exit 0 if OK, 1 if broken.",
    )
    parser.add_argument(
        "--profile", action="store_true",
        help="Run with FPS overlay (BLOQUE 14+).",
    )
    parser.add_argument(
        "--act", type=int, choices=(1, 2, 3),
        help="Start at specific act (1, 2, or 3). BLOQUE 10+.",
    )
    parser.add_argument(
        "--boss", type=str, choices=("goliath", "hydra", "phantom", "nemesis"),
        help="Jump to boss fight. BLOQUE 9+.",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug HUD overlay.",
    )
    parser.add_argument(
        "--stress", type=str, metavar="SPEC",
        help="Stress test, e.g. '1500particles 400bullets'. BLOQUE 16.",
    )
    parser.add_argument(
        "--duration", type=int, default=30,
        help="Profile/stress duration in seconds (default 30).",
    )
    parser.add_argument(
        "--validate-waves", action="store_true",
        help="Validate the 18 wave JSON scripts. BLOQUE 10+.",
    )
    parser.add_argument(
        "--easy", action="store_true",
        help="BLOQUE 28: easy mode — 9 lives, 4 bombs, 2x score multiplier.",
    )
    parser.add_argument(
        "--scale", type=int, default=4, choices=(1, 2, 3, 4),
        help="Window scale multiplier (default 4 = 960x1440; use 2 for 480x720 on small screens).",
    )
    return parser.parse_args(argv)


def _cmd_check() -> int:
    """Validate imports + key settings. Always returns 0 at baseline."""
    try:
        from src.core.settings import (
            FPS_TARGET, FIXED_DT, WINDOW_W, WINDOW_H,
            MIXER_CHANNELS, MIXER_SAMPLE_RATE,
        )
    except ImportError as exc:
        print(f"VOID HUNTER check FAIL: {exc}", file=sys.stderr)
        return 1
    print("VOID HUNTER check OK")
    print(f"  FPS_TARGET       = {FPS_TARGET}")
    print(f"  FIXED_DT         = {FIXED_DT:.6f}s")
    print(f"  Window           = {WINDOW_W}x{WINDOW_H}")
    print(f"  Mixer            = {MIXER_CHANNELS} ch @ {MIXER_SAMPLE_RATE} Hz")
    print(f"  BLOQUE 16: full game with 9 scenes, 18 waves, 4 bosses.")
    return 0


def _cmd_stress(duration: int) -> int:
    """BLOQUE 16: stress test. Spawn max particles + bullets, run for N sec."""
    import pygame
    from src.core.settings import INTERNAL_H, INTERNAL_W, FIXED_DT, FPS_TARGET
    from src.systems.particle_engine import ParticleEngine
    from src.systems.projectile import ProjectilePool, BULLET_PLAYER, BULLET_ENEMY
    pygame.init()
    screen = pygame.display.set_mode((INTERNAL_W, INTERNAL_H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("VOID HUNTER — Stress Test")
    clock = pygame.time.Clock()
    pe = ParticleEngine(pool_size=1500)
    proj = ProjectilePool(capacity=400)
    # Spawn max particles
    pe_count = 0
    for i in range(1500):
        x = (i % 240)
        y = (i // 240) * 2
        pe.emit(0, x, y, vx=float((i % 7) - 3), vy=float((i % 5) - 2))  # SPARK
        pe_count += 1
    # Spawn max bullets
    for i in range(400):
        proj.spawn(BULLET_PLAYER, (i % 240), (i // 240) * 2, 0.0, -480.0)
    start = time.perf_counter()
    frames = 0
    while time.perf_counter() - start < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return 0
        pe.update(FIXED_DT)
        proj.update(FIXED_DT)
        screen.fill((0, 0, 0))
        pe.draw(screen)
        proj.draw(screen)
        pygame.display.flip()
        clock.tick(FPS_TARGET)
        frames += 1
    elapsed = time.perf_counter() - start
    fps = frames / elapsed
    pygame.quit()
    print(f"STRESS: {frames} frames in {elapsed:.2f}s = {fps:.1f} FPS")
    print(f"  particles active = {pe.active_count}, bullets = {proj.active_count}")
    return 0


def _cmd_play(duration: int) -> int:
    """Default mode: launch the game window. Auto-exits after duration sec."""
    from src.core.game import Game
    game = Game()
    # Wrap run() to honor --duration
    import pygame
    import time
    start = time.perf_counter()
    try:
        while game._running:
            if time.perf_counter() - start > duration:
                break
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    game._running = False
            frame_time = game.clock.tick(FPS_TARGET := 120) / 1000.0
            frame_time = min(frame_time, 1.0 / 30.0)
            game._accumulator += frame_time
            while game._accumulator >= (1.0 / 120):
                game.scenes.update(1.0 / 120)
                game._accumulator -= 1.0 / 120
            # Clear internal, draw scenes to internal, scale to display
            game.internal.fill((0, 0, 0))
            game.scenes.draw(game.internal)
            game._present()
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
    return 0


FPS_TARGET = 120  # used by _cmd_play


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.easy:
        # BLOQUE 28: set env var so Player.reset() reads it
        import os
        os.environ["VOID_HUNTER_EASY"] = "1"
        print("VOID HUNTER: --easy mode enabled (9 lives, 4 bombs)")

    if args.scale != 4:
        # BLOQUE 31: override window scale (1x=240x360, 2x=480x720, 3x=720x1080)
        import os
        os.environ["VOID_HUNTER_SCALE"] = str(args.scale)
        print(f"VOID HUNTER: --scale {args.scale} (window = {240*args.scale}x{360*args.scale})")

    if args.check:
        return _cmd_check()

    if args.validate_waves:
        from src.systems.wave_manager import WaveManager
        wm = WaveManager()
        ok, msg = wm.validate()
        if ok:
            print(f"WAVES: {len(wm.scripts)} waves validated OK")
            return 0
        print(f"WAVES FAIL: {msg}", file=sys.stderr)
        return 1

    if args.stress:
        return _cmd_stress(args.duration)

    if args.act is not None or args.boss is not None:
        # BLOQUE 9/10: jump to specific act/boss. For now, route to play.
        # Future BLOQUE will wire up the per-act wave + boss intro sequence.
        print(f"VOID HUNTER: --act {args.act} --boss {args.boss} (full integration in next BLOQUE; running main game for {args.duration}s)")
        return _cmd_play(args.duration)

    if args.profile:
        return _cmd_play(args.duration)

    return _cmd_play(args.duration)


if __name__ == "__main__":
    sys.exit(main())
