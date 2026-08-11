"""Export the player ship sprite to a PNG file.

The ship is generated procedurally in src/ui/gameplay_runtime.py
(line ~3216: _draw_player). This script invokes the same draw
logic and saves the resulting 32x24 surface to a PNG so it can
be used as a sprite asset.
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_INVULN"] = "1"
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from src.entities.player.player import Player, PlayerState
from src.ui.gameplay_runtime import GameplayRuntime
from src.core.settings import PLAYER_SPRITE_SCALE

# Build a minimal runtime-like object
rt = GameplayRuntime.__new__(GameplayRuntime)
rt._player = Player()
rt._t = 0.0
rt._player.x = 0
rt._player.y = 0
rt._player.tilt = 0.0
rt._player.current_tilt = 0.0
rt._player.nose_angle = 0.0
rt._player.current_nose_angle = 0.0
rt._player.dash_iframes_left = 0
rt._player.respawn_invuln = 0.0
rt._player.dash_heat = 0.0
rt._muzzle_flash = 0.0

# Save the IDLE ship
rt._player.state = PlayerState.IDLE
surf_idle = pygame.Surface((32, 24), pygame.SRCALPHA)
# Manually call the ship's drawing helpers, but capture the surface
# Hack: monkey-patch the target in _draw_engine_flame and _draw_player
# Actually, the cleanest way: copy the ship-drawing code from _draw_player

# We need a different approach - replicate the body of _draw_player
# but write to our own surface.
# Let's temporarily replace rt._player and use the actual draw.
# Even simpler: capture the resulting rotated surface via a custom target.

# Custom target: a surface we own, with ox=oy=0
target = pygame.Surface((128, 96), pygame.SRCALPHA)
target.fill((0, 0, 0, 0))  # transparent

# Place the ship centered on target
rt._player.x = 64
rt._player.y = 48
rt._player.state = PlayerState.IDLE
rt._draw_player(target, 0, 0)

# Find the non-transparent bounds
bounds = target.get_bounding_rect()
ship_idle = target.subsurface(bounds).copy()

# Save IDLE sprite
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_idle = out_dir / "ship_idle.png"
pygame.image.save(ship_idle, str(out_idle))
print(f"IDLE ship saved: {out_idle}  size={ship_idle.get_size()}")

# Save PROPULSION sprite
rt._player.x = 64
rt._player.y = 48
rt._player.state = PlayerState.PROPULSION
target2 = pygame.Surface((128, 96), pygame.SRCALPHA)
target2.fill((0, 0, 0, 0))
rt._draw_player(target2, 0, 0)
bounds2 = target2.get_bounding_rect()
ship_prop = target2.subsurface(bounds2).copy()
out_prop = out_dir / "ship_propulsion.png"
pygame.image.save(ship_prop, str(out_prop))
print(f"PROPULSION ship saved: {out_prop}  size={ship_prop.get_size()}")

# Also save a CHARGE (level 3) sprite
# Skipped: CHARGE state needs more runtime state (_laser_active, etc).
# The main two states (IDLE + PROPULSION) are enough for asset use.

# Also save the raw 32x24 source sprite (no scale, no rotation) for both states
import math
def make_raw_sprite(state):
    surf = pygame.Surface((32, 24), pygame.SRCALPHA)
    # Manually replicate the body of _draw_player without the
    # _draw_engine_flame call (which uses self._engine_flame) and
    # without the rotation/scale at the end. We just inline the
    # colors and shapes from the source.
    is_propulsion = (state == PlayerState.PROPULSION)
    if is_propulsion:
        body_color = (240, 248, 255)
        wing_color = (160, 200, 240)
        cockpit_color = (140, 200, 255)
        stripe_color = (65, 105, 225)
        left_laser_color = (140, 200, 255)
        right_laser_color = (200, 230, 255)
        left_glow_outer = (100, 180, 255, 110)
        left_glow_inner = (160, 220, 255, 70)
        right_glow_outer = (160, 220, 255, 110)
        right_glow_inner = (220, 240, 255, 70)
        left_tip_color = (180, 220, 255)
        right_tip_color = (220, 240, 255)
        frame_color = (40, 60, 100)
        engine_glow_color = (200, 230, 255)
        intake_color = (40, 50, 70)
        red_color = (100, 180, 255)
        green_color = (160, 220, 255)
    else:
        body_color = (220, 240, 255)
        wing_color = (180, 200, 230)
        cockpit_color = (255, 100, 100)
        stripe_color = (255, 80, 80)
        left_laser_color = (200, 80, 80)
        right_laser_color = (80, 200, 100)
        left_glow_outer = (255, 80, 80, 110)
        left_glow_inner = (255, 150, 100, 70)
        right_glow_outer = (100, 255, 130, 110)
        right_glow_inner = (160, 255, 180, 70)
        left_tip_color = (255, 120, 100)
        right_tip_color = (120, 255, 150)
        frame_color = (60, 40, 50)
        engine_glow_color = (255, 140, 60)
        intake_color = (40, 50, 70)
        red_pulse = 0.5 + 0.5 * math.sin(0.0)
        green_pulse = 0.5 + 0.5 * math.sin(0.0 + math.pi)
        red_color = (int(255 * (0.4 + 0.6 * red_pulse)),
                     int(60 * (0.4 + 0.6 * red_pulse)),
                     int(60 * (0.4 + 0.6 * red_pulse)))
        green_color = (int(60 * (0.4 + 0.6 * green_pulse)),
                       int(255 * (0.4 + 0.6 * green_pulse)),
                       int(100 * (0.4 + 0.6 * green_pulse)))
    # Body shading + body + wings
    pygame.draw.polygon(surf, (250, 252, 255), [(16, 0), (13, 8), (19, 8)])
    pygame.draw.line(surf, (130, 150, 180), (13, 8), (11, 18), 1)
    pygame.draw.line(surf, (130, 150, 180), (19, 8), (21, 18), 1)
    pygame.draw.polygon(surf, body_color, [(16, 0), (13, 8), (11, 18), (16, 20), (21, 18), (19, 8)])
    pygame.draw.polygon(surf, (180, 200, 230), [(13, 14), (19, 14), (16, 18)])
    pygame.draw.polygon(surf, wing_color, [(13, 8), (10, 11), (0, 17), (0, 19), (4, 20), (11, 14)])
    pygame.draw.polygon(surf, wing_color, [(19, 8), (22, 11), (32, 17), (32, 19), (28, 20), (21, 14)])
    pygame.draw.line(surf, (240, 245, 255), (13, 8), (0, 17), 1)
    pygame.draw.line(surf, (240, 245, 255), (19, 8), (32, 17), 1)
    pygame.draw.line(surf, (110, 130, 160), (10, 11), (4, 20), 1)
    pygame.draw.line(surf, (110, 130, 160), (22, 11), (28, 20), 1)
    # Canopy
    pygame.draw.polygon(surf, frame_color, [(14, 5), (18, 5), (19, 8), (16, 11), (13, 8)])
    pygame.draw.polygon(surf, cockpit_color, [(15, 6), (17, 6), (18, 8), (16, 10), (14, 8)])
    pygame.draw.circle(surf, (255, 255, 255), (15, 7), 1)
    highlight_color = (255, 220, 220) if not is_propulsion else (220, 240, 255)
    pygame.draw.circle(surf, highlight_color, (17, 7), 0)
    # Lasers
    pygame.draw.rect(surf, left_laser_color, (1, 16, 3, 2))
    pygame.draw.rect(surf, left_tip_color, (0, 17, 2, 1))
    pygame.draw.rect(surf, right_laser_color, (28, 16, 3, 2))
    pygame.draw.rect(surf, right_tip_color, (30, 17, 2, 1))
    # Wing-tip glow halos
    glow = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(glow, left_glow_outer, (1, 17), 3)
    pygame.draw.circle(glow, left_glow_inner, (1, 17), 2)
    surf.blit(glow, (-2, 14))
    glow2 = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(glow2, right_glow_outer, (4, 17), 3)
    pygame.draw.circle(glow2, right_glow_inner, (4, 17), 2)
    surf.blit(glow2, (26, 14))
    # Wing tip lights
    pygame.draw.circle(surf, red_color, (1, 13), 1)
    pygame.draw.circle(surf, green_color, (31, 13), 1)
    # Engine intakes + glow
    pygame.draw.rect(surf, intake_color, (12, 16, 3, 2))
    pygame.draw.rect(surf, intake_color, (17, 16, 3, 2))
    pygame.draw.line(surf, (15, 20, 30), (13, 17), (13, 17), 1)
    pygame.draw.line(surf, (15, 20, 30), (18, 17), (18, 17), 1)
    pygame.draw.rect(surf, engine_glow_color, (12, 18, 3, 1))
    pygame.draw.rect(surf, engine_glow_color, (17, 18, 3, 1))
    # Center stripe
    pygame.draw.line(surf, stripe_color, (16, 6), (16, 16), 1)
    return surf

raw_idle = make_raw_sprite(PlayerState.IDLE)
pygame.image.save(raw_idle, str(out_dir / "ship_sprite_32x24_idle.png"))
print(f"Raw 32x24 IDLE: {(out_dir / 'ship_sprite_32x24_idle.png')}")

raw_prop = make_raw_sprite(PlayerState.PROPULSION)
pygame.image.save(raw_prop, str(out_dir / "ship_sprite_32x24_propulsion.png"))
print(f"Raw 32x24 PROPULSION: {(out_dir / 'ship_sprite_32x24_propulsion.png')}")
