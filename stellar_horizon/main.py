"""STELLAR HORIZON — entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stellar-horizon",
        description="STELLAR HORIZON — horizontal 16-bit shmup, 480x270 internal.",
    )
    parser.add_argument("--check", action="store_true", help="Validate imports + settings; exit 0/1.")
    parser.add_argument("--duration", type=int, default=0, help="Auto-exit after N seconds (0 = no auto-exit).")
    args = parser.parse_args(argv)
    if args.check:
        from stellar_horizon.settings import INTERNAL_W, INTERNAL_H, FPS_TARGET
        print("STELLAR HORIZON check OK")
        print(f"  Internal: {INTERNAL_W}x{INTERNAL_H}")
        print(f"  FPS target: {FPS_TARGET}")
        return 0
    from stellar_horizon.core.game import Game
    g = Game()
    if args.duration > 0:
        import time
        start = time.perf_counter()
        g._running = True
        last = pygame.time.get_ticks() / 1000.0 if pygame.get_init() else 0.0
        import pygame as _pygame
        while g._running and (time.perf_counter() - start) < args.duration:
            g._tick_frame(last)
            last = _pygame.time.get_ticks() / 1000.0
        _pygame.quit()
    else:
        g.run()
    return 0


if __name__ == "__main__":
    import pygame
    sys.exit(main())
