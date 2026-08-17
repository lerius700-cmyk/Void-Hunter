"""Capture screenshots of the new wave types in action.

Renders 4 snapshots, one per new enemy type, so we can visually verify
the sprite cycling + new behaviors before the user playtests:
  1. BOMBER — orange bomber sprite + visible bomb drop
  2. UFO     — gold royal sprite + sinuous path
  3. KAMIKAZE — coral snake sprite + red warning flash
  4. MIXED   — wave 6 final onslaught (everything)
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import sys
from pathlib import Path

ROOT = Path("D:/AI/void-hunter")
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.entities.enemy import EnemyKind


def _force_spawn(scene, kind: str, formation="v_pointing_left", count=3,
                 y_offset=0, path="s_right_to_left", sprite_name=""):
    """Inject a wave spawn directly into the wave manager's queue."""
    from stellar_horizon.waves.wave_manager import _build_enemies
    from stellar_horizon.waves.bezier_horizontal import path_s_right_to_left
    from src.movement import HybridPath, PathFollower

    spawn = {
        "formation": formation,
        "formation_count": count,
        "enemy_kind": kind,
        "path": path,
        "path_y_offset": y_offset,
    }
    enemies = _build_enemies(spawn, sprite_picker=lambda k: sprite_name)
    # Pre-position them so they're already on screen for the snapshot.
    for i, e in enumerate(enemies):
        e.x = 380 - i * 22
        e.y = 130 + y_offset
        e.path_done = True
    scene.wave_manager.spawned_enemies.extend(enemies)


def _capture(scene, label: str, out_path: Path):
    internal = pygame.Surface((480, 270))
    scene.draw(internal)
    scaled = pygame.transform.scale(internal, (1920, 1080))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(scaled, str(out_path))
    print(f"  {label}: saved {out_path.name}")


def main():
    out_dir = ROOT / "tools" / "playtest_out"

    # Snapshot 1: BOMBER
    s = GameplayScene(MidiPlayer(), Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    _force_spawn(s, "bomber", formation="line_horizontal", count=3,
                 y_offset=-20, path="s_right_to_left", sprite_name="enemy_03")
    _capture(s, "BOMBER (orange_bomber)", out_dir / "new_wave_bomber.png")

    # Snapshot 2: UFO
    s = GameplayScene(MidiPlayer(), Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    _force_spawn(s, "ufo", formation="line_horizontal", count=3,
                 y_offset=20, path="ufo_entry", sprite_name="enemy_06")
    _capture(s, "UFO (yellow_saucer)", out_dir / "new_wave_ufo.png")

    # Snapshot 3: KAMIKAZE
    s = GameplayScene(MidiPlayer(), Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    _force_spawn(s, "kamikaze", formation="v_pointing_left", count=4,
                 y_offset=10, path="kamikaze_dive", sprite_name="enemy_15")
    _capture(s, "KAMIKAZE (coral_snake)", out_dir / "new_wave_kamikaze.png")

    # Snapshot 4: MIXED — simulate wave 6 by force-spawning all kinds.
    s = GameplayScene(MidiPlayer(), Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    _force_spawn(s, "heavy", formation="diamond_pointing_left", count=3,
                 y_offset=80, path="s_right_to_left", sprite_name="enemy_04")
    _force_spawn(s, "ufo", formation="line_horizontal", count=2,
                 y_offset=-60, path="ufo_entry", sprite_name="enemy_18")
    _force_spawn(s, "bomber", formation="line_horizontal", count=2,
                 y_offset=10, path="s_right_to_left", sprite_name="enemy_17")
    _force_spawn(s, "kamikaze", formation="v_pointing_left", count=4,
                 y_offset=-30, path="kamikaze_dive", sprite_name="enemy_10")
    _force_spawn(s, "scout", formation="v_pointing_left", count=5,
                 y_offset=50, path="s_right_to_left", sprite_name="enemy_07")
    _capture(s, "MIXED (wave 6 final)", out_dir / "new_wave_mixed.png")


if __name__ == "__main__":
    main()
