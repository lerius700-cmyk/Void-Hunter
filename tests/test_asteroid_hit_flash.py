"""BLOQUE 71: Asteroid hit_timer and flash render."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from src.entities.asteroid import Asteroid, draw_asteroid_with_hit_flash
from src.core.settings import HIT_FLASH_DURATION_S


def _make_asteroid() -> Asteroid:
    return Asteroid(x=160, y=240, radius=24, variant=0, scale=1.0)


def test_asteroid_hit_sets_hit_timer():
    ast = _make_asteroid()
    assert ast.hit_timer == 0.0
    result = ast.hit(damage=1)
    assert result is False
    assert ast.hit_timer == HIT_FLASH_DURATION_S


def test_asteroid_hit_timer_decrements():
    ast = _make_asteroid()
    ast.hit()
    initial = ast.hit_timer
    ast.update(dt=0.05)
    assert ast.hit_timer == pytest.approx(initial - 0.05)


def test_asteroid_hit_timer_reaches_zero():
    ast = _make_asteroid()
    ast.hit()
    ast.update(dt=HIT_FLASH_DURATION_S + 0.01)
    assert ast.hit_timer == 0.0


def test_asteroid_indestructible_always_returns_false():
    ast = _make_asteroid()
    for _ in range(5):
        assert ast.hit(damage=99) is False
    assert ast.active is True  # still alive


def test_draw_asteroid_with_hit_flash_does_not_crash():
    pygame.init()
    # dummy driver requires a display set_mode before pygame.image.load
    # (the brief's "no crash even if sprite missing" note assumes fallback;
    #  in this env the sprite exists, so we need a display for image.load)
    pygame.display.set_mode((320, 480))
    target = pygame.Surface((320, 480))
    ast = _make_asteroid()
    ast.hit()
    # Should not raise even if sprite is missing
    draw_asteroid_with_hit_flash(target, ast)
    pygame.quit()


def test_asteroid_flash_preserves_shape_at_70_percent_opacity():
    """BLOQUE 71.1: the hit flash should be SHAPE-AWARE (follow the
    asteroid's silhouette, not a square) at 70% opacity, so the original
    sprite is visible underneath (not replaced with pure white).
    """
    from src.entities.asteroid import _load_asteroid_sprite
    from src.core.settings import HIT_FLASH_OPACITY
    assert HIT_FLASH_OPACITY == 0.70  # the new default

    pygame.init()
    pygame.display.set_mode((320, 480))
    target = pygame.Surface((320, 480))
    target.fill((0, 0, 0))
    ast = _make_asteroid()
    ast.hit()
    draw_asteroid_with_hit_flash(target, ast)

    # The asteroid is at (160, 240). Find a pixel where the original
    # sprite is opaque AND not pure white. The flash should preserve
    # the original color (just lighter), not make it pure (255,255,255).
    sprite = _load_asteroid_sprite(ast.variant)
    sw, sh = sprite.get_size()
    cx, cy = 160, 240
    found_sprite_pixel = False
    for dx in range(sw):
        for dy in range(sh):
            r, g, b, a = sprite.get_at((dx, dy))
            if a == 0:
                continue
            if r == 255 and g == 255 and b == 255:
                continue
            # Found a non-white opaque sprite pixel
            tx = cx - sw // 2 + dx
            ty = cy - sh // 2 + dy
            tr, tg, tb, _ta = target.get_at((tx, ty))[:4]
            # The flash should NOT make this pixel pure white. With 70%
            # opacity overlay on a non-white sprite, the result is a
            # blend (e.g., the original color shifted toward white but
            # not pure white). If the pixel IS pure white, the original
            # sprite is not visible — that means the flash is 100%
            # opaque (the OLD broken behavior).
            assert not (tr == 255 and tg == 255 and tb == 255), (
                f"BLOQUE 71.1 violation: flash made pixel ({tx}, {ty}) pure white. "
                f"Expected 70% overlay (original sprite visible at 30%). "
                f"Original sprite pixel was RGB({r},{g},{b})."
            )
            found_sprite_pixel = True
            break
        if found_sprite_pixel:
            break

    if not found_sprite_pixel:
        pytest.skip("All asteroid sprite pixels are white; cannot verify flash")

    pygame.quit()


def test_asteroid_flash_uses_helper_from_asteroid_module():
    """BLOQUE 71.1: the helper `_build_white_flash_overlay` should be
    importable from src.entities.asteroid and should return a surface
    whose non-transparent pixels are white-tinted at 70% alpha.
    """
    from src.entities.asteroid import _build_white_flash_overlay
    from src.core.settings import HIT_FLASH_OPACITY

    pygame.init()
    # Build a 4x4 SRCALPHA sprite with one opaque red pixel and one transparent pixel
    sprite = pygame.Surface((4, 4), pygame.SRCALPHA)
    sprite.set_at((0, 0), (255, 0, 0, 255))  # red, fully opaque
    sprite.set_at((1, 0), (0, 0, 0, 0))      # transparent

    overlay = _build_white_flash_overlay(sprite, HIT_FLASH_OPACITY)
    r, g, b, a = overlay.get_at((0, 0))
    # The overlay should be white at this pixel
    assert r == 255 and g == 255 and b == 255, "Overlay should be white where sprite is opaque"
    # The alpha should be 70% of the original alpha
    assert a == int(255 * 0.7), f"Overlay alpha should be ~178, got {a}"

    r, g, b, a = overlay.get_at((1, 0))
    # Transparent pixel in the original should be transparent in the overlay
    assert a == 0, f"Overlay should be transparent where sprite is transparent, got alpha={a}"
    pygame.quit()
