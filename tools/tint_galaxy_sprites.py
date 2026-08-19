"""BLOQUE 58.14.8 follow-up: generate tinted pixel art galaxy variants.

The user wants variety: 3-4 pixel art galaxies in different tints
(red, blue, cyan, violet). This script takes the source pixel art
galaxy and creates 3 hue-shifted copies.

Approach: convert each pixel to HSL, shift hue, convert back. This
preserves the saturation/lightness so the chunky pixel art aesthetic
stays intact — only the COLOR changes.
"""
import os
import colorsys
from PIL import Image


def shift_hue(r: int, g: int, b: int, hue_shift_deg: float):
    """Return (r, g, b) with hue rotated by `hue_shift_deg`."""
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    h = (h + hue_shift_deg / 360.0) % 1.0
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return (
        max(0, min(255, int(r2 * 255))),
        max(0, min(255, int(g2 * 255))),
        max(0, min(255, int(b2 * 255))),
    )


def main():
    src_path = r"D:\AI\void-hunter\Assets\background\galaxy_pixelart_sprite.png"
    out_dir = r"D:\AI\void-hunter\Assets\background"

    im = Image.open(src_path).convert("RGBA")
    w, h = im.size
    print(f"source: {w}x{h} mode={im.mode}")

    # Variants: (suffix, hue_shift_deg)
    # Original is blue (~200°). Shifts:
    #   +0°   → blue (the original)
    #   +60°  → violet (~260°)
    #   -80°  → green (~120°) — wait, this would be too cyan-green
    #   +150° → red (~350°)
    #   -160° → cyan (~40°)
    variants = [
        ("blue", 0.0),       # original (no shift)
        ("violet", 60.0),     # blue → violet
        ("red", 155.0),       # blue → red/magenta
        ("cyan", -160.0),     # blue → cyan/teal
    ]
    # Note: negative shifts work in Python modulo (h + shift) % 1.0

    px = im.load()
    for suffix, shift in variants:
        # Copy pixel data with hue shift applied
        variant = im.copy()
        vpx = variant.load()
        shifted = 0
        for y in range(h):
            for x in range(w):
                r, g, b, a = vpx[x, y]
                if a == 0:
                    continue
                nr, ng, nb = shift_hue(r, g, b, shift)
                vpx[x, y] = (nr, ng, nb, a)
                shifted += 1
        out_path = os.path.join(out_dir, f"galaxy_pixelart_{suffix}.png")
        variant.save(out_path)
        print(f"  {suffix}: shifted {shifted} px, saved {out_path}")


if __name__ == "__main__":
    main()
