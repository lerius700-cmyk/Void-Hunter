"""VOID HUNTER — entry point (BLOQUE 16: full CLI flags).

Description: parse CLI flags, dispatch to the right runtime path.
BLOQUE 16 adds --duration to auto-exit after N seconds (for stress/smoke).
BLOQUE 54: friendly defaults when running as a packaged .exe.
Dependencies: pygame, src.core.{settings,game}.
"""
from __future__ import annotations

import argparse
import os
import sys
import time


# BLOQUE 58.55: set the SDL audio driver BEFORE pygame.init(). The
# default is whatever SDL picks first, but on some Windows machines
# with multiple audio devices (HDMI + speakers, or virtual audio
# cables), the default can be the muted one. Explicitly trying
# wasapi first, then directsound, then winmm, gives the most reliable
# audio output across configurations.
# BLOQUE 58.57: don't force a specific driver — let pygame pick. If
# the user has weird audio routing, the default works better than a
# forced driver that might fail. Diagnostic logging will reveal what
# was actually selected.
if sys.platform == "win32":
    # Make sure logs dir exists
    try:
        os.makedirs("logs", exist_ok=True)
    except Exception:
        pass
    with open("logs/_audio_status.log", "w", encoding="utf-8") as _f:
        _f.write(f"=== void-hunter audio diagnostic ===\n")
        _f.write(f"SDL_VIDEODRIVER={os.environ.get('SDL_VIDEODRIVER', '<unset>')}\n")
        _f.write(f"SDL_AUDIODRIVER={os.environ.get('SDL_AUDIODRIVER', '<unset>')}\n")
        _f.write(f"sys.platform={sys.platform}\n")


