"""Generate 3 placeholder 480x270 background PNGs for the 3 acts.

Run: `python stellar_horizon/tools/make_placeholder_bgs.py stellar_horizon/assets/backgrounds`
"""
from __future__ import annotations

import random
from pathlib import Path


def make_placeholder_backgrounds(out_dir: Path) -> None:
    """Generate 3 simple 480x270 PNGs as placeholders for the 3 acts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    palettes = {
        "act1_asteroid_belt": ((10, 15, 31), (74, 63, 53)),
        "act2_nebula":        ((20, 12, 40), (110, 70, 160)),
        "act3_sun_close":     ((40, 16, 8),  (220, 120, 40)),
    }
    import pygame
    pygame.init()
    for name, (bg_color, star_color) in palettes.items():
        surf = pygame.Surface((480, 270))
        surf.fill(bg_color)
        rng = random.Random(hash(name) & 0xFFFFFFFF)
        for _ in range(80):
            x = rng.randint(0, 479)
            y = rng.randint(0, 269)
            surf.set_at((x, y), star_color)
        pygame.image.save(surf, str(out_dir / f"{name}.png"))


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("stellar_horizon/assets/backgrounds")
    make_placeholder_backgrounds(target)
    print(f"Wrote placeholder backgrounds to {target}")
