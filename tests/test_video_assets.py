"""BLOQUE 58.59: Video asset manifest + frame count tests.

Validates that:
- Assets/video/title/manifest.json and zoom/manifest.json exist + are valid JSON
- The frame_count declared in manifest matches the actual number of PNG files
- The dimensions declared match the actual frame dimensions
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest
from PIL import Image


# The test should pass in both dev and PyInstaller contexts
def _find_assets_dir() -> Path | None:
    """Mirror the _find_video_assets_dir logic in scenes.py (test version)."""
    import sys
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_p = Path(meipass)
        candidates.append(meipass_p / "Assets" / "video")
        candidates.append(meipass_p / "_internal" / "Assets" / "video")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).resolve().parent.parent
    candidates.append(exe_dir / "Assets" / "video")
    candidates.append(exe_dir / "_internal" / "Assets" / "video")
    candidates.append(exe_dir.parent / "Assets" / "video")
    for c in candidates:
        if c.is_dir():
            return c
    return None


@pytest.fixture(scope="module")
def video_assets_dir():
    path = _find_assets_dir()
    if path is None:
        pytest.skip("Assets/video/ not found (run from project root or .exe with bundle)")
    return path


def test_title_manifest_exists(video_assets_dir):
    p = video_assets_dir / "title" / "manifest.json"
    assert p.is_file(), f"Missing manifest: {p}"


def test_zoom_manifest_exists(video_assets_dir):
    p = video_assets_dir / "zoom" / "manifest.json"
    assert p.is_file(), f"Missing manifest: {p}"


def test_title_manifest_valid_json(video_assets_dir):
    p = video_assets_dir / "title" / "manifest.json"
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert "fps" in data
    assert "frame_count" in data
    assert "width" in data
    assert "height" in data
    assert data["fps"] == 30
    assert data["width"] == 240
    assert data["height"] == 360


def test_zoom_manifest_valid_json(video_assets_dir):
    p = video_assets_dir / "zoom" / "manifest.json"
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["fps"] == 30
    assert data["width"] == 240
    assert data["height"] == 360


def test_title_frame_count_matches_manifest(video_assets_dir):
    p = video_assets_dir / "title" / "manifest.json"
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    frames = list((video_assets_dir / "title" / "frames").glob("frame_*.png"))
    assert len(frames) == data["frame_count"], (
        f"Manifest says {data['frame_count']} frames but found {len(frames)} PNGs"
    )


def test_zoom_frame_count_matches_manifest(video_assets_dir):
    p = video_assets_dir / "zoom" / "manifest.json"
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    frames = list((video_assets_dir / "zoom" / "frames").glob("frame_*.png"))
    assert len(frames) == data["frame_count"], (
        f"Manifest says {data['frame_count']} frames but found {len(frames)} PNGs"
    )


def test_title_frames_are_correct_dimensions(video_assets_dir):
    """Every frame must be 240x360 RGBA."""
    p = video_assets_dir / "title" / "manifest.json"
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    w, h = data["width"], data["height"]
    # Spot check 5 frames
    frames = sorted((video_assets_dir / "title" / "frames").glob("frame_*.png"))
    indices = [0, len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4, len(frames) - 1]
    for i in indices:
        with Image.open(frames[i]) as im:
            assert im.size == (w, h), f"Frame {frames[i].name} is {im.size}, expected {(w, h)}"
            assert im.mode == "RGBA", f"Frame {frames[i].name} mode={im.mode}, expected RGBA"


def test_zoom_frames_are_correct_dimensions(video_assets_dir):
    """Every frame must be 240x360 RGBA."""
    p = video_assets_dir / "zoom" / "manifest.json"
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    w, h = data["width"], data["height"]
    frames = sorted((video_assets_dir / "zoom" / "frames").glob("frame_*.png"))
    indices = [0, len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4, len(frames) - 1]
    for i in indices:
        with Image.open(frames[i]) as im:
            assert im.size == (w, h), f"Frame {frames[i].name} is {im.size}, expected {(w, h)}"
            assert im.mode == "RGBA", f"Frame {frames[i].name} mode={im.mode}, expected RGBA"


def test_title_frames_are_nonzero(video_assets_dir):
    """Spot check that frames are not all-black (i.e. real content was rendered)."""
    frames = sorted((video_assets_dir / "title" / "frames").glob("frame_*.png"))
    # Check a frame at t=8s (demo phase) where ships + bullets are visible
    idx = min(240, len(frames) - 1)
    with Image.open(frames[idx]) as im:
        extrema = im.getextrema()
        # The 'max' channel should be > 0 (some pixel is non-black)
        max_channels = [e[1] for e in extrema]
        assert max(max_channels) > 50, (
            f"Frame {frames[idx].name} appears to be all-black "
            f"(max channel values: {max_channels})"
        )
