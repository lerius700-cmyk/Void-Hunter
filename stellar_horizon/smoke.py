"""STELLAR HORIZON — 11-gate smoke test, mirrors Void-Hunter's smoke.py."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _gate(name, fn):
    try:
        msg = fn() or ""
        return (name, True, msg)
    except Exception as exc:
        tb = traceback.format_exc()
        return (name, False, f"{type(exc).__name__}: {exc}\n{tb}")


def run() -> tuple[int, int, list[tuple[str, bool, str]]]:
    results: list[tuple[str, bool, str]] = []

    def g01_import_settings():
        from stellar_horizon.settings import INTERNAL_W, INTERNAL_H, FPS_TARGET
        assert INTERNAL_W == 480 and INTERNAL_H == 270 and FPS_TARGET == 120
        return f"{INTERNAL_W}x{INTERNAL_H} @ {FPS_TARGET} FPS"

    def g02_import_movement():
        from src.movement import BezierPath, WaypointPath, HybridPath, FlightFormation
        return "imported"

    def g03_bezier_horizontal_paths():
        from stellar_horizon.waves.bezier_horizontal import (
            path_s_right_to_left, path_top_dive, path_zigzag_exit_top, path_boss_entry,
        )
        p = path_s_right_to_left()
        assert p.position_at(0).x > 480
        return "off-screen entry"

    def g04_formations_rotated():
        from stellar_horizon.waves.formations_h import v_pointing_left
        offsets = v_pointing_left(count=5)
        assert len(offsets) == 5
        assert offsets[0] == (0.0, 0.0)
        return "5 slots"

    def g05_player_construction():
        import pygame
        from stellar_horizon.entities.player import Player
        p = Player(pygame.Rect(0, 0, 480, 270))
        assert p.lives == 3
        return f"lives={p.lives}"

    def g06_enemy_construction():
        from stellar_horizon.entities.enemy import Enemy, EnemyKind
        e = Enemy()
        e.kind = EnemyKind.SCOUT
        e.on_spawn()
        assert e.hp == 1
        return f"hp={e.hp}"

    def g07_boss_construction():
        from stellar_horizon.entities.boss import Boss, BossPhase
        b = Boss()
        assert b.phase == BossPhase.ENTERING
        assert b.hp == 600
        return f"hp={b.hp}"

    def g08_wave_manager_loads():
        from stellar_horizon.waves.wave_manager import WaveManager
        wm = WaveManager(Path(__file__).resolve().parent / "waves" / "waves_act1.json")
        assert wm.act == 1
        return f"act={wm.act}, waves={len(wm.waves)}"

    def g09_hud_draws():
        import pygame
        from stellar_horizon.ui.hud import Hud
        from stellar_horizon.entities.player import Player
        surf = pygame.Surface((480, 270))
        h = Hud()
        h.set_player(Player(pygame.Rect(0, 0, 480, 270)))
        h.set_score(12345)
        h.set_wave(2, 4)
        h.draw(surf)
        return "ok"

    def g10_midi_files_exist():
        assets = Path(__file__).resolve().parent / "assets" / "midi"
        for name in ("title", "act1", "boss", "game_over"):
            assert (assets / f"{name}.mid").exists(), f"missing {name}.mid"
        return f"4/4 midis"

    def g11_backgrounds_exist():
        assets = Path(__file__).resolve().parent / "assets" / "backgrounds"
        for name in ("act1_asteroid_belt", "act2_nebula", "act3_sun_close"):
            assert (assets / f"{name}.png").exists(), f"missing {name}.png"
        return f"3/3 bgs"

    for name, fn in [
        ("01_import_settings",   g01_import_settings),
        ("02_import_movement",   g02_import_movement),
        ("03_bezier_horizontal", g03_bezier_horizontal_paths),
        ("04_formations_rotated", g04_formations_rotated),
        ("05_player",            g05_player_construction),
        ("06_enemy",             g06_enemy_construction),
        ("07_boss",              g07_boss_construction),
        ("08_wave_manager",      g08_wave_manager_loads),
        ("09_hud",               g09_hud_draws),
        ("10_midi_files",        g10_midi_files_exist),
        ("11_backgrounds",       g11_backgrounds_exist),
    ]:
        results.append(_gate(name, fn))

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    return passed, failed, results


if __name__ == "__main__":
    p, f, results = run()
    print(f"STELLAR HORIZON smoke: {p}/{p + f} passed, {f} failed")
    for name, ok, msg in results:
        mark = "OK " if ok else "FAIL"
        print(f"  [{mark}] {name}: {msg}")
    sys.exit(0 if f == 0 else 1)
