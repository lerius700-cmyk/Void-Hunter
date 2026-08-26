"""Encode a directory of PNG frames to mp4 using ffmpeg.

Usage:
  python encode_mp4.py <frames_dir> <output_mp4> [width] [height] [fps]

Example:
  python encode_mp4.py output/frames/v1 output/v1.mp4 1080 1920 30
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def encode_mp4(
    frames_dir: Path,
    output_mp4: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    crf: int = 18,
) -> None:
    """Encode PNG sequence to H.264 mp4."""
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    # ffmpeg pattern: -i frame_%04d.png
    pattern = str(frames_dir / "frame_%04d.png")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", pattern,
        "-vf", f"scale={width}:{height}:flags=neighbor",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_mp4),
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg stderr:")
        print(result.stderr[-2000:])
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")
    size_mb = output_mp4.stat().st_size / 1024 / 1024
    print(f"  Done: {output_mp4}  ({size_mb:.2f} MB)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    frames_dir = Path(sys.argv[1])
    output_mp4 = Path(sys.argv[2])
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 1920
    fps = int(sys.argv[5]) if len(sys.argv) > 5 else 30
    encode_mp4(frames_dir, output_mp4, width, height, fps)
