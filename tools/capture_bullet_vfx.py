"""Render a strip showing all 10 laser weapons in flight with their
code-driven VFX (alpha pulse, scale pulse, halo).

For each weapon we spawn a row of bullets at evenly-spaced times so
each one is at a different phase of its animation. Then we composite
them into one preview image and save it to tools/playtest_out/.

Useful for verifying the VFX tuning without launching the game.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import sys
from pathlib import Path

import pygame

# Add the project root to sys.path so `stellar_horizon` imports.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.fx.bullet_vfx import compute as compute_bullet_vfx
from stellar_horizon.scenes.gameplay import GameplayScene


# (weapon_idx, label)
WEAPONS = [
    (0, "1 yellow plasma"),
    (1, "2 red pulse"),
    (2, "3 blue ion"),
    (3, "4 green acid"),
    (4, "5 purple void"),
    (5, "6 orange fire"),
    (6, "7 white pierce"),
    (7, "8 pink heart"),
    (8, "9 cyan ice"),
    (9, "0 rainbow"),
]


def render_weapon_row(s: GameplayScene, weapon_idx: int,
                      surface: pygame.Surface,
                      x_offset: int, y_offset: int) -> None:
    """Render 8 bullets in flight for `weapon_idx` at increasing
    spawn_time offsets. The first bullet has the freshest phase, the
    oldest is way at the back."""
    s.player.set_weapon(weapon_idx)
    # Update _elapsed to a sane baseline so VFX phase is consistent.
    s._elapsed = 1.0
    bullet_count = 8
    spacing = 28
    for i in range(bullet_count):
        # Each bullet spawned 0.1s after the previous -> 8 bullets
        # cover 0.7s of phase.
        spawn_t = 0.4 + i * 0.12
        # Mock bullet object
        class _B:
            weapon = weapon_idx
            spawn_time = spawn_t
        b = _B()
        vfx = compute_bullet_vfx(b, s._elapsed)
        # Draw center position
        cx = x_offset + i * spacing + 14
        cy = y_offset + 14
        # Halo first
        if vfx.halo_color is not None and vfx.halo_size > 0 \
                and vfx.halo_alpha > 0:
            rad = vfx.halo_size
            halo = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*vfx.halo_color, vfx.halo_alpha),
                               (rad, rad), rad)
            surface.blit(halo, (cx - rad, cy - rad))
        # Sprite
        weapon_name = f"laser_{weapon_idx + 1:02d}"
        sprite = s._laser_sprites.get(weapon_name)
        if sprite is not None:
            if vfx.scale != 1.0:
                sw, sh = sprite.get_size()
                nw, nh = max(1, int(sw * vfx.scale)), max(1, int(sh * vfx.scale))
                rendered = pygame.transform.scale(sprite, (nw, nh))
            else:
                rendered = sprite
            if vfx.alpha < 255:
                rendered = rendered.copy()
                rendered.set_alpha(vfx.alpha)
            rect = rendered.get_rect(center=(cx, cy))
            surface.blit(rendered, rect)


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))  # dummy mode
    pygame.font.init()
    font = pygame.font.SysFont("monospace", 11, bold=True)
    # Build a GameplayScene just to load sprites. Skip on_enter() so
    # we don't start the wave manager / midi; we just need the
    # sprite caches and a Player for the weapon field.
    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s._load_sprites()
    # Construct a minimal player for set_weapon() calls. The capture
    # only reads s._laser_sprites and s.player.weapon, not the
    # player's physics.
    from stellar_horizon.entities.player import Player
    s.player = Player(pygame.Rect(0, 0, 480, 270))
    # Layout: 10 rows, one per weapon. Each row: label + 8 bullets.
    row_h = 36
    label_w = 130
    bullet_area_w = 8 * 28
    canvas_w = label_w + bullet_area_w + 10
    canvas_h = 10 * row_h + 20
    canvas = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
    canvas.fill((20, 24, 48))  # dark background
    for row, (weapon, label) in enumerate(WEAPONS):
        y = 10 + row * row_h
        # Label
        text = font.render(label, False, (220, 220, 240))
        canvas.blit(text, (8, y + 10))
        # Bullets
        render_weapon_row(s, weapon, canvas, label_w, y)
    # Save
    out_dir = Path("tools/playtest_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "bullet_vfx_preview.png"
    pygame.image.save(canvas, str(out_path))
    print(f"saved {out_path} ({canvas_w}x{canvas_h})")


if __name__ == "__main__":
    main()
