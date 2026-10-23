"""BLOQUE 66.6: build a "stable body silhouette" backplate from phase1_idle
by keeping only pixels that are opaque in 9/10 or all 10 of the frames.
That preserves the boss's torso, head, helmet and legs (which barely
move in idle) while dropping the spear (which is held at different
angles per frame).

Then composite the backplate UNDER each javelin / laser / purple_bullet /
death frame so the boss always carries his complete silhouette, even when
the AI-generated pose has gaps (javelin/frame_03 in particular, where the
right shoulder disappears into a wide-stance lateral swing).
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
ASSETS = ROOT / "Assets" / "sprites" / "bosses" / "goliath"


def make_backplate() -> Image.Image:
    p1 = ASSETS / "phase1_idle"
    frames = [
        Image.open(p1 / f"frame_{i:02d}.png").convert("RGBA")
        for i in range(10)
    ]
    w, h = frames[0].size
    # Count alpha > THRESHOLD per (x, y) across the 10 frames.
    THRESHOLD = 10  # alpha value above which a pixel counts as opaque
    STABLE_FRAMES = 10  # require opaque in ALL 10 frames to keep (drops spear)
    counts = [[0] * h for _ in range(w)]
    for fr in frames:
        a = fr.split()[-1]
        for y in range(h):
            for x in range(w):
                if a.getpixel((x, y)) > THRESHOLD:
                    counts[x][y] += 1
    # Take the colour from frame_00 (any frame works) wherever the count
    # passes the stability threshold, otherwise transparent.
    sample = frames[0].load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out_px = out.load()
    for y in range(h):
        for x in range(w):
            if counts[x][y] >= STABLE_FRAMES:
                out_px[x, y] = sample[x, y]
    return out


def composite_under(base: Image.Image, overlay_path: Path) -> Image.Image:
    overlay = Image.open(overlay_path).convert("RGBA")
    return Image.alpha_composite(base, overlay)


if __name__ == "__main__":
    backplate = make_backplate()
    out_png = ROOT / "tools/playtest_out/goliath_body_backplate.png"
    backplate.save(out_png)
    # Report opaque pixel count
    op = sum(1 for px in backplate.split()[-1].getdata() if px > 10)
    print(f"backplate opaque pixels: {op}")
    print(f"saved {out_png}")
    # Preview composite.
    canvas = Image.new("RGBA", (96 * 3 + 24, 80 + 24), (12, 12, 22, 255))
    big = lambda im: im.resize((96 * 3, 80 * 3), Image.NEAREST)
    b = big(backplate)
    src = Image.open(ASSETS / "javelin/frame_03.png").convert("RGBA")
    bk = big(src)
    co = big(Image.alpha_composite(backplate, src))
    canvas.paste(b, (4, 24), b)
    canvas.paste(bk, (4 + 96 * 3 + 8, 24), bk)
    canvas.paste(co, (4 + 96 * 6 + 16, 24), co)
    canvas.save(ROOT / "tools/playtest_out/goliath_backplate_fullbody_preview.png")
    print("wrote goliath_backplate_fullbody_preview.png")
    print("Layout: [STABLE BODY] [javelin/frame_03 raw] [COMPOSITE]")
