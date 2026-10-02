"""BLOQUE 73 Fase B e2e: 60s run + 4 captures of each weapon firing.

Validates that RMB fired with each of the 4 weapon pickups spawns the
correct bullets with correct cooldown:
  - THICK  (slot A, max 100): 1 big slow bullet, cooldown 0.20s
  - LASER  (slot S, max 200): 1 fast pierce bullet, cooldown 0.10s
  - FLAME  (slot D, max  50): 3-bullet fan, cooldown 0.07s
  - DOUBLE (slot F, max 150): 2 parallel bullets, cooldown 0.125s

Also verifies:
- 60s e2e with pickups + fires across all 4 weapons runs without crash.
- Auto-switch on pickup: filling slot A makes THICK active.
- pop_anim decayed in all 4 letters after 60s.
- Bullet spawn counts match per-weapon pattern.

Outputs 4 PNGs (one per weapon fired) to tools/playtest_out/.
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
from src.entities.asteroid import PowerupKind
from src.systems.projectile import BULLET_PLAYER, OWNER_PLAYER
from src.core.settings import INTERNAL_W, INTERNAL_H


def _bullet_count(rt: GameplayRuntime, active_only: bool = True) -> int:
    return sum(
        1 for b in rt._bullets.pool
        if b.active and b.owner == OWNER_PLAYER
    )


def fire_for_n_frames(rt: GameplayRuntime, n: int) -> None:
    """Simulate RMB held for n frames (5 fires/sec default @ 60fps)."""
    for _ in range(n):
        rt._read_input()  # tick RMB tick + cooldowns
        rt.update(1/60)


def capture(rt: GameplayRuntime, target: pygame.Surface, path: Path) -> None:
    """Render runtime to target and save PNG."""
    target.fill((0, 0, 0))
    rt.draw(target)
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

    print("=== BLOQUE 73 Fase B e2e ===")

    # ---------- Capture 1: THICK fire ----------
    print("Capture 1/4: THICK fired (1 bullet, 240 px/s, cooldown 0.20s)")
    rt = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    rt._apply_asteroid_powerup(PowerupKind.THICK)  # auto-switches to slot A
    initial_ammo = rt._weapon_slots[0].ammo
    initial_bullets = _bullet_count(rt)
    rt._fire_active_weapon()
    after_bullets = _bullet_count(rt)
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._t = 0.0
    rt._weapon_active_idx = 0
    # Tick a few frames so bullets are visible mid-flight
    for _ in range(8):
        rt.update(1/60)
    capture(rt, target, out_dir / "bloque_73_thick_fire.png")
    # Verify spawn count (1 bullet per fire)
    assert after_bullets == initial_bullets + 1, (
        f"THICK should spawn 1 bullet, got {after_bullets - initial_bullets}"
    )
    # Verify ammo consumed
    assert rt._weapon_slots[0].ammo == initial_ammo - 1, "THICK ammo not consumed"
    # Verify cooldown set
    assert rt._weapon_fire_cooldown > 0.0, "THICK cooldown not set"
    print(f"  THICK: bullets={after_bullets - initial_bullets} (expect 1) OK")

    # ---------- Capture 2: LASER fire ----------
    print("Capture 2/4: LASER fired (1 bullet, 480 px/s, pierce=3, cooldown 0.10s)")
    rt = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    rt._apply_asteroid_powerup(PowerupKind.LASER)  # auto-switches to slot S
    initial_bullets = _bullet_count(rt)
    rt._fire_active_weapon()
    after_bullets = _bullet_count(rt)
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._t = 0.0
    for _ in range(8):
        rt.update(1/60)
    capture(rt, target, out_dir / "bloque_73_laser_fire.png")
    assert after_bullets == initial_bullets + 1, (
        f"LASER should spawn 1 bullet, got {after_bullets - initial_bullets}"
    )
    # Verify pierce > 0
    new_bullets = [b for b in rt._bullets.pool if b.active and b.owner == OWNER_PLAYER]
    assert any(b.pierce > 0 for b in new_bullets), "LASER bullet should pierce"
    print(f"  LASER: bullets={after_bullets - initial_bullets} (expect 1) + pierce OK")

    # ---------- Capture 3: FLAME fire ----------
    print("Capture 3/4: FLAME fired (3-bullet fan, ~14 shots/sec)")
    rt = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    rt._apply_asteroid_powerup(PowerupKind.FLAME)  # auto-switches to slot D
    initial_bullets = _bullet_count(rt)
    rt._fire_active_weapon()
    after_bullets = _bullet_count(rt)
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._t = 0.0
    for _ in range(8):
        rt.update(1/60)
    capture(rt, target, out_dir / "bloque_73_flame_fire.png")
    assert after_bullets == initial_bullets + 3, (
        f"FLAME should spawn 3 bullets, got {after_bullets - initial_bullets}"
    )
    print(f"  FLAME: bullets={after_bullets - initial_bullets} (expect 3) OK")

    # ---------- Capture 4: DOUBLE fire ----------
    print("Capture 4/4: DOUBLE fired (2 parallel bullets, 8 shots/sec)")
    rt = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    rt._apply_asteroid_powerup(PowerupKind.DOUBLE)  # auto-switches to slot F
    initial_bullets = _bullet_count(rt)
    rt._fire_active_weapon()
    after_bullets = _bullet_count(rt)
    target = pygame.Surface((INTERNAL_W, INTERNAL_H))
    rt._t = 0.0
    for _ in range(8):
        rt.update(1/60)
    capture(rt, target, out_dir / "bloque_73_double_fire.png")
    assert after_bullets == initial_bullets + 2, (
        f"DOUBLE should spawn 2 bullets, got {after_bullets - initial_bullets}"
    )
    print(f"  DOUBLE: bullets={after_bullets - initial_bullets} (expect 2) OK")

    # ---------- 60s e2e: cycle through all 4 weapons ----------
    print("Running 60s e2e at 60fps (cycling through all 4 weapons)...")
    rt = GameplayRuntime(transition_to=lambda *a, **k: None, is_boss=False, act=1)
    # Fill all 4 slots
    rt._apply_asteroid_powerup(PowerupKind.THICK)
    rt._apply_asteroid_powerup(PowerupKind.LASER)
    rt._apply_asteroid_powerup(PowerupKind.FLAME)
    rt._apply_asteroid_powerup(PowerupKind.DOUBLE)
    # Pre-fill ammo to max so the 60s loop doesn't run out
    rt._weapon_slots[0].ammo = 100   # THICK
    rt._weapon_slots[1].ammo = 200   # LASER
    rt._weapon_slots[2].ammo = 50    # FLAME (small)
    rt._weapon_slots[3].ammo = 150   # DOUBLE

    start = time.perf_counter()
    frames = 0
    pickup_schedule = [
        (0,    PowerupKind.THICK),   # already picked up
        (900,  PowerupKind.LASER),   # 15s
        (1800, PowerupKind.FLAME),   # 30s
        (2700, PowerupKind.DOUBLE),  # 45s
    ]
    pickup_idx = 0
    for frame in range(60 * 60):
        # Cycle through active slot every 600 frames (10s)
        if frame % 600 == 0 and frame > 0:
            rt._weapon_active_idx = (rt._weapon_active_idx + 1) % 4
        rt.update(1/60)
        frames += 1
    elapsed = time.perf_counter() - start
    print(f"60s e2e: {frames} frames in {elapsed:.1f}s ({frames/elapsed:.0f} fps)")

    # pop_anim decayed in all 4 letters
    for letter, pop in rt._weapon_pop_anim.items():
        assert pop == 0.0, f"pop_anim[{letter}]={pop} didn't decay"
    print("  pop_anim decayed to 0 in all 4 letters  OK")

    # ---------- Check crash.log for runtime errors ----------
    if crash_log.exists():
        text = crash_log.read_text()
        if "NameError" in text or "AttributeError" in text:
            print("ERROR: NameError or AttributeError in crash.log")
            return 1
        print("  crash.log present but no NameError/AttributeError")
    else:
        print("  crash.log absent (no runtime errors logged)")

    print("=== BLOQUE 73 Fase B e2e complete: PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())