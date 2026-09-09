"""Capture the BLOQUE 63 MINE-ASTEROID in its 4 states for visual proof.

This script produces 3 PNGs that prove the camouflage mechanic works:

  1. ``tools/playtest_out/bloque_63_mine_asteroid_closed.png``
     1 MINE-ASTEROID + 3 regular asteroids, ALL in closed state.
     The MINE-ASTEROID looks byte-equal to a round asteroid (perfect
     camo proof — user can't tell which is the threat).

  2. ``tools/playtest_out/bloque_63_mine_asteroid_open.png``
     1 MINE-ASTEROID in 'open' state, gun barrel clearly visible.
     The threat is revealed.

  3. ``tools/playtest_out/bloque_63_mine_asteroid_transition.png``
     1 MINE-ASTEROID in 'opening' OR 'closing' state, panels
     mid-animation.

All captures are 320x480 (internal playfield size) with a deep-space
background. Sprites are loaded from the new
``Assets/sprites/enemies/mine_asteroid/<state>/frame_NN.png`` paths.

Usage:
    cd D:\\AI\\void-hunter
    .venv\\Scripts\\python.exe tools/capture/capture_bloque_63_mine_asteroid.py
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

from src.entities.enemies.enemy import Enemy, EnemyKind
from src.entities.asteroid import Asteroid, draw_asteroid, _load_asteroid_sprite

OUT_DIR = ROOT / "tools" / "playtest_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BG = (8, 8, 20)
SCALE = 4  # 4x nearest-neighbor upscale (matches BLOQUE 61/62 captures)
MINE_DIR = ROOT / "Assets" / "sprites" / "enemies" / "mine_asteroid"


def load_mine_frame(state: str, frame: int = 0) -> pygame.Surface:
    """Load a MINE-ASTEROID sprite for the given state + frame index.

    Uses the same layout the game runtime uses (animation_path
    property): enemies/mine_asteroid/<state>/frame_NN.png.
    """
    path = MINE_DIR / state / f"frame_{frame:02d}.png"
    img = Image.open(path)
    # PIL: drop alpha-friendly to pygame with convert_alpha
    raw = img.tobytes()
    surf = pygame.image.fromstring(raw, img.size, img.mode)
    return surf


def upscale(surf: pygame.Surface, factor: int) -> pygame.Surface:
    return pygame.transform.scale(
        surf, (surf.get_width() * factor, surf.get_height() * factor),
        pygame.Surface,
    ) if False else pygame.transform.scale(
        surf, (surf.get_width() * factor, surf.get_height() * factor),
    )


def render_camouflage_proof() -> None:
    """Scene 1: 3 regular asteroids + 1 MINE-ASTEROID, all in closed state.
    The MINE-ASTEROID looks identical to the round asteroid (perfect camo).
    """
    surf = pygame.Surface((320, 480))
    surf.fill(BG)
    # Load sprites
    ast_round = _load_asteroid_sprite(0)  # variant 0 = round
    mine_closed = load_mine_frame("closed", 0)
    # Upscale for visibility (4x)
    ast_big = upscale(ast_round, SCALE)
    mine_big = upscale(mine_closed, SCALE)
    # Layout: 4 columns at y=180, evenly spaced
    y = 180
    positions = [(40, y), (108, y), (176, y), (244, y)]
    labels = ("asteroid 0", "asteroid 1", "MINE-ASTEROID (closed)", "asteroid 2")
    for i, (x, y) in enumerate(positions):
        sprite = mine_big if i == 2 else ast_big
        # Center the sprite on (x, y)
        w, h = sprite.get_size()
        surf.blit(sprite, (x - w // 2, y - h // 2))
    # Labels at the bottom
    font = pygame.font.Font(None, 14)
    label_y = 280
    for i, label in enumerate(labels):
        x, _ = positions[i]
        text = font.render(label, True, (200, 200, 200))
        surf.blit(text, (x - text.get_width() // 2, label_y))
    # Highlight (with an arrow / outline) to show which is the MINE-ASTEROID
    x, y = positions[2]
    w, h = mine_big.get_size()
    pygame.draw.rect(surf, (255, 255, 100),
                     (x - w // 2 - 2, y - h // 2 - 2, w + 4, h + 4), 1)
    label2 = font.render("^ threat ^", True, (255, 255, 100))
    surf.blit(label2, (x - label2.get_width() // 2, label_y + 18))
    # Title
    title_font = pygame.font.Font(None, 18)
    title = title_font.render(
        "BLOQUE 63: MINE-ASTEROID closed (indistinguishable from asteroid)",
        True, (255, 255, 255),
    )
    surf.blit(title, (10, 10))
    out = OUT_DIR / "bloque_63_mine_asteroid_closed.png"
    pygame.image.save(surf, str(out))
    print(f"saved {out}")


def render_open_state() -> None:
    """Scene 2: 1 MINE-ASTEROID in 'open' state, gun barrel visible."""
    surf = pygame.Surface((320, 480))
    surf.fill(BG)
    mine_open = load_mine_frame("open", 0)
    mine_big = upscale(mine_open, SCALE)
    x, y = 160, 200
    w, h = mine_big.get_size()
    surf.blit(mine_big, (x - w // 2, y - h // 2))
    font = pygame.font.Font(None, 18)
    title = font.render(
        "BLOQUE 63: MINE-ASTEROID open (gun barrel revealed)",
        True, (255, 100, 100),
    )
    surf.blit(title, (10, 10))
    label = pygame.font.Font(None, 14).render(
        "fires 3 bullets in ±15° fan, 80 px/s", True, (200, 200, 200),
    )
    surf.blit(label, (10, 30))
    out = OUT_DIR / "bloque_63_mine_asteroid_open.png"
    pygame.image.save(surf, str(out))
    print(f"saved {out}")


def render_transition_state() -> None:
    """Scene 3: 1 MINE-ASTEROID in 'opening' state (panels mid-open)."""
    surf = pygame.Surface((320, 480))
    surf.fill(BG)
    # Use the middle frame (frame_01) of the opening sequence
    mine_opening = load_mine_frame("opening", 1)
    mine_big = upscale(mine_opening, SCALE)
    x, y = 160, 200
    w, h = mine_big.get_size()
    surf.blit(mine_big, (x - w // 2, y - h // 2))
    font = pygame.font.Font(None, 18)
    title = font.render(
        "BLOQUE 63: MINE-ASTEROID opening transition (panels mid-split)",
        True, (255, 200, 100),
    )
    surf.blit(title, (10, 10))
    label = pygame.font.Font(None, 14).render(
        "0.5s opening -> 0.3s open (fires) -> 0.5s closing -> closed (no reopen)",
        True, (200, 200, 200),
    )
    surf.blit(label, (10, 30))
    out = OUT_DIR / "bloque_63_mine_asteroid_transition.png"
    pygame.image.save(surf, str(out))
    print(f"saved {out}")


def main() -> int:
    render_camouflage_proof()
    render_open_state()
    render_transition_state()
    print("\nDone. 3 BLOQUE 63 visual captures saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
