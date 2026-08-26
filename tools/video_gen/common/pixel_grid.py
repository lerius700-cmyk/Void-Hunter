"""Pixel grid enforcement — keeps generated frames consistent with the game's 8-bit aesthetic.

Strategy: downscale to a low-res reference, then upscale with NEAREST. This forces
the image into a regular grid where every "pixel" is the same size, removing
sub-pixel artifacts and anti-aliasing that AI tools tend to leave behind.
"""
from __future__ import annotations
from PIL import Image


def enforce_pixel_grid(
    img: Image.Image,
    target_w: int,
    target_h: int,
    ref_w: int | None = None,
    ref_h: int | None = None,
) -> Image.Image:
    """Force the image into a strict pixel grid at (target_w, target_h).

    - If ref_w/ref_h not provided, defaults to target_w/target_h (no downscale).
    - When ref is smaller than target, the image is downscaled to (ref_w, ref_h)
      using LANCZOS (for clean averaging of neighboring source pixels), then
      upscaled with NEAREST to (target_w, target_h). The NEAREST upscale is what
      makes the pixel grid "snap" — every source pixel becomes a uniform block.

    Args:
        img: source image (any mode; alpha preserved)
        target_w, target_h: final output size
        ref_w, ref_h: optional "internal" reference resolution. If smaller than
                      target, the image will be downscaled to this then upscaled
                      with NEAREST. Useful for 1080×1920 outputs that should
                      "feel" like 240×360 pixel art (i.e. 4.5× super-sampling).
    """
    if ref_w is None:
        ref_w = target_w
    if ref_h is None:
        ref_h = target_h

    # Downscale to reference resolution (preserves alpha)
    if (img.width, img.height) != (ref_w, ref_h):
        img = img.resize((ref_w, ref_h), Image.Resampling.LANCZOS)

    # Upscale to target with NEAREST to enforce pixel grid
    if (ref_w, ref_h) != (target_w, target_h):
        img = img.resize((target_w, target_h), Image.Resampling.NEAREST)

    return img


def pixel_size_for_canvas(canvas_w: int, canvas_h: int, target_pixel_size: int = 4) -> tuple[int, int]:
    """Compute reference resolution so that each "logical pixel" is target_pixel_size
    source pixels. E.g. canvas 1080×1920 with target_pixel_size=4 → ref 270×480.

    Returns (ref_w, ref_h).
    """
    return (canvas_w // target_pixel_size, canvas_h // target_pixel_size)
