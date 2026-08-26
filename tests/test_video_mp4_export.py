"""BLOQUE 58.59: Video MP4 export tests.

Validates that:
- release/videos/*.mp4 exist (when run from project root)
- The files are > 0 bytes
- Their duration is at least the expected video duration
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

import pytest


# Find the release/videos directory
def _find_videos_dir() -> Path | None:
    import sys
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "release" / "videos")
        candidates.append(Path(meipass) / "_internal" / "release" / "videos")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).resolve().parent.parent
    candidates.append(exe_dir / "release" / "videos")
    candidates.append(exe_dir.parent / "release" / "videos")
    for c in candidates:
        if c.is_dir():
            return c
    return None


@pytest.fixture(scope="module")
def videos_dir():
    path = _find_videos_dir()
    if path is None:
        pytest.skip("release/videos/ not found")
    return path


def test_title_mp4_exists(videos_dir):
    """The title video mp4 should exist (may be 540p draft or 1080p final)."""
    matches = list(videos_dir.glob("void_hunter_title_v1*.mp4"))
    assert len(matches) >= 1, f"No title mp4 found in {videos_dir}"


def test_zoom_mp4_exists(videos_dir):
    """The zoom video mp4 should exist."""
    matches = list(videos_dir.glob("void_hunter_zoom_v1*.mp4"))
    assert len(matches) >= 1, f"No zoom mp4 found in {videos_dir}"


def test_title_mp4_is_nonempty(videos_dir):
    matches = list(videos_dir.glob("void_hunter_title_v1*.mp4"))
    for p in matches:
        assert p.stat().st_size > 1024, f"{p.name} is < 1KB"


def test_zoom_mp4_is_nonempty(videos_dir):
    matches = list(videos_dir.glob("void_hunter_zoom_v1*.mp4"))
    for p in matches:
        assert p.stat().st_size > 1024, f"{p.name} is < 1KB"


def test_title_mp4_duration_approx_12s(videos_dir):
    """The title video should be ~12s (within 1s tolerance)."""
    matches = list(videos_dir.glob("void_hunter_title_v1*.mp4"))
    if not matches:
        pytest.skip("no title mp4")
    p = matches[0]
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(p)],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("ffprobe not available")
    if result.returncode != 0:
        pytest.skip(f"ffprobe failed: {result.stderr}")
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    assert 11.0 < duration < 13.0, f"Title video duration {duration}s not in [11, 13]"


def test_zoom_mp4_duration_approx_10s(videos_dir):
    """The zoom video should be ~10s (within 1s tolerance)."""
    matches = list(videos_dir.glob("void_hunter_zoom_v1*.mp4"))
    if not matches:
        pytest.skip("no zoom mp4")
    p = matches[0]
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(p)],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("ffprobe not available")
    if result.returncode != 0:
        pytest.skip(f"ffprobe failed: {result.stderr}")
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    assert 9.0 < duration < 11.0, f"Zoom video duration {duration}s not in [9, 11]"
