"""BLOQUE 58.14.8 follow-up: extract the user's pixel art galaxy
from the reference image (the one they attached) and save it as a
sprite the parallax can use.

The reference image is 1920x1080 with:
  - Yellow header "ACT 1 - WAVE 1/6 [AI GALAXY NEBULA]" at top-left
  - Pixel art galaxy in the bottom-right corner
  - White background (the rest)

We crop just the galaxy, convert the white "background" to
transparent so the sprite can overlay the game's dark space, and
save it.
"""
import os
import sys
from PIL import Image


def main():
    src_path = r"D:\AI\void-hunter\Assets\background\galaxy_pixelart_reference.png"
    out_dir = r"D:\AI\void-hunter\Assets\background"

    im = Image.open(src_path).convert("RGBA")
    w, h = im.size
    print(f"reference: {w}x{h} mode={im.mode}")

    # The galaxy is in the bottom-right area. Looking at the image, it spans
    # roughly:
    #   x: 1100..1820 (out of 1920)
    #   y: 400..1000 (out of 1080)
    galaxy_box = (1080, 380, 1850, 1020)
    galaxy = im.crop(galaxy_box)
    gw, gh = galaxy.size
    print(f"cropped galaxy: {gw}x{gh}")

    # Convert white "background" pixels to TRANSPARENT. Threshold
    # r/g/b > 220 → alpha = 0. This keeps the small stars (which are
    # nearly white but slightly tinted) visible.
    px = galaxy.load()
    transparent_count = 0
    for y in range(gh):
        for x in range(gw):
            r, g, b, a = px[x, y]
            if r > 220 and g > 220 and b > 220:
                px[x, y] = (0, 0, 0, 0)
                transparent_count += 1
    print(f"set {transparent_count} pixels to transparent")

    # Now find the bbox of the actual galaxy content (non-transparent)
    min_x, min_y, max_x, max_y = gw, gh, 0, 0
    for y in range(gh):
        for x in range(gw):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if x < min_x: min_x = x
            if y < min_y: min_y = y
            if x > max_x: max_x = x
            if y > max_y: max_y = y
    if max_x < min_x or max_y < min_y:
        print("WARNING: no content found, using full crop")
        min_x, min_y, max_x, max_y = 0, 0, gw, gh
    print(f"galaxy bbox: ({min_x},{min_y}) to ({max_x},{max_y})")

    # Crop to content (with small margin)
    margin = 4
    min_x = max(0, min_x - margin)
    min_y = max(0, min_y - margin)
    max_x = min(gw - 1, max_x + margin)
    max_y = min(gh - 1, max_y + margin)
    galaxy_trimmed = galaxy.crop((min_x, min_y, max_x + 1, max_y + 1))
    tw, th = galaxy_trimmed.size
    print(f"trimmed galaxy: {tw}x{th}")

    # Downscale with NEAREST to preserve pixel art aesthetic. The parallax
    # will then upscale with NEAREST too, so the chunky pixels stay chunky.
    # Target: max 160px on the longest side.
    target_size = 160
    if tw > target_size or th > target_size:
        scale = target_size / max(tw, th)
        new_w = int(tw * scale)
        new_h = int(th * scale)
        galaxy_small = galaxy_trimmed.resize(
            (new_w, new_h), Image.NEAREST,
        )
    else:
        galaxy_small = galaxy_trimmed
    sw, sh = galaxy_small.size
    print(f"sprite: {sw}x{sh}")

    out_path = os.path.join(out_dir, "galaxy_pixelart_sprite.png")
    galaxy_small.save(out_path)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()

