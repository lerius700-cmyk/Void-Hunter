"""VOID HUNTER — entry point.

BLOQUE 0: minimal CLI. --check validates the bootstrap. Default mode opens a
window at 120 FPS (BLOQUE 0 stub); --profile / --act / --boss / --stress will
light up as their respective BLOQUE land.

Description: parse CLI flags, dispatch to the right runtime path.
Dependencies: pygame, src.core.{settings,game}.
"""
from __future__ import annotations

import argparse
import sys


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="void-hunter",
        description="VOID HUNTER — vertical shmup, 8-bit + Metal Slug juice, 120 FPS lock.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate imports + settings; exit 0 if OK, 1 if broken.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run with FPS overlay (requires BLOQUE 14+; stub at BLOQUE 0).",
    )
    parser.add_argument(
        "--act",
        type=int,
        choices=(1, 2, 3),
        help="Start at specific act (1, 2, or 3). Requires BLOQUE 10+.",
    )
    parser.add_argument(
        "--boss",
        type=str,
        choices=("goliath", "hydra", "phantom", "nemesis"),
        help="Jump to boss fight. Requires BLOQUE 9+.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug HUD overlay.",
    )
    parser.add_argument(
        "--stress",
        type=str,
        metavar="SPEC",
        help="Stress test, e.g. '1500particles 400bullets'. Requires BLOQUE 16.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Profile/stress duration in seconds (default 30).",
    )
    parser.add_argument(
        "--validate-waves",
        action="store_true",
        help="Validate the 18 wave JSON scripts. Requires BLOQUE 10+.",
    )
    return parser.parse_args(argv)


def _cmd_check() -> int:
    """Validate imports + key settings. Always returns 0 at BLOQUE 0 baseline."""
    try:
        from src.core.settings import (
            FPS_TARGET,
            FIXED_DT,
            WINDOW_W,
            WINDOW_H,
            MIXER_CHANNELS,
            MIXER_SAMPLE_RATE,
        )
    except ImportError as exc:
        print(f"VOID HUNTER check FAIL: {exc}", file=sys.stderr)
        return 1

    print("VOID HUNTER check OK")
    print(f"  FPS_TARGET       = {FPS_TARGET}")
    print(f"  FIXED_DT         = {FIXED_DT:.6f}s")
    print(f"  Window           = {WINDOW_W}x{WINDOW_H}")
    print(f"  Mixer            = {MIXER_CHANNELS} ch @ {MIXER_SAMPLE_RATE} Hz")
    print("  BLOQUE 0 baseline — game loop lands in BLOQUE 14.")
    return 0


def _cmd_play() -> int:
    """Default mode: launch the game window (BLOQUE 0 stub)."""
    from src.core.game import Game
    return Game().run()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.check:
        return _cmd_check()

    if args.profile or args.act or args.boss or args.stress or args.validate_waves:
        print(
            f"VOID HUNTER: --{_active_flag(args)} requires later BLOQUE.",
            file=sys.stderr,
        )
        print(
            "  --profile  → BLOQUE 14 (GameStateMachine + scene stack)",
            file=sys.stderr,
        )
        print(
            "  --act/--boss → BLOQUE 9-10 (boss FSM + wave manager)",
            file=sys.stderr,
        )
        print(
            "  --stress  → BLOQUE 16 (stress harness + coverage gate)",
            file=sys.stderr,
        )
        print(
            "  --validate-waves → BLOQUE 10 (wave JSON loader)",
            file=sys.stderr,
        )
        return 1

    return _cmd_play()


def _active_flag(args: argparse.Namespace) -> str:
    for name in (
        "profile",
        "act",
        "boss",
        "stress",
        "validate_waves",
    ):
        if getattr(args, name, None):
            return name.replace("_", "-")
    return "unknown"


if __name__ == "__main__":
    sys.exit(main())
