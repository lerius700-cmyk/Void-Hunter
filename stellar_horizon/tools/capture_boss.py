"""Render the boss sprite at each frame of its animation sheet, so we
can see which frames are 'borderless' (clean alpha) vs which have
gray/white fringe.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import sys
from pathlib import Path

import pygame
if not pygame.get_init():
    pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass
pygame.display.set_mode((1, 1))

ROOT = Path("D:/AI/void-hunter")
sys.path.insert(0, str(ROOT))

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene


def main() -> None:
    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s._load_sprites()
    # Draw a contact sheet of all 6 boss frames
    FRAME_W, FRAME_H, FRAME_COUNT = 48, 48, 6
    out_w = 6 * FRAME_W + 40
    out_h = FRAME_H + 60
    canvas = pygame.Surface((out_w, out_h), pygame.SRCALPHA)
    canvas.fill((20, 24, 48))
    pygame.font.init()
    font = pygame.font.SysFont("monospace", 12, bold=True)
    anim = s._animated.get("boss")
    if anim is None or not anim.loaded:
        print("Boss sprite not loaded!")
        return
    for i in range(FRAME_COUNT):
        anim._index = i
        frame = anim.get_current_surface()
        x = 5 + i * (FRAME_W + 5)
        y = 30
        # Background grid for transparency check
        pygame.draw.rect(canvas, (40, 40, 60),
                         (x - 1, y - 1, FRAME_W + 2, FRAME_H + 2), 1)
        canvas.blit(frame, (x, y))
        # Label
        lbl = font.render(f"frame {i}", False, (240, 240, 240))
        canvas.blit(lbl, (x, 5))
    # Title
    title = font.render("BOSS SPRITE SHEET (48x48 x 6 frames)", False, (255, 240, 100))
    canvas.blit(title, (5, out_h - 18))
    out = ROOT / "stellar_horizon" / "tools" / "playtest_out" / "boss_sheet_review.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    scaled = pygame.transform.scale(canvas, (out_w * 4, out_h * 4))
    pygame.image.save(scaled, str(out))
    print(f"saved {out}")
    # Also render a real gameplay frame with the boss in the middle
    s.on_enter()
    s._spawn_boss()
    s.boss.x, s.boss.y = 350.0, 135.0
    s.boss.phase = "phase_1"
    for _ in range(60):  # tick animations once
        for anim in s._animated.values():
            anim.update(1 / 120)
    internal = pygame.Surface((480, 270))
    s.draw(internal)
    scaled2 = pygame.transform.scale(internal, (1920, 1080))
    out2 = ROOT / "stellar_horizon" / "tools" / "playtest_out" / "boss_in_game_v1.29.png"
    pygame.image.save(scaled2, str(out2))
    print(f"saved {out2}")


if __name__ == "__main__":
    main()
