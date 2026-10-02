"""BLOQUE 73 Fase B+: generate weapon bullet sprites (16x16 PNGs).

Creates 4 procedural 16x16 pixel-art sprites, one per weapon pickup.
Locked palette per spec (8-bit feel, 3-4 shades per sprite):

  - bullet_thick.png  : chunky orange diamond (heavy shot)
  - bullet_laser.png  : elongated green beam segment (pierce)
  - bullet_flame.png  : round red-orange fire particle (cone)
  - bullet_double.png : wide cyan double-bar (parallel pair)

Generated with PIL (Pillow) — no AI, no manual pixel placement. Output
is locked to the existing palette so the sprites blend with the
8-bit pixelart rest of the game (vessel, asteroids, MINE camouflage).

Usage:
  .venv/Scripts/python.exe tools/weapon_assets/generate_bullets.py

Outputs 4 PNGs to Assets/sprites/weapons/. Idempotent — overwrites
existing files.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


# Output path: Assets/sprites/weapons/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "Assets" / "sprites" / "weapons"


def _new_canvas(size: int = 16) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a 16x16 RGBA canvas with full transparency."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _save(img: Image.Image, name: str) -> Path:
    """Save to OUTPUT_DIR/name.png."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{name}.png"
    img.save(path)
    print(f"  wrote {path.relative_to(REPO_ROOT)} ({path.stat().st_size} bytes)")
    return path


# ---------------------------------------------------------------------------
# THICK: chunky orange diamond with 4 shaded facets
# ---------------------------------------------------------------------------
def generate_thick() -> Path:
    """16x16 chunky diamond bullet (orange). 4 color stops + outline."""
    im, d = _new_canvas()
    # Outline (dark brown)
    OUT = (80, 40, 10, 255)
    # Bright fill (orange)
    BRIGHT = (255, 200, 80, 255)
    # Mid fill (orange)
    MID = (255, 160, 60, 255)
    # Shadow
    SHADOW = (200, 100, 30, 255)
    # Diamond shape: top apex at (8, 1), bottom at (8, 14), widest at row 8
    diamond = [(8, 1), (13, 4), (14, 8), (13, 12), (8, 14), (2, 12), (1, 8), (2, 4)]
    d.polygon(diamond, fill=MID, outline=OUT)
    # Bright facet (top-left)
    bright = [(8, 5), (10, 7), (8, 9), (6, 7)]
    d.polygon(bright, fill=BRIGHT)
    # Shadow facet (bottom-right)
    shadow = [(8, 9), (10, 7), (12, 9), (10, 11)]
    d.polygon(shadow, fill=SHADOW)
    return _save(im, "bullet_thick")


# ---------------------------------------------------------------------------
# LASER: elongated vertical beam (green)
# ---------------------------------------------------------------------------
def generate_laser() -> Path:
    """16x16 elongated laser beam (green). Tall narrow shape with glow."""
    im, d = _new_canvas()
    OUT = (20, 80, 30, 255)
    BRIGHT = (180, 255, 200, 255)
    MID = (80, 255, 120, 255)
    CORE = (220, 255, 240, 255)
    # Vertical beam: x=7..9, y=1..14
    d.rectangle((7, 1, 9, 14), fill=MID)
    # Bright center column
    d.rectangle((8, 1, 8, 14), fill=CORE)
    # Glow edges
    d.rectangle((6, 2, 10, 14), fill=BRIGHT)
    # Outline
    d.rectangle((7, 1, 9, 14), outline=OUT)
    # Tapered tip (top)
    d.point((8, 0), fill=CORE)
    d.point((8, 15), fill=CORE)
    return _save(im, "bullet_laser")


# ---------------------------------------------------------------------------
# FLAME: round fire spark (red-orange) with bright core
# ---------------------------------------------------------------------------
def generate_flame() -> Path:
    """16x16 round flame particle (red-orange). Small ball with hot core."""
    im, d = _new_canvas()
    OUT = (120, 30, 10, 255)
    BRIGHT = (255, 220, 100, 255)
    MID = (255, 100, 40, 255)
    SHADOW = (180, 50, 20, 255)
    # Round shape with 4 facets
    # Outer ring (8 corners at radius ~6)
    octagon = []
    import math
    for i in range(8):
        a = math.pi * 2 * i / 8 - math.pi / 8
        x = 8 + int(6 * math.cos(a))
        y = 8 + int(6 * math.sin(a))
        octagon.append((x, y))
    d.polygon(octagon, fill=MID, outline=OUT)
    # Bright top-left
    d.polygon([(8, 4), (10, 5), (10, 7), (8, 8), (6, 7), (6, 5)], fill=BRIGHT)
    # Shadow bottom-right
    d.polygon([(8, 8), (10, 9), (10, 11), (8, 12), (6, 11)], fill=SHADOW)
    # Core spark (1px bright)
    d.point((8, 6), fill=BRIGHT)
    return _save(im, "bullet_flame")


# ---------------------------------------------------------------------------
# DOUBLE: wide double-bar (cyan)
# ---------------------------------------------------------------------------
def generate_double() -> Path:
    """16x16 wide double-bar bullet (cyan). Two parallel vertical bars."""
    im, d = _new_canvas()
    OUT = (30, 80, 110, 255)
    BRIGHT = (180, 240, 255, 255)
    MID = (100, 220, 255, 255)
    CORE = (240, 250, 255, 255)
    # Two vertical bars at x=4..6 and x=10..12
    for bar_x in (4, 10):
        d.rectangle((bar_x, 2, bar_x + 2, 13), fill=MID)
        d.rectangle((bar_x + 1, 2, bar_x + 1, 13), fill=CORE)
        # Glow edge
        d.rectangle((bar_x - 1, 3, bar_x + 3, 12), fill=BRIGHT)
        d.rectangle((bar_x, 2, bar_x + 2, 13), outline=OUT)
        # Tapered tip
        d.point((bar_x + 1, 1), fill=CORE)
        d.point((bar_x + 1, 14), fill=CORE)
    return _save(im, "bullet_double")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print(f"Generating 4 weapon bullet sprites in {OUTPUT_DIR.relative_to(REPO_ROOT)}/")
    generate_thick()
    generate_laser()
    generate_flame()
    generate_double()
    print("Done. 4 sprites written.")


if __name__ == "__main__":
    main()