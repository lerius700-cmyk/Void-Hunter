"""Sprite factory — 6 helpers for pixel-art sprite construction.

Per GDD §3 SpriteFactory: outline, glow_halo, tint_shift, composite_layers,
dithered_circle, scanline_overlay. All helpers return a fresh Surface;
caller is responsible for caching if hot-path.

Description: pure functional helpers. Each takes a Surface (or builds one)
             and returns a new Surface. No state, no caching (caller-side
             LRU if needed).
Dependencies: pygame.
"""
from __future__ import annotations

import math
from typing import Sequence

import pygame

# ---------------------------------------------------------------------------
# Bayer 4x4 dithering matrix (GDD §7 reference; normalized to 0..1).
# Used by dithered_circle.
# ---------------------------------------------------------------------------
_BAYER_4X4: tuple[tuple[int, ...], ...] = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)
_BAYER_NORMALIZED: tuple[tuple[float, ...], ...] = tuple(
    tuple(v / 16.0 for v in row) for row in _BAYER_4X4
)


def outline(src: pygame.Surface, color: tuple[int, int, int] = (0, 0, 0),
            width: int = 1) -> pygame.Surface:
    """Add a 1px (or Npx) outline around the non-transparent pixels of src.

    Edge case: src with all-transparent pixels → return 1x1 transparent.
    """
    w, h = src.get_size()
    if width < 1:
        width = 1
    # Detect content bounding box; if empty, return tiny transparent.
    mask = pygame.mask.from_surface(src)
    if mask.count() == 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    out = pygame.Surface((w + width * 2, h + width * 2), pygame.SRCALPHA)
    # Render outline by stamping src at all 8 (or 4*N) directions.
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx == 0 and dy == 0:
                continue
            out.blit(src, (dx + width, dy + width), special_flags=pygame.BLEND_RGBA_ADD)
    # Tint the outline by drawing a colored border mask
    border_mask = pygame.mask.from_surface(out)
    border_surf = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    border_surf.set_colorkey((0, 0, 0, 0))
    # Paint the outline by drawing a colored frame on the silhouette.
    for x in range(out.get_width()):
        for y in range(out.get_height()):
            if border_mask.get_at((x, y)) and not (
                width <= x < w + width and width <= y < h + width
            ):
                border_surf.set_at((x, y), (*color, 255))
    out.blit(border_surf, (0, 0))
    # Composite the original on top.
    out.blit(src, (width, width))
    return out


def glow_halo(src: pygame.Surface, radius: int = 4,
              color: tuple[int, int, int] | None = None) -> pygame.Surface:
    """Wrap src in a soft glow halo.

    Edge case: radius=0 → return src unchanged.
    """
    if radius <= 0:
        return src.copy()
    w, h = src.get_size()
    out = pygame.Surface((w + radius * 4, h + radius * 4), pygame.SRCALPHA)
    cx, cy = out.get_width() // 2, out.get_height() // 2
    # Halo as concentric alpha-falloff circles.
    halo_color = color if color is not None else (255, 255, 255)
    for r in range(radius * 2, 0, -1):
        a = int(80 * (r / (radius * 2.0)))
        pygame.draw.circle(
            out,
            (*halo_color, a),
            (cx, cy),
            max(w, h) // 2 + r,
        )
    out.blit(src, (cx - w // 2, cy - h // 2))
    return out


def tint_shift(surface: pygame.Surface, factor: float) -> pygame.Surface:
    """Multiply each pixel by factor, clamped to 255.

    factor=1.0 → identity. factor=0.5 → half brightness. factor=2.0 clamps
    per spec (no overflow).
    """
    if factor < 0:
        factor = 0.0
    out = surface.copy()
    w, h = out.get_size()
    # Vectorized approach would be faster; for correctness, iterate.
    # Pygame 2.6 has surfarray but we stay stdlib-only per GDD §0.
    for x in range(w):
        for y in range(h):
            r, g, b, a = out.get_at((x, y))
            nr = min(255, int(r * factor))
            ng = min(255, int(g * factor))
            nb = min(255, int(b * factor))
            out.set_at((x, y), (nr, ng, nb, a))
    return out


def composite_layers(layers: Sequence[pygame.Surface]) -> pygame.Surface:
    """Stack layers back-to-front. Order matters per spec.

    Edge case: empty list → return 1x1 transparent.
    """
    if not layers:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    # Find bounding size
    max_w = max(layer.get_width() for layer in layers)
    max_h = max(layer.get_height() for layer in layers)
    out = pygame.Surface((max_w, max_h), pygame.SRCALPHA)
    for layer in layers:
        x = (max_w - layer.get_width()) // 2
        y = (max_h - layer.get_height()) // 2
        out.blit(layer, (x, y))
    return out


def dithered_circle(radius: int, color: tuple[int, int, int],
                    background: tuple[int, int, int] = (0, 0, 0),
                    threshold: float = 0.5) -> pygame.Surface:
    """Render a circle using Bayer 4x4 dithering.

    Edge case: radius=0 → 1x1 surface with the background color.
    Edge case: radius=64 → Bayer pattern clearly visible per spec.
    """
    if radius < 1:
        s = pygame.Surface((1, 1), pygame.SRCALPHA)
        s.fill((*background, 255))
        return s
    diameter = radius * 2
    out = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    for y in range(diameter):
        for x in range(diameter):
            # Distance from center
            dx = x - radius + 0.5
            dy = y - radius + 0.5
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= radius:
                # Bayer threshold at this pixel
                bx = x % 4
                by = y % 4
                bayer = _BAYER_NORMALIZED[by][bx]
                # threshold=0 → all color; threshold=1 → all background
                if bayer >= threshold:
                    out.set_at((x, y), (*color, 255))
                else:
                    out.set_at((x, y), (*background, 255))
    return out


def scanline_overlay(width: int = 240, height: int = 360,
                      spacing: int = 2, alpha: int = 60) -> pygame.Surface:
    """CRT-style horizontal scanlines.

    Edge case: spacing <= 0 → no scanlines (return transparent).
    Edge case: alpha > 255 → clamp.
    """
    if spacing <= 0:
        return pygame.Surface((width, height), pygame.SRCALPHA)
    if alpha > 255:
        alpha = 255
    out = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, spacing):
        pygame.draw.line(out, (0, 0, 0, alpha), (0, y), (width, y), 1)
    return out
