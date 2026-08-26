"""Extract key frames from a generated video for visual review.

Usage:
  python preview_frames.py <frames_dir> <output_dir> [n_keyframes]

Extracts the most important moments to PNGs so the user can review the
look without watching the full video.
"""
from __future__ import annotations
import sys
from pathlib import Path
from PIL import Image


# Key frame timestamps (in seconds) for V1 (12s total)
V1_KEYFRAMES_S = [
    0.0,    # frame 0 — black + stars
    1.0,    # ship silhouette entering
    2.0,    # V forming
    2.5,    # VOID complete
    3.0,    # HUNTER forming
    3.5,    # HUNTER complete
    4.0,    # logo settled
    5.0,    # ambient phase
    7.0,    # ambient phase late
    8.0,    # demo phase start
    10.0,   # demo phase mid
    11.5,   # demo phase late
]


# Key frame timestamps for V2 (10s total)
V2_KEYFRAMES_S = [
    0.0,    # ship close
    2.0,    # nebula starts
    3.5,    # asteroids start
    5.0,    # planet appears
    6.5,    # mid-dolly
    8.0,    # near gameplay
    9.5,    # final ease-out
]


def extract_keyframes(
    frames_dir: Path,
    output_dir: Path,
    keyframes_s: list[float],
    fps: int = 30,
    prefix: str = "v1",
) -> None:
    """Extract keyframes from a PNG sequence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for t in keyframes_s:
        frame_idx = int(t * fps)
        src = frames_dir / f"frame_{frame_idx:04d}.png"
        if not src.exists():
            print(f"  [skip] {src.name} not found")
            continue
        img = Image.open(src)
        out_name = f"{prefix}_t{t:.1f}s.png"
        # Upscale 2x for visibility
        img_big = img.resize((img.width * 2, img.height * 2), Image.Resampling.NEAREST)
        img_big.save(output_dir / out_name)
        print(f"  [ok] {out_name}  ({img.size} -> {img_big.size})")
    # Also extract a "loop seam" comparison: frames 357, 358, 359, 0, 1, 2 stacked
    if any(t >= 11.0 for t in keyframes_s):
        seam_frames = []
        for i in [357, 358, 359, 0, 1, 2]:
            src = frames_dir / f"frame_{i:04d}.png"
            if src.exists():
                seam_frames.append(Image.open(src))
        if len(seam_frames) == 6:
            w, h = seam_frames[0].size
            # Stack horizontally 6 frames at 2x scale
            scaled = [f.resize((w * 2, h * 2), Image.Resampling.NEAREST) for f in seam_frames]
            sw, sh = scaled[0].size
            composite = Image.new("RGBA", (sw * 6, sh), (0, 0, 0, 255))
            for j, sf in enumerate(scaled):
                composite.paste(sf, (j * sw, 0))
            composite.save(output_dir / f"{prefix}_loop_seam.png")
            print(f"  [ok] {prefix}_loop_seam.png  (frames 357-2 side by side)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    frames_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    fps = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    prefix = sys.argv[4] if len(sys.argv) > 4 else "v1"
    keyframes = V1_KEYFRAMES_S if prefix == "v1" else V2_KEYFRAMES_S
    extract_keyframes(frames_dir, output_dir, keyframes, fps, prefix)
