"""Process generated sprites into final pixel-art PNGs.

For each generated 1024x1024 image:
1. Detect and remove the dark-navy background (make transparent)
2. Find the bounding box of the non-background content
3. Crop with a small padding
4. Resize to the target sprite size with NEAREST (hard pixel edges)
5. Save as the final sprite file

Target sizes (designed for 480x270 internal, scaled 4x to 1920x1080):
  player:         16x16  (small sleek fighter)
  scout:          12x12  (small fast dart)
  cruiser:        16x16  (medium wing-fighter)
  heavy:          20x20  (large armored)
  boss:           48x48  (hexagonal asteroid boss)
  player_bullet:  12x4   (horizontal yellow streak)
  enemy_bullet:    8x8   (red plasma orb)
"""
from PIL import Image
import os

SPRITES_DIR = "stellar_horizon/assets/sprites"

# (source, target, target_w, target_h)
JOBS = [
    ("_gen_player.png",         "player.png",         16, 16),
    ("_gen_scout.png",          "scout.png",          12, 12),
    ("_gen_cruiser.png",        "cruiser.png",        16, 16),
    ("_gen_heavy.png",          "heavy.png",          20, 20),
    ("_gen_boss.png",           "boss.png",           48, 48),
    ("_gen_player_bullet.png",  "player_bullet.png",  12,  4),
    ("_gen_enemy_bullet.png",   "enemy_bullet.png",    8,  8),
]


def remove_navy_bg(img: Image.Image, threshold: int = 32) -> Image.Image:
    """Replace dark-navy background pixels with transparent.

    Auto-detects the actual background color from the four corners (the
    model doesn't always use the exact (10, 15, 31) navy from the game),
    then removes pixels within `threshold` of that color. The threshold
    is generous enough to catch anti-aliased edges around the sprite.
    """
    w, h = img.size
    px = img.load()
    # Sample corners to find the dominant background color
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg = (
        sum(c[0] for c in corners) // 4,
        sum(c[1] for c in corners) // 4,
        sum(c[2] for c in corners) // 4,
    )
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if abs(r - bg[0]) <= threshold and abs(g - bg[1]) <= threshold and abs(b - bg[2]) <= threshold:
                op[x, y] = (0, 0, 0, 0)
            else:
                op[x, y] = (r, g, b, a)
    return out


def crop_to_content(img: Image.Image, pad: int = 2) -> Image.Image:
    """Crop to the non-transparent bounding box plus `pad` pixels of padding."""
    bbox = img.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(img.size[0], r + pad)
    b = min(img.size[1], b + pad)
    return img.crop((l, t, r, b))


def process(src: str, dst: str, tw: int, th: int) -> None:
    src_path = os.path.join(SPRITES_DIR, src)
    dst_path = os.path.join(SPRITES_DIR, dst)
    img = Image.open(src_path).convert("RGBA")
    img = remove_navy_bg(img)
    cropped = crop_to_content(img, pad=4)
    # Center the cropped content in a (tw x th) canvas, then NEAREST-resize
    # to that canvas size. This avoids the content drifting to one side
    # when the source bbox is off-center.
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    cw, ch = cropped.size
    # If the cropped content is larger than the target, downscale it to
    # fit while keeping aspect ratio.
    if cw > tw or ch > th:
        scale = min(tw / cw, th / ch)
        new_size = (max(1, int(cw * scale)), max(1, int(ch * scale)))
        cropped = cropped.resize(new_size, Image.NEAREST)
        cw, ch = cropped.size
    ox = (tw - cw) // 2
    oy = (th - ch) // 2
    canvas.paste(cropped, (ox, oy), cropped)
    canvas.save(dst_path)
    print(f"  {src} -> {dst} ({tw}x{th})  content {cw}x{ch} at ({ox},{oy})")


if __name__ == "__main__":
    print("Processing sprites...")
    for src, dst, tw, th in JOBS:
        process(src, dst, tw, th)
    print("Done.")
