"""BLOQUE 66.6: visual audit of GOLIATH javelin frames.

Reports each frame's alpha bounding box margins (how many transparent px
exist on each side of the silhouette inside the 96x80 canvas). Catches
both "anatomy clipped at the canvas edge" and "anatomy missing in the
middle" because we also report the count of opaque pixels per frame, so
a frame that has tiny opaque area (vs its neighbours) is a pose that the
AI drew thin instead of full.
"""
from PIL import Image

ANIMS = ["phase1_idle", "phase2_idle", "javelin", "laser", "purple_bullet", "death"]


def margins(path: str) -> tuple[int, int, int, int, int]:
    im = Image.open(path).convert("RGBA")
    a = im.split()[-1]
    bbox = a.getbbox()
    w, h = im.size
    if bbox is None:
        return (0, 0, 0, 0, 0)
    L, T, R, B = bbox
    op = sum(1 for px in a.getdata() if px > 10)
    return (L, T, w - R, h - B, op)


def report(anim: str) -> None:
    print(f"\n=== {anim} ===")
    print(f"  frame    L   R   T   B   opaque_px  comment")
    for i in range(10):
        path = f"Assets/sprites/bosses/goliath/{anim}/frame_{i:02d}.png"
        L, T, R, B, op = margins(path)
        flag = ""
        if min(L, R, T, B) <= 2:
            flag = "  <-- TIGHT EDGE"
        print(f"  {i:02d}    {L:>3} {R:>3} {T:>3} {B:>3}     {op:>5}{flag}")


if __name__ == "__main__":
    for a in ANIMS:
        report(a)
