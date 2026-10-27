"""BLOQUE 74: the repair pass must be deterministic and idempotent.

Mirroring is the repair for a turned-around character. It must flip the
sprite inside its own canvas (not move it), and it must leave every other
frame byte-identical.

The flip itself is an INVOLUTION -- mirroring twice restores the original
pixels. What is idempotent is the repair PASS: it only acts on a
LADO_EQUIVOCADO finding, and once the frame has been mirrored the next
audit finds none, so a second `--fix` changes nothing.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline.repair import mirror_frame  # noqa: E402


def test_mirror_flips_the_pixels(tmp_path):
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    surf.set_at((10, 10), (255, 0, 0, 255))
    pygame.image.save(surf, str(path))

    assert mirror_frame(path) is True

    after = pygame.image.load(str(path)).convert_alpha()
    assert after.get_at((85, 10)) == (255, 0, 0, 255)
    assert after.get_at((10, 10))[3] == 0


def test_mirror_is_an_involution(tmp_path):
    """Mirroring twice restores the original pixels.

    The flip is its own inverse -- that is a property of the primitive, not
    a bug. What is idempotent is the REPAIR PASS: it only acts on a
    LADO_EQUIVOCADO finding, and once the frame has been mirrored the next
    audit finds none, so the second run does nothing.
    """
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    surf.set_at((10, 10), (255, 0, 0, 255))
    pygame.image.save(surf, str(path))

    mirror_frame(path)
    once = pygame.image.load(str(path)).convert_alpha()
    mirror_frame(path)
    twice = pygame.image.load(str(path)).convert_alpha()

    assert once.get_at((85, 10)) == (255, 0, 0, 255)
    assert twice.get_at((10, 10)) == (255, 0, 0, 255)
    assert twice.get_at((85, 10))[3] == 0


def test_mirror_keeps_the_canvas_size(tmp_path):
    path = tmp_path / "frame_00.png"
    surf = pygame.Surface((96, 80), pygame.SRCALPHA, 32)
    surf.fill((0, 0, 0, 0))
    pygame.image.save(surf, str(path))

    mirror_frame(path)
    after = pygame.image.load(str(path)).convert_alpha()
    assert after.get_size() == (96, 80)
