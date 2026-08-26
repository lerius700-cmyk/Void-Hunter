"""Build a combined sprite sheet PNG from the per-frame sprites.

BLOQUE 58.60: the project stores ship_01 as 5 animations x 8 frames in
separate subdirs (idle, rotating, propulsion, charging, damage). For
artists and external tools, it's much more useful to have a SINGLE
sprite sheet PNG that shows all 40 frames in a grid with labels.

Layout:
  +---------------------------------------------------+
  | idle:        f0  f1  f2  f3  f4  f5  f6  f7        |
  | rotating:    f0  f1  f2  f3  f4  f5  f6  f7        |
  | propulsion:  f0  f1  f2  f3  f4  f5  f6  f7        |
  | charging:    f0  f1  f2  f3  f4  f5  f6  f7        |
  | damage:      f0  f1  f2  f3  f4  f5  f6  f7        |
  +---------------------------------------------------+

Each cell = 64x64 px (matches the FINAL_SIZE used by
generate_player_ship_sheets.py). Plus a 64px-wide label column on the
left for the animation name.

Final image: 64 (label) + 8*64 (frames) = 576 wide, 5*64 (rows) = 320 tall.

Usage:
  python tools/build_sprite_sheet.py [ship_id]
  python tools/build_sprite_sheet.py 1
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SHIPS_DIR = ROOT / "Assets" / "sprites" / "player_ships"

ANIMATIONS: tuple[str, ...] = (
    "idle",
    "rotating",
    "propulsion",
    "charging",
    "damage",
)
FRAME_SIZE: int = 64
LABEL_WIDTH: int = 96  # pixels reserved for the row label
COLUMNS: int = 8
ROWS: int = len(ANIMATIONS)
PADDING: int = 8
GRID_BG: tuple[int, int, int] = (28, 24, 36)         # dark indigo
LABEL_BG: tuple[int, int, int] = (16, 12, 24)         # darker indigo
LABEL_COLOR: tuple[int, int, int] = (200, 220, 255)   # pale cyan
FRAME_BORDER: tuple[int, int, int] = (60, 50, 80)     # subtle border

SHEET_WIDTH: int = LABEL_WIDTH + COLUMNS * FRAME_SIZE + PADDING * (COLUMNS + 1)
SHEET_HEIGHT: int = ROWS * FRAME_SIZE + PADDING * (ROWS + 1)


def _load_font(size: int) -> ImageFont.ImageFont:
    """Load a default font at the requested size."""
    try:
        return ImageFont.truetype("consola.ttf", size=size)
    except OSError:
        pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _load_frame(ship_dir: Path, anim: str, frame_idx: int) -> Image.Image | None:
    """Load a single frame PNG. Returns None if missing."""
    p = ship_dir / anim / f"frame_{frame_idx:02d}.png"
    if not p.is_file():
        return None
    img = Image.open(p).convert("RGBA")
    if img.size != (FRAME_SIZE, FRAME_SIZE):
        img = img.resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.NEAREST)
    return img


def _chroma_key(img: Image.Image, max_gray: int = 150) -> Image.Image:
    """Make dark-gray pixels transparent (sprite ships have a baked-in
    dark-gray checker background; this is the same logic the video tools use)."""
    import numpy as np
    arr = np.array(img, dtype=np.uint8)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    is_gray = (r == g) & (g == b)
    is_dark = r < max_gray
    is_bg = is_gray & is_dark
    new_a = np.where(is_bg, 0, a)
    # Fade low-chroma edge pixels (anti-aliasing)
    chroma = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    fade = (chroma < 30) & (new_a > 0)
    new_a = np.where(fade, (new_a * chroma // 60).astype(np.uint8), new_a)
    out = np.stack([r, g, b, new_a], axis=-1)
    return Image.fromarray(out, mode="RGBA")


def build_sheet(ship_id: int = 1) -> Path:
    """Build the sprite sheet for a given ship_id. Returns the output path."""
    ship_dir = SHIPS_DIR / f"ship_0{ship_id}"
    if not ship_dir.is_dir():
        raise FileNotFoundError(f"Ship directory not found: {ship_dir}")
    # Try to load the base sprite for the cover image
    base_path = SHIPS_DIR / f"ship_0{ship_id}_base.png"
    base_img: Image.Image | None = None
    if base_path.is_file():
        base_img = Image.open(base_path).convert("RGBA")
        # Resize to FRAME_SIZE for the cover
        if base_img.size != (FRAME_SIZE, FRAME_SIZE):
            base_img = base_img.resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.NEAREST)
    # Create the sheet canvas
    sheet = Image.new("RGBA", (SHEET_WIDTH, SHEET_HEIGHT), GRID_BG + (255,))
    draw = ImageDraw.Draw(sheet)
    # Use a pixel font for the labels
    label_font = _load_font(11)
    # Draw each row
    for row, anim in enumerate(ANIMATIONS):
        y0 = PADDING + row * (FRAME_SIZE + PADDING)
        # Label background (left column)
        draw.rectangle(
            [0, y0, LABEL_WIDTH, y0 + FRAME_SIZE],
            fill=LABEL_BG + (255,),
        )
        # Label text
        label = anim.upper()
        bbox = draw.textbbox((0, 0), label, font=label_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (LABEL_WIDTH - text_w) // 2
        text_y = y0 + (FRAME_SIZE - text_h) // 2 - 2
        draw.text((text_x, text_y), label, fill=LABEL_COLOR, font=label_font)
        # Each frame in this row
        for col in range(COLUMNS):
            x0 = LABEL_WIDTH + PADDING + col * (FRAME_SIZE + PADDING)
            # Frame cell background (slightly lighter than the grid)
            cell_bg = (40, 34, 56, 255)
            draw.rectangle(
                [x0, y0, x0 + FRAME_SIZE, y0 + FRAME_SIZE],
                fill=cell_bg,
            )
            # Frame border
            draw.rectangle(
                [x0, y0, x0 + FRAME_SIZE - 1, y0 + FRAME_SIZE - 1],
                outline=FRAME_BORDER,
                width=1,
            )
            # Load and paste the frame
            if col == 0 and base_img is not None:
                # Use the base image for the first cell (the "source" preview)
                frame = base_img.copy()
            else:
                frame = _load_frame(ship_dir, anim, col)
            if frame is not None:
                # Apply chroma key to clean up the dark-gray background
                frame = _chroma_key(frame)
                sheet.alpha_composite(frame, (x0, y0))
            # Frame number label (small, in the corner)
            num_label = str(col)
            num_bbox = draw.textbbox((0, 0), num_label, font=label_font)
            num_w = num_bbox[2] - num_bbox[0]
            num_h = num_bbox[3] - num_bbox[1]
            draw.rectangle(
                [x0, y0, x0 + num_w + 4, y0 + num_h + 2],
                fill=(0, 0, 0, 160),
            )
            draw.text((x0 + 2, y0 - 1), num_label, fill=(255, 255, 200), font=label_font)
    # Header strip
    header = Image.new("RGBA", (SHEET_WIDTH, 18), (10, 8, 20, 255))
    header_draw = ImageDraw.Draw(header)
    header_draw.text(
        (4, 2),
        f"VOID HUNTER  -  SHIP_0{ship_id}  -  5 ANIM x 8 FRAMES  -  PIXEL ART",
        fill=(140, 200, 255),
        font=label_font,
    )
    # Composite the header at the top
    final = Image.new("RGBA", (SHEET_WIDTH, SHEET_HEIGHT + 18), GRID_BG + (255,))
    final.alpha_composite(header, (0, 0))
    final.alpha_composite(sheet, (0, 18))
    # Output path
    out_path = SHIPS_DIR / f"ship_0{ship_id}_spritesheet.png"
    final.save(out_path)
    return out_path


def main() -> int:
    ship_id = 1
    if len(sys.argv) > 1:
        try:
            ship_id = int(sys.argv[1])
        except ValueError:
            print(f"Invalid ship_id: {sys.argv[1]}")
            return 1
    print(f"Building sprite sheet for ship_0{ship_id}...")
    try:
        out = build_sheet(ship_id)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1
    size_kb = out.stat().st_size / 1024
    print(f"  -> {out}  ({size_kb:.1f} KB)")
    print(f"  Dimensions: {SHEET_WIDTH}x{SHEET_HEIGHT + 18} px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
