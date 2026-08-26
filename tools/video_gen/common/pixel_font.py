"""Minimal 5x7 pixel font for "VOID HUNTER" logo.

Hand-coded 5x7 bitmap font for the characters we need. Each character is
a list of 7 strings, where '#' is a lit pixel and ' ' is empty.

Used by the pixel-dissolve logo reveal effect.
"""
from __future__ import annotations
from typing import Final


# Each character: list of 7 rows, each row 5 chars wide.
# '#' = lit, ' ' = empty, '.' = optional / not used.
_FONT_5x7: Final[dict[str, list[str]]] = {
    " ": [
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
    ],
    "V": [
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        " # # ",
        "  #  ",
    ],
    "O": [
        " ### ",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        " ### ",
    ],
    "I": [
        " ### ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        " ### ",
    ],
    "D": [
        "#### ",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        "#### ",
    ],
    "H": [
        "#   #",
        "#   #",
        "#   #",
        "#####",
        "#   #",
        "#   #",
        "#   #",
    ],
    "U": [
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
        " ### ",
    ],
    "N": [
        "#   #",
        "##  #",
        "# # #",
        "# # #",
        "#  ##",
        "#   #",
        "#   #",
    ],
    "T": [
        "#####",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
    ],
    "E": [
        "#####",
        "#    ",
        "#    ",
        "#### ",
        "#    ",
        "#    ",
        "#####",
    ],
    "R": [
        "#### ",
        "#   #",
        "#   #",
        "#### ",
        "# #  ",
        "#  # ",
        "#   #",
    ],
    "P": [
        "#### ",
        "#   #",
        "#   #",
        "#### ",
        "#    ",
        "#    ",
        "#    ",
    ],
    "A": [
        " ### ",
        "#   #",
        "#   #",
        "#####",
        "#   #",
        "#   #",
        "#   #",
    ],
    "S": [
        " ####",
        "#    ",
        "#    ",
        " ### ",
        "    #",
        "    #",
        "#### ",
    ],
    "C": [
        " ####",
        "#    ",
        "#    ",
        "#    ",
        "#    ",
        "#    ",
        " ####",
    ],
    "Y": [
        "#   #",
        "#   #",
        " # # ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
    ],
    "K": [
        "#   #",
        "#  # ",
        "# #  ",
        "##   ",
        "# #  ",
        "#  # ",
        "#   #",
    ],
    "M": [
        "#   #",
        "## ##",
        "# # #",
        "#   #",
        "#   #",
        "#   #",
        "#   #",
    ],
    "L": [
        "#    ",
        "#    ",
        "#    ",
        "#    ",
        "#    ",
        "#    ",
        "#####",
    ],
    "G": [
        " ####",
        "#    ",
        "#    ",
        "# ###",
        "#   #",
        "#   #",
        " ####",
    ],
    "B": [
        "#### ",
        "#   #",
        "#   #",
        "#### ",
        "#   #",
        "#   #",
        "#### ",
    ],
    "F": [
        "#####",
        "#    ",
        "#    ",
        "#### ",
        "#    ",
        "#    ",
        "#    ",
    ],
    "W": [
        "#   #",
        "#   #",
        "#   #",
        "# # #",
        "# # #",
        "## ##",
        "#   #",
    ],
    "X": [
        "#   #",
        "#   #",
        " # # ",
        "  #  ",
        " # # ",
        "#   #",
        "#   #",
    ],
    "Z": [
        "#####",
        "    #",
        "   # ",
        "  #  ",
        " #   ",
        "#    ",
        "#####",
    ],
    "J": [
        "  ###",
        "   # ",
        "   # ",
        "   # ",
        "   # ",
        "#  # ",
        " ##  ",
    ],
    "Q": [
        " ### ",
        "#   #",
        "#   #",
        "#   #",
        "# # #",
        "#  # ",
        " ## #",
    ],
    ".": [
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "  #  ",
    ],
    ",": [
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "  #  ",
        " #   ",
    ],
    ":": [
        "     ",
        "  #  ",
        "     ",
        "     ",
        "     ",
        "  #  ",
        "     ",
    ],
    "!": [
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        "     ",
        "  #  ",
    ],
    "?": [
        " ### ",
        "#   #",
        "    #",
        "   # ",
        "  #  ",
        "     ",
        "  #  ",
    ],
    "1": [
        "  #  ",
        " ##  ",
        "  #  ",
        "  #  ",
        "  #  ",
        "  #  ",
        " ### ",
    ],
    "2": [
        " ### ",
        "#   #",
        "    #",
        "   # ",
        "  #  ",
        " #   ",
        "#####",
    ],
    "3": [
        " ####",
        "#   #",
        "    #",
        "  ## ",
        "    #",
        "#   #",
        " ####",
    ],
}


CHAR_W: Final = 5
CHAR_H: Final = 7


def get_char(ch: str) -> list[str] | None:
    """Get the 5x7 bitmap for a character (uppercase). Returns None if missing."""
    ch = ch.upper()
    if ch in _FONT_5x7:
        return _FONT_5x7[ch]
    return None


def text_bitmap(text: str) -> list[list[int]]:
    """Render text to a 2D bitmap (0/1). Each char is 5 wide, 1 col spacing between.

    Returns a list of rows, each row a list of 0/1 ints.
    """
    text = text.upper()
    # Calculate total width
    total_w = len(text) * CHAR_W + (len(text) - 1) * 1  # 1 col spacing between chars
    total_h = CHAR_H
    bitmap = [[0] * total_w for _ in range(total_h)]
    col = 0
    for ch in text:
        glyph = get_char(ch)
        if glyph is None:
            col += CHAR_W + 1
            continue
        for row in range(CHAR_H):
            for c in range(CHAR_W):
                if glyph[row][c] == "#":
                    bitmap[row][col + c] = 1
        col += CHAR_W + 1
    return bitmap


def text_dimensions(text: str) -> tuple[int, int]:
    """Return (width, height) of rendered text."""
    text = text.upper()
    w = len(text) * CHAR_W + max(0, (len(text) - 1) * 1)
    return (w, CHAR_H)
