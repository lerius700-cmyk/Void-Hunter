"""Pixel-art effects: glow halos, scanlines, chromatic aberration, starfield, etc.

All functions operate on PIL.Image. Most return new images; some mutate in place
and return the same image (documented inline).
"""
from __future__ import annotations
import random
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from . import palette


# ----- STARFIELD -----

def make_starfield(
    width: int,
    height: int,
    count: int = 120,
    rng: random.Random | None = None,
    bg_color: tuple[int, int, int] = palette.BLACK,
) -> Image.Image:
    """Create a starfield background. Stars are 1-2 px, with subtle color variation."""
    if rng is None:
        rng = random.Random()
    img = Image.new("RGB", (width, height), bg_color)
    arr = np.array(img)
    for _ in range(count):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        roll = rng.random()
        if roll < 0.05:
            color = palette.STAR_WHITE
        elif roll < 0.20:
            color = rng.choice([palette.STAR_PALE, palette.STAR_BLUE, palette.STAR_PINK])
        else:
            color = palette.STAR_PALE
        arr[y, x] = color
    return Image.fromarray(arr)


def make_parallax_starfield(
    width: int,
    height: int,
    count: int = 80,
    scroll_offset: int = 0,
    rng: random.Random | None = None,
) -> Image.Image:
    """Starfield where scroll_offset moves the field vertically (top→bottom scroll)."""
    if rng is None:
        rng = random.Random()
    img = Image.new("RGB", (width, height), palette.BLACK)
    arr = np.array(img)
    for _ in range(count):
        x = rng.randint(0, width - 1)
        base_y = rng.randint(0, height - 1)
        y = (base_y + scroll_offset) % height
        roll = rng.random()
        if roll < 0.10:
            color = palette.STAR_WHITE
        elif roll < 0.30:
            color = rng.choice([palette.STAR_PALE, palette.STAR_BLUE])
        else:
            color = (60, 70, 90)
        arr[y, x] = color
    return Image.fromarray(arr)


# ----- GLOW / HALO -----

def add_glow_halo(
    img: Image.Image,
    color: tuple[int, int, int] = palette.NEON_CYAN,
    intensity: float = 0.6,
    blur_radius: int = 8,
) -> Image.Image:
    """Add a soft neon glow over the bright pixels of the image. intensity 0..1.

    Vectorized using numpy — fast even at 1080×1920.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.array(img, dtype=np.float32)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    brightness = r + g + b
    mask = (brightness > 90) & (a > 100)
    # Build glow layer
    glow = np.zeros_like(arr)
    glow[mask, 0] = color[0]
    glow[mask, 1] = color[1]
    glow[mask, 2] = color[2]
    glow[mask, 3] = 255 * intensity
    glow_img = Image.fromarray(glow.astype(np.uint8), mode="RGBA")
    # Blur the glow
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    glow_arr = np.array(glow_img, dtype=np.float32) / 255.0
    # Composite: glow behind, original on top (additive-ish, controlled by glow alpha)
    out_arr = arr.copy()
    # Add glow contribution
    glow_alpha = glow_arr[..., 3:4]  # HxWx1
    glow_rgb = glow_arr[..., :3]
    out_arr[..., :3] = np.clip(out_arr[..., :3] * (1 - glow_alpha * 0.3) + glow_rgb * glow_alpha, 0, 255)
    return Image.fromarray(out_arr.astype(np.uint8), mode="RGBA")


def glow_rect(
    target: Image.Image,
    xy: tuple[int, int, int, int],
    color: tuple[int, int, int],
    thickness: int = 1,
    outer_glow: int = 4,
    intensity: float = 0.7,
) -> None:
    """Draw a rectangle with a soft outer neon glow. Mutates target in place."""
    glow_layer = Image.new("RGBA", target.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    for i in range(outer_glow, 0, -1):
        alpha = int(255 * intensity * (i / outer_glow) * 0.4)
        gd.rectangle(xy, outline=color + (alpha,), width=thickness + i * 2)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=outer_glow // 2 + 1))
    target.alpha_composite(glow_layer)
    draw = ImageDraw.Draw(target)
    draw.rectangle(xy, outline=color, width=thickness)


# ----- CHROMATIC ABERRATION -----

def chromatic_aberration(
    img: Image.Image,
    offset: int = 2,
) -> Image.Image:
    """Shift the red channel by +offset and blue by -offset. Returns new image."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.array(img)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    h, w = arr.shape[:2]
    r_shifted = np.zeros_like(r)
    b_shifted = np.zeros_like(b)
    # Shift R right
    if offset > 0:
        r_shifted[:, offset:] = r[:, :-offset]
    else:
        r_shifted[:, :offset] = r[:, -offset:]
    # Shift B left
    if offset > 0:
        b_shifted[:, :-offset] = b[:, offset:]
    else:
        b_shifted[:, -offset:] = b[:, :offset]
    out = np.stack([r_shifted, g, b_shifted, a], axis=-1)
    return Image.fromarray(out, mode="RGBA")


# ----- SCANLINES -----

def add_scanlines(
    img: Image.Image,
    spacing: int = 2,
    alpha: int = 50,
) -> Image.Image:
    """Add subtle horizontal scanlines (1px dark every `spacing` rows)."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.array(img)
    arr[::spacing, :, 3] = np.where(
        arr[::spacing, :, 3] > alpha,
        arr[::spacing, :, 3] - alpha,
        0,
    )
    return Image.fromarray(arr, mode="RGBA")


# ----- VIGNETTE -----

def add_vignette(
    img: Image.Image,
    strength: float = 0.4,
) -> Image.Image:
    """Add a soft dark vignette around the edges. strength 0..1."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    # Build a radial mask using numpy
    y_grid, x_grid = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
    max_r = np.sqrt(cx ** 2 + cy ** 2)
    # Normalize and apply strength
    mask = np.clip((dist / max_r) ** 2, 0, 1) * strength
    arr = np.array(img, dtype=np.float32)
    arr[..., :3] = arr[..., :3] * (1 - mask[..., None] * 0.7)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGBA")
