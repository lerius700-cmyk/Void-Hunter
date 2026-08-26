"""BLOQUE 58.59: VideoPlayer unit tests.

Validates the PNG-sequence VideoPlayer used by TitleScene (V1-G) and
CinematicScene (V2-G). Uses a temporary directory of generated PNG frames
to keep tests hermetic — no dependency on the committed frame assets.
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path

import pygame
import pytest

from src.ui.video_player import VideoPlayer


# Initialize pygame once for the test session
@pytest.fixture(scope="module", autouse=True)
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture
def fake_video_dir():
    """Create a temp directory with N fake frames + manifest.json."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        frames = d / "frames"
        frames.mkdir()
        # Generate 12 fake 8x8 RGBA PNG frames (red, green, blue cycling)
        n_frames = 12
        for i in range(n_frames):
            surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            color = ((i * 30) % 255, 128, 200, 255)
            surf.fill(color)
            pygame.image.save(surf, str(frames / f"frame_{i:04d}.png"))
        manifest = {
            "name": "test_video",
            "fps": 30,
            "frame_count": n_frames,
            "width": 8,
            "height": 8,
            "loop": True,
            "loop_start_frame": 4,
            "loop_end_frame": 11,
        }
        with (d / "manifest.json").open("w", encoding="utf-8") as f:
            json.dump(manifest, f)
        yield d


def test_loads_manifest(fake_video_dir):
    player = VideoPlayer(
        frames_dir=fake_video_dir / "frames",
        manifest_path=fake_video_dir / "manifest.json",
        loop=True,
    )
    player.play()
    assert player._fps == 30
    assert player._frame_count == 12
    assert player._src_w == 8
    assert player._src_h == 8
    assert player._loop is True


def test_initial_state_not_playing(fake_video_dir):
    player = VideoPlayer(
        frames_dir=fake_video_dir / "frames",
        manifest_path=fake_video_dir / "manifest.json",
    )
    # Before play(), not playing
    assert player.is_playing() is False
    assert player.is_finished() is False


def test_play_resets_to_frame_0(fake_video_dir):
    player = VideoPlayer(
        frames_dir=fake_video_dir / "frames",
        manifest_path=fake_video_dir / "manifest.json",
    )
    player.play()
    # Advance some frames
    for _ in range(3):
        player.update(1 / 30)
    assert player._frame_index > 0
    # play() resets
    player.play()
    assert player._frame_index == 0


def test_update_advances_one_frame_at_fps(fake_video_dir):
    player = VideoPlayer(
        frames_dir=fake_video_dir / "frames",
        manifest_path=fake_video_dir / "manifest.json",
        loop=False,
    )
    player.play()
    # Advance ~33ms (1 frame at 30 FPS)
    player.update(1 / 30)
    assert player._frame_index == 1
    # Advance another 33ms
    player.update(1 / 30)
    assert player._frame_index == 2


def test_loop_wraps_to_loop_start(fake_video_dir):
    """When loop=True and a loop_start_frame is set, the player should
    jump back to loop_start when reaching the end (not to 0)."""
    player = VideoPlayer(
        frames_dir=fake_video_dir / "frames",
        manifest_path=fake_video_dir / "manifest.json",
        loop=True,
    )
    player.play()
    # Set frame_index to loop_end - 1 and advance
    player._frame_index = player._loop_end - 1  # 10
    player.update(1 / 30)  # → 11 (loop_end)
    player.update(1 / 30)  # → loop_start (4)
    assert player._frame_index == player._loop_start


def test_non_loop_finishes_at_last_frame(fake_video_dir):
    player = VideoPlayer(
        frames_dir=fake_video_dir / "frames",
        manifest_path=fake_video_dir / "manifest.json",
        loop=False,
    )
    player.play()
    # Force to last frame
    player._frame_index = player._frame_count - 1
    player.update(1 / 30)  # → attempts to advance past end
    assert player.is_finished() is True
    assert player.is_playing() is False


def test_get_progress_0_to_1(fake_video_dir):
    player = VideoPlayer(
        frames_dir=fake_video_dir / "frames",
        manifest_path=fake_video_dir / "manifest.json",
        loop=False,
    )
    player.play()
    assert player.get_progress() == 0.0
    # Advance to half
    target = player._frame_count // 2
    for _ in range(target):
        player.update(1 / 30)
    # Progress should be roughly target / (frame_count - 1)
    assert 0.3 < player.get_progress() < 0.7


def test_draw_blits_to_target(fake_video_dir):
    """draw() should blit the current frame onto the target surface."""
    player = VideoPlayer(
        frames_dir=fake_video_dir / "frames",
        manifest_path=fake_video_dir / "manifest.json",
        scale_to_fit=True,
    )
    player.play()
    target = pygame.Surface((16, 16))
    target.fill((0, 0, 0))
    player.draw(target)
    # The target should now have a non-zero pixel from the source frame
    # (8x8 scaled to 16x16 means it fills the whole surface)
    arr = pygame.surfarray.array3d(target)
    assert (arr != 0).any(), "VideoPlayer did not blit to target"


def test_missing_assets_returns_none_via_builder(monkeypatch):
    """If Assets/video/ is missing, _build_video_player returns None.
    We test the indirect behavior via a fake empty path."""
    from src.ui import scenes
    # Monkey-patch _find_video_assets_dir to return None
    monkeypatch.setattr(scenes, "_find_video_assets_dir", lambda: None)
    result = scenes._build_video_player("nonexistent_subdir", loop=True)
    assert result is None
