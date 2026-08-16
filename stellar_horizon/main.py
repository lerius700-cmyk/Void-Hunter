"""STELLAR HORIZON — entry point."""
from __future__ import annotations

import argparse
import sys


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
    # Defer to Task 15 for the real run loop. For now, just acknowledge.
    print(f"STELLAR HORIZON: --duration {args.duration} (game loop wired in Task 15)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
