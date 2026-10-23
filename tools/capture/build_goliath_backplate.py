"""BLOQUE 66.6: build a body backplate from phase1_idle and composite it
underneath javelin frames so the AI-generated pose keeps GOLIATH's complete
silhouette even when one shoulder/arm is missing in the source.

Composition:
  result = phase1_idle_base (full body silhouette, gold/brown)
       + javelin_frame       (pose details: spear, raised arm, twist)

PIL.Image.alpha_composite(base, overlay) does exactly this: where the
overlay (javelin) is opaque its pixels win, where the overlay is
transparent the base shows through. So the missing-shoulder slots in
lopsided javelin poses get filled by phase1_idle's body.
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
OUT = ROOT / "Assets/sprites/bosses/goliath"
PLAYTEST = ROOT / "tools/playtest_out"

# Reference body silhouette: a phase1_idle pose where both shoulders,
# shield arm, spear arm and legs are all present (typical of frames 0/1/2).
REF_FRAME = "phase1_idle/frame_00.png"

# Animations to composite.
TARGETS = [
    "javelin",
    "laser",
    "purple_bullet",
    "death",
]


def composite_one(anim: str, idx: int) -> None:
    base = Image.open(OUT / REF_FRAME).convert("RGBA")
    src = Image.open(OUT / f"{anim}/frame_{idx:02d}.png").convert("RGBA")
    # Make sure they're the same size.
    if base.size != src.size:
        raise SystemExit(f"size mismatch: {REF_FRAME}={base.size} vs {anim}={src.size}")
    out = Image.alpha_composite(base, src)
    out.save(OUT / f"{anim}/frame_{idx:02d}.png")


def audit_opaque_diff(anim: str, idx: int) -> tuple[int, int, int]:
    """Return (base_opaque, src_opaque, composite_opaque)."""
    base = Image.open(OUT / REF_FRAME).convert("RGBA")
    src = Image.open(OUT / f"{anim}/frame_{idx:02d}.png").convert("RGBA")
    composite = Image.alpha_composite(base, src)
    def op(im):
        return sum(1 for px in im.split()[-1].getdata() if px > 10)
    return (op(base), op(src), op(composite))


if __name__ == "__main__":
    # PREVIEW first (do not mutate originals yet).
    # Show before/after for javelin/frame_03 — the worst offender.
    preview = Image.new("RGBA", (96 * 3 + 16, 80 + 24), (16, 16, 28, 255))
    base = Image.open(OUT / REF_FRAME).convert("RGBA")
    src = Image.open(OUT / "javelin/frame_03.png").convert("RGBA")
    comp = Image.alpha_composite(base, src)
    preview.paste(base, (4, 24), base)
    preview.paste(src, (4 + 96 + 8, 24), src)
    preview.paste(comp, (4 + 96 * 2 + 16, 24), comp)
    preview.save(PLAYTEST / "goliath_backplate_preview.png")
    print("wrote tools/playtest_out/goliath_backplate_preview.png")
    print("Layout: [phase1_idle] [javelin/frame_03 BEFORE] [composite AFTER]")
