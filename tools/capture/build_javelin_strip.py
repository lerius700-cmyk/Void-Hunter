"""BLOQUE 66.6: build a 5x2 strip of the javelin frames with a 4x zoom so we
can SEE if anatomy is truncated or missing.
"""
from PIL import Image

ZOOM = 4
OUT = "tools/playtest_out/goliath_javelin_zoom_strip.png"


def load(anim: str, idx: int) -> Image.Image:
    p = f"Assets/sprites/bosses/goliath/{anim}/frame_{idx:02d}.png"
    return Image.open(p).convert("RGBA")


def build_strip(anim: str) -> Image.Image:
    cell_w, cell_h = 96, 80
    canvas_w = cell_w * 5 * ZOOM + 4 * 8 * ZOOM
    canvas_h = cell_h * 2 * ZOOM + 8 * ZOOM
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (20, 20, 28, 255))
    for idx in range(10):
        fr = load(anim, idx)
        # Magnify
        big = fr.resize((cell_w * ZOOM, cell_h * ZOOM), Image.NEAREST)
        row = idx // 5
        col = idx % 5
        x = col * (cell_w * ZOOM + 8 * ZOOM)
        y = row * (cell_h * ZOOM + 8 * ZOOM)
        canvas.paste(big, (x, y), big)
    # Grid overlay for visibility
    return canvas


if __name__ == "__main__":
    for a in ["phase1_idle", "javelin"]:
        out = f"tools/playtest_out/goliath_{a}_zoom_strip.png"
        strip = build_strip(a)
        strip.save(out)
        print(f"wrote {out} ({strip.size})")
