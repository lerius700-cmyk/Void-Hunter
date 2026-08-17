"""BLOQUE 58.14: capture the new pause screen for visual verification.

Boots a fake game in pause mode, draws the PauseScene with a synthetic
get_pause_stats callback (HP damaged, rings collected, etc), and saves
a PNG of the 240x360 internal surface (scaled 4x for clarity).

Usage:
    python tools/capture/capture_pause_screen_v1.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `src.*` importable from the project root.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import pygame  # noqa: E402

from src.core.scene_manager import GameState  # noqa: E402
from src.core.settings import INTERNAL_H, INTERNAL_W  # noqa: E402
from src.ui.scenes import PauseScene  # noqa: E402


def main() -> int:
    pygame.init()
    pygame.display.set_mode((INTERNAL_W * 4, INTERNAL_H * 4), pygame.RESIZABLE)
    internal = pygame.Surface((INTERNAL_W, INTERNAL_H))

    # Synthetic stats: simulate mid-game state so the panel is rich.
    def fake_stats() -> dict:
        return {
            "hp": 18,
            "hp_max": 30,
            "hp_doubled": False,
            "lives": 2,
            "lives_max": 3,
            "bombs": 2,
            "bombs_max": 4,
            "dash_heat": 35.0,
            "dash_heat_max": 100.0,
            "gold_rings": 1,
            "gold_rings_max": 30,
            "score": 12450,
        }

    scene = PauseScene(
        transition_to=lambda s: None,
        get_pause_stats=fake_stats,
    )
    scene.on_enter()
    # Cycle to ship 3 (X-wing) + charging animation for visual variety
    scene._ship_id = 3
    scene._ship_anim = "charging"
    scene._ship_frames.clear()  # force reload
    # Tick the scene a bit so the rotating ship frame is mid-spin.
    for _ in range(8):
        scene.update(0.1)

    # Dim background (so the pause overlay is visible on a black canvas)
    internal.fill((10, 10, 30))
    scene.draw(internal)

    # Scale up 4x and save.
    scaled = pygame.transform.scale(
        internal, (INTERNAL_W * 4, INTERNAL_H * 4),
    )
    out_dir = ROOT / "tools" / "playtest_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pause_screen_v1.png"
    pygame.image.save(scaled, str(out_path))
    print(f"saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
