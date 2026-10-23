"""BLOQUE 66.6: bake the body backplate into every GOLIATH AI frame at
the PNG level, so the runtime doesn't need a separate backplate layer.

Approach:
  composite = PIL.Image.alpha_composite(backplate, src_frame)

The backplate fills in any transparent pixels in the AI frame. For AI
frames where the AI drew a complete silhouette (the majority), the
backplate adds nothing visible. For lopsided poses (javelin/frame_03
where the right shoulder/arm is missing), the backplate restores those
pixels so the silhouette reads as complete.

Why not a runtime backplate layer? Because centroid compensation shifts
the sprite by 20+ px from the world anchor (e.g. javelin/frame_03 has
dx=+20). If the runtime drew backplate at the world anchor and sprite
at the offset blit, the user would see two overlapping bodies — the
backplate stayed put while the sprite shifted. By baking the backplate
into the source PNG instead, the modified frame IS the body, no
overlay maths needed.

Process:
  1. Read phase1_idle/frame_*.png and compute the alpha-stable
     intersection as before (already saved at
     Assets/sprites/bosses/goliath/_backplate/body.png).
  2. For every javelin / laser / purple_bullet / death frame, do
     alpha_composite(backplate, frame) and overwrite the source PNG.
  3. Skip phase1_idle and phase2_idle (their bodies are already correct
     and re-compositing could degrade colour matching).
"""
from pathlib import Path
from PIL import Image

ROOT = Path(".")
ASSETS = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
BACKPLATE_PATH = ASSETS / "_backplate" / "body.png"
TARGETS = ["javelin", "laser", "purple_bullet", "death"]


def main() -> None:
    backplate = Image.open(BACKPLATE_PATH).convert("RGBA")
    print(f"backplate opaque pixels: "
          f"{sum(1 for px in backplate.split()[-1].getdata() if px > 10)}")
    total_modified = 0
    for anim in TARGETS:
        anim_dir = ASSETS / anim
        for i in range(10):
            p = anim_dir / f"frame_{i:02d}.png"
            src = Image.open(p).convert("RGBA")
            composite = Image.alpha_composite(backplate, src)
            # Only write if the result is actually different (skip frames
            # that already have the backplate baked in, e.g. on re-run).
            if composite.tobytes() != src.tobytes():
                composite.save(p)
                total_modified += 1
    print(f"frames re-baked: {total_modified}")


if __name__ == "__main__":
    main()
