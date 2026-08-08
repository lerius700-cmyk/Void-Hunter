"""VOID HUNTER ASCII palette — 64 unique chars mapped to RGB.

8-bit aesthetic (Shovel Knight postmortem 2014: 54-color global palette is
standard; we go to 64 for the 6 themes × 10 accents + 4 universal). Each
char represents one color, indexed by sprite factory. The CHAR map is
append-only — never reorder, never delete. New colors go at the end with
a docstring entry below.

Categories (see GDD §8):
  - 12 Negros / Grises / Blancos  (background, stars, highlights)
  - 10 Rojos / Naranjas            (plasma, fire, danger, mars)
  - 10 Azules / Cyans              (ion, void, tech, teal)
  - 6  Verdes                      (UI, shields, health)
  - 8  Violetas / Magentas         (shock, dusk, special)
  - 6  Dorados / Amber             (act 3, score, rank)
  - 2  Pink                        (pink void theme)
                                   ─────
                                   64 chars
"""
from __future__ import annotations

# Universal transparency / neutrals (12)
PALETTE: dict[str, tuple[int, int, int]] = {
    " ": (0, 0, 0),          # transparent / void bg
    "░": (40, 40, 60),       # shadow soft
    "▒": (80, 80, 100),      # mid-gray outline shadow
    "▓": (120, 120, 140),    # light gray debris
    ".": (160, 160, 180),    # distant stars / dithered
    ":": (200, 200, 220),    # nearby stars / scanline
    "-": (220, 220, 240),    # metallic highlight
    "=": (240, 240, 255),    # ship base light
    "+": (255, 255, 255),    # pure white / beams / flash
    "*": (255, 240, 200),    # warm white / charge L3
    "~": (180, 200, 255),    # cool white / ion glow
    "^": (100, 100, 120),    # outline dark
    # Rojos / Naranjas (10)
    "r": (255, 60, 40),      # danger red / hit flash
    "R": (200, 40, 20),      # deep red / kamikaze glow
    "1": (255, 100, 40),     # plasma L1
    "2": (255, 140, 60),     # plasma L2
    "3": (255, 180, 80),     # plasma L3 / fire
    "4": (255, 220, 100),    # bright fire / muzzle
    "5": (255, 240, 140),    # yellow fire / sun
    "o": (180, 80, 40),      # mars accent
    "O": (220, 100, 40),     # mars highlight
    "p": (255, 80, 40),      # plasma special / kamikaze core
    # Azules / Cyans (10)
    "b": (40, 80, 180),      # blue void base
    "B": (80, 120, 220),     # blue void mid
    "c": (80, 200, 255),     # cyan ion L1
    "C": (120, 220, 255),    # cyan bright / ion L2
    "i": (40, 160, 220),     # ion trail
    "I": (100, 200, 240),    # ion highlight
    "t": (80, 220, 200),     # teal nebula
    "T": (140, 240, 220),    # teal highlight
    "n": (40, 60, 120),      # deep void
    "N": (80, 100, 180),     # mid void
    # Verdes (6)
    "g": (80, 200, 80),      # health / shield
    "G": (120, 240, 120),    # health highlight
    "e": (40, 160, 80),      # dark green / UI
    "E": (80, 200, 120),     # mid green
    "l": (180, 255, 120),    # lime / power-up P
    "L": (220, 255, 180),    # lime highlight
    # Violetas / Magentas (8)
    "v": (180, 80, 220),     # shock base
    "V": (220, 120, 255),    # shock highlight
    "m": (220, 80, 180),     # magenta / dusk
    "M": (255, 120, 200),    # magenta bright
    "d": (120, 80, 180),     # purple dusk base
    "D": (160, 100, 220),    # purple dusk mid
    "k": (80, 40, 120),      # deep dusk
    "K": (140, 80, 180),     # mid dusk
    # Dorados / Amber (6)
    "y": (255, 200, 80),     # gold / score popup
    "Y": (255, 220, 120),    # gold highlight
    "a": (220, 160, 60),     # amber
    "A": (255, 200, 100),    # amber bright
    "q": (180, 130, 40),     # dark gold
    "Q": (140, 100, 30),     # deep amber
    # Pink (2)
    "h": (255, 100, 180),    # pink void base
    "H": (255, 160, 220),    # pink void highlight
    # Accent extension (10) — high-saturation accents for power-ups, UI, and
    # unique enemy tints. Each one is unique (no collision with the 54 above).
    "0": (255, 60, 200),     # magenta-pink accent
    "6": (200, 255, 60),     # chartreuse
    "7": (60, 255, 200),     # mint
    "8": (100, 60, 255),     # deep blue-violet
    "9": (255, 100, 60),     # peach
    "j": (60, 100, 255),     # electric blue
    "J": (100, 160, 255),    # electric blue mid
    "f": (180, 60, 100),     # raspberry
    "x": (80, 200, 100),     # bright green
    "X": (160, 100, 60),     # copper
}

