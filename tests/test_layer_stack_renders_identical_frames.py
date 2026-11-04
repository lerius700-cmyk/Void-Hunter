"""BLOQUE 75 Fase 2: the proof. The frame must not change by a pixel.

The golden frames were captured from the runtime BEFORE the LayerStack
existed (Task 1). After the refactor, every one of them must be
PIXEL-IDENTICAL. This is the only thing that proves checkpoint 2A: the
frame loop was reorganised into layers without changing what is drawn.

The sixth frame (`shake`) is the one the five originals could NOT prove:
their screen shake truncates to (0, 0), so the layers that consume the
shake were never exercised by the committed set. A regression in the
shake plumbing would have left all of them identical.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tools" / "golden" / "layerstack"
HARNESS = ROOT / "tools" / "capture" / "layerstack_frames.py"


@pytest.fixture(scope="module")
def display():
    """A video mode: `Surface.convert_alpha()` needs one.

    The comparison is done in THIS process, so the frame has to be
    loadable here -- and loading it with an alpha channel needs the
    display format, which needs an initialized video mode.
    """
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


@pytest.mark.parametrize(
    "name",
    ("enemies", "boss", "mine_open", "firing", "hud", "shake"),
)
def test_the_frame_is_pixel_identical(tmp_path, name, display):
    if not (GOLDEN / f"{name}.png").is_file():
        pytest.skip(f"no golden frame for {name}")
    proc = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--out",
            str(tmp_path),
            "--only",
            name,
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    golden = pygame_pixels(GOLDEN / f"{name}.png")
    current = pygame_pixels(tmp_path / f"{name}.png")
    assert golden == current, (
        f"{name}: the frame changed -- "
        f"{sum(1 for a, b in zip(golden, current) if a != b)} differing pixels"
    )


def pygame_pixels(path: Path):
    """The frame's pixels as a flat tuple of RGB triples."""
    import pygame

    surf = pygame.image.load(str(path)).convert_alpha()
    return tuple(surf.get_at((x, y))[:3] for y in range(surf.get_height())
                 for x in range(surf.get_width()))
