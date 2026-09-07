"""Tests for the ship sprite redesign pipeline (BLOQUE 59)."""
from __future__ import annotations

import subprocess
from unittest import mock

from PIL import Image

from tools.redesign_ships._ai_client import generate_ship_base
from tools.redesign_ships._palette_map import map_image_to_palette, nearest_palette_color
from src.utils.palette import PALETTE


def test_nearest_palette_color_returns_exact_match():
    """A color that's exactly in the palette returns itself."""
    palette_rgb = next(iter(PALETTE.values()))
    result = nearest_palette_color(palette_rgb)
    assert result == palette_rgb


def test_nearest_palette_color_finds_nearest():
    """A color near a palette entry returns that entry (Euclidean RGB)."""
    target = next(iter(PALETTE.values()))
    # Nudge each channel by +1
    near = (target[0] + 1, target[1] + 1, target[2] + 1)
    result = nearest_palette_color(near)
    assert result == target


def test_map_image_to_palette_uses_only_palette_colors():
    """Every pixel after mapping is within ±2 of a palette color."""
    # Create a small test image with random colors
    test_img = Image.new("RGB", (4, 4))
    pixels = test_img.load()
    for x in range(4):
        for y in range(4):
            pixels[x, y] = (50, 100, 150)  # arbitrary RGB
    mapped = map_image_to_palette(test_img)
    assert mapped.size == (4, 4)
    mapped_pixels = mapped.load()
    palette_set = set(PALETTE.values())
    for x in range(4):
        for y in range(4):
            rgb = mapped_pixels[x, y]
            # Check this pixel is within ±2 of some palette color
            found = False
            for p in palette_set:
                if all(abs(rgb[i] - p[i]) <= 2 for i in range(3)):
                    found = True
                    break
            assert found, f"pixel {rgb} not within ±2 of any palette color"


def test_generate_ship_base_invokes_mcode_tools(monkeypatch, tmp_path):
    """The wrapper calls mcode-tools with the right args and returns the node_id."""
    fake_response = '{"success_items": [{"node_id": "abc123", "file_name": "test.png"}]}'
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout=fake_response, stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    out_file = str(tmp_path / "out.png")
    node_id = generate_ship_base(
        prompt="16-bit pixel art spaceship",
        output_file=out_file,
    )
    assert node_id == "abc123"
    cmd = captured["cmd"]
    assert cmd[0] == "mcode-tools"
    assert cmd[1] == "connector"
    assert cmd[2] == "call"
    assert cmd[3] == "connector__matrix__generate_image"
    assert "--args" in cmd


def test_generate_ship_base_raises_on_no_success(monkeypatch):
    """If the response has no success_items, raise RuntimeError."""
    fake_response = '{"success_items": []}'

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=fake_response, stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    try:
        generate_ship_base(prompt="x", output_file="y.png")
    except RuntimeError as e:
        assert "no success_items" in str(e).lower()
    else:
        raise AssertionError("expected RuntimeError")

