"""Stage 2b: Generate the 10 frame PNGs per state (BLOQUE 60).

After 02_postprocess.py has produced <state>/_source.png, this script
calls the right animation generator for each state to produce 10 frames.

Usage:
    python tools/redesign_bosses/02b_generate_animations.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_bosses import _animation_frames as af
from tools.redesign_bosses._specs import GOLIATH_SPEC

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "goliath"

GENERATORS = {
    "idle": af.generate_idle_frames,
    "damage": af.generate_damage_frames,
    "phase2": af.generate_phase2_frames,
    "death": af.generate_death_frames,
    "intro": af.generate_intro_frames,
}


def main() -> int:
    for spec in GOLIATH_SPEC.states:
        state_dir = REDESIGN_DIR / spec.key
        source = state_dir / "_source.png"
        if not source.exists():
            print(f"[skip] {spec.key} (no _source.png)")
            continue
        # Skip if all 10 frames exist
        out_dir = state_dir
        if all((out_dir / f"frame_{i:02d}.png").exists() for i in range(10)):
            print(f"[skip] {spec.key} (all 10 frames exist)")
            continue
        gen = GENERATORS[spec.key]
        gen(source, out_dir)
        print(f"[anim] {spec.key} -> 10 frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