# Theme swatches — each theme overrides particle tints (GDD §8).
# Type is a Mapping because values are mixed: some single RGB, others tuples of RGB.
from typing import Any
THEMES: dict[str, dict[str, Any]] = {
    "blue_void": {
        "bg": (0, 0, 0),
        "nebula": ((40, 60, 120), (80, 100, 180), (40, 80, 180)),
        "stars": ((160, 160, 180), (200, 200, 220), (180, 200, 255)),
        "accent": (80, 200, 255),
        "particle_tint": (80, 200, 255),
    },
    "pink_void": {
        "bg": (0, 0, 0),
        "nebula": ((80, 40, 120), (120, 80, 180), (255, 100, 180)),
        "stars": ((160, 160, 180), (200, 200, 220), (180, 200, 255)),
        "accent": (255, 160, 220),
        "particle_tint": (255, 100, 180),
    },
    "mars": {
        "bg": (0, 0, 0),
        "nebula": ((180, 80, 40), (220, 100, 40), (255, 60, 40)),
        "stars": ((255, 220, 100), (255, 240, 140), (255, 240, 200)),
        "accent": (255, 180, 80),
        "particle_tint": (255, 140, 60),
    },
    "teal": {
        "bg": (0, 0, 0),
        "nebula": ((80, 220, 200), (140, 240, 220), (40, 80, 180)),
        "stars": ((160, 160, 180), (255, 255, 255), (180, 200, 255)),
        "accent": (140, 240, 220),
        "particle_tint": (80, 220, 200),
    },
    "purple_dusk": {
        "bg": (0, 0, 0),
        "nebula": ((80, 40, 120), (140, 80, 180), (120, 80, 180)),
        "stars": ((255, 255, 255), (255, 240, 200), (180, 200, 255)),
        "accent": (220, 120, 255),
        "particle_tint": (220, 120, 255),
    },
    "gold_amber": {
        "bg": (0, 0, 0),
        "nebula": ((180, 130, 40), (140, 100, 30), (220, 160, 60)),
        "stars": ((255, 220, 120), (255, 240, 200), (255, 255, 255)),
        "accent": (255, 200, 80),
        "particle_tint": (255, 200, 80),
    },
}

THEME_NAMES: tuple[str, ...] = (
    "blue_void", "pink_void", "mars", "teal", "purple_dusk", "gold_amber",
)


def get_palette() -> dict[str, tuple[int, int, int]]:
    """Return the global palette. Returns a copy to prevent mutation."""
    return dict(PALETTE)


def get_theme(name: str) -> dict[str, Any]:
    """Return the theme swatch. Falls back to blue_void if unknown."""
    return THEMES.get(name, THEMES["blue_void"])


def validate_palette_integrity() -> tuple[bool, str]:
    """Sanity check: exactly 64 chars, all unique, all RGB tuples in [0,255]."""
    if len(PALETTE) != 64:
        return False, f"palette has {len(PALETTE)} entries, expected 64"
    if len(set(PALETTE.keys())) != 64:
        return False, "duplicate chars in palette"
    for ch, rgb in PALETTE.items():
        if not isinstance(rgb, tuple) or len(rgb) != 3:
            return False, f"char {ch!r} has non-RGB-tuple color {rgb!r}"
        for component in rgb:
            if not 0 <= int(component) <= 255:
                return False, f"char {ch!r} color {rgb!r} out of [0,255]"
    return True, "ok"
