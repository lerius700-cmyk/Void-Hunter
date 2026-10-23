"""BLOQUE 66.6: Compute the actual centroid (cx, cy) of each javelin frame's
alpha-weighted silhouette and compare to the (48, 40) canvas anchor. This
shows whether the per-frame centroid compensation is meaningful or a no-op.
"""
from PIL import Image


def centroid(im: Image.Image) -> tuple[float, float, float]:
    a = im.split()[-1]
    w, h = im.size
    sx = sy = sa = 0
    for py in range(h):
        for px in range(w):
            al = a.getpixel((px, py))
            if al == 0:
                continue
            sa += al
            sx += px * al
            sy += py * al
    if sa == 0:
        return (48.0, 40.0, 0.0)
    return (sx / sa, sy / sa, sa)


for anim in ["phase1_idle", "javelin"]:
    print(f"\n=== {anim} ===")
    print("  frame  centroid_x  centroid_y  offset_to(48,40)  total_alpha")
    for i in range(10):
        p = f"Assets/sprites/bosses/goliath/{anim}/frame_{i:02d}.png"
        cx, cy, sa = centroid(Image.open(p).convert("RGBA"))
        dx = int(round(48 - cx))
        dy = int(round(40 - cy))
        print(f"  {i:02d}     {cx:7.2f}     {cy:7.2f}     ({dx:+3d}, {dy:+3d})    {sa:>9.0f}")
