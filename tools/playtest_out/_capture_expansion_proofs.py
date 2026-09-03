"""Capture visual proofs for the BLOQUE 58.next movement expansion.

Renders 10 formations (slot dots on black bg), 7 paths (curve as dots),
and 1 mosaic of 5 random COMPOSED patterns. All output is saved to
tools/playtest_out/ which is gitignored.
"""
import os
import sys
import random
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.movement.formation import FlightFormation, FormationKind
from src.movement.lemniscate_path import LemniscatePath
from src.movement.cardioid_path import CardioidPath
from src.movement.lissajous_path import LissajousPath
from src.movement.rose_path import RoseK2Path, RoseK3Path
from src.movement.hypocycloid_path import HypocycloidPath
from src.movement.epicycloid_path import EpicycloidPath
from src.systems.wave_patterns.composed import COMPOSED_PATTERNS, FORMATION_GENERATORS, PATH_GENERATORS


W, H = 800, 800
WHITE = (255, 255, 255)
RED = (255, 80, 60)
BLUE = (80, 180, 255)
GREEN = (100, 255, 100)


def render_formation(form: FlightFormation, name: str) -> pygame.Surface:
    surf = pygame.Surface((W, H))
    surf.fill((0, 0, 0))
    # Origin at center, scale slots by 4
    cx, cy = W // 2, H // 2
    scale = 4
    for i, (dx, dy) in enumerate(form.offsets):
        x = int(cx + dx * scale)
        y = int(cy + dy * scale)
        color = RED if i == 0 else BLUE
        pygame.draw.circle(surf, color, (x, y), 8)
        pygame.draw.circle(surf, WHITE, (x, y), 8, 1)
    return surf


def render_path_samples(path, name: str, n_samples: int = 200) -> pygame.Surface:
    surf = pygame.Surface((W, H))
    surf.fill((0, 0, 0))
    cx, cy = W // 2, H // 2
    scale = 1.5
    for i in range(n_samples):
        t = i / (n_samples - 1)
        pos = path.position_at(t)
        x = int(cx + pos.x * scale)
        y = int(cy + pos.y * scale)
        if 0 <= x < W and 0 <= y < H:
            pygame.draw.circle(surf, GREEN, (x, y), 2)
    return surf


def render_composed_panel(p, w: int = 400, h: int = 400) -> pygame.Surface:
    surf = pygame.Surface((w, h))
    surf.fill((0, 0, 0))
    # Get the formation slots
    if p._formation in FORMATION_GENERATORS:
        slots = FORMATION_GENERATORS[p._formation](p._count)
    else:
        slots = []
    cx, cy = w // 2, h // 2
    scale = 1.5
    for dx, dy in slots:
        x = int(cx + dx * scale)
        y = int(cy + dy * scale)
        pygame.draw.circle(surf, BLUE, (x, y), 4)
    return surf


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(exist_ok=True)

    # 10 formations
    new_formations = [
        (FormationKind.FLOWER_OF_LIFE, "flower_of_life", lambda: FlightFormation.flower_of_life()),
        (FormationKind.VESICA_PISCIS, "vesica_piscis", lambda: FlightFormation.vesica_piscis()),
        (FormationKind.FIBONACFI_SPIRAL, "fibonacfi_spiral", lambda: FlightFormation.fibonacfi_spiral()),
        (FormationKind.TREE_OF_LIFE, "tree_of_life", lambda: FlightFormation.tree_of_life()),
        (FormationKind.SIERPINSKI_TRIANGLE, "sierpinski_triangle", lambda: FlightFormation.sierpinski_triangle()),
        (FormationKind.HEX_CLOSE_PACK, "hex_close_pack", lambda: FlightFormation.hex_close_pack()),
        (FormationKind.MANDALA_RINGS, "mandala_rings", lambda: FlightFormation.mandala_rings()),
        (FormationKind.GOLDEN_RATIO_ROW, "golden_ratio_row", lambda: FlightFormation.golden_ratio_row()),
        (FormationKind.KOCH_3FOLD, "koch_3fold", lambda: FlightFormation.koch_3fold()),
        (FormationKind.DRAGON_CURVE, "dragon_curve", lambda: FlightFormation.dragon_curve()),
    ]
    for kind, name, builder in new_formations:
        form = builder()
        surf = render_formation(form, name)
        out_path = out_dir / f"formation_{name}.png"
        pygame.image.save(surf, str(out_path))
        print(f"  formation {name} -> {out_path.name}")

    # 7 paths
    path_classes = [
        (LemniscatePath, "lemniscate"),
        (CardioidPath, "cardioid"),
        (LissajousPath, "lissajous"),
        (RoseK2Path, "rose_k2"),
        (RoseK3Path, "rose_k3"),
        (HypocycloidPath, "hypocycloid"),
        (EpicycloidPath, "epicycloid"),
    ]
    for cls, name in path_classes:
        path = cls().get_path()
        surf = render_path_samples(path, name)
        out_path = out_dir / f"path_{name}.png"
        pygame.image.save(surf, str(out_path))
        print(f"  path {name} -> {out_path.name}")

    # 1 mosaic: 5 random COMPOSED
    rng = random.Random(42)
    sample = rng.sample(COMPOSED_PATTERNS, 5)
    mosaic = pygame.Surface((W * 2, H))
    for i, p in enumerate(sample):
        col = i % 2
        row = i // 2
        panel = render_composed_panel(p, w=W, h=H)
        mosaic.blit(panel, (col * W, row * H))
    mosaic_path = out_dir / "composed_5_random.png"
    pygame.image.save(mosaic, str(mosaic_path))
    print(f"  mosaic -> {mosaic_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
