"""Tests for the ship sprite redesign pipeline (BLOQUE 59)."""
from __future__ import annotations

import subprocess
from unittest import mock

from PIL import Image

from tools.redesign_ships._ai_client import generate_ship_base
from tools.redesign_ships._animation_frames import (
    generate_death_frames,
    generate_damage_frames,
    generate_idle_frames,
    generate_thrust_frames,
)
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
    test_img = Image.new("RGB", (4, 4))
    pixels = test_img.load()
    for x in range(4):
        for y in range(4):
            pixels[x, y] = (50, 100, 150)
    mapped = map_image_to_palette(test_img)
    assert mapped.size == (4, 4)
    mapped_pixels = mapped.load()
    palette_set = set(PALETTE.values())
    for x in range(4):
        for y in range(4):
            rgb = mapped_pixels[x, y]
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
    assert "mcode-tools" in cmd[0].lower()
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


# --- Animation frame tests (Task 4) ---

def _make_test_source(size: int = 32) -> Image.Image:
    """Create a 32x32 RGBA test source with a simple ship shape."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    # Draw a 12x8 ship in the center
    for x in range(10, 22):
        for y in range(12, 20):
            px[x, y] = (200, 200, 220, 255)
    # Engine glow at bottom
    for y in range(20, 24):
        px[14, y] = (255, 180, 80, 255)
        px[15, y] = (255, 180, 80, 255)
        px[16, y] = (255, 180, 80, 255)
        px[17, y] = (255, 180, 80, 255)
    return img


def test_generate_idle_frames_produces_10(tmp_path):
    src = _make_test_source()
    out_dir = tmp_path / "idle"
    frames = generate_idle_frames(src, out_dir)
    assert len(frames) == 10
    assert all(f.exists() for f in frames)
    for f in frames:
        with Image.open(f) as img:
            assert img.size == (32, 32)


def test_generate_thrust_frames_produces_10(tmp_path):
    src = _make_test_source()
    out_dir = tmp_path / "thrust"
    frames = generate_thrust_frames(src, out_dir)
    assert len(frames) == 10


def test_generate_damage_frames_produces_10(tmp_path):
    src = _make_test_source()
    out_dir = tmp_path / "damage"
    frames = generate_damage_frames(src, out_dir)
    assert len(frames) == 10


def test_generate_death_frames_produces_10(tmp_path):
    src = _make_test_source()
    out_dir = tmp_path / "death"
    frames = generate_death_frames(src, out_dir)
    assert len(frames) == 10


def test_idle_frame0_equals_frame9(tmp_path):
    """Idle loop must be seamless: frame 0 == frame 9."""
    src = _make_test_source()
    out_dir = tmp_path / "idle"
    frames = generate_idle_frames(src, out_dir)
    with Image.open(frames[0]) as f0, Image.open(frames[9]) as f9:
        assert list(f0.getdata()) == list(f9.getdata()), "idle loop seam not pixel-perfect"


def test_thrust_frame0_equals_frame9(tmp_path):
    """Thrust loop must be seamless (all frames are identical, so trivially equal)."""
    src = _make_test_source()
    out_dir = tmp_path / "thrust"
    frames = generate_thrust_frames(src, out_dir)
    with Image.open(frames[0]) as f0, Image.open(frames[9]) as f9:
        assert list(f0.getdata()) == list(f9.getdata()), "thrust loop seam not pixel-perfect"


# --- Enemy state machine tests (Task 6) ---

def test_enemy_animation_starts_idle():
    """A new enemy starts in idle state, frame 0."""
    from src.entities.enemies.enemy import Enemy, EnemyKind
    e = Enemy(kind=EnemyKind.SCOUT, x=0, y=0)
    e.on_spawn()
    assert e.animation_state == "idle"
    assert e.animation_frame == 0


def test_enemy_animation_frame_advances_on_tick():
    """Each tick advances the frame after ANIMATION_FRAME_DURATION seconds."""
    from src.entities.enemies.enemy import Enemy, EnemyKind
    e = Enemy(kind=EnemyKind.SCOUT, x=0, y=0)
    e.on_spawn()
    e.active = True
    e.update(dt=e.ANIMATION_FRAME_DURATION, player_x=160, player_y=240)
    assert e.animation_frame == 1
    # 9 more frames
    e.update(dt=e.ANIMATION_FRAME_DURATION * 9, player_x=160, player_y=240)
    assert e.animation_frame == 0  # wrapped (mod 10)


def test_enemy_damage_state_transitions():
    """A non-lethal hit transitions to 'damage' state."""
    from src.entities.enemies.enemy import Enemy, EnemyKind
    e = Enemy(kind=EnemyKind.SCOUT, x=0, y=0)
    e.on_spawn()
    e.active = True
    # Give it enough HP to survive 1 hit
    e.hp = 5
    e.apply_damage(1)
    assert e.animation_state == "damage"
    assert e.animation_frame == 0


def test_enemy_death_state_transitions():
    """A lethal hit transitions to 'death' state."""
    from src.entities.enemies.enemy import Enemy, EnemyKind
    e = Enemy(kind=EnemyKind.SCOUT, x=0, y=0)
    e.on_spawn()
    e.active = True
    e.hp = 1
    e.apply_damage(1)
    assert e.animation_state == "death"
    assert e.animation_frame == 0


def test_enemy_animation_path_format():
    """animation_path returns the expected relative path under Assets/sprites/."""
    from src.entities.enemies.enemy import Enemy, EnemyKind
    e = Enemy(kind=EnemyKind.SCOUT, x=0, y=0)
    e.on_spawn()
    assert e.animation_path == "enemies/scout/idle/frame_00.png"
    e.animation_state = "thrust"
    e.animation_frame = 5
    assert e.animation_path == "enemies/scout/thrust/frame_05.png"
    e.animation_state = "death"
    e.animation_frame = 9
    assert e.animation_path == "enemies/scout/death/frame_09.png"


def test_enemy_animation_resets_on_respawn():
    """on_spawn() resets the animation state to idle/0."""
    from src.entities.enemies.enemy import Enemy, EnemyKind
    e = Enemy(kind=EnemyKind.SCOUT, x=0, y=0)
    e.on_spawn()
    e.active = True
    e.animation_state = "death"
    e.animation_frame = 7
    e.on_spawn()
    assert e.animation_state == "idle"
    assert e.animation_frame == 0



