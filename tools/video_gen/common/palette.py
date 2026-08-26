"""PALETTE_VOID — neon cyan/magenta/rose palette tuned for the Void Hunter aesthetic.

References:
- ship_01_base.png  (cyan Arwing)
- "Keep Kept" image (neon cyberpunk humanoid, cyan/magenta/pink)
- galaxy_pixelart_violet.png (purple nebula base)

All colors are 8-bit RGB tuples. Use PALETTE_VOID["key"] access.
"""
from __future__ import annotations
from typing import Final


# Background / space
BLACK: Final = (0, 0, 0)
DEEP_VOID: Final = (5, 5, 14)
NIGHT_PURPLE: Final = (12, 8, 32)
DARK_INDIGO: Final = (24, 18, 56)

# Stars
STAR_WHITE: Final = (255, 255, 255)
STAR_PALE: Final = (210, 220, 240)
STAR_BLUE: Final = (140, 180, 255)
STAR_PINK: Final = (255, 180, 220)

# Neon — cyan family
NEON_CYAN: Final = (100, 230, 255)
NEON_CYAN_BRIGHT: Final = (180, 250, 255)
NEON_CYAN_DIM: Final = (40, 130, 180)
NEON_CYAN_DARK: Final = (16, 60, 100)

# Neon — magenta/pink family
NEON_MAGENTA: Final = (255, 80, 200)
NEON_MAGENTA_BRIGHT: Final = (255, 160, 230)
NEON_MAGENTA_DIM: Final = (170, 40, 130)
NEON_PINK: Final = (255, 130, 180)
NEON_HOT_PINK: Final = (255, 70, 130)

# Neon — purple/violet
NEON_PURPLE: Final = (160, 80, 240)
NEON_PURPLE_BRIGHT: Final = (200, 140, 255)
NEON_VIOLET: Final = (120, 60, 200)

# Engine flame
FLAME_YELLOW: Final = (255, 220, 100)
FLAME_ORANGE: Final = (255, 160, 50)
FLAME_RED: Final = (255, 80, 40)

# Generic ship accents
SHIP_GREY: Final = (90, 100, 120)
SHIP_LIGHT: Final = (200, 220, 240)
SHIP_DARK: Final = (40, 50, 70)


PALETTE_VOID: Final[dict[str, tuple[int, int, int]]] = {
    "black": BLACK,
    "deep_void": DEEP_VOID,
    "night_purple": NIGHT_PURPLE,
    "dark_indigo": DARK_INDIGO,
    "star_white": STAR_WHITE,
    "star_pale": STAR_PALE,
    "star_blue": STAR_BLUE,
    "star_pink": STAR_PINK,
    "neon_cyan": NEON_CYAN,
    "neon_cyan_bright": NEON_CYAN_BRIGHT,
    "neon_cyan_dim": NEON_CYAN_DIM,
    "neon_cyan_dark": NEON_CYAN_DARK,
    "neon_magenta": NEON_MAGENTA,
    "neon_magenta_bright": NEON_MAGENTA_BRIGHT,
    "neon_magenta_dim": NEON_MAGENTA_DIM,
    "neon_pink": NEON_PINK,
    "neon_hot_pink": NEON_HOT_PINK,
    "neon_purple": NEON_PURPLE,
    "neon_purple_bright": NEON_PURPLE_BRIGHT,
    "neon_violet": NEON_VIOLET,
    "flame_yellow": FLAME_YELLOW,
    "flame_orange": FLAME_ORANGE,
    "flame_red": FLAME_RED,
    "ship_grey": SHIP_GREY,
    "ship_light": SHIP_LIGHT,
    "ship_dark": SHIP_DARK,
}


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert '#RRGGBB' to (r, g, b)."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Linear interpolate between two RGB colors. t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
