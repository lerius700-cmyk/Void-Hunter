"""Capture the 8 BLOQUE 62 ships in a 4x2 grid for visual verification.

Renders the player ship + 7 enemies, idle frame at 4x scale, in a
4-column x 2-row grid with labels, and saves the result to
``tools/playtest_out/bloque_62_8_ships.png``.

Visual goals (BLOQUE 62):
  - All ships have NOSE on the correct side (DOWN for enemies, UP for player)
  - Consistent top-down perspective (no 3/4 angle, no side-view)
  - Same eye-level across all 8 ships
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
pygame.display.set_mode((640, 360))

# 7 enemy kinds + 1 player. Order matches _ship_specs.SHIPS (with player last).
ENEMY_KINDS = (
    "scout",
    "drone",
    "kamikaze",
    "sniper",
    "turret",
    "heavy",
    "cruiser",
)
PLAYER_KIND = "ship_01"

FRAME_SIZE = 32
SCALE = 4  # 4x nearest-neighbor upscale
CELL_W = FRAME_SIZE * SCALE  # 128
CELL_H = FRAME_SIZE * SCALE
COLS = 4
ROWS = 2
LABEL_H = 16
PADDING = 8

GRID_W = COLS * CELL_W + (COLS + 1) * PADDING
GRID_H = ROWS * (CELL_H + LABEL_H) + (ROWS + 1) * PADDING
SURF_W = GRID_W
SURF_H = GRID_H

# Dark space background
BG_COLOR = (10, 8, 24)
LABEL_BG = (24, 20, 36)
LABEL_COLOR = (200, 220, 255)
BORDER_COLOR = (60, 50, 80)

PLAYER_DIR = ROOT / "Assets" / "sprites" / "player_ships" / "ship_01" / "idle"
ENEMY_DIR = ROOT / "Assets" / "sprites" / "enemies"
OUT_PATH = ROOT / "tools" / "playtest_out" / "bloque_62_8_ships.png"


def _load_frame(path: Path) -> pygame.Surface | None:
    if not path.is_file():
        return None
    img = pygame.image.load(str(path)).convert_alpha()
    if img.get_size() != (FRAME_SIZE, FRAME_SIZE):
        img = pygame.transform.scale(img, (FRAME_SIZE, FRAME_SIZE))
    return img


def _load_font(size: int) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("consola", size)
    except Exception:
        return pygame.font.Font(None, size)


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    surf = pygame.Surface((SURF_W, SURF_H))
    surf.fill(BG_COLOR)
    font = _load_font(14)

    # Layout: 4 cols x 2 rows. Cells:
    #   [0] scout      [1] drone      [2] kamikaze   [3] sniper
    #   [4] turret     [5] heavy      [6] cruiser    [7] ship_01 (player)
    cells: list[tuple[str, Path]] = []
    for kind in ENEMY_KINDS:
        cells.append((kind, ENEMY_DIR / kind / "idle" / "frame_00.png"))
    cells.append((PLAYER_KIND, PLAYER_DIR / "frame_00.png"))

    missing: list[str] = []
    for idx, (label, frame_path) in enumerate(cells):
        col = idx % COLS
        row = idx // COLS
        x0 = PADDING + col * (CELL_W + PADDING)
        y0 = PADDING + row * (CELL_H + LABEL_H + PADDING)
        # Cell border
        pygame.draw.rect(
            surf, BORDER_COLOR,
            (x0, y0, CELL_W, CELL_H + LABEL_H), width=1,
        )
        # Frame
        img = _load_frame(frame_path)
        if img is None:
            missing.append(label)
            text = font.render(f"MISSING", True, (255, 80, 80))
            surf.blit(text, (x0 + 8, y0 + 8))
        else:
            scaled = pygame.transform.scale(
                img, (CELL_W, CELL_H)
            ) if img.get_size() != (CELL_W, CELL_H) else img
            surf.blit(scaled, (x0, y0))
        # Label
        text = font.render(label, True, LABEL_COLOR)
        surf.blit(text, (x0 + 4, y0 + CELL_H + 2))

    pygame.image.save(surf, str(OUT_PATH))
    print(f"saved {OUT_PATH}")
    if missing:
        print(f"WARNING: missing frames: {missing}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
