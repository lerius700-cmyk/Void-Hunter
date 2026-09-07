"""Frame generation for the 4 ship animations (BLOQUE 59).

Each function takes a 32x32 RGBA source image and an output dir, generates
10 frames of one animation, and returns the list of frame paths in order.

idle: 1px Y bob + engine pulse, looped (frame 0 == frame 9)
thrust: 1px X forward lean + dilated engine, looped (frame 0 == frame 9)
damage: red flash + tilt ±1px, one-shot (no loop requirement)
death: expand + recolor + debris, one-shot (no loop requirement)
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image


# Colors used for the damage flash and death recolor
_RED_TINT = (255, 60, 40, 255)        # "r" in palette
_DEATH_TINT_1 = (255, 140, 60, 255)   # "2" in palette
_DEATH_TINT_2 = (255, 220, 100, 255)  # "4" in palette
_DEBRIS_COLOR = (120, 120, 140, 255)  # "▓" in palette


def _shift_image(img: Image.Image, dx: int, dy: int) -> Image.Image:
    """Return a new RGBA image with the source shifted by (dx, dy)."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (dx, dy), img)
    return out


def _tint_nontransparent(img: Image.Image, tint_rgba: tuple[int, int, int, int]) -> Image.Image:
    """Replace all non-transparent pixels with `tint_rgba`."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    src = img.load()
    dst = out.load()
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            r, g, b, a = src[x, y]
            if a > 0:
                dst[x, y] = tint_rgba
    return out


def _dilate_pixels(img: Image.Image, target_rgba: tuple[int, int, int, int], radius: int = 1) -> Image.Image:
    """Expand all pixels matching target_rgba by `radius` (cheap dilation)."""
    out = img.copy()
    src = img.load()
    dst = out.load()
    w, h = img.size
    matches: list[tuple[int, int]] = []
    for x in range(w):
        for y in range(h):
            if src[x, y] == target_rgba:
                matches.append((x, y))
    for x, y in matches:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] == 0:
                    dst[nx, ny] = target_rgba
    return out


def _write_frames(frames: list[Image.Image], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, frame in enumerate(frames):
        p = out_dir / f"frame_{i:02d}.png"
        frame.save(p)
        paths.append(p)
    return paths


def generate_idle_frames(source: Image.Image, out_dir: Path) -> list[Path]:
    """10 frames: 1px Y bob, frame 0 == frame 9 for seamless loop.

    Y bob uses sin(i * 2*pi/10) for a smooth oscillation that returns to 0
    at i=0 and i=10 (frame 9 has dy near 0 too).
    """
    frames: list[Image.Image] = []
    for i in range(10):
        dy = round(math.sin(i * 2 * math.pi / 10) * 1)  # 0,1,1,0,-1,-1,0,1,1,0
        if i == 9:
            dy = 0  # force seamless loop
        frames.append(_shift_image(source, 0, dy))
    return _write_frames(frames, out_dir)


def generate_thrust_frames(source: Image.Image, out_dir: Path) -> list[Path]:
    """10 frames: 1px X forward lean + dilated engine, frame 0 == frame 9.

    The engine dilation is applied to ALL 10 frames identically so the
    loop is pixel-perfect (frame 0 == frame 9). The "thrust" effect is
    the static lean + dilated engine; the engine doesn't pulse frame-to-frame
    because a 10-frame pulse cycle that returns to its start in 10 frames
    is mathematically impossible without stutter.
    """
    # Engine targets: orange/yellow palette entries likely used by AI
    engine_targets = [
        (255, 180, 80, 255),  # "3" plasma L3 / fire
        (255, 140, 60, 255),  # "2" plasma L2
        (255, 220, 100, 255), # "4" bright fire
        (255, 240, 140, 255), # "5" yellow fire
    ]
    # Build a "thrust pose" once: lean + dilated engine
    leaned = _shift_image(source, 1, 0)
    for target in engine_targets:
        leaned = _dilate_pixels(leaned, target, radius=1)
    # All 10 frames are the same image (loop is trivially seamless)
    frames = [leaned.copy() for _ in range(10)]
    return _write_frames(frames, out_dir)


def generate_damage_frames(source: Image.Image, out_dir: Path) -> list[Path]:
    """10 frames: red flash + tilt left then right, one-shot."""
    frames: list[Image.Image] = []
    for i in range(10):
        if i < 4:
            # Tilt left, red flash
            shifted = _shift_image(source, -1, 0)
            frames.append(_tint_nontransparent(shifted, _RED_TINT))
        elif i < 7:
            # Tilt right, red flash
            shifted = _shift_image(source, 1, 0)
            frames.append(_tint_nontransparent(shifted, _RED_TINT))
        else:
            # Return to rest
            frames.append(source.copy())
    return _write_frames(frames, out_dir)


def generate_death_frames(source: Image.Image, out_dir: Path) -> list[Path]:
    """10 frames: expanding recolor + debris, one-shot."""
    frames: list[Image.Image] = []
    w, h = source.size
    for i in range(10):
        if i == 0:
            frames.append(source.copy())
        elif i < 4:
            # Scale 1.2x, orange tint
            scaled = source.resize((int(w * 1.2), int(h * 1.2)), Image.NEAREST)
            canvas = Image.new("RGBA", source.size, (0, 0, 0, 0))
            canvas.paste(scaled, ((w - scaled.size[0]) // 2, (h - scaled.size[1]) // 2), scaled)
            frames.append(_tint_nontransparent(canvas, _DEATH_TINT_1))
        elif i < 7:
            # Scale 1.5x, yellow tint, add 4 debris pixels
            scaled = source.resize((int(w * 1.5), int(h * 1.5)), Image.NEAREST)
            canvas = Image.new("RGBA", source.size, (0, 0, 0, 0))
            canvas.paste(scaled, ((w - scaled.size[0]) // 2, (h - scaled.size[1]) // 2), scaled)
            canvas = _tint_nontransparent(canvas, _DEATH_TINT_2)
            for dx, dy in [(2, 28), (28, 2), (5, 25), (25, 5)]:
                if 0 <= dx < w and 0 <= dy < h:
                    canvas.putpixel((dx, dy), _DEBRIS_COLOR)
            frames.append(canvas)
        else:
            # Mostly transparent, gray specks
            canvas = Image.new("RGBA", source.size, (0, 0, 0, 0))
            for dx, dy in [(8, 24), (24, 8), (12, 28), (28, 12), (16, 26)]:
                if 0 <= dx < w and 0 <= dy < h:
                    canvas.putpixel((dx, dy), _DEBRIS_COLOR)
            frames.append(canvas)
    return _write_frames(frames, out_dir)
