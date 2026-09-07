"""Stage 1: Generate 5 AI bases for GOLIATH (BLOQUE 60).

For each state in GOLIATH_SPEC.states, call mcode-tools to produce a
1024x1024 PNG saved to Assets/sprites/bosses/goliath/_base/<state>_base.png.

Usage:
    python tools/redesign_bosses/01_generate_bases.py
    python tools/redesign_bosses/01_generate_bases.py --state idle
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_bosses._ai_client import generate_image
from tools.redesign_bosses._specs import GOLIATH_SPEC

BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "bosses" / "goliath" / "_base"


PROMPT_HEADER = (
    "16-bit pixel art, top-down 3/4 view, facing DOWNWARD (the character "
    "is at the top of the playfield looking down at the player), isolated "
    "on pure black background, single character, sharp clean pixel edges, "
    "no anti-aliasing, no gradients, limited palette (max 16 colors), "
    "Metal Slug aesthetic. Character: GOLIATH — biblical giant warrior in "
    "heavy BRONZE armor with helmet + visor, glowing RED EYES behind the "
    "slit, holding a long SPEAR in the right hand and a round SHIELD in "
    "the left. Heavy set, imposing. State: {state}. "
)


def build_prompt(state_key: str, prompt_fill: str) -> str:
    """Build the full mcode-tools prompt for a given state.

    Returns the prompt string. The header includes all shared
    visual rules; prompt_fill is the state-specific description.
    """
    return PROMPT_HEADER.format(state=state_key) + prompt_fill


def generate_one(state_key: str, prompt_fill: str, out_path: Path) -> Path:
    """Generate one AI base PNG. Skips if file already exists."""
    if out_path.exists():
        print(f"[skip] {out_path.name} (exists)")
        return out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(state_key, prompt_fill)
    print(f"[gen ] {out_path.name}  prompt_len={len(prompt)}")
    generate_image(prompt=prompt, out_path=out_path, width=1024, height=1024)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", help="Generate only this state key")
    args = parser.parse_args()
    targets = GOLIATH_SPEC.states
    if args.state:
        targets = [s for s in targets if s.key == args.state]
        if not targets:
            print(f"unknown state: {args.state}")
            return 1
    for spec in targets:
        out = BASE_DIR / spec.base_filename
        generate_one(spec.key, spec.prompt_fill, out)
    print(f"\nDone. {len(targets)} base(s) generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
