"""BLOQUE 65: generate the open1 (25% open) and open2 (75% open) frames
as composites of the closed round asteroid + the new ship reference.

Why composite instead of pure AI gen?
  The AI-generated intermediates from BLOQUE 65 stage 1 had a visible
  damero checkered background INSIDE the asteroid body (the AI rendered
  the checker pattern as part of the asteroid texture). Compositing
  the closed round with a programmatically-drawn crack + gun/cockpit
  hint produces a CLEAN intermediate that matches the user's style
  (perfect camo preserved, smooth transition between closed and open).

Inputs:
  - Assets/sprites/asteroids/round.png (the canonical closed sprite)
  - Assets/sprites/enemies/mine_asteroid/_new_reference_open.png
    (just for reference; not used in the composite)

Outputs:
  - Assets/sprites/enemies/mine_asteroid/open1/frame_00.png (25% open)
  - Assets/sprites/enemies/mine_asteroid/open2/frame_00.png (75% open)

BLOQUE 65 visual style:
  - The closed state is byte-equal to round.png (perfect camo).
  - The opening sequence plays ONE TIME, 0.6s total (0.2s per state).
  - open1 (25%): round with a thin horizontal crack, a small dark gun
    tip peeking through the center.
  - open2 (75%): round with a wider gap, gun barrel + cockpit visible.
  - open3 (terminal): the user's new ship reference (the open asteroid
    halves split, gun barrel pointing down).

Usage:
    cd D:\\AI\\void-hunter
    .venv\\Scripts\\python.exe tools/generate_mine_asteroid_intermediates_bloque_65.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from PIL import Image

OUT_DIR = PROJECT_ROOT / "Assets" / "sprites" / "enemies" / "mine_asteroid"
ROUND_PNG = PROJECT_ROOT / "Assets" / "sprites" / "asteroids" / "round.png"

# Locked palette (BLOQUE 65 spec):
#   base_brown:    (140, 100, 60)
#   highlight:     (180, 140, 90)
#   mid_shadow:    ( 90,  60, 30)
#   deep_shadow:   ( 50,  30, 15)
#   black_crack:   ( 20,  10,  5)
#   mineral_hi:    (210, 170, 110)
#   cockpit:       ( 40,  50,  70)
#   thruster:      (255, 140,  60)
BLACK_CRACK = (20, 10, 5)
COCKPIT = (40, 50, 70)
GUN_BARREL = (60, 60, 60)


def make_open1(closed: Image.Image) -> Image.Image:
    """25% open: closed round with a thin horizontal seam + tiny gun tip.

    The crack is 2 pixels wide (subtle), and a 2x2 dark blue cockpit
    hint is visible at the center. The gun barrel is NOT visible yet.
    """
    out = closed.copy().convert("RGBA")
    arr = np.array(out)
    # Thin horizontal crack: 2 pixels at y=31-32 (center)
    arr[31:33, :, :3] = BLACK_CRACK
    arr[31:33, :, 3] = 255
    # Tiny dark blue cockpit hint at the center (2x2)
    arr[31:33, 30:34, :3] = COCKPIT
    arr[31:33, 30:34, 3] = 255
    return Image.fromarray(arr, mode="RGBA")


def make_open2(closed: Image.Image) -> Image.Image:
    """75% open: closed round with a wider gap + visible gun + cockpit.

    The gap is 8 pixels wide, with a 4-pixel-wide gun barrel (gray)
    pointing down through the center. The cockpit is a 4x4 dark blue
    square at the top of the gap.
    """
    out = closed.copy().convert("RGBA")
    arr = np.array(out)
    # Wider gap: 8 pixels at y=28-35 (inner cavity, dark)
    arr[28:36, :, :3] = BLACK_CRACK
    arr[28:36, :, 3] = 255
    # Cockpit at the top of the gap: 4x4 dark blue square
    arr[28:32, 28:36, :3] = COCKPIT
    arr[28:32, 28:36, 3] = 255
    # Gun barrel: 4-pixel wide vertical bar (dark gray) pointing down
    # Through the center of the gap
    arr[28:40, 30:34, :3] = GUN_BARREL
    arr[28:40, 30:34, 3] = 255
    return Image.fromarray(arr, mode="RGBA")


def main() -> int:
    if not ROUND_PNG.is_file():
        print(f"missing {ROUND_PNG}")
        return 1
    closed = Image.open(ROUND_PNG)
    if closed.size != (64, 64):
        # BLOQUE 64.A: asteroids are 64x64 (was 32x32 in BLOQUE 61).
        closed = closed.resize((64, 64), Image.LANCZOS)
    open1 = make_open1(closed)
    out1 = OUT_DIR / "open1" / "frame_00.png"
    out1.parent.mkdir(parents=True, exist_ok=True)
    open1.save(out1)
    print(f"[save] {out1} ({out1.stat().st_size} bytes)")
    open2 = make_open2(closed)
    out2 = OUT_DIR / "open2" / "frame_00.png"
    open2.save(out2)
    print(f"[save] {out2} ({out2.stat().st_size} bytes)")
    print(f"\nDone. BLOQUE 65 open1 + open2 generated as composites.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
