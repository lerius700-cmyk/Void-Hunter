"""Stage 1 (BLOQUE 64.B): Generate 6 borderless AI bases for GOLIATH.

For each state in GOLIATH_SPEC_64B.states, call mcode-tools to produce
a 1024x1024 PNG saved to Assets/sprites/bosses/goliath/_base/<state>_base.png.

The BLOQUE 64.B prompt is BORDERLESS with a TRANSPARENT BACKGROUND. The
postprocess step (02_postprocess_64b.py) crops, resizes to 96x80, runs
the damero transparentize fallback, and saves a clean transparent PNG.

Usage:
    python tools/redesign_bosses/01b_generate_bases_64b.py
    python tools/redesign_bosses/01b_generate_bases_64b.py --state phase1_idle
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_bosses._ai_client import generate_image
from tools.redesign_bosses._specs_b64 import GOLIATH_SPEC_64B

BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "bosses" / "goliath" / "_base"


# BLOQUE 64.B prompt header. BORDERLESS + TRANSPARENT. Locked palette.
PROMPT_HEADER = (
    "16-bit pixel art, top-down view (strictly perpendicular, no angled perspective), "
    "strictly BORDERLESS, isolated on TRANSPARENT BACKGROUND (no black square, "
    "no dark frame, no border, no background scenery, no margin), sharp "
    "clean pixel edges, no anti-aliasing, no gradients, limited palette "
    "(max 16 colors), warrior-biblical aesthetic, Star Fox 64 boss style.\n\n"
    "Character: GOLIATH — large armored biblical warrior boss, golden "
    "bronze armor with red and blue trim, twin yellow engines on back, "
    "6 hull panels with rivets, single cyclopean red eye, bipedal stance.\n\n"
    "Anim: {anim}\n\n"
    "Mandatory elements:\n"
    "- 96x80 native size, transparent background\n"
    "- All silhouette details visible at 32x24 downscale\n"
    "- Sharp pixel art edges\n"
    "- No anti-aliasing artifacts on the sprite boundary\n"
    "- Center the character in the 96x80 frame (margin = 0)\n\n"
    "LOCKED palette (use exact RGB values):\n"
    "  gold_armor:     (220, 180,  80)\n"
    "  bronze:         (160, 110,  50)\n"
    "  red_accent:     (200,  60,  40)\n"
    "  dark_blue:      ( 40,  50,  80)\n"
    "  eye_glow_red:   (255,  80,  40)\n"
    "  eye_trail:      (255, 140,  60)\n"
    "  hull_dark:      ( 60,  40,  20)\n"
    "  rivet:          (240, 200, 120)\n"
)


def build_prompt(state_key: str, prompt_fill: str) -> str:
    """Build the full mcode-tools prompt for a given state."""
    return PROMPT_HEADER.format(anim=prompt_fill) + "State: " + state_key


def generate_one(state_key: str, prompt_fill: str, out_path: Path, *, force: bool = False) -> Path:
    """Generate one AI base PNG. Skips if file already exists and not --force."""
    if out_path.exists() and not force:
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
    parser.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    args = parser.parse_args()
    targets = GOLIATH_SPEC_64B.states
    if args.state:
        targets = [s for s in targets if s.key == args.state]
        if not targets:
            print(f"unknown state: {args.state}")
            return 1
    for spec in targets:
        out = BASE_DIR / spec.base_filename
        generate_one(spec.key, spec.prompt_fill, out, force=args.force)
    print(f"\nDone. {len(targets)} base(s) generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
