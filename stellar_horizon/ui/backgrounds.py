"""Background images per act. Phase 1 uses placeholders."""
from __future__ import annotations

from pathlib import Path

import pygame


def make_placeholder_backgrounds(out_dir: Path) -> None:
    """Generate 3 simple 480x270 PNGs as placeholders for the 3 acts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    palettes = {
        "act1_asteroid_belt": ((10, 15, 31), (74, 63, 53)),
        "act2_nebula":        ((20, 12, 40), (110, 70, 160)),
        "act3_sun_close":     ((40, 16, 8),  (220, 120, 40)),
    }
    for name, (bg_color, star_color) in palettes.items():
        surf = pygame.Surface((480, 270))
        surf.fill(bg_color)
        import random
        rng = random.Random(hash(name) & 0xFFFFFFFF)
        for _ in range(80):
            x = rng.randint(0, 479)
            y = rng.randint(0, 269)
            surf.set_at((x, y), star_color)
        pygame.image.save(surf, str(out_dir / f"{name}.png"))


class Background:
    def __init__(self, image_path: Path) -> None:
        # Don't use .convert() — it requires a display mode. For a 480x270
        # background, the performance impact of NOT converting is negligible.
        self.image = pygame.image.load(str(image_path))
        self.parallax_x: float = 0.0

    def update(self, dt: float, scroll_speed: float = 0.0) -> None:
        w = self.image.get_width()
        self.parallax_x = (self.parallax_x + scroll_speed * dt) % w

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.image, (-int(self.parallax_x), 0))
        if self.parallax_x > 0:
            surface.blit(self.image, (int(self.image.get_width() - self.parallax_x), 0))
