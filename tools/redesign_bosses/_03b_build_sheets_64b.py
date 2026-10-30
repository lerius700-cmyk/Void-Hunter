"""Build the 6x10 GOLIATH preview sheet from the CANONICAL frames.

Each row is one clip, each column is one frame. Saved to
Assets/sprites/bosses/goliath/spritesheet_goliath_64b.png for review.

BLOQUE 75: the sheet used to be built from
``Assets/sprites/redesign/goliath/`` -- the STAGING area of BLOQUE 64.B.
That directory still holds placeholder frames (the ten frames of a state
are byte-identical to each other), and the art was replaced twice since
(BLOQUE 67 and BLOQUE 74). The result was a review sheet showing art that
the game has not shipped since BLOQUE 64.B: not one of its 60 cells
matched the frame it claimed to show.

The sheet is now built from the same source the game reads:
``Assets/sprites/bosses/goliath/<clip.dir>/frame_NN.png``, and the clip
list, the frame counts and the canvas come from the MANIFEST
(``manifest.toml``), which is the set's spec. The sheet therefore cannot
drift from the game again: adding a clip to the manifest adds a row.

The standalone user-facing 6x10 sprite-sheet is built by
tools/capture/capture_bloque_64_goliath.py (not this file -- that one
strips the label column for a clean grid).

Usage:
    python tools/redesign_bosses/_03b_build_sheets_64b.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

from src.anim.manifest import load_set

SET_NAME = "goliath"
SETS_ROOT = PROJECT_ROOT / "Assets" / "sprites" / "bosses"
OUT_PATH = SETS_ROOT / SET_NAME / "spritesheet_goliath_64b.png"

PADDING = 4
LABEL_W = 100


def main() -> int:
    anim_set = load_set(SET_NAME, root=SETS_ROOT)

    clips = list(anim_set.clips.values())
    cell_w, cell_h = anim_set.canvas
    cols = max(clip.frames for clip in clips)

    sheet_w = LABEL_W + cols * (cell_w + PADDING) + PADDING
    sheet_h = len(clips) * (cell_h + PADDING) + PADDING
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (20, 20, 40, 255))

    for r, clip in enumerate(clips):
        for c in range(clip.frames):
            frame_path = anim_set.path / clip.dir / f"frame_{c:02d}.png"
            if not frame_path.exists():
                print(f"  !! missing {frame_path}")
                continue
            frame = Image.open(frame_path).convert("RGBA")
            x = LABEL_W + PADDING + c * (cell_w + PADDING)
            y = PADDING + r * (cell_h + PADDING)
            sheet.paste(frame, (x, y), frame)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT_PATH)
    print(f"saved {OUT_PATH} ({sheet_w}x{sheet_h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
