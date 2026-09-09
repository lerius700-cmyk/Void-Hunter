"""Capture the BLOQUE 65 MINE-ASTEROID 4-state cycle for visual proof (BLOQUE 65).

This script produces 1 PNG that demonstrates the new 4-state
opening cycle (closed -> open1 -> open2 -> open3):

  tools/playtest_out/bloque_65_mine_asteroid_4_frames.png
  4 frames arranged horizontally: closed | open1 | open2 | open3.
  All sprites are 64x64 with transparent background (the open3
  is the user's new ship reference). Confirms the new 4-state
  cycle is wired up.

The MINE-ASTEROID closed frame is byte-equal to round.png
(perfect camo, BLOQUE 63 invariant preserved). The open1 and
open2 frames are AI-generated intermediates from BLOQUE 65. The
open3 frame is the user's new ship reference (BLOQUE 65 swap).

Usage:
    cd D:\\AI\\void-hunter
    .venv\\Scripts\\python.exe tools/capture/capture_bloque_65_mine_asteroid.py
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from PIL import Image

OUT_DIR = ROOT / "tools" / "playtest_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BG = (8, 8, 20)
SCALE = 4  # 4x nearest-neighbor upscale (matches BLOQUE 61-64 captures)
MINE_DIR = ROOT / "Assets" / "sprites" / "enemies" / "mine_asteroid"


def load_mine_frame(state: str, frame: int = 0) -> pygame.Surface:
    """Load a MINE-ASTEROID sprite for the given state + frame index.

    Uses the same layout the game runtime uses (animation_path
    property): enemies/mine_asteroid/<state>/frame_NN.png.

    BLOQUE 65: the 'open' directory now contains the new ship
    reference (open3 / terminal vulnerable state).
    """
    path = MINE_DIR / state / f"frame_{frame:02d}.png"
    with Image.open(path) as img:
        raw = img.tobytes()
        size = img.size
        mode = img.mode
    surf = pygame.image.fromstring(raw, size, mode)
    return surf


def upscale(surf: pygame.Surface, factor: int) -> pygame.Surface:
    return pygame.transform.scale(
        surf, (surf.get_width() * factor, surf.get_height() * factor),
    )


def render_4_state_cycle() -> None:
    """Render the 4-state cycle horizontally: closed | open1 | open2 | open3.

    Each frame is 64x64 with a 4x upscale = 256x256 visible.
    """
    surf = pygame.Surface((320, 480))
    surf.fill(BG)
    states = [
        ("closed", "closed\n(0s, immune)"),
        ("open1",  "open1  25% open\n(0.2s, vulnerable)"),
        ("open2",  "open2  75% open\n(0.2s, vulnerable)"),
        ("open",   "open3  fully open\n(terminal, fires 3 bullets)"),
    ]
    # Layout: 4 columns at y=180, evenly spaced across 320px width
    # Each column is 64*4=256px wide — too big. Use 2x upscale (128px) instead.
    local_scale = 2
    y = 180
    x_positions = [40, 108, 176, 244]
    # Title
    title_font = pygame.font.Font(None, 18)
    title = title_font.render(
        "BLOQUE 65: MINE-ASTEROID 4-state cycle (closed -> open1 -> open2 -> open3)",
        True, (255, 255, 255),
    )
    surf.blit(title, (10, 10))
    subtitle = pygame.font.Font(None, 12).render(
        "0.6s total opening (open1=0.2s, open2=0.2s, open3=indefinite). "
        "HP=3, 3 hits to destroy when vulnerable. has_opened=True at open3 (no re-open).",
        True, (200, 200, 200),
    )
    surf.blit(subtitle, (10, 30))
    for i, ((state, label), x) in enumerate(zip(states, x_positions)):
        sprite = load_mine_frame(state, 0)
        big = upscale(sprite, local_scale)
        w, h = big.get_size()
        surf.blit(big, (x - w // 2, y - h // 2))
        # Label below each sprite
        for j, line in enumerate(label.split("\n")):
            txt = pygame.font.Font(None, 11).render(line, True, (200, 200, 200))
            surf.blit(txt, (x - txt.get_width() // 2, y + h // 2 + 10 + j * 12))
        # Border
        pygame.draw.rect(surf, (100, 100, 100),
                         (x - w // 2 - 1, y - h // 2 - 1, w + 2, h + 2), 1)
    # Footer
    footer = pygame.font.Font(None, 11).render(
        "open3 reuses the legacy 'open/' directory (BLOQUE 65: new ship reference). "
        "open1 + open2 are AI-generated intermediates at 64x64.",
        True, (180, 180, 180),
    )
    surf.blit(footer, (10, 440))
    out = OUT_DIR / "bloque_65_mine_asteroid_4_frames.png"
    pygame.image.save(surf, str(out))
    print(f"saved {out}")


def main() -> int:
    render_4_state_cycle()
    print("\nDone. 1 BLOQUE 65 visual capture saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
