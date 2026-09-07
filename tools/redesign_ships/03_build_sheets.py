"""Stage 3: Build sprite-sheet previews (BLOQUE 59).

For each ship, combine the 4 animations x 10 frames = 40 frames into a
single preview PNG with labels. Extends the logic from
tools/build_sprite_sheet.py to support 10-frame animations (the existing
script only supports 8).

Usage:
    python tools/redesign_ships/03_build_sheets.py
    python tools/redesign_ships/03_build_sheets.py --ship enemy_scout
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw, ImageFont

from tools.redesign_ships._ship_specs import SHIPS

ANIMATIONS = ("idle", "thrust", "damage", "death")
FRAME_SIZE = 32
LABEL_WIDTH = 96
COLUMNS = 10
ROWS = len(ANIMATIONS)
PADDING = 8
GRID_BG = (28, 24, 36)
LABEL_BG = (16, 12, 24)
LABEL_COLOR = (200, 220, 255)
FRAME_BORDER = (60, 50, 80)

SHEET_WIDTH = LABEL_WIDTH + COLUMNS * FRAME_SIZE + PADDING * (COLUMNS + 1)
SHEET_HEIGHT = ROWS * FRAME_SIZE + PADDING * (ROWS + 1)

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign"


def _load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("consola.ttf", size=size)
    except OSError:
        pass
    return ImageFont.load_default()


def _load_frame(ship_dir: Path, anim: str, frame_idx: int) -> Image.Image | None:
    p = ship_dir / anim / f"frame_{frame_idx:02d}.png"
    if not p.is_file():
        return None
    img = Image.open(p).convert("RGBA")
    if img.size != (FRAME_SIZE, FRAME_SIZE):
        img = img.resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.NEAREST)
    return img


def build_sheet(ship_key: str, out_path: Path) -> None:
    ship_dir = REDESIGN_DIR / ship_key
    sheet = Image.new("RGB", (SHEET_WIDTH, SHEET_HEIGHT), GRID_BG)
    draw = ImageDraw.Draw(sheet)
    font = _load_font(size=14)
    # Title bar at top
    title = f"VOID HUNTER - {ship_key.upper()} - 4 ANIM x 10 FRAMES - BLOQUE 59"
    draw.text((PADDING, 2), title, fill=LABEL_COLOR, font=font)
    for row, anim in enumerate(ANIMATIONS):
        # Label column
        y0 = PADDING + row * (FRAME_SIZE + PADDING) + PADDING
        draw.rectangle((0, y0 - PADDING, LABEL_WIDTH, y0 + FRAME_SIZE), fill=LABEL_BG)
        draw.text((PADDING, y0 + FRAME_SIZE // 2 - 8), anim.upper(), fill=LABEL_COLOR, font=font)
        # 10 frame cells
        for col in range(COLUMNS):
            x0 = LABEL_WIDTH + PADDING + col * (FRAME_SIZE + PADDING)
            # Cell border
            draw.rectangle((x0, y0, x0 + FRAME_SIZE, y0 + FRAME_SIZE), outline=FRAME_BORDER)
            # Frame number
            draw.text((x0 + 2, y0 + 2), str(col), fill=(100, 100, 120), font=font)
            # Frame image
            frame = _load_frame(ship_dir, anim, col)
            if frame is not None:
                sheet.paste(frame, (x0, y0), frame)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ship", help="Build sheet for only this ship key")
    args = parser.parse_args()
    targets = SHIPS if not args.ship else [s for s in SHIPS if s.key == args.ship]
    if args.ship and not targets:
        print(f"unknown ship: {args.ship}")
        return 1
    for spec in targets:
        out = REDESIGN_DIR / f"spritesheet_{spec.key}.png"
        build_sheet(spec.key, out)
        print(f"[sheet] {spec.key} -> {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
