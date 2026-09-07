"""Stage 4: Copy redesigned frames to live boss assets (BLOQUE 60).

Source:      Assets/sprites/redesign/goliath/<state>/frame_NN.png
Destination: Assets/sprites/bosses/goliath/<state>/frame_NN.png

The destination is what the runtime reads via
Boss.animation_path = "bosses/goliath/<state>/frame_NN.png".

BLOQUE 60 deviation: filename is ``_04_integrate.py`` (underscore prefix)
instead of the plan's ``04_integrate.py`` so the module is importable as
a Python identifier via ``from tools.redesign_bosses import _04_integrate``.

Usage:
    python tools/redesign_bosses/_04_integrate.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "goliath"
LIVE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "bosses" / "goliath"
STATE_COUNT = 5
FRAMES_PER_STATE = 10


def integrate() -> int:
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for state in ("idle", "damage", "phase2", "death", "intro"):
        src_state = REDESIGN_DIR / state
        dst_state = LIVE_DIR / state
        if not src_state.exists():
            print(f"[skip] {state} (no source dir)")
            continue
        dst_state.mkdir(parents=True, exist_ok=True)
        for i in range(FRAMES_PER_STATE):
            src = src_state / f"frame_{i:02d}.png"
            dst = dst_state / f"frame_{i:02d}.png"
            if src.exists():
                shutil.copy2(src, dst)
                copied += 1
        print(f"[done] {state} -> {dst_state}")
    print(f"\nStage 4 done. {copied} frame(s) integrated.")
    return 0


if __name__ == "__main__":
    sys.exit(integrate())
