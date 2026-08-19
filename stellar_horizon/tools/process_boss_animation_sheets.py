"""Process the 4 AI-generated boss key frames into 6-frame sprite sheets.

Each input is a 1:1 PNG (~1024x1024). We:
  1. Remove the near-black background (corners sample).
  2. Crop to content bounding box (with 2px pad).
  3. NEAREST-resize to 48x48 (the game's per-frame boss size).
  4. Build a 6-frame horizontal strip (288x48) where each frame is
     the same processed image (code-driven animation will add pulse
     and scale variation at draw time).
  5. Save as <name>_sheet.png in stellar_horizon/assets/sprites/.

Input files (looked up in both the workspace root D:\AI\ and the
project root D:\AI\void-hunter\ since the image_synthesize tool can
land images in either):
  boss_idle_key.png, boss_telegraph_key.png, boss_charge_key.png,
  boss_dying_key.png

Output files (in stellar_horizon/assets/sprites/):
  boss_idle_sheet.png (288x48)
  boss_telegraph_sheet.png (288x48)
  boss_charge_sheet.png (288x48)
  boss_dying_sheet.png (288x48)

Usage: from D:\AI\void-hunter, run
  python -m stellar_horizon.tools.process_boss_animation_sheets
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PIL import Image

# Where the AI generator drops the key frames (workspace root).
SOURCE_DIR_CANDIDATES = [
    Path("D:/AI"),
    Path("D:/AI/void-hunter"),
]

# Where the processed sprite sheets live in the project.
SPRITES_DIR = Path("D:/AI/void-hunter/stellar_horizon/assets/sprites")

BOSS_FRAMES = [
    ("boss_idle_key",      "boss_idle_sheet"),
    ("boss_telegraph_key", "boss_telegraph_sheet"),
    ("boss_charge_key",    "boss_charge_sheet"),
    ("boss_dying_key",     "boss_dying_sheet"),
]
FRAME_SIZE = 48
FRAME_COUNT = 6


def remove_near_black_bg(img: Image.Image, threshold: int = 28) -> Image.Image:
    """Replace near-black pixels with transparent (corners sample)."""
    w, h = img.size
    px = img.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    # Average the four corner colors as the "background" reference.
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
            if (abs(r - bg[0]) <= threshold
                    and abs(g - bg[1]) <= threshold
                    and abs(b - bg[2]) <= threshold):
                op[x, y] = (0, 0, 0, 0)
            else:
                op[x, y] = (r, g, b, a)
    return out


def crop_to_content(img: Image.Image, pad: int = 2) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(img.size[0], r + pad)
    b = min(img.size[1], b + pad)
    return img.crop((l, t, r, b))


def find_source(name: str) -> Path | None:
    """Look for <name>.png in any of the candidate source dirs."""
    fname = f"{name}.png"
    for d in SOURCE_DIR_CANDIDATES:
        p = d / fname
        if p.exists():
            return p
    return None


def build_sheet(src: Path, dst: Path) -> None:
    img = Image.open(src).convert("RGBA")
    img = remove_near_black_bg(img)
    img = crop_to_content(img, pad=4)
    # Resize to the target frame size with NEAREST so the pixel
    # art stays crisp.
    frame = img.resize((FRAME_SIZE, FRAME_SIZE), Image.NEAREST)
    # Build a 6-frame strip where each frame is the same image —
    # code-driven animation (scale, alpha, rotation) provides
    # visible variation in the game.
    strip = Image.new("RGBA", (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE),
                      (0, 0, 0, 0))
    for i in range(FRAME_COUNT):
        strip.paste(frame, (i * FRAME_SIZE, 0), frame)
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    strip.save(dst)
    print(f"  {src.name} -> {dst.name} "
          f"({FRAME_SIZE * FRAME_COUNT}x{FRAME_SIZE}, "
          f"{FRAME_COUNT} frames of {FRAME_SIZE}x{FRAME_SIZE})")


def main() -> int:
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    print("Processing boss animation sheets...")
    for src_name, dst_name in BOSS_FRAMES:
        src = find_source(src_name)
        if src is None:
            print(f"  [SKIP] {src_name}.png not found in any source dir")
            continue
        dst = SPRITES_DIR / f"{dst_name}.png"
        build_sheet(src, dst)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
