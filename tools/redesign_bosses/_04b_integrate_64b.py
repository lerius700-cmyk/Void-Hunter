"""Stage 4 (BLOQUE 64.B): Copy redesigned frames to live boss assets.

Source:      Assets/sprites/redesign/goliath/<state>/frame_NN.png
Destination: Assets/sprites/bosses/goliath/<state>/frame_NN.png

The destination is what the runtime reads via
Boss.animation_path = "bosses/goliath/<state>/frame_NN.png".

BLOQUE 64.B states: phase1_idle, phase2_idle, javelin, laser,
purple_bullet, death (replaces the BLOQUE 60 idle/damage/phase2/death/intro
states).

Usage:
    python tools/redesign_bosses/_04b_integrate_64b.py
    python tools/redesign_bosses/_04b_integrate_64b.py --clean   # also remove the old BLOQUE 60 dirs
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_bosses._specs_b64 import GOLIATH_SPEC_64B

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "goliath"
LIVE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "bosses" / "goliath"

# BLOQUE 60 state names — directories we want to drop on --clean.
BLOQUE_60_OLD_STATES = ("idle", "damage", "intro", "phase2")
BLOQUE_60_OLD_BASES = tuple(f"goliath_{s}_base.png" for s in BLOQUE_60_OLD_STATES)


def integrate(clean_old: bool = False) -> int:
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    states = tuple(s.key for s in GOLIATH_SPEC_64B.states)
    for state in states:
        src_state = REDESIGN_DIR / state
        dst_state = LIVE_DIR / state
        if not src_state.exists():
            print(f"[skip] {state} (no source dir)")
            continue
        dst_state.mkdir(parents=True, exist_ok=True)
        frame_count = next(s.frame_count for s in GOLIATH_SPEC_64B.states if s.key == state)
        for i in range(frame_count):
            src = src_state / f"frame_{i:02d}.png"
            dst = dst_state / f"frame_{i:02d}.png"
            if src.exists():
                shutil.copy2(src, dst)
                copied += 1
        print(f"[done] {state} -> {dst_state}")
    if clean_old:
        # Drop the BLOQUE 60 idle/damage/intro/phase2 directories + bases.
        for old_state in BLOQUE_60_OLD_STATES:
            old_dir = LIVE_DIR / old_state
            if old_dir.exists():
                shutil.rmtree(old_dir)
                print(f"[clean] removed {old_dir}")
        base_dir = LIVE_DIR / "_base"
        if base_dir.exists():
            for old_base in BLOQUE_60_OLD_BASES:
                p = base_dir / old_base
                if p.exists():
                    p.unlink()
                    print(f"[clean] removed {p}")
        # Also drop the BLOQUE 60 preview sheet (keep only the 64B one).
        old_sheet = LIVE_DIR / "spritesheet_goliath.png"
        if old_sheet.exists():
            old_sheet.unlink()
            print(f"[clean] removed {old_sheet}")
    print(f"\nStage 4 done. {copied} frame(s) integrated.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Drop the old BLOQUE 60 dirs and base files")
    args = parser.parse_args()
    return integrate(clean_old=args.clean)


if __name__ == "__main__":
    sys.exit(main())
