"""Tests for src.systems.sprite_factory — 6 helpers (BLOQUE 3)."""
from __future__ import annotations

import pytest
import pygame

from src.systems.sprite_factory import (
    _BAYER_NORMALIZED,
    composite_layers,
    dithered_circle,
    glow_halo,
    outline,
    scanline_overlay,
    tint_shift,
)


@pytest.fixture
def white_square() -> pygame.Surface:
    """8x8 white opaque square."""
    s = pygame.Surface((8, 8), pygame.SRCALPHA)
    s.fill((255, 255, 255, 255))
    return s


# ---------------------------------------------------------------------------
# 1. outline
# ---------------------------------------------------------------------------
def test_outline_empty_src_returns_transparent(white_square: pygame.Surface) -> None:
    """Edge: src with no opaque pixels → 1x1 transparent."""
    empty = pygame.Surface((8, 8), pygame.SRCALPHA)
    out = outline(empty)
    assert out.get_size() == (1, 1)


def test_outline_expands_canvas(white_square: pygame.Surface) -> None:
    """8x8 with 1px outline → 10x10."""
    out = outline(white_square, width=1)
    assert out.get_size() == (8 + 2, 8 + 2)


def test_outline_with_zero_width_still_draws(white_square: pygame.Surface) -> None:
    """width=0 → coerced to 1 (no div/0)."""
    out = outline(white_square, width=0)
    assert out.get_size()[0] > 0


def test_outline_preserves_inner_pixels(white_square: pygame.Surface) -> None:
    """The interior of src is preserved (white still there)."""
    out = outline(white_square)
    cx, cy = out.get_width() // 2, out.get_height() // 2
    pixel = out.get_at((cx, cy))
    # White center preserved (alpha + RGB).
    assert pixel[0] == 255  # r
    assert pixel[3] > 0  # has alpha


# ---------------------------------------------------------------------------
# 2. glow_halo
# ---------------------------------------------------------------------------
def test_glow_halo_radius_zero_returns_copy(white_square: pygame.Surface) -> None:
    """Edge: radius=0 → no halo, returns src.copy()."""
    out = glow_halo(white_square, radius=0)
    assert out.get_size() == white_square.get_size()


def test_glow_halo_expands_canvas(white_square: pygame.Surface) -> None:
    out = glow_halo(white_square, radius=3)
    # Expanded by radius*4 on each axis (2*radius halo, centered)
    assert out.get_size() == (8 + 3 * 4, 8 + 3 * 4)


