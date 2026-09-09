"""Capture all 6 BLOQUE 64.B GOLIATH anims + the 6x10 sprite-sheet grid.

For each of the 6 new states (phase1_idle / phase2_idle / javelin / laser /
purple_bullet / death), renders frame_00.png centered on a 240x360 surface
and saves to ``tools/playtest_out/bloque_64_goliath_<state>.png``.

Then renders the 6x10 sprite-sheet grid (all 60 frames in one image) and
saves to ``tools/playtest_out/bloque_64_goliath_spritesheet.png``.

This is the visual verification step for BLOQUE 64.B: the user must
confirm the borderless prompt worked (no dark frame, transparent
background) and the silhouettes match the locked-palette brief.
"""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image

GOLIATH_STATES = (
    "phase1_idle",
    "phase2_idle",
    "javelin",
    "laser",
    "purple_bullet",
    "death",
)
LIVE_DIR = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
OUT_DIR = ROOT / "tools" / "playtest_out"

# GOLIATH native frame size
FRAME_W, FRAME_H = 96, 80

# Per-anim preview background — same dark space color as the game
BG_COLOR = (8, 8, 20)


def capture_single_anim(state: str) -> Path:
    """Save one PNG with frame_00 centered on a 240x360 dark surface."""
    surf = Image.new("RGB", (240, 360), BG_COLOR)
    frame_path = LIVE_DIR / state / "frame_00.png"
    if not frame_path.exists():
        raise FileNotFoundError(f"missing {frame_path}")
    with Image.open(frame_path) as frame:
        frame = frame.convert("RGBA")
        # Center the 96x80 frame in 240x360
        x = (240 - FRAME_W) // 2
        y = (360 - FRAME_H) // 2
        # Composite over the dark background (RGBA → RGB via alpha)
        bg = Image.new("RGBA", surf.size, (*BG_COLOR, 255))
        bg.paste(frame, (x, y), frame)
        surf = bg.convert("RGB")
    out = OUT_DIR / f"bloque_64_goliath_{state}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    surf.save(out)
    return out


def capture_spritesheet() -> Path:
    """Build a 6x10 grid (60 frames) of all GOLIATH states."""
    cols = 10
    rows = 6
    padding = 2
    label_h = 16
    sheet_w = cols * (FRAME_W + padding) + padding
    sheet_h = label_h + rows * (FRAME_H + padding) + padding
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (*BG_COLOR, 255))
    for r, state in enumerate(GOLIATH_STATES):
        for c in range(cols):
            frame_path = LIVE_DIR / state / f"frame_{c:02d}.png"
            if not frame_path.exists():
                continue
            with Image.open(frame_path) as f:
                f = f.convert("RGBA")
                x = padding + c * (FRAME_W + padding)
                y = label_h + padding + r * (FRAME_H + padding)
                sheet.paste(f, (x, y), f)
    out = OUT_DIR / "bloque_64_goliath_spritesheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out)
    return out


def main() -> int:
    for state in GOLIATH_STATES:
        out = capture_single_anim(state)
        print(f"  {state:14s} -> {out.name}")
    sheet = capture_spritesheet()
    print(f"  spritesheet    -> {sheet.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
