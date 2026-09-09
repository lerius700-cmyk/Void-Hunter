"""BLOQUE 65: process the user's new reference images into game-ready sprites.

BLOQUE 65 replaces the legacy MINE-ASTEROID 'open' sprite (32x32 BLOQUE 63
gun barrel) with the user's new ship reference (a ship with a gun barrel
visible). It also adds 2 new intermediate frames (open1, open2) that show
the asteroid in mid-opening states.

Inputs (user-provided 2026-09-09):
  - Assets/sprites/enemies/mine_asteroid/_new_reference_closed.png
    (round asteroid — used as the 'closed' state, already byte-equal to round.png)
  - Assets/sprites/enemies/mine_asteroid/_new_reference_open.png
    (new ship with gun barrel — replaces the legacy 'open' state)

Processing:
  1. Detect dark background (RGB < 30), make transparent
  2. Crop to content bbox with small padding
  3. Resize to 64x64 with LANCZOS
  4. Apply second-pass damero transparentize (gray mid-range in 40-220)
  5. Threshold alpha to binary
  6. Save as enemies/mine_asteroid/<state>/frame_00.png

The 4-state cycle (closed/open1/open2/open3) needs:
  - closed: round.png (byte-equal, perfect camo)
  - open1: AI-generated 25% open (already processed by postprocess_mine_asteroid.py)
  - open2: AI-generated 75% open (already processed)
  - open3 (reuses 'open/'): user's new ship reference (this script)

The open1 and open2 are AI-generated via:
  tools/generate_mine_asteroid_bloque_65_bases.py
and processed via:
  tools/postprocess_mine_asteroid.py

This script ONLY handles the new reference images for the open3 state.

Usage:
    cd D:\\AI\\void-hunter
    .venv\\Scripts\\python.exe tools/postprocess_mine_asteroid_bloque_65.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from PIL import Image

OUT_DIR = PROJECT_ROOT / "Assets" / "sprites" / "enemies" / "mine_asteroid"
REF_DIR = OUT_DIR  # _new_reference_*.png live alongside the state directories
SOURCE_SIZE = 64


def process_reference_to_open(ref_filename: str, out_path: Path) -> None:
    """Take a user-provided reference PNG, remove its dark background,
    crop to content bbox, resize to 64x64, and save as a transparent
    RGBA sprite at ``out_path``.

    The reference images are NOT AI-generated — they are the user's
    hand-picked art for the BLOQUE 65 redesign. They have an opaque
    dark olive/black background that needs to be detected and made
    transparent before the sprite can be composited in-game.
    """
    src = Image.open(REF_DIR / ref_filename)
    arr = np.array(src)
    # Detect dark olive/black background (RGB < 30 on all channels)
    is_bg = (arr[:, :, 0] < 30) & (arr[:, :, 1] < 30) & (arr[:, :, 2] < 30)
    arr[is_bg, 3] = 0
    # Find content bbox (non-transparent pixels)
    nonzero = np.where(arr[:, :, 3] > 0)
    if len(nonzero[0]) == 0:
        raise ValueError(f"no content found in {ref_filename}")
    y0, y1 = nonzero[0].min(), nonzero[0].max()
    x0, x1 = nonzero[1].min(), nonzero[1].max()
    # Crop with 4px padding
    pad = 4
    y0 = max(0, y0 - pad)
    y1 = min(arr.shape[0], y1 + pad)
    x0 = max(0, x0 - pad)
    x1 = min(arr.shape[1], x1 + pad)
    cropped = arr[y0:y1, x0:x1]
    img = Image.fromarray(cropped, mode="RGBA")
    # Resize to 64x64 with LANCZOS
    img64 = img.resize((SOURCE_SIZE, SOURCE_SIZE), Image.LANCZOS)
    # Apply post-resize damero transparentize (catches any LANCZOS
    # blended mid-gray that survived the pre-resize pass)
    arr2 = np.array(img64)
    rgb = arr2[:, :, :3]
    is_gray = (
        (np.abs(rgb[:, :, 0].astype(np.int16) - rgb[:, :, 1].astype(np.int16)) < 15)
        & (np.abs(rgb[:, :, 1].astype(np.int16) - rgb[:, :, 2].astype(np.int16)) < 15)
    )
    is_mid = (rgb[:, :, 0] > 40) & (rgb[:, :, 0] < 220)
    is_opaque = arr2[:, :, 3] > 128
    is_bg2 = is_gray & is_mid & is_opaque
    arr2[is_bg2, 3] = 0
    # Threshold alpha to binary
    arr2[:, :, 3] = np.where(arr2[:, :, 3] >= 128, 255, 0)
    out = Image.fromarray(arr2, mode="RGBA")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    print(f"[save] {out_path} ({out_path.stat().st_size} bytes) — size {out.size}")


def main() -> int:
    # Process the new 'open' reference (BLOQUE 65 open3 = terminal state)
    process_reference_to_open(
        "_new_reference_open.png",
        OUT_DIR / "open" / "frame_00.png",
    )
    print(f"\nDone. BLOQUE 65 reference processing complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
