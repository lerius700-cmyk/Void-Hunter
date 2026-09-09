"""Stage 2b (BLOQUE 64.B): Generate the 10 frame PNGs per state.

After 02b_postprocess_64b.py has produced <state>/_source.png, this script
calls the right animation generator for each state to produce 10 frames.

Usage:
    python tools/redesign_bosses/02c_generate_animations_64b.py
    python tools/redesign_bosses/02c_generate_animations_64b.py --force
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_bosses import _animation_frames_64b as af
from tools.redesign_bosses._specs_b64 import GOLIATH_SPEC_64B

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "goliath"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Regenerate frames even if they exist")
    args = parser.parse_args()
    for spec in GOLIATH_SPEC_64B.states:
        state_dir = REDESIGN_DIR / spec.key
        source = state_dir / "_source.png"
        if not source.exists():
            print(f"[skip] {spec.key} (no _source.png)")
            continue
        # Skip if all 10 frames exist (unless --force)
        if not args.force and all(
            (state_dir / f"frame_{i:02d}.png").exists() for i in range(spec.frame_count)
        ):
            print(f"[skip] {spec.key} (all {spec.frame_count} frames exist)")
            continue
        gen = af.GENERATORS[spec.key]
        gen(source, state_dir)
        print(f"[anim] {spec.key} -> {spec.frame_count} frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