def _detect_screen_scale() -> float:
    """BLOQUE 54 + 58.35 + 58.36g: pick a window scale that fills the
    monitor WORK AREA height (excludes the Windows taskbar).

    Uses the Windows API to read primary monitor work area (not full
    screen height) so the game window reaches top + bottom of the USABLE
    area without overlapping the taskbar. Returns a float in [1.0, 6.0]
    (was int 1..6 in BLOQUE 58.35; now fractional so 1032-tall work
    areas get 1032/480 = 2.15x and reach the edges with no black bars).
    Falls back to 3.0 if detection fails.
    """
    if sys.platform != "win32":
        return 3.0  # safe default for non-Windows hosts
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        # Get work area (excludes taskbar + docked toolbars).
        # SPI_GETWORKAREA = 0x0030
        rect = wintypes.RECT()
        ok = user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        if ok and rect.bottom > rect.top:
            work_h = rect.bottom - rect.top
            work_w = rect.right - rect.left
        else:
            # Fallback: use full monitor
            gdi32 = ctypes.windll.gdi32
            hdc = user32.GetDC(0)
            try:
                work_w = int(gdi32.GetDeviceCaps(hdc, 8))   # HORZRES
                work_h = int(gdi32.GetDeviceCaps(hdc, 10))  # VERTRES
            finally:
                user32.ReleaseDC(0, hdc)
        # Game internal is 320x480 (BLOQUE 34). Pick the EXACT float scale
        # that fills the work-area height. For 1032-tall work area
        # (1080 monitor minus 48 taskbar): 1032/480 = 2.15x. The window
        # then lands EXACTLY between the top of the monitor and the top
        # of the taskbar.
        scale_h = max(1.0, work_h / 480.0)
        return float(min(scale_h, 6.0))  # cap at 6 for 4K
    except Exception:
        return 3.0


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
        "--duration", type=int, default=0,
        help="Profile/stress duration in seconds (default 0 = no auto-exit; --duration 30 for 30s play).",
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
        "--scale", type=float, default=4.0,
        help="Window scale multiplier. Default 4 = auto-detect (fills monitor "
             "height exactly with float scale). Use --scale 2 for 640x960, "
             "--scale 2.25 for 720x1080, --scale 3 for 960x1440, etc.",
    )
    parser.add_argument(
        "--roguelike", type=int, nargs="?", const=0, default=None, metavar="SEED",
        help="BLOQUE 58: full roguelike mode. SEED is an optional int; "
             "if omitted, derived from level+attempt+salt. Procedurally generates "
             "4 chained waves + sub-boss + final boss + powerup drops. "
             "This is now the default mode (--campaign for the 18 hand-tuned JSON waves).",
    )
    parser.add_argument(
        "--campaign", action="store_true",
        help="BLOQUE 58: opt back into the 18 hand-tuned JSON waves (legacy mode).",
    )
    parser.add_argument(
        "--patterns", type=int, nargs="?", const=42, default=None, metavar="SEED",
        help="BLOQUE 58.8: use procedural wave patterns (5 Star Fox-inspired "
             "patterns: BEZIER_SWEEP, V_FORMATION, LEADER_FOLLOWER_CHAIN, "
             "DICE_FIVE_GRID, PINCER_CROSS) instead of the hardcoded WaveChain. "
             "SEED is optional (default 42).",
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
    import traceback
    from pathlib import Path
    start = time.perf_counter()
    # BLOQUE 46: heartbeat + crash log — if game exits unexpectedly, we know why
    crash_log = Path(__file__).resolve().parent / "logs" / "crash.log"
    crash_log.parent.mkdir(parents=True, exist_ok=True)
    last_heartbeat = 0.0
    try:
        while game._running:
            now = time.perf_counter()
            # BLOQUE 46: only auto-exit if --duration was specified (>0)
            if duration > 0 and now - start > duration:
                break
            # Heartbeat every 2s
            if now - last_heartbeat >= 2.0:
                with crash_log.open("a", encoding="utf-8") as f:
                    f.write(f"[{now - start:6.1f}s] heartbeat — state={game.scenes.current_state.name}\n")
                last_heartbeat = now
            # BLOQUE 46 FIX: only check QUIT here; let scenes drain KEYDOWN
            # themselves. The previous code drained ALL events in the main loop,
            # which created a race condition where scenes saw an empty KEYDOWN
            # queue (events posted between drain and scene.update were caught by
            # the next frame's drain, missing the scene entirely).
            for event in pygame.event.get(pygame.QUIT):
                with crash_log.open("a", encoding="utf-8") as f:
                    f.write(f"[{now - start:6.1f}s] QUIT event received (window close). exiting.\n")
                game._running = False
            try:
                frame_time = game.clock.tick(FPS_TARGET := 120) / 1000.0
                frame_time = min(frame_time, 1.0 / 30.0)
                game._accumulator += frame_time
                while game._accumulator >= (1.0 / 120):
                    game.scenes.update(1.0 / 120)
                    game._accumulator -= 1.0 / 120
                game.internal.fill((0, 0, 0))
                game.scenes.draw(game.internal)
                game._present()
            except Exception as inner_exc:
                # Defensive: scene error doesn't kill the game; log and continue
                with crash_log.open("a", encoding="utf-8") as f:
                    f.write(f"[{now - start:6.1f}s] SCENE ERROR: {type(inner_exc).__name__}: {inner_exc}\n")
                    f.write(traceback.format_exc())
                    f.write("\n")
                # Reset accumulator so we don't try to catch up many frames
                game._accumulator = 0.0
    except KeyboardInterrupt:
        pass
    except Exception as outer_exc:
        with crash_log.open("a", encoding="utf-8") as f:
            f.write(f"[{time.perf_counter() - start:6.1f}s] CRASH: {type(outer_exc).__name__}: {outer_exc}\n")
            f.write(traceback.format_exc())
        raise
    finally:
        pygame.quit()
    return 0


FPS_TARGET = 120  # used by _cmd_play


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    import os

    # BLOQUE 54: friendly defaults when running as a frozen .exe (PyInstaller).
    # Developers using `python main.py ...` still get full CLI control.
    _frozen_launch = getattr(sys, "frozen", False) and argv is None
    if _frozen_launch:
        if not args.easy:
            args.easy = True
            os.environ["VOID_HUNTER_EASY"] = "1"
        print("VOID HUNTER: launched as packaged .exe")
        print(f"  easy mode  = ON (9 lives, 4 bombs)")

    if args.easy:
        # BLOQUE 28: set env var so Player.reset() reads it
        os.environ["VOID_HUNTER_EASY"] = "1"
        if not _frozen_launch:
            print("VOID HUNTER: --easy mode enabled (9 lives, 4 bombs)")

    # BLOQUE 58.36g-taskbar: auto-detect window scale based on the
    # monitor's work area (excludes taskbar). Runs for ALL launch modes
    # when --scale is not explicitly passed. Previously the auto-detect
    # only ran for frozen .exe, so `python main.py --easy` without
    # --scale would use the default 4.0 scale and the window would be
    # much bigger than the monitor.
    _scale_was_explicit = "--scale" in sys.argv
    if not _scale_was_explicit:
        auto_scale = _detect_screen_scale()
        if auto_scale != args.scale:
            args.scale = auto_scale
        os.environ["VOID_HUNTER_SCALE"] = str(args.scale)
        print(f"VOID HUNTER: auto-detected scale = {args.scale}")
    elif not _frozen_launch:
        # User passed --scale explicitly; honor it. Note: game.py will
        # still cap the actual window size at the work area so it never
        # overlaps the taskbar.
        os.environ["VOID_HUNTER_SCALE"] = str(args.scale)
        _iw, _ih = 320, 480
        _ww, _wh = int(_iw * args.scale), int(_ih * args.scale)
        print(f"VOID HUNTER: --scale {args.scale} (window = {_ww}x{_wh})")

    if args.roguelike is not None:
        # BLOQUE 58: roguelike mode (opt-in). 4 chained waves per level
        # with sub-boss + final boss + powerup drops.
        from src.roguelike.integration import enable_roguelike
        seed = enable_roguelike(seed=args.roguelike if args.roguelike != 0 else None)
        print(f"VOID HUNTER: --roguelike mode (seed={seed})")
        print(f"  - 4 chained waves per level (ship counts fixed)")
        print(f"  - sub-boss at fixed position (after wave 2)")
        print(f"  - final boss at fixed position (end of level)")
        print(f"  - boss identity random per seed (4-boss pool)")
        print(f"  - powerup drops between waves (seeded pool)")
    elif args.campaign:
        # BLOQUE 58: opt back into the 18 hand-tuned JSON waves.
        from src.roguelike.integration import disable_roguelike
        disable_roguelike()
        print("VOID HUNTER: --campaign mode (18 hand-tuned JSON waves)")
    else:
        # BLOQUE 58.62: DEFAULT is now procedural patterns (bezier curves,
        # V formation, follow the leader, dice grid, pincer cross, 50
        # composed multi-segment patterns). The 5 base patterns are
        # Star Fox-inspired: ships follow actual flight paths instead of
        # rigid lines. --roguelike stays opt-in for the roguelike flow,
        # --campaign for the 18 hand-tuned waves.
        if args.patterns is None:
            args.patterns = 42  # default seed
        seed = args.patterns
        print(f"VOID HUNTER: default procedural patterns mode (seed={seed})")
        print(f"  - 6 base patterns: BEZIER_SWEEP, V_FORMATION, LEADER_FOLLOWER_CHAIN,")
        print(f"    DICE_FIVE_GRID, PINCER_CROSS, OSCILLATING_BUTTERFLY")
        print(f"  - 50 composed multi-segment patterns (BLOQUE 58.14.7)")
        print(f"  - bezier curves for actual flight paths, not rigid lines")
        print(f"  - solo red enemy every 5s for ambient variety")
        print(f"  - difficulty curve by floor (1-2 easy, 3-4 medium, 5+ hard)")
        import os as _os
        _os.environ["VOID_HUNTER_PATTERNS_SEED"] = str(seed)

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
