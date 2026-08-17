"""Process the 4 AI-generated spiral galaxy sprites into final
nebula surfaces.

Unlike the ship's pixel-art sprites (which use NEAREST resize to
preserve hard edges), galaxies are SOFT GRADIENT digital art — the
spiral arms and core glow depend on smooth color transitions, so we
use LANCZOS resize. We also keep some padding around the galaxy so
the diffuse edges aren't clipped.

Pipeline:
1. Detect and remove the dark background (auto-detect from corners)
2. Crop to the non-background bounding box + small pad
3. Pad to a square so all 4 variants have the same aspect ratio
4. Resize to TARGET_SIZE (280x280 — fits nebula_radius_max=140)
5. Save as galaxy_sprite_NN.png in Assets/background/
"""
from PIL import Image
import os

SRC_DIR = "D:/AI/void-hunter/Assets/background"
DST_DIR = "D:/AI/void-hunter/Assets/background"
TARGET_SIZE = 280  # fits max nebula radius 140 with some bleed

# (source, target, target_w, target_h)
JOBS = [
    ("galaxy_sprite_01.png", "galaxy_sprite_01.png", TARGET_SIZE, TARGET_SIZE),
    ("galaxy_sprite_02.png", "galaxy_sprite_02.png", TARGET_SIZE, TARGET_SIZE),
    ("galaxy_sprite_03.png", "galaxy_sprite_03.png", TARGET_SIZE, TARGET_SIZE),
    ("galaxy_sprite_04.png", "galaxy_sprite_04.png", TARGET_SIZE, TARGET_SIZE),
]


def remove_dark_bg(img: Image.Image, threshold: int = 28) -> Image.Image:
    """Replace dark background pixels with transparent.

    The AI-generated galaxies sit on a near-black background, but
    the actual color varies (the corners can be #0a1530 navy or
    pure black). We auto-detect the dominant background from the
    four corners and remove pixels within `threshold` of it. The
    threshold is generous enough to keep anti-aliased edges.
    """
    w, h = img.size
    px = img.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    # Average the four corners; ignore alpha for the average (alpha
    # should always be 255 in the source).
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
            if (abs(r - bg[0]) <= threshold and
                abs(g - bg[1]) <= threshold and
                abs(b - bg[2]) <= threshold):
                op[x, y] = (0, 0, 0, 0)
            else:
                op[x, y] = (r, g, b, a)
    return out


def process(src: str, dst: str, tw: int, th: int) -> None:
    src_path = os.path.join(SRC_DIR, src)
    dst_path = os.path.join(DST_DIR, dst)
    img = Image.open(src_path).convert("RGBA")
    print(f"  {src}: {img.size} -> removing bg")
    img = remove_dark_bg(img)
    bbox = img.getbbox()
    if not bbox:
        print(f"    [SKIP] {src}: no content after bg removal")
        return
    print(f"    bbox: {bbox}")
    # Crop with a small pad so the diffuse edges aren't clipped.
    l, t, r, b = bbox
    pad = 4
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(img.size[0], r + pad)
    b = min(img.size[1], b + pad)
    cropped = img.crop((l, t, r, b))
    cw, ch = cropped.size
    print(f"    cropped: {cw}x{ch}")
    # Pad to square (largest dimension wins) so the galaxy is
    # centered and the spiral arms don't get squished on resize.
    square = max(cw, ch)
    padded = Image.new("RGBA", (square, square), (0, 0, 0, 0))
    ox = (square - cw) // 2
    oy = (square - ch) // 2
    padded.paste(cropped, (ox, oy), cropped)
    # Resize with LANCZOS to preserve the soft galaxy gradients.
    final = padded.resize((tw, th), Image.LANCZOS)
    final.save(dst_path)
    print(f"  -> {dst} ({tw}x{th})")


if __name__ == "__main__":
    print("Processing galaxy sprites...")
    for src, dst, tw, th in JOBS:
        if not os.path.exists(os.path.join(SRC_DIR, src)):
            print(f"  [SKIP] {src} (not found)")
            continue
        process(src, dst, tw, th)
    print("Done.")
