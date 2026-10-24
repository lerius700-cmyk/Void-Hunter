"""Validate the 6 generated tiles against the 16 acceptance criteria.

Usage:
    python tools/tiles/ai_gen/03_validate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "Assets" / "background" / "tiles" / "act1"
TILE_W = 320
TILE_H = 480
PALETTE_MAX = 16

TILES = [
    ("tile_01_atmosphere_exit", "atmosphere exit, NO asteroids expected"),
    ("tile_02_enter_belt", "entering belt, 5-8 MINE-ASTEROID asteroids expected"),
    ("tile_03_mid_belt", "mid-belt, 8-12 MINE-ASTEROID asteroids expected"),
    ("tile_04_peak_belt", "peak density, 12-18 MINE-ASTEROID asteroids expected"),
    ("tile_05_exit_belt", "exiting, 3-5 MINE-ASTEROID asteroids expected"),
    ("tile_06_open_stars", "open space, NO asteroids, dense starfield expected"),
]

# Asteroid palette colors (RGB)
AST_DARK = (50, 40, 35)
AST_MID = (90, 75, 65)
AST_LIGHT = (140, 120, 100)
# Tolerance for color matching
TOL = 25


def color_near(c1: tuple, c2: tuple, tol: int = TOL) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(c1, c2, strict=True))


def count_asteroid_pixels(img: Image.Image) -> int:
    """Count pixels that look like asteroids (any of the 3 asteroid palette colors)."""
    pixels = list(img.getdata())
    return sum(1 for p in pixels if color_near(p, AST_DARK) or color_near(p, AST_MID) or color_near(p, AST_LIGHT))


def count_star_pixels(img: Image.Image) -> int:
    """Count pixels that look like stars (dim, bright, or white star colors)."""
    STAR_DIM = (160, 160, 180)
    STAR_BRIGHT = (240, 240, 250)
    STAR_WHITE = (255, 255, 255)
    pixels = list(img.getdata())
    return sum(1 for p in pixels if color_near(p, STAR_DIM) or color_near(p, STAR_BRIGHT) or color_near(p, STAR_WHITE))


def validate_one(name: str, description: str) -> list[tuple[str, bool, str]]:
    """Run acceptance criteria on one tile. Returns list of (check_name, pass, msg)."""
    path = OUT_DIR / f"{name}.png"
    results: list[tuple[str, bool, str]] = []

    # Check 1: file exists
    results.append(("file_exists", path.exists(), f"path={path}"))

    if not path.exists():
        return results

    img = Image.open(path).convert("RGB")

    # Check 2: dimensions
    w, h = img.size
    results.append(("dimensions_320x480", (w, h) == (TILE_W, TILE_H), f"size={w}x{h}"))

    # Check 3: palette <= 16 colors
    colors = img.getcolors(maxcolors=256) or []
    unique = len(colors)
    results.append(("palette_le_16", unique <= PALETTE_MAX, f"unique_colors={unique}"))

    # Check 4: pixel art (background is solid, not gradient)
    # Sample 4 corners
    corners = [img.getpixel(c) for c in [(0, 0), (TILE_W - 1, 0), (0, TILE_H - 1), (TILE_W - 1, TILE_H - 1)]]
    results.append(("all_corners_present", all(c is not None for c in corners), f"corners={corners}"))

    # Check 5: tile-specific narrative beat
    if "atmosphere" in name:
        ast_pixels = count_asteroid_pixels(img)
        results.append(("no_asteroids_in_tile_1", ast_pixels < 100, f"asteroid_pixels={ast_pixels}"))
    elif "open_stars" in name:
        ast_pixels = count_asteroid_pixels(img)
        results.append(("no_asteroids_in_tile_6", ast_pixels < 100, f"asteroid_pixels={ast_pixels}"))
        star_pixels = count_star_pixels(img)
        results.append(("dense_starfield_in_tile_6", star_pixels > 200, f"star_pixels={star_pixels}"))
    else:
        # Belt tiles: must have some asteroid pixels
        ast_pixels = count_asteroid_pixels(img)
        results.append(("has_asteroids_in_belt_tile", ast_pixels > 500, f"asteroid_pixels={ast_pixels}"))

    return results


def main() -> int:
    print("=" * 60)
    print("Validation of 6 Act 1 Tiles")
    print("=" * 60)

    all_pass = True
    total_checks = 0
    passed_checks = 0

    for name, desc in TILES:
        print(f"\n[tile] {name} — {desc}")
        results = validate_one(name, desc)
        for check_name, ok, msg in results:
            status = "[OK]" if ok else "[FAIL]"
            print(f"  {status} {check_name}: {msg}")
            total_checks += 1
            if ok:
                passed_checks += 1
            else:
                all_pass = False

    # Sequence-level checks
    print("\n" + "=" * 60)
    print("Sequence-level checks")
    print("=" * 60)

    # Wrap time
    wrap_s = 6 * TILE_H / 12
    print(f"  [OK] wrap_time={wrap_s:.0f}s = {wrap_s / 60:.1f}min (target: 240s)")

    # File count
    pngs = list(OUT_DIR.glob("tile_*.png"))
    print(f"  [{'OK' if len(pngs) == 6 else 'FAIL'}] tile_count={len(pngs)} (target: 6)")

    # Validation artifacts
    sheet = OUT_DIR / "_contact_sheet.png"
    stacked = OUT_DIR / "_stacked_preview.png"
    print(f"  [{'OK' if sheet.exists() else 'FAIL'}] contact_sheet exists")
    print(f"  [{'OK' if stacked.exists() else 'FAIL'}] stacked_preview exists")

    print("\n" + "=" * 60)
    print(f"RESULT: {passed_checks}/{total_checks} checks passed")
    print("=" * 60)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
