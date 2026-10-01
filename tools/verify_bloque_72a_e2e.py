"""BLOQUE 72.A e2e: 60s run + 4 captures of the weapon slot HUD.

Validates Tasks 5-9 end-to-end:
  - T5: WeaponSlot dataclass + ammo constants (8/8 tests)
  - T6: 4 empty weapon slots in player state (6/6 tests)
  - T7: PowerupKind: 4 weapon kinds replace WEAPON (4/4 tests)
  - T8: _apply_asteroid_powerup fills weapon slots + pop anim (7/7 tests)
  - T9: HUD weapon slot rendering (4/4 tests)

The 7-point checklist for BLOQUE 72.A is satisfied:
  1. Tests pass (T5-T9) - verified separately
  2. No regressions - verified separately
  3. THIS SCRIPT: 60s e2e without NameError/AttributeError
  4. THIS SCRIPT: 4 PNG captures (0/1/2/4 slots filled)
  5. User confirms visual (post-task)
  6. Commit + push
  7. CHANGELOG entry (separate file edit)
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui.gameplay_runtime import GameplayRuntime
from src.entities.asteroid import PowerupKind
from src.core.settings import WEAPON_PICKUP_AMMO, INTERNAL_W, INTERNAL_H


def render_and_capture(runtime: GameplayRuntime, target: pygame.Surface, path: Path) -> None:
    """Render runtime to target and save PNG."""
    target.fill((0, 0, 0))
    runtime.draw(target)
    pygame.image.save(target, str(path))
    size = path.stat().st_size
    print(f"  Saved {path.name} ({size} bytes)")


def main() -> int:
    out_dir = Path("tools/playtest_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clear crash.log so we can detect new errors
    crash_log = Path("logs/crash.log")
    if crash_log.exists():
        crash_log.unlink()

    print("=== BLOQUE 72.A e2e ===")
    runtime = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))

    # ---------- Capture 1: empty slots ----------
    print("Capture 1/4: empty slots (initial state)")
    render_and_capture(runtime, target, out_dir / "bloque_72a_slots_empty.png")
    initial_slots = [(s.letter, s.ammo) for s in runtime._weapon_slots]
    print(f"  Slots state: {initial_slots}")
    assert all(s[1] == 0 for s in initial_slots), "Expected all slots empty initially"

    # ---------- 60s e2e simulation (with periodic pickups) ----------
    # We cycle pickups across the 60s to exercise the slot-fill + pop anim
    # paths repeatedly. This catches any latent dispatch or pop decay bug.
    print("Running 60s e2e at 60fps (pickup cycling every ~10s)...")
    start = time.perf_counter()
    frames = 0
    pickup_schedule = [
        (600, PowerupKind.THICK),    # 10s
        (1200, PowerupKind.LASER),   # 20s
        (1800, PowerupKind.FLAME),   # 30s
        (2400, PowerupKind.DOUBLE),  # 40s
        (3000, PowerupKind.THICK),   # 50s (stack test)
    ]
    pickup_idx = 0
    for frame in range(60 * 60):
        runtime.update(1/60)
        # Trigger pickup if scheduled
        if pickup_idx < len(pickup_schedule) and frame == pickup_schedule[pickup_idx][0]:
            kind = pickup_schedule[pickup_idx][1]
            runtime._apply_asteroid_powerup(kind)
            slot_idx = {
                PowerupKind.THICK: 0, PowerupKind.LASER: 1,
                PowerupKind.FLAME: 2, PowerupKind.DOUBLE: 3,
            }[kind]
            ammo = runtime._weapon_slots[slot_idx].ammo
            pop = runtime._weapon_pop_anim[runtime._weapon_slots[slot_idx].letter]
            print(f"  frame={frame}: pickup {kind.name}, slot[{slot_idx}].ammo={ammo}, pop={pop:.2f}")
            pickup_idx += 1
        frames += 1
    elapsed = time.perf_counter() - start
    print(f"60s e2e: {frames} frames in {elapsed:.1f}s ({frames/elapsed:.0f} fps)")

    # ---------- State verification ----------
    final_slots = {s.letter: s.ammo for s in runtime._weapon_slots}
    print(f"Final slots after 60s: {final_slots}")
    # Expected: A=60 (THICK twice, 30+30, capped at 100), S=30 (LASER once),
    # D=30 (FLAME once), F=30 (DOUBLE once).
    expected = {"A": 60, "S": 30, "D": 30, "F": 30}
    if final_slots != expected:
        print(f"ERROR: slot ammo mismatch. Expected {expected}, got {final_slots}")
        return 1

    # pop_anim should have decayed to 0 by now (60s >> 0.2s decay window)
    for letter, pop in runtime._weapon_pop_anim.items():
        if pop > 0.0:
            print(f"ERROR: pop_anim[{letter}]={pop} didn't decay to 0 after 60s")
            return 1
    print("  pop_anim decayed to 0 in all 4 letters  OK")

    # ---------- Capture 2: 1 slot filled (THICK) ----------
    print("Capture 2/4: 1 slot filled (THICK)")
    # Reset state for clean captures
    runtime = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._weapon_pop_anim["A"] = 0.15  # mid-pop for visual interest
    # Tick a few frames so the pop animation is visible (peak at pop_t~0)
    for _ in range(2):
        runtime.update(1/60)
    render_and_capture(runtime, target, out_dir / "bloque_72a_slots_filled_1.png")

    # ---------- Capture 3: 2 slots filled (THICK + LASER) ----------
    print("Capture 3/4: 2 slots filled (THICK + LASER)")
    runtime = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._apply_asteroid_powerup(PowerupKind.LASER)
    runtime._weapon_pop_anim["A"] = 0.10  # mid-pop THICK
    runtime._weapon_pop_anim["S"] = 0.10  # mid-pop LASER
    runtime._weapon_active_idx = 1  # LASER selected (S)
    for _ in range(4):
        runtime.update(1/60)
    render_and_capture(runtime, target, out_dir / "bloque_72a_slots_filled_2.png")

    # ---------- Capture 4: 4 slots filled ----------
    print("Capture 4/4: 4 slots filled (all weapons)")
    runtime = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    runtime._apply_asteroid_powerup(PowerupKind.THICK)
    runtime._apply_asteroid_powerup(PowerupKind.LASER)
    runtime._apply_asteroid_powerup(PowerupKind.FLAME)
    runtime._apply_asteroid_powerup(PowerupKind.DOUBLE)
    # Different ammo counts to show variation
    runtime._weapon_slots[0].ammo = 100   # THICK capped (was 30+30=60; bump to 100)
    runtime._weapon_slots[1].ammo = 200   # LASER max
    runtime._weapon_slots[2].ammo = 50    # FLAME max
    runtime._weapon_slots[3].ammo = 150   # DOUBLE max
    runtime._weapon_active_idx = 2  # FLAME selected (D)
    # Let pop animations decay so the screenshot is clean
    for _ in range(15):
        runtime.update(1/60)
    render_and_capture(runtime, target, out_dir / "bloque_72a_slots_filled_4.png")

    # ---------- Verify all PNGs are valid 320x480 ----------
    for png in out_dir.glob("bloque_72a_slots_*.png"):
        loaded = pygame.image.load(str(png))
        w, h = loaded.get_size()
        if (w, h) != (320, 480):
            print(f"ERROR: {png.name} dimensions are {w}x{h}, expected 320x480")
            return 1
        print(f"  {png.name}: {w}x{h} OK")

    # ---------- Check crash.log for runtime errors ----------
    if crash_log.exists():
        text = crash_log.read_text()
        if "NameError" in text or "AttributeError" in text:
            print("ERROR: NameError or AttributeError in crash.log")
            print("First 500 chars:")
            print(text[:500])
            return 1
        print("  crash.log present but no NameError/AttributeError")
    else:
        print("  crash.log absent (no runtime errors logged)")

    print("=== BLOQUE 72.A e2e complete: PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