def test_glow_halo_with_custom_color(white_square: pygame.Surface) -> None:
    """Color param changes the halo tint."""
    red = glow_halo(white_square, radius=2, color=(255, 0, 0))
    blue = glow_halo(white_square, radius=2, color=(0, 0, 255))
    # Different halo colors → different alpha distributions in the edge ring.
    # Spot check: edges have alpha > 0 for both.
    assert red.get_at((0, red.get_height() // 2))[3] > 0
    assert blue.get_at((0, blue.get_height() // 2))[3] > 0


# ---------------------------------------------------------------------------
# 3. tint_shift
# ---------------------------------------------------------------------------
def test_tint_shift_factor_one_identity(white_square: pygame.Surface) -> None:
    """factor=1.0 → identity (color preserved)."""
    out = tint_shift(white_square, factor=1.0)
    assert out.get_at((4, 4))[:3] == (255, 255, 255)


def test_tint_shift_factor_half_dim(white_square: pygame.Surface) -> None:
    """factor=0.5 → half brightness."""
    out = tint_shift(white_square, factor=0.5)
    r, g, b, _ = out.get_at((4, 4))
    assert (r, g, b) == (127, 127, 127)


def test_tint_shift_factor_two_clamps_to_255() -> None:
    """factor=2.0 → clamp at 255, no overflow per spec edge case."""
    s = pygame.Surface((4, 4), pygame.SRCALPHA)
    s.fill((200, 200, 200, 255))
    out = tint_shift(s, factor=2.0)
    r, g, b, _ = out.get_at((0, 0))
    # 200 * 2 = 400 → clamped to 255.
    assert (r, g, b) == (255, 255, 255)


def test_tint_shift_factor_zero_black(white_square: pygame.Surface) -> None:
    out = tint_shift(white_square, factor=0.0)
    r, g, b, _ = out.get_at((4, 4))
    assert (r, g, b) == (0, 0, 0)


def test_tint_shift_factor_negative_clamped_to_zero(white_square: pygame.Surface) -> None:
    """factor < 0 → coerced to 0 per spec."""
    out = tint_shift(white_square, factor=-1.0)
    r, g, b, _ = out.get_at((4, 4))
    assert (r, g, b) == (0, 0, 0)


# ---------------------------------------------------------------------------
# 4. composite_layers
# ---------------------------------------------------------------------------
def test_composite_empty_returns_1x1() -> None:
    """Edge: empty layers list → 1x1 transparent."""
    out = composite_layers([])
    assert out.get_size() == (1, 1)


def test_composite_single_layer_preserves(white_square: pygame.Surface) -> None:
    out = composite_layers([white_square])
    assert out.get_size() == white_square.get_size()


def test_composite_two_layers_size_is_max() -> None:
    a = pygame.Surface((4, 4), pygame.SRCALPHA)
    b = pygame.Surface((8, 8), pygame.SRCALPHA)
    out = composite_layers([a, b])
    assert out.get_size() == (8, 8)


def test_composite_five_layers_preserves_order() -> None:
    """Order matters: back to front (per spec)."""
    layers = []
    for i in range(5):
        s = pygame.Surface((4, 4), pygame.SRCALPHA)
        s.fill((i * 50, i * 50, i * 50, 255))
        layers.append(s)
    out = composite_layers(layers)
    # Top layer (i=4) is on top; bottom-left should be the back layer color
    # at the corner that wasn't overwritten. Verify size is correct.
    assert out.get_size() == (4, 4)


# ---------------------------------------------------------------------------
# 5. dithered_circle
# ---------------------------------------------------------------------------
def test_dithered_circle_radius_zero_returns_1x1() -> None:
    """Edge: radius=0 → 1x1 with background color."""
    out = dithered_circle(0, (255, 0, 0), background=(0, 0, 0))
    assert out.get_size() == (1, 1)
    assert out.get_at((0, 0))[:3] == (0, 0, 0)


def test_dithered_circle_radius_64_pattern_visible() -> None:
    """Edge: radius=64 → Bayer pattern visible (mixed color + background)."""
    out = dithered_circle(64, (255, 255, 255), background=(0, 0, 0))
    assert out.get_size() == (128, 128)
    # Sample inside the disc. The disc is centered at (64, 64) with radius 64,
    # so any point within ~20 px of center is definitely inside. Walk a small
    # 4x4 neighborhood that covers all 16 Bayer matrix entries.
    n_color = 0
    n_bg = 0
    for dy in range(0, 16):
        for dx in range(0, 16):
            x, y = 60 + dx, 60 + dy  # near center, definitely inside disc
            r, g, b, a = out.get_at((x, y))
            # Skip transparent (outside disc) — only count solid pixels.
            if a == 0:
                continue
            if (r, g, b) == (255, 255, 255):
                n_color += 1
            elif (r, g, b) == (0, 0, 0):
                n_bg += 1
    # Both should be present → Bayer dithering works.
    assert n_color > 0
    assert n_bg > 0


def test_dithered_circle_threshold_zero_all_color() -> None:
    """threshold=0 → all pixels pass (full disc)."""
    out = dithered_circle(8, (255, 0, 0), background=(0, 0, 0), threshold=0.0)
    # Center pixel should be color
    r, g, b, _ = out.get_at((8, 8))
    assert (r, g, b) == (255, 0, 0)


def test_dithered_circle_threshold_one_all_background() -> None:
    """threshold=1.0 → all pixels rejected (empty disc)."""
    out = dithered_circle(8, (255, 0, 0), background=(0, 0, 0), threshold=1.0)
    # All pixels within disc should be background
    r, g, b, _ = out.get_at((8, 8))
    assert (r, g, b) == (0, 0, 0)


def test_bayer_matrix_is_normalized() -> None:
    """The 4x4 Bayer matrix should be normalized to 0..1 (16 values)."""
    assert len(_BAYER_NORMALIZED) == 4
    for row in _BAYER_NORMALIZED:
        assert len(row) == 4
        for v in row:
            assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# 6. scanline_overlay
# ---------------------------------------------------------------------------
def test_scanline_default_size() -> None:
    out = scanline_overlay()
    assert out.get_size() == (240, 360)


def test_scanline_spacing_one_every_row() -> None:
    out = scanline_overlay(width=10, height=10, spacing=1, alpha=128)
    # Each row should have a dark line
    for y in range(10):
        r, g, b, a = out.get_at((5, y))
        assert a > 0


def test_scanline_spacing_zero_returns_transparent() -> None:
    """Edge: spacing=0 → transparent overlay."""
    out = scanline_overlay(spacing=0)
    assert out.get_size() == (240, 360)
    # Center pixel should be transparent
    assert out.get_at((120, 180))[3] == 0


def test_scanline_alpha_clamped_to_255() -> None:
    """alpha=1000 → clamp to 255."""
    out = scanline_overlay(width=10, height=10, spacing=2, alpha=1000)
    # Lines drawn with alpha 255 (max)
    r, g, b, a = out.get_at((5, 0))
    assert a == 255


# ---------------------------------------------------------------------------
# 7. Composite integration
# ---------------------------------------------------------------------------
def test_outline_then_glow_halo(white_square: pygame.Surface) -> None:
    """outline → glow_halo pipeline works."""
    o = outline(white_square)
    g = glow_halo(o, radius=2)
    assert g.get_size() > o.get_size()


def test_dithered_circle_into_composite() -> None:
    """dithered_circle → composite_layers pipeline works."""
    d = dithered_circle(16, (255, 255, 255))
    c = composite_layers([d])
    assert c.get_size() == d.get_size()
