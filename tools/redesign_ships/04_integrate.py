"""Stage 4: Copy redesigned sprites to live asset locations (BLOQUE 59).

For each ship:
  - Player: copy Assets/sprites/redesign/player/<anim>/frame_NN.png
    to Assets/sprites/player_ships/ship_01/<anim>/frame_NN.png
    (overwriting the existing 8-frame version; new files have 10 frames).
  - Enemies: copy Assets/sprites/redesign/enemy_<kind>/<anim>/frame_NN.png
    to Assets/sprites/enemies/<kind>/<anim>/frame_NN.png (new dir).
  - Old single-frame enemy PNGs at Assets/sprites/enemy_<variant>.png
    are moved to archive/_legacy_sprites/ for git history preservation.

Usage:
    python tools/redesign_ships/04_integrate.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_ships._ship_specs import SHIPS

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign"
PLAYER_LIVE = PROJECT_ROOT / "Assets" / "sprites" / "player_ships" / "ship_01"
ENEMY_LIVE_PARENT = PROJECT_ROOT / "Assets" / "sprites" / "enemies"
LEGACY_DIR = PROJECT_ROOT / "archive" / "_legacy_sprites"
ANIMATIONS = ("idle", "thrust", "damage", "death")


def integrate_player() -> None:
    src_root = REDESIGN_DIR / "player"
    if not src_root.exists():
        print(f"[skip] player: no source dir {src_root}")
        return
    for anim in ANIMATIONS:
        src_anim = src_root / anim
        dst_anim = PLAYER_LIVE / anim
        if not src_anim.exists():
            print(f"[skip] player/{anim}: no source")
            continue
        dst_anim.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            src = src_anim / f"frame_{i:02d}.png"
            dst = dst_anim / f"frame_{i:02d}.png"
            if src.exists():
                shutil.copy2(src, dst)
    print(f"[done] player: copied 4 anims x 10 frames to {PLAYER_LIVE}")


def integrate_enemy(spec_key: str) -> None:
    src_root = REDESIGN_DIR / spec_key
    if not src_root.exists():
        print(f"[skip] {spec_key}: no source dir")
        return
    kind = spec_key.replace("enemy_", "")
    for anim in ANIMATIONS:
        src_anim = src_root / anim
        dst_anim = ENEMY_LIVE_PARENT / kind / anim
        if not src_anim.exists():
            print(f"[skip] {spec_key}/{anim}: no source")
            continue
        dst_anim.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            src = src_anim / f"frame_{i:02d}.png"
            dst = dst_anim / f"frame_{i:02d}.png"
            if src.exists():
                shutil.copy2(src, dst)
    print(f"[done] {spec_key} -> {ENEMY_LIVE_PARENT / kind}")


def archive_old_enemy_pngs() -> None:
    LEGACY_DIR.mkdir(parents=True, exist_ok=True)
    for spec in SHIPS:
        if not spec.key.startswith("enemy_"):
            continue
        old = PROJECT_ROOT / "Assets" / "sprites" / f"{spec.key}.png"
        if old.exists():
            dest = LEGACY_DIR / old.name
            shutil.move(str(old), str(dest))
            print(f"[arch] {old.name} -> {dest}")


def main() -> int:
    integrate_player()
    for spec in SHIPS:
        if spec.key.startswith("enemy_"):
            integrate_enemy(spec.key)
    archive_old_enemy_pngs()
    print("\nStage 4 done. Live assets updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
