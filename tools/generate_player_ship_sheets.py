"""BLOQUE 58.14: generate player ship sprite sheets.

Loads 5 AI-generated base sprites (Assets/sprites/player_ships/ship_NN_base.png)
and procedurally generates 5 animations × 8 frames for each = 200 PNGs.

Animations:
  - idle:        vertical bob (sin wave, 1 full cycle = 8 frames)
  - rotating:    8 rotation angles (0°, 45°, ..., 315°)
  - propulsion:  animated flame at the back
  - charging:    growing charge glow around the front
  - damage:      red flicker overlay (alternating)

Layout:
  Assets/sprites/player_ships/
    ship_01_base.png            (5 unique base sprites, AI-generated)
    ship_01/
      idle/frame_00.png ... frame_07.png
      rotating/frame_00.png ... frame_07.png
      propulsion/frame_00.png ... frame_07.png
      charging/frame_00.png ... frame_07.png
      damage/frame_00.png ... frame_07.png
    ship_02/... (same)
    ...

Usage:
    python tools/generate_player_ship_sheets.py
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import pygame  # noqa: E402

SHIPS_DIR = ROOT / "Assets" / "sprites" / "player_ships"
ANIMATIONS = ("idle", "rotating", "propulsion", "charging", "damage")
SHIP_IDS = (1, 2, 3, 4, 5)
FINAL_SIZE = 64  # 64x64 for nice visibility in the pause screen (scaled up from 32x32)


def load_base(ship_id: int) -> pygame.Surface:
    """Load and normalize the AI-generated base sprite to FINAL_SIZE x FINAL_SIZE."""
    path = SHIPS_DIR / f"ship_0{ship_id}_base.png"
    surf = pygame.image.load(str(path)).convert_alpha()
    # Center-crop to square, then scale to FINAL_SIZE
    w, h = surf.get_size()
    side = min(w, h)
    x0 = (w - side) // 2
    y0 = (h - side) // 2
    cropped = surf.subsurface((x0, y0, side, side)).copy()
    return pygame.transform.smoothscale(cropped, (FINAL_SIZE, FINAL_SIZE))


def render_rotating(base: pygame.Surface, frame: int) -> pygame.Surface:
    """8 angles: 0°, 45°, 90°, ..., 315° (front of sprite = nose up)."""
    angle = frame * 45.0
    return pygame.transform.rotate(base, -angle)  # negative: pygame is CCW


def render_idle(base: pygame.Surface, frame: int) -> pygame.Surface:
    """Subtle vertical bob: y_offset = sin(2*pi*frame/8) * 2 px."""
    out = pygame.Surface(base.get_size(), pygame.SRCALPHA)
    y_off = int(math.sin(2 * math.pi * frame / 8.0) * 2.0)
    out.blit(base, (0, y_off))
    return out


def render_propulsion(base: pygame.Surface, frame: int) -> pygame.Surface:
    """Animated flame coming out the back of the ship (bottom)."""
    out = base.copy()
    # Flame dimensions cycle: 8 frames = flicker pattern
    flame_heights = [6, 8, 5, 9, 7, 10, 6, 8]
    flame_w = 6
    flame_x = out.get_width() // 2 - flame_w // 2
    flame_y = out.get_height() - 4
    h = flame_heights[frame]
    # Outer flame (orange)
    pygame.draw.polygon(out, (255, 140, 40), [
        (flame_x, flame_y),
        (flame_x + flame_w, flame_y),
        (flame_x + flame_w // 2, flame_y + h),
    ])
    # Inner flame (yellow-white)
    pygame.draw.polygon(out, (255, 230, 130), [
        (flame_x + 1, flame_y),
        (flame_x + flame_w - 1, flame_y),
        (flame_x + flame_w // 2, flame_y + max(2, h - 2)),
    ])
    return out


def render_charging(base: pygame.Surface, frame: int) -> pygame.Surface:
    """Growing charge glow: 8 frames = charge up to 100%, then full bright."""
    out = base.copy()
    # Glow radius grows from 2 to 12
    glow_r = 2 + int(10 * (frame / 7.0))
    cx = out.get_width() // 2
    cy = out.get_height() // 2
    # Outer glow (alpha decreases with frame)
    glow_alpha = 60 + int(120 * (frame / 7.0))
    glow_surf = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (130, 200, 255, glow_alpha), (cx, cy), glow_r)
    # Inner brighter core
    pygame.draw.circle(glow_surf, (200, 240, 255, min(255, glow_alpha + 50)),
                        (cx, cy), max(1, glow_r // 2))
    out.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)
    return out


def render_damage(base: pygame.Surface, frame: int) -> pygame.Surface:
    """Red flicker: even frames = clean, odd frames = red tint."""
    out = base.copy()
    if frame % 2 == 1:
        # Red flicker overlay
        tint = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        tint.fill((255, 60, 60, 100))
        out.blit(tint, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)
    return out


RENDERERS = {
    "idle": render_idle,
    "rotating": render_rotating,
    "propulsion": render_propulsion,
    "charging": render_charging,
    "damage": render_damage,
}


def generate_for_ship(ship_id: int) -> int:
    """Generate all 5x8 = 40 frames for one ship. Returns the count saved."""
    base = load_base(ship_id)
    ship_dir = SHIPS_DIR / f"ship_0{ship_id}"
    count = 0
    for anim in ANIMATIONS:
        anim_dir = ship_dir / anim
        anim_dir.mkdir(parents=True, exist_ok=True)
        renderer = RENDERERS[anim]
        for frame in range(8):
            surf = renderer(base, frame)
            out_path = anim_dir / f"frame_{frame:02d}.png"
            pygame.image.save(surf, str(out_path))
            count += 1
    return count


def main() -> int:
    pygame.init()
    # We don't need a display for image processing, but pygame.image.save
    # requires the mixer to be init'd... actually no, just the display
    # needs to be init for convert_alpha to work properly.
    pygame.display.set_mode((1, 1))
    total = 0
    for ship_id in SHIP_IDS:
        n = generate_for_ship(ship_id)
        print(f"ship_0{ship_id}: generated {n} frames")
        total += n
    print(f"TOTAL: {total} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
