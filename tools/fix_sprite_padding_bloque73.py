"""BLOQUE 73.4: pad sprites whose silhouette touches the canvas edge.

The original "GOLIATH se ve cortado" report was a sprite whose top row sat
1 px from the canvas top: the helmet flame clipped against the frame. A
handful of frames across the set have this, because the AI generator
sometimes fills the full 96x80 box.

Fix: composite the sprite 2 px lower (and 1 px right) onto a fresh
transparent canvas of the same size, so the whole silhouette sits inside
with a >= 2 px margin on every side. The visual content is untouched --
only its position inside the canvas shifts, which the centroid and
arm/eye anchors recompute automatically on next access.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(".")
BASE = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
ANIMS = ["phase1_idle", "phase2_idle", "javelin", "laser", "purple_bullet", "death"]
MIN_MARGIN = 3


def needs_pad(img: Image.Image) -> tuple[bool, tuple[int, int, int, int]]:
    bbox = img.split()[-1].getbbox()
    if bbox is None:
        return False, (0, 0, 0, 0)
    w, h = img.size
    # (left, top, right-margin, bottom-margin) — all four are "space
    # between the silhouette and the canvas edge on that side".
    margins = (bbox[0], bbox[1], w - bbox[2], h - bbox[3])
    tight = min(margins) < MIN_MARGIN
    return tight, margins


def main() -> None:
    padded = 0
    for anim in ANIMS:
        for i in range(10):
            p = BASE / anim / f"frame_{i:02d}.png"
            img = Image.open(p).convert("RGBA")
            tight, margins = needs_pad(img)
            if not tight:
                continue
            w, h = img.size
            # margins are (L, T, R, B): space between silhouette and edge.
            L, T, R, B = margins
            # Shift down first — in practice the helmet flame clips at the
            # top, and the sprite has room below it.
            dx = 0
            dy = max(0, MIN_MARGIN - T)
            if h - dy + (B) < MIN_MARGIN:
                # Not enough room below: split the shortfall across top/bottom.
                dy = max(0, (2 * MIN_MARGIN - T - B) // 2)
            if w - dx + R < MIN_MARGIN:
                dx = max(0, MIN_MARGIN - L)
            out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            out.paste(img, (dx, dy), img)
            _, new_margins = needs_pad(out)
            if min(new_margins) >= MIN_MARGIN:
                out.save(p)
                padded += 1
                print(
                    f"  padded {anim}/frame_{i:02d}: "
                    f"L{margins[0]} T{margins[1]} R{margins[2]} B{margins[3]}"
                    f" -> L{new_margins[0]} T{new_margins[1]} R{new_margins[2]} B{new_margins[3]}"
                    f" (shift dx={dx} dy={dy})"
                )
            else:
                print(
                    f"  SKIPPED {anim}/frame_{i:02d}: cannot reach {MIN_MARGIN}px "
                    f"margin, best was L{new_margins[0]} T{new_margins[1]} "
                    f"R{new_margins[2]} B{new_margins[3]}"
                )
    print(f"padded {padded} frames")


if __name__ == "__main__":
    main()