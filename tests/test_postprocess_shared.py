"""Tests for the reusable transparentize helpers in tools/redesign_ships.

BLOQUE 60: refactor _transparentize_damero_after_resize to accept a
distance_threshold parameter so tools/redesign_bosses/02_postprocess.py
can reuse it (default 70 for 32x32 ships, 90 for 96x80 bosses).

The module under test is loaded via importlib because the file is named
``02_postprocess.py`` (a script-style numeric prefix), and Python does
not allow importing modules whose names start with a digit. The plan's
literal import ``from tools.redesign_ships import _02_postprocess as pp``
cannot succeed, so we load the file by path instead. This preserves the
test intent (verify the function is importable, has a default
distance_threshold, and behaves correctly).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PIL import Image

# Load 02_postprocess.py by file path (its numeric prefix is not a
# valid Python module identifier).
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
_POSTPROCESS_PATH = (
    _PROJECT_ROOT / "tools" / "redesign_ships" / "02_postprocess.py"
)

_spec = importlib.util.spec_from_file_location(
    "_postprocess_shared", _POSTPROCESS_PATH
)
assert _spec is not None and _spec.loader is not None, (
    f"could not load spec for {_POSTPROCESS_PATH}"
)
pp = importlib.util.module_from_spec(_spec)
sys.modules["_postprocess_shared"] = pp
_spec.loader.exec_module(pp)


def test_transparentize_damero_exported():
    """The damero-cleaner must be importable as a module-level function
    so tools/redesign_bosses/02_postprocess.py can reuse it."""
    assert hasattr(pp, "_transparentize_damero_after_resize")
    assert callable(pp._transparentize_damero_after_resize)


def test_transparentize_damero_default_threshold_70():
    """Default distance threshold is 70 (BLOQUE 59 ships baseline)."""
    # Create a 32x32 image with mid-gray damero (R=G=B=120, alpha=255)
    im = Image.new("RGBA", (32, 32), (120, 120, 120, 255))
    out = pp._transparentize_damero_after_resize(im)
    # All 4 corners should be transparent (R=120, G=120, B=120, alpha=0)
    assert out.getpixel((0, 0)) == (120, 120, 120, 0)
    assert out.getpixel((31, 0)) == (120, 120, 120, 0)
    assert out.getpixel((0, 31)) == (120, 120, 120, 0)
    assert out.getpixel((31, 31)) == (120, 120, 120, 0)


def test_transparentize_damero_threshold_90_catches_more():
    """Larger threshold (90) must be accepted as a kwarg — this is the
    BLOQUE 60 contract for the bosses pipeline (96x80)."""
    im = Image.new("RGBA", (32, 32), (120, 120, 120, 255))
    # If the parameter isn't on the signature, this call raises TypeError.
    out70 = pp._transparentize_damero_after_resize(im, distance_threshold=70.0)
    out90 = pp._transparentize_damero_after_resize(im, distance_threshold=90.0)
    # Both should be fully transparent at 120-gray
    assert out70.getpixel((0, 0))[3] == 0
    assert out90.getpixel((0, 0))[3] == 0


def test_transparentize_preserves_saturated_colors():
    """Saturated (non-gray) pixels survive regardless of threshold."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    # Set center pixel to saturated blue (40, 80, 180)
    im.putpixel((16, 16), (40, 80, 180, 255))
    out = pp._transparentize_damero_after_resize(im, distance_threshold=70.0)
    assert out.getpixel((16, 16)) == (40, 80, 180, 255)


def test_transparentize_preserves_pure_white_hull():
    """Pure white (R=G=B=255) is NOT marked as background — the player
    ship has a white hull that must survive."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    im.putpixel((16, 16), (255, 255, 255, 255))
    out = pp._transparentize_damero_after_resize(im, distance_threshold=70.0)
    assert out.getpixel((16, 16)) == (255, 255, 255, 255)


def test_transparentize_preserves_pure_black_outlines():
    """Pure black (R=G=B=0) is NOT marked as background — ship outlines
    and engine cores must survive."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    im.putpixel((16, 16), (0, 0, 0, 255))
    out = pp._transparentize_damero_after_resize(im, distance_threshold=70.0)
    assert out.getpixel((16, 16)) == (0, 0, 0, 255)
