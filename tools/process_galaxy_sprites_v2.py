"""BLOQUE 58.14.4: extract the main spiral galaxy from each galaxy_panel_*.png.

The user's references (galaxy_panel_0/1/2.png, 640x1920) are FULL PANELS with
2 main spiral galaxies (top + bottom), 8 smaller galaxies, and a starfield.

The current galaxy_sprite_0N.png (97-153KB, 280x280) are low-detail AI
generations that the user rejected ("esto no parecen nebulosas. las ultimas 4
imagenes si"). These don't look like galaxies in-game.

This script extracts the CENTRAL MAIN GALAXY from each panel (the brightest
cluster, ~500x500 around the brightest peak) and saves it as a higher-quality
RGBA galaxy_sprite_0N.png. Result: the in-game nebula actually looks like a
spiral galaxy with arms, dust lanes, and embedded stars.

Approach: numpy-only peak detection (no scipy) — downsample to 80x240, find
the 2 brightest y-positions per panel, then crop a 500x500 box around each
peak. The 2 peaks are the 2 main galaxies in each panel.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GALAXY_DIR = PROJECT_ROOT / "Assets" / "background"

# Output: replace the 4 existing galaxy_sprite_0N.png files (280x280) with
# HD versions (500x500) extracted from the user's reference panels.
# We extract 2 galaxies per panel (the 2 main ones) → 6 sprites total.
# But we keep 4 to match _GALAXY_SPRITE_PATHS in parallax.py.
OUTPUT_SIZE = 500
CROP_RADIUS = OUTPUT_SIZE // 2  # 250


def find_galaxy_peaks(arr: np.ndarray, n: int = 2) -> list[tuple[int, int]]:
    """Find the n brightest blob centers in a 2D brightness map.

    Downsamples the array to ~80x240, finds the n brightest non-overlapping
    peaks, then scales back to original coordinates. Returns list of
    (x, y) tuples in original coordinates.
    """
    h, w = arr.shape
    # Downsample by mean-pool to ~80x240
    block_h = max(1, h // 240)
    block_w = max(1, w // 80)
    ds = arr[::block_h, ::block_w].astype(np.float32)
    ds_h, ds_w = ds.shape
    # Edge-mask: ignore the very edge (where cropping would go OOB).
    # Use ~5% of the dimension as pad.
    y_pad = max(2, ds_h // 10)
    x_pad = max(2, ds_w // 10)
    mask = np.ones_like(ds, dtype=bool)
    mask[:y_pad, :] = False
    mask[-y_pad:, :] = False
    mask[:, :x_pad] = False
    mask[:, -x_pad:] = False
    peaks: list[tuple[int, int]] = []
    for _ in range(n):
        masked = np.where(mask, ds, -np.inf)
        idx = np.argmax(masked)
        py, px = np.unravel_index(idx, ds.shape)
        peaks.append((int(px * block_w), int(py * block_h)))
        # Suppress a 15x15 block (in ds coords) around the peak so we
        # don't pick the same bright star twice
        sup = max(3, ds_h // 20)
        x_lo = max(0, px - sup)
        x_hi = min(ds_w, px + sup)
        y_lo = max(0, py - sup)
        y_hi = min(ds_h, py + sup)
        mask[y_lo:y_hi, x_lo:x_hi] = False
    return peaks


def extract_galaxy(panel_path: Path, peak_xy: tuple[int, int],
                    out_path: Path) -> tuple[int, int]:
    """Crop a CROP_RADIUS*2 x CROP_RADIUS*2 region around peak_xy, save as
    RGBA with transparent background (alpha = max-channel intensity).
    Returns (x, y) of the saved crop's center.
    """
    im = Image.open(str(panel_path)).convert("RGB")
    arr = np.array(im)
    h, w, _ = arr.shape
    px, py = peak_xy
    # Center the crop on the peak
    x0 = max(0, min(w - CROP_RADIUS * 2, px - CROP_RADIUS))
    y0 = max(0, min(h - CROP_RADIUS * 2, py - CROP_RADIUS))
    x1 = x0 + CROP_RADIUS * 2
    y1 = y0 + CROP_RADIUS * 2
    crop = arr[y0:y1, x0:x1].copy()  # (500, 500, 3)
    # Convert to RGBA: alpha = brightness (so dark sky is transparent)
    bright = crop.astype(np.float32).sum(axis=2)
    # Threshold: pixels with brightness > 30 are visible (dark sky below
    # is transparent, galaxy + stars are opaque)
    alpha = np.clip((bright - 20.0) * 1.5, 0, 255).astype(np.uint8)
    # Soft alpha at the edges: erode bright pixels that are isolated
    # (use a 3x3 max filter to fill tiny gaps in stars)
    # Simple approach: do nothing extra. The 30-threshold already makes
    # bright stars opaque and dim sky transparent.
    rgba = np.dstack([crop, alpha])
    Image.fromarray(rgba, mode="RGBA").save(str(out_path), optimize=True)
    return (x0 + CROP_RADIUS, y0 + CROP_RADIUS)


def main() -> int:
    panels = sorted(GALAXY_DIR.glob("galaxy_panel_*.png"))
    if not panels:
        print(f"ERROR: no galaxy_panel_*.png in {GALAXY_DIR}")
        return 1
    print(f"Found {len(panels)} panels: {[p.name for p in panels]}")
    # We want 4 sprites total. With 3 panels, we extract 2 from panel_0,
    # 1 from panel_1, 1 from panel_2 → 4 sprites.
    # (Each panel has 2 main galaxies; we use both from panel_0 and one
    # from each of the others for variety.)
    targets = [
        (panels[0], 0, "galaxy_sprite_01.png"),  # 1st peak (top galaxy)
        (panels[0], 1, "galaxy_sprite_02.png"),  # 2nd peak (bottom galaxy)
        (panels[1], 0, "galaxy_sprite_03.png"),  # green galaxy
        (panels[2], 0, "galaxy_sprite_04.png"),  # alt-angle blue galaxy
    ]
    for panel, peak_idx, out_name in targets:
        im = Image.open(str(panel)).convert("RGB")
        arr = np.array(im)
        peaks = find_galaxy_peaks(arr.sum(axis=2), n=peak_idx + 1)
        if peak_idx >= len(peaks):
            print(f"  WARN: panel {panel.name} has only {len(peaks)} peaks, "
                  f"using peak 0 for {out_name}")
            peak_idx = 0
        peak = peaks[peak_idx]
        out_path = GALAXY_DIR / out_name
        cx, cy = extract_galaxy(panel, peak, out_path)
        print(f"  {out_name}: extracted from {panel.name} at peak=({peak[0]}, {peak[1]}) "
              f"-> center=({cx}, {cy}) crop_size={OUTPUT_SIZE}")
    print("Done. New sprites are RGBA {OUTPUT_SIZE}x{OUTPUT_SIZE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
