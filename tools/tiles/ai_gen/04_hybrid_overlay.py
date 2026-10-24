"""Hybrid overlay: AI tile backdrop + crisp MINE-ASTEROID asteroid sprites on top.

For tiles 2-5, composites procedural MINE-ASTEROID asteroid sprites on top of
the AI-generated tile. The AI tile provides the atmosphere/nebula background;
the procedural asteroids give crisp pixel art that matches BLOQUE 61.

For tiles 1 and 6, no overlay is added (they should be asteroid-free).

Output: replaces the 6 final PNGs in Assets/background/tiles/act1/ with
hybrid versions. Contact sheet and stacked preview rebuilt.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image

# Paths
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[2]
ACT1_DIR = REPO_ROOT / "Assets" / "background" / "tiles" / "act1"
ASTEROID_DIR = REPO_ROOT / "Assets" / "sprites" / "asteroids"

TILE_W = 320
TILE_H = 480

# Asteroid layout per tile: (count, scale_min, scale_max, y_min_pct, y_max_pct)
# y_min_pct, y_max_pct define the vertical band where asteroids spawn (0.0 = top, 1.0 = bottom)
# Picked to match the narrative beat.
TILE_ASTEROID_LAYOUT: dict[str, dict] = {
    "tile_01_atmosphere_exit": {"asteroids": 0},  # NO asteroids
    "tile_02_enter_belt": {"asteroids": 6, "scale_min": 0.7, "scale_max": 1.1, "y_band": (0.30, 0.95)},
    "tile_03_mid_belt": {"asteroids": 10, "scale_min": 0.7, "scale_max": 1.4, "y_band": (0.10, 0.95)},
    "tile_04_peak_belt": {"asteroids": 14, "scale_min": 0.8, "scale_max": 1.5, "y_band": (0.05, 0.95)},
    "tile_05_exit_belt": {"asteroids": 4, "scale_min": 0.7, "scale_max": 1.0, "y_band": (0.30, 0.85)},
    "tile_06_open_stars": {"asteroids": 0},  # NO asteroids
}

VARIANTS = ["round", "elongated", "spiked", "hollowed", "cracked"]


def load_asteroid_variants() -> dict[str, list[Image.Image]]:
    """Load all 5 MINE-ASTEROID variants at multiple scales.

    Returns dict mapping variant name -> list of pre-scaled RGBA images.
    Scale factors: 0.5, 0.75, 1.0, 1.25, 1.5 (covers the 0.7-1.5 range).
    """
    cache: dict[str, list[Image.Image]] = {}
    scale_factors = [0.5, 0.75, 1.0, 1.25, 1.5]
    for v in VARIANTS:
        path = ASTEROID_DIR / f"{v}.png"
        if not path.exists():
            print(f"  WARN: asteroid variant {v}.png not found, skipping")
            cache[v] = []
            continue
        img = Image.open(path).convert("RGBA")
        scaled = []
        for s in scale_factors:
            new_size = (max(1, int(img.size[0] * s)), max(1, int(img.size[1] * s)))
            scaled.append(img.resize(new_size, Image.NEAREST))
        cache[v] = scaled
        print(f"  Loaded {v}: {img.size}, {len(scaled)} scales")
    return cache


def composite_asteroid(
    bg: Image.Image, sprite: Image.Image, x: int, y: int
) -> Image.Image:
    """Paste a transparent RGBA asteroid sprite onto bg (RGB) at (x, y)."""
    sprite_w, sprite_h = sprite.size
    # Clip to bg bounds
    px = max(0, x)
    py = max(0, y)
    # Compute sprite clip region
    sx = max(0, -x)
    sy = max(0, -y)
    sprite_w_clip = min(sprite_w - sx, TILE_W - px)
    sprite_h_clip = min(sprite_h - sy, TILE_H - py)
    if sprite_w_clip <= 0 or sprite_h_clip <= 0:
        return bg
    sprite_clip = sprite.crop((sx, sy, sx + sprite_w_clip, sy + sprite_h_clip))
    # Composite using alpha as mask
    bg.paste(sprite_clip, (px, py), sprite_clip)
    return bg


def overlay_tile(
    tile_name: str, variant_cache: dict[str, list[Image.Image]], seed: int
) -> Image.Image:
    """Overlay asteroids on a single AI tile."""
    tile_path = ACT1_DIR / f"{tile_name}.png"
    print(f"\n[overlay] {tile_name}")
    img = Image.open(tile_path).convert("RGB")
    print(f"  Base: {img.size}")

    layout = TILE_ASTEROID_LAYOUT.get(tile_name)
    if not layout or layout["asteroids"] == 0:
        print(f"  No asteroids in this tile, returning as-is")
        return img

    n = layout["asteroids"]
    rng = random.Random(seed)
    print(f"  Overlay: {n} asteroids, scale {layout['scale_min']}-{layout['scale_max']}, y band {layout['y_band']}")

    for i in range(n):
        variant = VARIANTS[rng.randint(0, len(VARIANTS) - 1)]
        scales = variant_cache.get(variant, [])
        if not scales:
            continue
        # Pick a random scale index (0..len(scales)-1)
        scale_idx = rng.randint(0, len(scales) - 1)
        sprite = scales[scale_idx]
        sprite_w, sprite_h = sprite.size
        # Random x position (allow partial bleed off edges)
        x = rng.randint(-sprite_w // 4, TILE_W - sprite_w + sprite_w // 4)
        # Random y position within band
        y_min = int(layout["y_band"][0] * TILE_H)
        y_max = int(layout["y_band"][1] * TILE_H) - sprite_h
        if y_max < y_min:
            y_max = y_min
        y = rng.randint(y_min, y_max)
        img = composite_asteroid(img, sprite, x, y)

    return img


def build_contact_sheet(tile_paths: list[Path]) -> Path:
    sheet = Image.new("RGB", (TILE_W * 6, TILE_H), (4, 8, 20))
    for i, p in enumerate(tile_paths):
        tile = Image.open(p).convert("RGB")
        sheet.paste(tile, (i * TILE_W, 0))
    out = ACT1_DIR / "_contact_sheet.png"
    sheet.save(out, optimize=True)
    print(f"\nContact sheet: {out}")
    return out


def build_stacked_preview(tile_paths: list[Path]) -> Path:
    stacked = Image.new("RGB", (TILE_W, TILE_H * 6), (4, 8, 20))
    for i, p in enumerate(tile_paths):
        tile = Image.open(p).convert("RGB")
        stacked.paste(tile, (0, i * TILE_H))
    out = ACT1_DIR / "_stacked_preview.png"
    stacked.save(out, optimize=True)
    print(f"Stacked preview: {out}")
    return out


def main() -> int:
    print("=" * 60)
    print("Hybrid overlay: AI tile backdrop + MINE-ASTEROID overlay")
    print("=" * 60)

    print("\nLoading MINE-ASTEROID variants...")
    variant_cache = load_asteroid_variants()
    total_loaded = sum(len(v) for v in variant_cache.values())
    if total_loaded == 0:
        print("ERROR: no asteroid variants loaded. Run BLOQUE 61 first.")
        return 1

    tiles = [
        "tile_01_atmosphere_exit",
        "tile_02_enter_belt",
        "tile_03_mid_belt",
        "tile_04_peak_belt",
        "tile_05_exit_belt",
        "tile_06_open_stars",
    ]

    # Use a fixed seed for reproducibility
    seed = 42
    for tile_name in tiles:
        result = overlay_tile(tile_name, variant_cache, seed=hash(tile_name) & 0xFFFF)
        out_path = ACT1_DIR / f"{tile_name}.png"
        result.save(out_path, optimize=True)
        # Re-quantize to 16 colors after overlay
        result_q = result.quantize(colors=16, method=Image.Quantize.MEDIANCUT).convert("RGB")
        unique = len(result_q.getcolors(maxcolors=256) or [])
        print(f"  Saved: {out_path.name} ({result.size}, {unique} unique colors after re-quantize)")
        result_q.save(out_path, optimize=True)

    # Rebuild contact sheet and stacked preview
    tile_paths = [ACT1_DIR / f"{t}.png" for t in tiles]
    build_contact_sheet(tile_paths)
    build_stacked_preview(tile_paths)

    print("\n" + "=" * 60)
    print("Hybrid overlay complete: 6/6 tiles updated")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
