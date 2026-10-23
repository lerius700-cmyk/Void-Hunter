"""BLOQUE 66.6 (v2): body backplate WITHOUT the head/helmet.

The v1 backplate included the helmet and flames, but when baked into
sprites where the AI's helmet was tilted to one side (e.g. javelin/frame_03
where the boss is leaning into the throw), the result read as TWO HEADS
stacked at slightly different positions. The user reports the boss is
"doubled / overlapped".

v2 keeps only the body silhouette BELOW the collar line (rows 25-72):
torso + legs + the bottom edge of the helmet visor. So when the AI
omits a shoulder/arm/leg in any pose, the backplate fills that gap
without painting a second helmet on top of the AI's tilted one.
"""
from PIL import Image
from pathlib import Path

ROOT = Path(".")
ASSETS = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
OUT = ASSETS / "_backplate" / "body.png"

THRESHOLD = 10
N_FRAMES = 10
# Crop band: from this row down, keep the stable body pixels; above,
# discard so the backplate does NOT include helmet/flames/head.
KEEP_FROM_ROW = 25  # inclusive; rows <25 (helmet/top of head) are dropped


def main() -> None:
    p1 = ASSETS / "phase1_idle"
    frames = [Image.open(p1 / f"frame_{i:02d}.png").convert("RGBA") for i in range(N_FRAMES)]
    w, h = frames[0].size
    counts = [[0] * h for _ in range(w)]
    for fr in frames:
        a = fr.split()[-1]
        for y in range(h):
            for x in range(w):
                if a.getpixel((x, y)) > THRESHOLD:
                    counts[x][y] += 1
    sample = frames[0].load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out_px = out.load()
    for y in range(h):
        if y < KEEP_FROM_ROW:
            continue
        for x in range(w):
            if counts[x][y] == N_FRAMES:
                out_px[x, y] = sample[x, y]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    op = sum(1 for px in out.split()[-1].getdata() if px > 10)
    print(f"backplate saved: {OUT} ({op} opaque pixels)")


if __name__ == "__main__":
    main()
