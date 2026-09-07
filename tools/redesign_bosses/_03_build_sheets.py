"""Stage 3: Build a 5x10 preview sheet (BLOQUE 60).

Each row is one state, each column is one frame. Saved to
Assets/sprites/bosses/goliath/spritesheet_goliath.png for review.

BLOQUE 60 deviation: filename is ``_03_build_sheets.py`` (underscore
prefix) instead of the plan's ``03_build_sheets.py`` so the module is
importable as a Python identifier via
``from tools.redesign_bosses import _03_build_sheets``.

Usage:
    python tools/redesign_bosses/_03_build_sheets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

from tools.redesign_bosses._specs import GOLIATH_SPEC

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "goliath"
OUT_PATH = PROJECT_ROOT / "Assets" / "sprites" / "bosses" / "goliath" / "spritesheet_goliath.png"

STATES = ("idle", "damage", "phase2", "death", "intro")
FRAMES_PER_STATE = 10
CELL_W, CELL_H = 96, 80
PADDING = 4
LABEL_W = 80


def main() -> int:
    cols = FRAMES_PER_STATE
    rows = len(STATES)
    sheet_w = LABEL_W + cols * (CELL_W + PADDING) + PADDING
    sheet_h = rows * (CELL_H + PADDING) + PADDING
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (20, 20, 40, 255))
    for r, state in enumerate(STATES):
        for c in range(FRAMES_PER_STATE):
            frame_path = REDESIGN_DIR / state / f"frame_{c:02d}.png"
            if not frame_path.exists():
                continue
            frame = Image.open(frame_path).convert("RGBA")
            x = LABEL_W + PADDING + c * (CELL_W + PADDING)
            y = PADDING + r * (CELL_H + PADDING)
            sheet.paste(frame, (x, y), frame)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT_PATH)
    print(f"saved {OUT_PATH} ({sheet_w}x{sheet_h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
