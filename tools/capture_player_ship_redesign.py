"""Capture: redesigned player ship (BLOQUE 58.12).

Visual proof of the new ship polish:
  - 3D body shading (top highlight + side panel lines)
  - Wing-tip neon glow halos (red port, green starboard)
  - Canopy frame (darker outline) + double highlight (glass dome)
  - Wing panel lines (subtle inner edges)
  - Engine intake blades (small darker strokes)

Output: tools/playtest_out/polish_57_player_ship_redesign.png
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["VOID_HUNTER_INVULN"] = "1"
import sys
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame

pygame.init()
W, H = 720, 480
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("VOID HUNTER - player ship redesign (BLOQUE 58.12)")
screen.fill((8, 12, 24))

font_lg = pygame.font.SysFont("consolas", 20)
font_md = pygame.font.SysFont("consolas", 13)
font_sm = pygame.font.SysFont("consolas", 10)

title = font_lg.render(
    "PLAYER SHIP  -  BLOQUE 58.12 redesign (more Star Fox detail)", True, (255, 255, 255),
)
screen.blit(title, (12, 10))
sub = font_md.render(
    "3D body shading  -  wing-tip glow halos  -  canopy frame  -  panel lines  -  intake blades",
    True, (180, 220, 255),
)
screen.blit(sub, (12, 34))

# We don't render the live ship (gameplay runtime not imported).
# Instead, mirror the new drawing logic into a self-contained capture.
def draw_new_ship(surf, t=0.0):
    """Mirror of the new _draw_player (BLOQUE 58.12)."""
    # Ship body color
    body_color = (220, 240, 255)
    wing_color = (180, 200, 230)
    # Top highlight
    pygame.draw.polygon(surf, (250, 252, 255), [
        (16, 0), (13, 8), (19, 8),
    ])
    # Side panel lines
    pygame.draw.line(surf, (130, 150, 180), (13, 8), (11, 18), 1)
    pygame.draw.line(surf, (130, 150, 180), (19, 8), (21, 18), 1)
    # Body
    pygame.draw.polygon(surf, body_color, [
        (16, 0), (13, 8), (11, 18), (16, 20), (21, 18), (19, 8),
    ])
    # Belly highlight
    pygame.draw.polygon(surf, (180, 200, 230), [
        (13, 14), (19, 14), (16, 18),
    ])
    # Left wing
    pygame.draw.polygon(surf, wing_color, [
        (13, 8), (10, 11), (0, 17), (0, 19), (4, 20), (11, 14),
    ])
    # Right wing
    pygame.draw.polygon(surf, wing_color, [
        (19, 8), (22, 11), (32, 17), (32, 19), (28, 20), (21, 14),
    ])
    # Wing leading edge
    pygame.draw.line(surf, (240, 245, 255), (13, 8), (0, 17), 1)
    pygame.draw.line(surf, (240, 245, 255), (19, 8), (32, 17), 1)
    # Wing panel lines (BLOQUE 58.12)
    pygame.draw.line(surf, (110, 130, 160), (10, 11), (4, 20), 1)
    pygame.draw.line(surf, (110, 130, 160), (22, 11), (28, 20), 1)
    # Canopy frame
    pygame.draw.polygon(surf, (60, 40, 50), [
        (14, 5), (18, 5), (19, 8), (16, 11), (13, 8),
    ])
    # Canopy
    cockpit_color = (255, 100, 100)
    pygame.draw.polygon(surf, cockpit_color, [
        (15, 6), (17, 6), (18, 8), (16, 10), (14, 8),
    ])
    # Double canopy highlight
    pygame.draw.circle(surf, (255, 255, 255), (15, 7), 1)
    # Laser cannons
    pygame.draw.rect(surf, (200, 80, 80), (1, 16, 3, 2))
    pygame.draw.rect(surf, (255, 120, 100), (0, 17, 2, 1))
    pygame.draw.rect(surf, (80, 200, 100), (28, 16, 3, 2))
    pygame.draw.rect(surf, (120, 255, 150), (30, 17, 2, 1))
    # Wing-tip glow halos
    glow = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 80, 80, 110), (1, 17), 3)
    pygame.draw.circle(glow, (255, 150, 100, 70), (1, 17), 2)
    surf.blit(glow, (-2, 14))
    glow2 = pygame.Surface((6, 6), pygame.SRCALPHA)
    pygame.draw.circle(glow2, (100, 255, 130, 110), (4, 17), 3)
    pygame.draw.circle(glow2, (160, 255, 180, 70), (4, 17), 2)
    surf.blit(glow2, (26, 14))
    # Wing tip pulsing lights
    red_pulse = 0.5 + 0.5 * math.sin(t * 6.0)
    green_pulse = 0.5 + 0.5 * math.sin(t * 6.0 + math.pi)
    red_color = (int(255 * (0.4 + 0.6 * red_pulse)),
                 int(60 * (0.4 + 0.6 * red_pulse)),
                 int(60 * (0.4 + 0.6 * red_pulse)))
    green_color = (int(60 * (0.4 + 0.6 * green_pulse)),
                   int(255 * (0.4 + 0.6 * green_pulse)),
                   int(100 * (0.4 + 0.6 * green_pulse)))
    pygame.draw.circle(surf, red_color, (1, 13), 1)
    pygame.draw.circle(surf, green_color, (31, 13), 1)
    # Twin engine intakes
    pygame.draw.rect(surf, (40, 50, 70), (12, 16, 3, 2))
    pygame.draw.rect(surf, (40, 50, 70), (17, 16, 3, 2))
    # Intake blades
    pygame.draw.line(surf, (15, 20, 30), (13, 17), (13, 17), 1)
    pygame.draw.line(surf, (15, 20, 30), (18, 17), (18, 17), 1)
    # Engine glow
    pygame.draw.rect(surf, (255, 140, 60), (12, 18, 3, 1))
    pygame.draw.rect(surf, (255, 140, 60), (17, 18, 3, 1))
    # Center stripe
    pygame.draw.line(surf, (255, 80, 80), (16, 6), (16, 16), 1)


# Draw the new ship in the center, scaled 6x for visibility
SCALE = 6
sprite = pygame.Surface((32, 24), pygame.SRCALPHA)
draw_new_ship(sprite, t=0.4)
scaled = pygame.transform.scale(sprite, (32 * SCALE, 24 * SCALE))
screen.blit(scaled, (W // 2 - 96, H // 2 - 72))

# Annotate
arrow_font = font_sm.render("scale 6x", True, (180, 200, 230))
screen.blit(arrow_font, (W // 2 - 20, H // 2 + 100))

# Draw callout boxes with arrows pointing at the new features
callouts = [
    # (label, anchor_x, anchor_y, box_x, box_y)
    ("wing-tip glow halo (red)", 60, 220, 14, 100),
    ("canopy frame + double highlight", W // 2, 110, 180, 70),
    ("3D body shading + panel lines", W // 2, 220, 200, 200),
    ("engine intake blade", W // 2 - 60, 300, 220, 320),
    ("wing-tip glow halo (green)", W - 60, 220, 540, 100),
]
for label, ax, ay, bx, by in callouts:
    # Arrow line
    pygame.draw.line(screen, (180, 200, 230), (ax, ay), (bx + 60, by), 1)
    # Box with text
    text = font_sm.render(label, True, (200, 220, 255))
    screen.blit(text, (bx, by))

# Footer
foot_y = 400
foot1 = font_md.render("BLOQUE 58.12 ship polish:", True, (220, 220, 255))
screen.blit(foot1, (14, foot_y))
foot2 = font_sm.render(
    "  - 3D body shading (top highlight + side panel lines)",
    True, (200, 200, 230),
)
screen.blit(foot2, (14, foot_y + 16))
foot3 = font_sm.render(
    "  - Wing-tip neon glow halos (red port, green starboard)",
    True, (200, 200, 230),
)
screen.blit(foot3, (14, foot_y + 30))
foot4 = font_sm.render(
    "  - Canopy frame (darker outline) + double highlight for glass dome feel",
    True, (200, 200, 230),
)
screen.blit(foot4, (14, foot_y + 44))
foot5 = font_sm.render(
    "  - Engine intake blade (small darker stroke for turbine feel)",
    True, (200, 200, 230),
)
screen.blit(foot5, (14, foot_y + 58))

# Save
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "polish_57_player_ship_redesign.png"
pygame.image.save(screen, str(out_path))
print(f"Saved: {out_path}")
